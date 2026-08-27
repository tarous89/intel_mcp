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
    FilterCounts,
    FilterTrialItem,
)
from intel_mcp.documents import (
    AppDocumentAccess,
    AppDocumentAccessResponse,
    EngineDocumentResponse,
)
from intel_mcp.extraction import (
    AppExtractionAccess,
    AppExtractionAccessResponse,
    EngineExtractionSourceResponse,
)
from intel_mcp.profiles import (
    AppProfileAccess,
    AppProfileAccessResponse,
    EngineProfilesResponse,
    FullProfileItem,
)
from intel_mcp.server import MCPServiceAuthMiddleware, app, mcp, settings


class StubControlPlane:
    def __init__(self) -> None:
        self.extraction_operations: list[str] = []

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
                    document_text_documents=50,
                    document_text_characters=200000,
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

    async def authorize_profiles(
        self, analysis_id: str, trial_ids: list[str]
    ) -> AppProfileAccessResponse:
        assert analysis_id == "ana_123456789012345678901234"
        return AppProfileAccessResponse(
            access=AppProfileAccess(
                allowed_trial_ids=trial_ids,
                limit=500,
                used=len(trial_ids),
                remaining=500 - len(trial_ids),
                exhausted=False,
            )
        )

    async def authorize_document(
        self, analysis_id: str, document_key: str
    ) -> AppDocumentAccessResponse:
        assert analysis_id == "ana_123456789012345678901234"
        return AppDocumentAccessResponse(
            access=AppDocumentAccess(
                document_key=document_key,
                limit=50,
                used=1,
                remaining=49,
                exhausted=False,
            )
        )

    async def authorize_extraction(
        self,
        analysis_id: str,
        extraction_key: str,
        variable_count: int,
        operation: str = "reserve",
    ) -> AppExtractionAccessResponse:
        assert analysis_id == "ana_123456789012345678901234"
        assert variable_count == 2
        self.extraction_operations.append(operation)
        return AppExtractionAccessResponse(
            access=AppExtractionAccess(
                extractionKey=extraction_key,
                limit=200,
                used=1 if operation == "commit" else 0,
                remaining=199,
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
                    available_extracted_document_names=["Protocol v2"],
                )
            ],
            counts=FilterCounts(total_profiles=7, total_matches=1, returned=1),
        )

    async def get_profiles(self, trial_ids: list[str]) -> EngineProfilesResponse:
        unavailable = [trial_id for trial_id in trial_ids if trial_id.endswith("02-00-00")]
        return EngineProfilesResponse(
            data=[
                FullProfileItem(
                    eu_number=trial_id,
                    profile_schema_version="8.4.0",
                    approved_at="2026-08-27T12:00:00+00:00",
                    profile={
                        "filtering_variables": {"phase": [2]},
                        "classification_variables": {"trial_title": f"Full {trial_id}"},
                    },
                )
                for trial_id in trial_ids
                if trial_id not in unavailable
            ],
            unavailable_trial_ids=unavailable,
            schema_version="1.0.0",
        )

    async def get_document(self, **kwargs) -> EngineDocumentResponse:
        assert kwargs == {
            "trial_id": "2024-500001-00-00",
            "document_name": "Protocol v2",
            "part": 1,
        }
        return EngineDocumentResponse(
            trial_id="2024-500001-00-00",
            document_name="Protocol v2",
            document_type="protocol",
            part=1,
            text="[[PAGE 1]]\nExtracted text",
            next_part=2,
            document_access_key="a" * 64,
            schema_version="1.0.0",
        )

    async def extraction_source(self, trial_id: str) -> EngineExtractionSourceResponse:
        assert trial_id == "2024-500001-00-00"
        return EngineExtractionSourceResponse(
            trial_id=trial_id,
            profile={"planned_sample_size": 420},
            protocol_text="Complete protocol",
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
        assert "offset" in tool.input_schema["properties"]
        assert "cursor" not in tool.input_schema["properties"]
        assert tool.annotations is not None
        assert "first screening step" in (tool.description or "").lower()
        assert "classify_trials" in (tool.description or "")
        # The Engine query is read-only, but admission persists observable allowance usage.
        assert tool.annotations.read_only_hint is False

        result = await client.call_tool(
            "filter_trials",
            {
                "analysis_id": "ana_123456789012345678901234",
                "filters": {"phase": {"operator": "contains_any", "values": [2]}},
            },
        )
        assert result.is_error is False
        assert result.structured_content is not None
        assert set(result.structured_content) == {"data", "counts", "analysis_allowance"}
        assert result.structured_content["data"][0] == {
            "eu_number": "2024-500001-00-00",
            "trial_title": "Phase 2 head and neck study",
            "sponsor_name": "Example Sponsor",
            "available_extracted_document_names": ["Protocol v2"],
        }
        assert result.structured_content["counts"] == {
            "total_profiles": 7,
            "total_matches": 1,
            "returned": 1,
        }
        assert result.structured_content["analysis_allowance"] == {
            "limit": 1000,
            "used": 1,
            "remaining": 999,
        }


@pytest.mark.anyio
async def test_get_profiles_has_only_two_inputs_and_returns_complete_profiles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("intel_mcp.server.control_plane_client", lambda: StubControlPlane())
    monkeypatch.setattr("intel_mcp.server.engine_client", lambda: StubEngine())
    async with Client(mcp) as client:
        tools = await client.list_tools()
        tool = next(item for item in tools.tools if item.name == "get_profiles")
        assert set(tool.input_schema["properties"]) == {"analysis_id", "trial_ids"}
        assert tool.annotations is not None
        assert tool.annotations.read_only_hint is False
        assert tool.annotations.destructive_hint is False
        assert tool.annotations.idempotent_hint is True

        result = await client.call_tool(
            "get_profiles",
            {
                "analysis_id": "ana_123456789012345678901234",
                "trial_ids": [
                    "2024-500001-00-00",
                    "2024-500002-00-00",
                    "2024-500001-00-00",
                ],
            },
        )

    assert result.is_error is False
    assert result.structured_content is not None
    assert set(result.structured_content) == {
        "profiles",
        "unavailable_trial_ids",
        "allowance_reached_trial_ids",
        "counts",
        "analysis_allowance",
    }
    assert result.structured_content["profiles"][0]["profile"] == {
        "filtering_variables": {"phase": [2]},
        "classification_variables": {"trial_title": "Full 2024-500001-00-00"},
    }
    assert result.structured_content["unavailable_trial_ids"] == ["2024-500002-00-00"]
    assert result.structured_content["allowance_reached_trial_ids"] == []
    assert result.structured_content["counts"] == {
        "requested": 2,
        "returned": 1,
        "unavailable": 1,
        "allowance_reached": 0,
    }
    assert result.structured_content["analysis_allowance"] == {
        "limit": 500,
        "used": 1,
        "remaining": 499,
    }


@pytest.mark.anyio
async def test_get_documents_returns_one_text_document_part(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("intel_mcp.server.control_plane_client", lambda: StubControlPlane())
    monkeypatch.setattr("intel_mcp.server.engine_client", lambda: StubEngine())
    async with Client(mcp) as client:
        tools = await client.list_tools()
        tool = next(item for item in tools.tools if item.name == "get_documents")
        assert set(tool.input_schema["properties"]) == {
            "analysis_id",
            "trial_id",
            "document_name",
            "part",
        }
        assert tool.input_schema["properties"]["part"]["default"] == 1
        assert tool.annotations is not None
        assert tool.annotations.read_only_hint is False
        assert tool.annotations.destructive_hint is False
        assert tool.annotations.idempotent_hint is True

        result = await client.call_tool(
            "get_documents",
            {
                "analysis_id": "ana_123456789012345678901234",
                "trial_id": "2024-500001-00-00",
                "document_name": "Protocol v2",
            },
        )

    assert result.is_error is False
    assert result.structured_content == {
        "trial_id": "2024-500001-00-00",
        "document_name": "Protocol v2",
        "document_type": "protocol",
        "part": 1,
        "text": "[[PAGE 1]]\nExtracted text",
        "next_part": 2,
        "analysis_allowance": {"limit": 50, "used": 1, "remaining": 49},
    }


@pytest.mark.anyio
async def test_extract_variables_uses_one_trial_and_returns_values_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    control = StubControlPlane()
    monkeypatch.setattr("intel_mcp.server.control_plane_client", lambda: control)
    monkeypatch.setattr("intel_mcp.server.engine_client", lambda: StubEngine())

    class StubExtractor:
        def __init__(self, _settings) -> None:
            pass

        async def extract(self, **kwargs):
            assert kwargs["trial_id"] == "2024-500001-00-00"
            assert kwargs["profile"] == {"planned_sample_size": 420}
            assert kwargs["protocol_text"] == "Complete protocol"
            assert len(kwargs["variables"]) == 2
            return {
                "planned_sample_size": 420,
                "central_imaging_review": None,
            }

    monkeypatch.setattr("intel_mcp.server.TerraExtractor", StubExtractor)

    async with Client(mcp) as client:
        tools = await client.list_tools()
        tool = next(item for item in tools.tools if item.name == "extract_variables")
        assert set(tool.input_schema["properties"]) == {
            "analysis_id",
            "trial_id",
            "variables",
        }
        assert tool.annotations is not None
        assert tool.annotations.read_only_hint is False
        assert tool.annotations.idempotent_hint is False

        result = await client.call_tool(
            "extract_variables",
            {
                "analysis_id": "ana_123456789012345678901234",
                "trial_id": "2024-500001-00-00",
                "variables": [
                    {
                        "name": "planned_sample_size",
                        "instruction": "Return the planned randomized population.",
                        "value_type": "integer",
                    },
                    {
                        "name": "central_imaging_review",
                        "instruction": "Is central imaging review required?",
                        "value_type": "boolean",
                    },
                ],
            },
        )

    assert result.is_error is False
    assert control.extraction_operations == ["reserve", "commit"]
    assert result.structured_content == {
        "trial_id": "2024-500001-00-00",
        "values": {
            "planned_sample_size": 420,
            "central_imaging_review": None,
        },
        "analysis_allowance": {"limit": 200, "used": 1, "remaining": 199},
    }
    assert not {
        "status",
        "explanation",
        "source",
        "document_name",
        "page",
    } & set(result.structured_content)


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


def test_expanded_therapeutic_area_values_are_exposed_and_normalized() -> None:
    from intel_mcp.models import TrialFilters

    filters = TrialFilters.model_validate(
        {
            "therapeutic_areas": {
                "operator": "contains_all",
                "values": ["blood disorders", "GYNECOLOGY", "emergency medicine"],
            }
        }
    )

    assert filters.therapeutic_areas is not None
    assert filters.therapeutic_areas.values == [
        "Blood Disorders",
        "Gynecology",
        "Emergency Medicine",
    ]


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
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "intel-mcp"
    assert "classifier_configured" in body
    assert "extractor_configured" in body
