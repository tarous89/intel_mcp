from __future__ import annotations

import httpx
import pytest

from intel_mcp.config import Settings
from intel_mcp.control_plane import ControlPlaneClient, ControlPlaneError
from intel_mcp.auth_context import reset_oauth_subject, set_oauth_subject


def settings() -> Settings:
    return Settings(
        app_control_url="https://intel.example.test",
        app_service_token="test-service-token",
        engine_api_url="https://engine.example.test",
        engine_service_token="test-engine-token",
        mcp_inbound_service_token="test-mcp-service-token",
        allowed_hosts=("localhost",),
        port=8000,
        request_timeout_seconds=1,
    )


@pytest.mark.anyio
async def test_start_analysis_parses_and_authenticates() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-service-token"
        assert request.url.path == "/api/internal/mcp/start-analysis"
        assert request.content == b'{"reportRunId":"run-123"}'
        return httpx.Response(
            200,
            json={
                "analysis": {
                    "analysisId": "ana_123456789012345678901234",
                    "reportRunId": "run-123",
                    "tier": "light",
                    "expiresAt": "2026-08-26T14:00:00Z",
                    "enabledTools": ["filter_trials", "get_profiles"],
                    "limits": {
                        "filteredTrialIds": 100,
                        "profiles": 50,
                        "classifiedTrials": 25,
                        "documentMetadata": 100,
                        "documentTextDocuments": 25,
                        "documentTextCharacters": 150000,
                        "extractionTrials": 20,
                        "extractionDocuments": 50,
                        "variables": 20,
                    },
                    "reused": False,
                }
            },
        )

    client = ControlPlaneClient(settings(), transport=httpx.MockTransport(handler))
    result = await client.start_analysis("run-123")
    assert result.analysis.analysis_id.startswith("ana_")
    assert result.analysis.limits.filtered_trial_ids == 100


@pytest.mark.anyio
async def test_oauth_subject_is_forwarded_to_control_plane() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/internal/mcp/filter-access"
        assert request.content == b'{"analysisId":"ana-1","trialIds":[],"oauthSubject":"user-123"}'
        return httpx.Response(200, json={"access": {"allowedTrialIds": [], "limit": 100, "used": 0, "remaining": 100, "exhausted": False}})

    context_token = set_oauth_subject("user-123")
    try:
        client = ControlPlaneClient(settings(), transport=httpx.MockTransport(handler))
        await client.authorize_filter_results("ana-1", [])
    finally:
        reset_oauth_subject(context_token)


@pytest.mark.anyio
async def test_oauth_introspection_does_not_forward_subject() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/internal/oauth/introspect"
        assert request.content == b'{"token":"public-token"}'
        return httpx.Response(200, json={"active": True, "sub": "user-123", "scope": "mcp:tools", "resource": "https://mcp.trialagents.com/mcp"})

    context_token = set_oauth_subject("should-not-leak")
    try:
        client = ControlPlaneClient(settings(), transport=httpx.MockTransport(handler))
        result = await client.introspect_access_token("public-token")
    finally:
        reset_oauth_subject(context_token)
    assert result["active"] is True


@pytest.mark.anyio
async def test_start_analysis_preserves_typed_allowance_error() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            402,
            json={"error": {"code": "ANALYSIS_ALLOWANCE_REQUIRED", "message": "No light allowance is available."}},
        )

    client = ControlPlaneClient(settings(), transport=httpx.MockTransport(handler))
    with pytest.raises(ControlPlaneError) as captured:
        await client.start_analysis("run-123")
    assert captured.value.code == "ANALYSIS_ALLOWANCE_REQUIRED"
    assert captured.value.status_code == 402


@pytest.mark.anyio
async def test_filter_access_is_authenticated_and_parsed() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-service-token"
        assert request.url.path == "/api/internal/mcp/filter-access"
        assert request.content == b'{"analysisId":"ana_123456789012345678901234","trialIds":["2024-500001-00-00"]}'
        return httpx.Response(
            200,
            json={
                "access": {
                    "allowedTrialIds": ["2024-500001-00-00"],
                    "limit": 100,
                    "used": 1,
                        "remaining": 99,
                        "exhausted": False,
                }
            },
        )

    client = ControlPlaneClient(settings(), transport=httpx.MockTransport(handler))
    result = await client.authorize_filter_results(
        "ana_123456789012345678901234", ["2024-500001-00-00"]
    )
    assert result.access.remaining == 99


@pytest.mark.anyio
async def test_profile_access_is_authenticated_and_parsed() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-service-token"
        assert request.url.path == "/api/internal/mcp/profile-access"
        assert request.content == b'{"analysisId":"ana_123456789012345678901234","trialIds":["2024-500001-00-00"]}'
        return httpx.Response(
            200,
            json={
                "access": {
                    "allowedTrialIds": ["2024-500001-00-00"],
                    "limit": 50,
                    "used": 1,
                    "remaining": 49,
                    "exhausted": False,
                }
            },
        )

    client = ControlPlaneClient(settings(), transport=httpx.MockTransport(handler))
    result = await client.authorize_profiles(
        "ana_123456789012345678901234", ["2024-500001-00-00"]
    )
    assert result.access.allowed_trial_ids == ["2024-500001-00-00"]
    assert result.access.remaining == 49


@pytest.mark.anyio
async def test_document_access_is_authenticated_and_parsed() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-service-token"
        assert request.url.path == "/api/internal/mcp/document-access"
        assert request.content == (
            b'{"analysisId":"ana_123456789012345678901234","documentKey":"'
            + b"a" * 64
            + b'"}'
        )
        return httpx.Response(
            200,
            json={
                "access": {
                    "documentKey": "a" * 64,
                    "limit": 10,
                    "used": 1,
                    "remaining": 9,
                    "exhausted": False,
                }
            },
        )

    client = ControlPlaneClient(settings(), transport=httpx.MockTransport(handler))
    result = await client.authorize_document(
        "ana_123456789012345678901234", "a" * 64
    )
    assert result.access.document_key == "a" * 64
    assert result.access.remaining == 9


@pytest.mark.anyio
async def test_extraction_access_is_authenticated_and_parsed() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-service-token"
        assert request.url.path == "/api/internal/mcp/extraction-access"
        assert request.content == (
            b'{"analysisId":"ana_123456789012345678901234","extractionKey":"'
            + b"a" * 64
            + b'","variableCount":2,"operation":"reserve"}'
        )
        return httpx.Response(
            200,
            json={
                "access": {
                    "extractionKey": "a" * 64,
                    "limit": 20,
                    "used": 0,
                        "remaining": 19,
                        "exhausted": False,
                        "workerModel": "gpt-5.6-luna",
                        "configVersion": 2,
                }
            },
        )

    client = ControlPlaneClient(settings(), transport=httpx.MockTransport(handler))
    result = await client.authorize_extraction(
        "ana_123456789012345678901234", "a" * 64, 2, "reserve"
    )
    assert result.access.extraction_key == "a" * 64
    assert result.access.remaining == 19
    assert result.access.worker_model == "gpt-5.6-luna"
