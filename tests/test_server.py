from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import httpx
import pytest
from mcp import Client
from starlette.responses import Response

from intel_mcp.models import (
    AppAnalysis,
    AppAnalysisLimits,
    AppFilterAccess,
    AppFilterAccessResponse,
    AppStartAnalysisResponse,
    EngineFilterResponse,
    FilterCoverage,
    FilterTrialItem,
)
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

    async def authorize_filter_results(
        self, analysis_id: str, trial_ids: list[str]
    ) -> AppFilterAccessResponse:
        assert analysis_id == "ana_123456789012345678901234"
        return AppFilterAccessResponse(
            access=AppFilterAccess(
                allowed_trial_ids=trial_ids,
                limit=1000,
                used=len(trial_ids),
                remaining=1000 - len(trial_ids),
                exhausted=False,
            )
        )


class StubEngine:
    async def filter_trials(self, **_kwargs) -> EngineFilterResponse:
        return EngineFilterResponse(
            data=[
                FilterTrialItem(
                    eu_number="2024-500001-00-00",
                    trial_title="Phase 2 head and neck study",
                    sponsor_name="Example Sponsor",
                    phase=[2],
                    latest_country_submission_or_approval_date="2026-08-01",
                    available_extracted_document_types=["protocol"],
                    available_extracted_document_names=["Protocol v2"],
                )
            ],
            applied_filters={"phase": {"operator": "contains_any", "values": [2]}},
            coverage=FilterCoverage(approved_profiles_considered=7, total_matches=1),
            warnings=[],
            returned=1,
            applied_limit=20,
            has_more=False,
            next_cursor=None,
            schema_version="1.0.0",
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
async def test_filter_trials_exposes_only_structured_filters(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("intel_mcp.server.control_plane_client", lambda: StubControlPlane())
    monkeypatch.setattr("intel_mcp.server.engine_client", lambda: StubEngine())
    async with Client(mcp) as client:
        tools = await client.list_tools()
        tool = next(item for item in tools.tools if item.name == "filter_trials")
        schema_text = str(tool.input_schema)
        assert "profile_contains" not in schema_text
        assert "sponsor_name" in schema_text
        assert tool.annotations is not None
        assert tool.annotations.read_only_hint is True

        result = await client.call_tool(
            "filter_trials",
            {
                "analysis_id": "ana_123456789012345678901234",
                "filters": {"phase": {"operator": "contains_any", "values": [2]}},
            },
        )
        assert result.is_error is False
        assert result.structured_content is not None
        assert result.structured_content["returned"] == 1
        assert result.structured_content["data"][0]["eu_number"] == "2024-500001-00-00"


def test_controlled_filter_values_accept_any_case_and_normalize() -> None:
    from intel_mcp.models import TrialFilters

    filters = TrialFilters.model_validate(
        {
            "therapeutic_areas": {"values": ["solid tumor oncology"]},
            "countries": [
                {
                    "country_codes": {"values": ["de"]},
                    "recruitment_statuses": {"values": ["authorised"]},
                }
            ],
        }
    )
    assert filters.therapeutic_areas is not None
    assert filters.therapeutic_areas.values == ["Solid Tumor Oncology"]
    assert filters.countries[0].country_codes is not None
    assert filters.countries[0].country_codes.values == ["DE"]
    assert filters.countries[0].recruitment_statuses is not None
    assert filters.countries[0].recruitment_statuses.values == ["Authorised"]


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
