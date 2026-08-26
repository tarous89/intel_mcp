from __future__ import annotations

from dataclasses import dataclass

import httpx
from pydantic import ValidationError

from intel_mcp.config import Settings
from intel_mcp.models import AppStartAnalysisResponse


@dataclass(frozen=True)
class ControlPlaneError(Exception):
    code: str
    message: str
    status_code: int


class ControlPlaneClient:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._settings = settings
        self._transport = transport

    async def start_analysis(self, report_run_id: str) -> AppStartAnalysisResponse:
        self._settings.validate_control_plane()
        url = f"{self._settings.app_control_url}/api/internal/mcp/start-analysis"
        try:
            async with httpx.AsyncClient(
                timeout=self._settings.request_timeout_seconds,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    url,
                    headers={"Authorization": f"Bearer {self._settings.app_service_token}"},
                    json={"reportRunId": report_run_id},
                )
        except httpx.TimeoutException as error:
            raise ControlPlaneError("CONTROL_PLANE_TIMEOUT", "The analysis control plane timed out; retry this call.", 504) from error
        except httpx.HTTPError as error:
            raise ControlPlaneError("CONTROL_PLANE_UNAVAILABLE", "The analysis control plane is temporarily unavailable.", 503) from error

        if response.is_success:
            try:
                return AppStartAnalysisResponse.model_validate(response.json())
            except (ValueError, ValidationError) as error:
                raise ControlPlaneError(
                    "CONTROL_PLANE_INVALID_RESPONSE",
                    "The analysis control plane returned an invalid response.",
                    502,
                ) from error

        code = "ANALYSIS_START_FAILED"
        message = "The analysis could not be started."
        try:
            body = response.json()
            error_body = body.get("error") if isinstance(body, dict) else None
            if isinstance(error_body, dict):
                if isinstance(error_body.get("code"), str):
                    code = error_body["code"]
                if isinstance(error_body.get("message"), str):
                    message = error_body["message"]
        except ValueError:
            pass
        raise ControlPlaneError(code, message, response.status_code)
