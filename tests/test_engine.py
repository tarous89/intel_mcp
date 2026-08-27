from __future__ import annotations

import httpx
import pytest

from intel_mcp.config import Settings
from intel_mcp.engine import EngineClient
from intel_mcp.models import PhaseFilter, TrialFilters, TrialSort


def settings() -> Settings:
    return Settings(
        app_control_url="https://intel.example.test",
        app_service_token="test-app-token",
        engine_api_url="https://engine.example.test",
        engine_service_token="test-engine-token",
        mcp_inbound_service_token="test-mcp-token",
        allowed_hosts=("localhost",),
        port=8000,
        request_timeout_seconds=1,
    )


@pytest.mark.anyio
async def test_engine_filter_is_service_authenticated_and_strict() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-engine-token"
        assert request.url.path == "/api/internal/mcp/filter-trials"
        assert b'"phase":{"operator":"contains_any","values":[2]}' in request.content
        assert b'"offset":100' in request.content
        return httpx.Response(
            200,
            json={
                "data": [],
                "counts": {"total_profiles": 7, "total_matches": 0, "returned": 0},
            },
        )

    client = EngineClient(settings(), transport=httpx.MockTransport(handler))
    result = await client.filter_trials(
        filters=TrialFilters(phase=PhaseFilter(values=[2])),
        sort=TrialSort(),
        limit=20,
        offset=100,
    )
    assert result.counts.total_matches == 0


@pytest.mark.anyio
async def test_engine_get_profiles_is_service_authenticated_and_preserves_partial_availability() -> None:
    trial_ids = ["2024-500002-00-00", "2024-500001-00-00"]

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-engine-token"
        assert request.url.path == "/api/internal/mcp/profiles"
        assert request.content == (
            b'{"trial_ids":["2024-500002-00-00","2024-500001-00-00"]}'
        )
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "eu_number": "2024-500001-00-00",
                        "profile_schema_version": "8.4.0",
                        "approved_at": "2026-08-27T12:00:00+00:00",
                        "profile": {"filtering_variables": {}, "classification_variables": {}},
                    }
                ],
                "unavailable_trial_ids": ["2024-500002-00-00"],
                "schema_version": "1.0.0",
            },
        )

    client = EngineClient(settings(), transport=httpx.MockTransport(handler))
    result = await client.get_profiles(trial_ids)
    assert [item.eu_number for item in result.data] == ["2024-500001-00-00"]
    assert result.unavailable_trial_ids == ["2024-500002-00-00"]
