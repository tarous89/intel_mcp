from __future__ import annotations

from datetime import UTC, datetime

import pytest
from mcp import Client

from intel_mcp.models import AppAnalysis, AppAnalysisLimits, AppStartAnalysisResponse
from intel_mcp.server import mcp


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
