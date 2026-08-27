from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import httpx
from pydantic import ValidationError

from intel_mcp.classification import AppClassificationAccessResponse
from intel_mcp.config import Settings
from intel_mcp.documents import AppDocumentAccessResponse
from intel_mcp.extraction import AppExtractionAccessResponse
from intel_mcp.models import AppFilterAccessResponse, AppStartAnalysisResponse
from intel_mcp.profiles import AppProfileAccessResponse


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
        response = await self._post(url, {"reportRunId": report_run_id})
        if response.is_success:
            try:
                return AppStartAnalysisResponse.model_validate(response.json())
            except (ValueError, ValidationError) as error:
                raise ControlPlaneError(
                    "CONTROL_PLANE_INVALID_RESPONSE",
                    "The analysis control plane returned an invalid response.",
                    502,
                ) from error
        raise self._response_error(response, "ANALYSIS_START_FAILED", "The analysis could not be started.")

    async def authorize_filter_results(
        self, analysis_id: str, trial_ids: list[str]
    ) -> AppFilterAccessResponse:
        """Validate the lease and atomically meter newly returned trial IDs."""
        self._settings.validate_control_plane()
        url = f"{self._settings.app_control_url}/api/internal/mcp/filter-access"
        response = await self._post(url, {"analysisId": analysis_id, "trialIds": trial_ids})
        if response.is_success:
            try:
                return AppFilterAccessResponse.model_validate(response.json())
            except (ValueError, ValidationError) as error:
                raise ControlPlaneError(
                    "CONTROL_PLANE_INVALID_RESPONSE",
                    "The analysis control plane returned an invalid response.",
                    502,
                ) from error
        raise self._response_error(response, "FILTER_ACCESS_FAILED", "The filter request could not be authorized.")

    async def authorize_classifications(
        self,
        analysis_id: str,
        classification_keys: list[str],
        operation: Literal["reserve", "commit", "release"] = "reserve",
    ) -> AppClassificationAccessResponse:
        """Reserve, commit or release trial+criteria classification allowance.

        Exact retries reuse the same stable SHA-256 keys. Changed criteria create new keys.
        Reservations protect the allowance under concurrency; only successful Terra work is committed.
        """
        self._settings.validate_control_plane()
        url = f"{self._settings.app_control_url}/api/internal/mcp/classification-access"
        response = await self._post(
            url,
            {
                "analysisId": analysis_id,
                "classificationKeys": classification_keys,
                "operation": operation,
            },
        )
        if response.is_success:
            try:
                return AppClassificationAccessResponse.model_validate(response.json())
            except (ValueError, ValidationError) as error:
                raise ControlPlaneError(
                    "CONTROL_PLANE_INVALID_RESPONSE",
                    "The analysis control plane returned an invalid classification authorization response.",
                    502,
                ) from error
        raise self._response_error(
            response,
            "CLASSIFICATION_ACCESS_FAILED",
            "The classification request could not be authorized.",
        )

    async def authorize_profiles(
        self, analysis_id: str, trial_ids: list[str]
    ) -> AppProfileAccessResponse:
        """Validate the lease and atomically meter complete profiles returned."""
        self._settings.validate_control_plane()
        url = f"{self._settings.app_control_url}/api/internal/mcp/profile-access"
        response = await self._post(
            url,
            {"analysisId": analysis_id, "trialIds": trial_ids},
        )
        if response.is_success:
            try:
                return AppProfileAccessResponse.model_validate(response.json())
            except (ValueError, ValidationError) as error:
                raise ControlPlaneError(
                    "CONTROL_PLANE_INVALID_RESPONSE",
                    "The analysis control plane returned an invalid profile authorization response.",
                    502,
                ) from error
        raise self._response_error(
            response,
            "PROFILE_ACCESS_FAILED",
            "The profile request could not be authorized.",
        )

    async def authorize_document(
        self, analysis_id: str, document_key: str
    ) -> AppDocumentAccessResponse:
        """Validate the lease and atomically meter one unique extracted document."""
        self._settings.validate_control_plane()
        url = f"{self._settings.app_control_url}/api/internal/mcp/document-access"
        response = await self._post(
            url,
            {"analysisId": analysis_id, "documentKey": document_key},
        )
        if response.is_success:
            try:
                return AppDocumentAccessResponse.model_validate(response.json())
            except (ValueError, ValidationError) as error:
                raise ControlPlaneError(
                    "CONTROL_PLANE_INVALID_RESPONSE",
                    "The analysis control plane returned an invalid document authorization response.",
                    502,
                ) from error
        raise self._response_error(
            response,
            "DOCUMENT_ACCESS_FAILED",
            "The document request could not be authorized.",
        )

    async def authorize_extraction(
        self,
        analysis_id: str,
        extraction_key: str,
        variable_count: int,
        operation: Literal["reserve", "commit", "release"] = "reserve",
    ) -> AppExtractionAccessResponse:
        """Reserve, commit or release one trial+variables extraction unit."""
        self._settings.validate_control_plane()
        url = f"{self._settings.app_control_url}/api/internal/mcp/extraction-access"
        response = await self._post(
            url,
            {
                "analysisId": analysis_id,
                "extractionKey": extraction_key,
                "variableCount": variable_count,
                "operation": operation,
            },
        )
        if response.is_success:
            try:
                return AppExtractionAccessResponse.model_validate(response.json())
            except (ValueError, ValidationError) as error:
                raise ControlPlaneError(
                    "CONTROL_PLANE_INVALID_RESPONSE",
                    "The analysis control plane returned an invalid extraction authorization response.",
                    502,
                ) from error
        raise self._response_error(
            response,
            "EXTRACTION_ACCESS_FAILED",
            "The extraction request could not be authorized.",
        )

    async def _post(self, url: str, payload: dict) -> httpx.Response:
        try:
            async with httpx.AsyncClient(
                timeout=self._settings.request_timeout_seconds,
                transport=self._transport,
            ) as client:
                return await client.post(
                    url,
                    headers={"Authorization": f"Bearer {self._settings.app_service_token}"},
                    json=payload,
                )
        except httpx.TimeoutException as error:
            raise ControlPlaneError(
                "CONTROL_PLANE_TIMEOUT",
                "The analysis control plane timed out; retry this call.",
                504,
            ) from error
        except httpx.HTTPError as error:
            raise ControlPlaneError(
                "CONTROL_PLANE_UNAVAILABLE",
                "The analysis control plane is temporarily unavailable.",
                503,
            ) from error

    @staticmethod
    def _response_error(response: httpx.Response, default_code: str, default_message: str) -> ControlPlaneError:
        code = default_code
        message = default_message
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
        return ControlPlaneError(code, message, response.status_code)
