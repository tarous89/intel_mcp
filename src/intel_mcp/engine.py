from __future__ import annotations

from dataclasses import dataclass

import httpx
from pydantic import ValidationError

from intel_mcp.config import Settings
from intel_mcp.models import EngineFilterResponse, TrialFilters, TrialSort


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
        cursor: str | None,
    ) -> EngineFilterResponse:
        self._settings.validate_engine()
        url = f"{self._settings.engine_api_url}/api/internal/mcp/filter-trials"
        payload = {
            "filters": filters.model_dump(mode="json", exclude_none=True),
            "sort": sort.model_dump(mode="json"),
            "limit": limit,
            "cursor": cursor,
        }
        try:
            async with httpx.AsyncClient(
                timeout=self._settings.request_timeout_seconds,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    url,
                    headers={"Authorization": f"Bearer {self._settings.engine_service_token}"},
                    json=payload,
                )
        except httpx.TimeoutException as error:
            raise EngineError("ENGINE_TIMEOUT", "The trial filter timed out; retry this call.", 504) from error
        except httpx.HTTPError as error:
            raise EngineError("ENGINE_UNAVAILABLE", "The trial data service is temporarily unavailable.", 503) from error

        if response.is_success:
            try:
                return EngineFilterResponse.model_validate(response.json())
            except (ValueError, ValidationError) as error:
                raise EngineError(
                    "ENGINE_INVALID_RESPONSE",
                    "The trial data service returned an invalid response.",
                    502,
                ) from error

        code = "TRIAL_FILTER_FAILED"
        message = "The trials could not be filtered."
        try:
            body = response.json()
            error_body = body.get("error") if isinstance(body, dict) else None
            if isinstance(error_body, dict):
                code = error_body.get("code", code)
                message = error_body.get("message", message)
        except ValueError:
            pass
        raise EngineError(str(code), str(message), response.status_code)
