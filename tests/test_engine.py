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
        return httpx.Response(
            200,
            json={
                "data": [],
                "applied_filters": {"phase": {"operator": "contains_any", "values": [2]}},
                "coverage": {"approved_profiles_considered": 7, "total_matches": 0},
                "warnings": [],
                "returned": 0,
                "applied_limit": 20,
                "has_more": False,
                "next_cursor": None,
                "schema_version": "1.0.0",
            },
        )

    client = EngineClient(settings(), transport=httpx.MockTransport(handler))
    result = await client.filter_trials(
        filters=TrialFilters(phase=PhaseFilter(values=[2])),
        sort=TrialSort(),
        limit=20,
        cursor=None,
    )
    assert result.coverage.total_matches == 0
