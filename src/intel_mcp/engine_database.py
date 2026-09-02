from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable
from typing import Any

import psycopg
from psycopg.conninfo import make_conninfo
from psycopg_pool import ConnectionPool, PoolTimeout
from pydantic import ValidationError

from intel_mcp.classification import EngineClassificationProfilesResponse
from intel_mcp.config import Settings
from intel_mcp.documents import EngineDocumentResponse
from intel_mcp.engine import EngineError
from intel_mcp.engine_read.classification_profiles import (
    ClassificationProfileRequestError,
    get_approved_classification_profiles,
)
from intel_mcp.engine_read.document_retrieval import (
    DocumentRetrievalRequestError,
    get_approved_document_text,
)
from intel_mcp.engine_read.extraction_source import (
    ExtractionSourceRequestError,
    get_approved_extraction_source,
)
from intel_mcp.engine_read.filtering import FilterRequestError, filter_approved_trials
from intel_mcp.engine_read.profile_retrieval import (
    ProfileRetrievalRequestError,
    get_approved_profiles,
)
from intel_mcp.extraction import EngineExtractionSourceResponse
from intel_mcp.models import EngineFilterResponse, TrialFilters, TrialSort
from intel_mcp.profiles import EngineProfilesResponse


ReadFunction = Callable[[psycopg.Connection[Any], dict[str, Any]], dict[str, Any]]
class DatabaseEngineClient:
    """Run the five MCP reads locally against Engine-owned serving views.

    The configured login is constrained twice: the Engine migration grants it
    SELECT only on ``mcp_serving`` views, and each checkout transaction is
    explicitly marked read-only.  Synchronous psycopg work runs in a worker
    thread so slow database I/O never blocks the MCP event loop.
    """

    def __init__(
        self,
        settings: Settings,
        *,
        pool: ConnectionPool[Any] | None = None,
    ) -> None:
        self._settings = settings
        self._pool = pool
        self._pool_lock = threading.Lock()

    def _get_pool(self) -> ConnectionPool[Any]:
        if self._pool is not None:
            return self._pool
        with self._pool_lock:
            if self._pool is None:
                dsn = make_conninfo(
                    self._settings.engine_database_dsn(),
                    application_name="intel-mcp-read-v1",
                )
                pool = ConnectionPool(
                    conninfo=dsn,
                    min_size=0,
                    max_size=self._settings.engine_database_pool_size,
                    timeout=self._settings.request_timeout_seconds,
                    max_lifetime=1_800,
                    max_idle=300,
                    kwargs={"autocommit": True},
                    open=False,
                )
                pool.open(wait=True, timeout=self._settings.request_timeout_seconds)
                self._pool = pool
        return self._pool

    def _execute(self, function: ReadFunction, request: dict[str, Any]) -> dict[str, Any]:
        pool = self._get_pool()
        with pool.connection(timeout=self._settings.request_timeout_seconds) as connection:
            with connection.transaction():
                connection.execute("SET TRANSACTION READ ONLY")
                return function(connection, request)

    async def _read(self, function: ReadFunction, request: dict[str, Any]) -> dict[str, Any]:
        try:
            self._settings.validate_engine()
            return await asyncio.to_thread(self._execute, function, request)
        except (
            FilterRequestError,
            ClassificationProfileRequestError,
            ProfileRetrievalRequestError,
            DocumentRetrievalRequestError,
            ExtractionSourceRequestError,
        ) as error:
            raise EngineError(error.code, error.message, error.status_code) from error
        except PoolTimeout as error:
            raise EngineError(
                "ENGINE_TIMEOUT",
                "The trial data store is busy; retry this call.",
                504,
            ) from error
        except (psycopg.Error, RuntimeError, ValueError) as error:
            raise EngineError(
                "ENGINE_UNAVAILABLE",
                "The trial data store is temporarily unavailable.",
                503,
            ) from error

    async def filter_trials(
        self,
        *,
        filters: TrialFilters,
        sort: TrialSort,
        limit: int,
        offset: int,
    ) -> EngineFilterResponse:
        payload = {
            "filters": filters.model_dump(mode="json", exclude_none=True),
            "sort": sort.model_dump(mode="json"),
            "limit": limit,
            "offset": offset,
        }
        result = await self._read(filter_approved_trials, payload)
        try:
            return EngineFilterResponse.model_validate(result)
        except ValidationError as error:
            raise EngineError(
                "ENGINE_INVALID_RESPONSE",
                "The trial data store returned an invalid response.",
                502,
            ) from error

    async def classification_profiles(
        self, trial_ids: list[str]
    ) -> EngineClassificationProfilesResponse:
        result = await self._read(
            get_approved_classification_profiles,
            {"trial_ids": trial_ids},
        )
        try:
            parsed = EngineClassificationProfilesResponse.model_validate(result)
        except ValidationError as error:
            raise EngineError(
                "ENGINE_INVALID_RESPONSE",
                "The trial data store returned invalid classification profiles.",
                502,
            ) from error
        if [item.eu_number for item in parsed.data] != trial_ids:
            raise EngineError(
                "ENGINE_INVALID_RESPONSE",
                "The trial data store returned misaligned classification profiles.",
                502,
            )
        return parsed

    async def get_profiles(self, trial_ids: list[str]) -> EngineProfilesResponse:
        result = await self._read(get_approved_profiles, {"trial_ids": trial_ids})
        try:
            parsed = EngineProfilesResponse.model_validate(result)
        except ValidationError as error:
            raise EngineError(
                "ENGINE_INVALID_RESPONSE",
                "The trial data store returned invalid Trial Profiles.",
                502,
            ) from error

        unavailable = set(parsed.unavailable_trial_ids)
        returned_ids = [item.eu_number for item in parsed.data]
        expected_returned = [trial_id for trial_id in trial_ids if trial_id not in unavailable]
        if (
            returned_ids != expected_returned
            or parsed.unavailable_trial_ids
            != [trial_id for trial_id in trial_ids if trial_id in unavailable]
            or len(unavailable) != len(parsed.unavailable_trial_ids)
            or set(returned_ids) & unavailable
            or set(returned_ids) | unavailable != set(trial_ids)
        ):
            raise EngineError(
                "ENGINE_INVALID_RESPONSE",
                "The trial data store returned misaligned Trial Profiles.",
                502,
            )
        return parsed

    async def get_document(
        self,
        *,
        trial_id: str,
        document_name: str,
        part: int,
    ) -> EngineDocumentResponse:
        result = await self._read(
            get_approved_document_text,
            {
                "trial_id": trial_id,
                "document_name": document_name,
                "part": part,
            },
        )
        try:
            return EngineDocumentResponse.model_validate(result)
        except ValidationError as error:
            raise EngineError(
                "ENGINE_INVALID_RESPONSE",
                "The trial data store returned invalid document text.",
                502,
            ) from error

    async def extraction_source(
        self, trial_id: str
    ) -> EngineExtractionSourceResponse:
        result = await self._read(
            get_approved_extraction_source,
            {"trial_id": trial_id},
        )
        try:
            parsed = EngineExtractionSourceResponse.model_validate(result)
        except ValidationError as error:
            raise EngineError(
                "ENGINE_INVALID_RESPONSE",
                "The trial data store returned an invalid extraction source.",
                502,
            ) from error
        if parsed.trial_id != trial_id:
            raise EngineError(
                "ENGINE_INVALID_RESPONSE",
                "The trial data store returned a misaligned extraction source.",
                502,
            )
        return parsed

    async def healthcheck(self) -> None:
        def check(connection: psycopg.Connection[Any], _request: dict[str, Any]) -> dict[str, Any]:
            connection.execute("SELECT 1 FROM mcp_serving.profile_filter_v1 LIMIT 0")
            return {}

        await self._read(check, {})

    def close(self) -> None:
        if self._pool is not None:
            self._pool.close()
