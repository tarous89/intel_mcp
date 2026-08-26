from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import httpx
import pytest
from mcp import Client
from starlette.responses import Response

from intel_mcp.models import AppAnalysis, AppAnalysisLimits, AppStartAnalysisResponse
from intel_mcp.server import MCPServiceAuthMiddleware, app, mcp, settings


class StubControlPlane:
    async def start_analysis(self, report_run_id: str) -> AppStartAnalysisResponse:
        return AppStartAnalysisResponse(
            analysis=AppAnalysis(
                analysis_id="ana_123456789012345678901234",
                report_run_id=report_run_id,
                tier="max",
                expires_at=datetime(2026, 8, 26, 14, 0, tzinfo=UTC),
                enabled_tools=["filter_trials", "classify_trials", "get_profiles", "get_documents", "extract_variables"],
                limits=AppAnalysisLimits(
                    filtered_trial_ids=1000,
                    profiles=500,
                    classified_trials=200,
                    document_metadata=1000,
                    document_text_documents=200,
                    document_text_characters=150000,
                    extraction_trials=200,
                    extraction_documents=500,
                    variables=50,
                ),
                reused=False,
            )
        )


@pytest.mark.anyio
async def test_start_analysis_tool_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("intel_mcp.server.control_plane_client", lambda: StubControlPlane())
    async with Client(mcp) as client:
        tools = await client.list_tools()
        tool = next(item for item in tools.tools if item.name == "start_analysis")
        assert tool.annotations is not None
        assert tool.annotations.read_only_hint is False
        assert tool.annotations.destructive_hint is False
        assert tool.annotations.idempotent_hint is True

        result = await client.call_tool("start_analysis", {"report_run_id": "run-123"})
        assert result.is_error is False
        assert result.structured_content is not None
        assert result.structured_content["analysis_id"].startswith("ana_")
        assert result.structured_content["report_run_id"] == "run-123"


@pytest.mark.anyio
async def test_mcp_http_requires_service_bearer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("intel_mcp.server.settings", replace(settings, mcp_inbound_service_token="expected-token"))

    async def accepted(scope, receive, send) -> None:
        await Response(status_code=204)(scope, receive, send)

    transport = httpx.ASGITransport(app=MCPServiceAuthMiddleware(accepted))
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
        unauthenticated = await client.post("/mcp")
        invalid = await client.post("/mcp", headers={"Authorization": "Bearer wrong-token"})
        authorized = await client.post("/mcp", headers={"Authorization": "Bearer expected-token"})

    assert unauthenticated.status_code == 401
    assert unauthenticated.headers["www-authenticate"] == "Bearer"
    assert invalid.status_code == 401
    assert authorized.status_code == 204


@pytest.mark.anyio
async def test_health_remains_public() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "intel-mcp"}
