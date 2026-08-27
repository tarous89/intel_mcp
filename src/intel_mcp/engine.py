from __future__ import annotations

from dataclasses import dataclass

import httpx
from pydantic import ValidationError

from intel_mcp.classification import EngineClassificationProfilesResponse
from intel_mcp.config import Settings
from intel_mcp.documents import EngineDocumentResponse
from intel_mcp.extraction import EngineExtractionSourceResponse
from intel_mcp.models import EngineFilterResponse, TrialFilters, TrialSort
from intel_mcp.profiles import EngineProfilesResponse


@dataclass(frozen=True)
class EngineError(Exception):
    code: str
    message: str
    status_code: int


class EngineClient:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._settings = settings
        self._transport = transport

    async def filter_trials(
        self,
        *,
        filters: TrialFilters,
        sort: TrialSort,
        limit: int,
        offset: int,
    ) -> EngineFilterResponse:
        self._settings.validate_engine()
        url = f"{self._settings.engine_api_url}/api/internal/mcp/filter-trials"
        payload = {
            "filters": filters.model_dump(mode="json", exclude_none=True),
            "sort": sort.model_dump(mode="json"),
            "limit": limit,
            "offset": offset,
        }
        response = await self._post(url, payload, timeout_message="The trial filter timed out; retry this call.")

        if response.is_success:
            try:
                return EngineFilterResponse.model_validate(response.json())
            except (ValueError, ValidationError) as error:
                raise EngineError(
                    "ENGINE_INVALID_RESPONSE",
                    "The trial data service returned an invalid response.",
                    502,
                ) from error

        raise self._response_error(response, "TRIAL_FILTER_FAILED", "The trials could not be filtered.")

    async def classification_profiles(self, trial_ids: list[str]) -> EngineClassificationProfilesResponse:
        self._settings.validate_engine()
        url = f"{self._settings.engine_api_url}/api/internal/mcp/classification-profiles"
        response = await self._post(
            url,
            {"trial_ids": trial_ids},
            timeout_message="The approved Trial Profiles could not be retrieved in time; retry this call.",
        )
        if response.is_success:
            try:
                result = EngineClassificationProfilesResponse.model_validate(response.json())
            except (ValueError, ValidationError) as error:
                raise EngineError(
                    "ENGINE_INVALID_RESPONSE",
                    "The trial data service returned invalid classification profiles.",
                    502,
                ) from error
            if [item.eu_number for item in result.data] != trial_ids:
                raise EngineError(
                    "ENGINE_INVALID_RESPONSE",
                    "The trial data service returned misaligned classification profiles.",
                    502,
                )
            return result

        raise self._response_error(
            response,
            "CLASSIFICATION_PROFILES_FAILED",
            "The approved Trial Profiles could not be retrieved for classification.",
        )

    async def get_profiles(self, trial_ids: list[str]) -> EngineProfilesResponse:
        self._settings.validate_engine()
        url = f"{self._settings.engine_api_url}/api/internal/mcp/profiles"
        response = await self._post(
            url,
            {"trial_ids": trial_ids},
            timeout_message="The approved Trial Profiles could not be retrieved in time; retry this call.",
        )
        if response.is_success:
            try:
                result = EngineProfilesResponse.model_validate(response.json())
            except (ValueError, ValidationError) as error:
                raise EngineError(
                    "ENGINE_INVALID_RESPONSE",
                    "The trial data service returned invalid Trial Profiles.",
                    502,
                ) from error

            unavailable = set(result.unavailable_trial_ids)
            returned_ids = [item.eu_number for item in result.data]
            expected_returned = [trial_id for trial_id in trial_ids if trial_id not in unavailable]
            if (
                returned_ids != expected_returned
                or result.unavailable_trial_ids != [trial_id for trial_id in trial_ids if trial_id in unavailable]
                or len(unavailable) != len(result.unavailable_trial_ids)
                or set(returned_ids) & unavailable
                or set(returned_ids) | unavailable != set(trial_ids)
            ):
                raise EngineError(
                    "ENGINE_INVALID_RESPONSE",
                    "The trial data service returned misaligned Trial Profiles.",
                    502,
                )
            return result

        raise self._response_error(
            response,
            "PROFILE_RETRIEVAL_FAILED",
            "The approved Trial Profiles could not be retrieved.",
        )

    async def get_document(
        self,
        *,
        trial_id: str,
        document_name: str,
        part: int,
    ) -> EngineDocumentResponse:
        self._settings.validate_engine()
        url = f"{self._settings.engine_api_url}/api/internal/mcp/documents"
        response = await self._post(
            url,
            {
                "trial_id": trial_id,
                "document_name": document_name,
                "part": part,
            },
            timeout_message="The extracted document text could not be retrieved in time; retry this call.",
        )
        if response.is_success:
            try:
                return EngineDocumentResponse.model_validate(response.json())
            except (ValueError, ValidationError) as error:
                raise EngineError(
                    "ENGINE_INVALID_RESPONSE",
                    "The trial data service returned invalid document text.",
                    502,
                ) from error
        raise self._response_error(
            response,
            "DOCUMENT_RETRIEVAL_FAILED",
            "The extracted document text could not be retrieved.",
        )

    async def extraction_source(self, trial_id: str) -> EngineExtractionSourceResponse:
        self._settings.validate_engine()
        url = f"{self._settings.engine_api_url}/api/internal/mcp/extraction-source"
        response = await self._post(
            url,
            {"trial_id": trial_id},
            timeout_message="The approved extraction source could not be retrieved in time; retry this call.",
        )
        if response.is_success:
            try:
                result = EngineExtractionSourceResponse.model_validate(response.json())
            except (ValueError, ValidationError) as error:
                raise EngineError(
                    "ENGINE_INVALID_RESPONSE",
                    "The trial data service returned an invalid extraction source.",
                    502,
                ) from error
            if result.trial_id != trial_id:
                raise EngineError(
                    "ENGINE_INVALID_RESPONSE",
                    "The trial data service returned a misaligned extraction source.",
                    502,
                )
            return result
        raise self._response_error(
            response,
            "EXTRACTION_SOURCE_FAILED",
            "The approved extraction source could not be retrieved.",
        )

    async def _post(self, url: str, payload: dict, *, timeout_message: str) -> httpx.Response:
        try:
            async with httpx.AsyncClient(
                timeout=self._settings.request_timeout_seconds,
                transport=self._transport,
            ) as client:
                return await client.post(
                    url,
                    headers={"Authorization": f"Bearer {self._settings.engine_service_token}"},
                    json=payload,
                )
        except httpx.TimeoutException as error:
            raise EngineError("ENGINE_TIMEOUT", timeout_message, 504) from error
        except httpx.HTTPError as error:
            raise EngineError("ENGINE_UNAVAILABLE", "The trial data service is temporarily unavailable.", 503) from error

    @staticmethod
    def _response_error(response: httpx.Response, default_code: str, default_message: str) -> EngineError:
        code = default_code
        message = default_message
        try:
            body = response.json()
            error_body = body.get("error") if isinstance(body, dict) else None
            if isinstance(error_body, dict):
                code = error_body.get("code", code)
                message = error_body.get("message", message)
        except ValueError:
            pass
        return EngineError(str(code), str(message), response.status_code)
