from __future__ import annotations

from dataclasses import replace

import httpx
import pytest
from pydantic import ValidationError

from intel_mcp.report_plan import (
    REPORT_PLAN_INSTRUCTIONS,
    REPORT_PLAN_MODEL,
    REPORT_PLAN_VERSION,
    ReportPlan,
    SolReportPlanner,
)
from intel_mcp.server import settings


SAMPLE_PLAN = {
    "version": 2,
    "studyCohorts": [
        {"role": "primary", "title": "Inherited retinal gene-therapy trials", "details": ["Adults with inherited retinal disorders"]},
        {"role": "adjacent", "title": "Inherited retinal disease trials", "details": ["Broader modalities in the same disease space"]},
    ],
    "exclusionSummary": "Healthy-volunteer, non-interventional, and unrelated ophthalmology studies will be excluded.",
    "reportSections": [
        {"title": "Eligibility", "analyses": ["Most frequent inclusion and exclusion criteria"], "coverage": "strong", "maxOnly": False},
        {"title": "Endpoints", "analyses": ["Most frequent primary endpoints and trial count per endpoint"], "coverage": "strong", "maxOnly": False},
        {"title": "Countries & timelines", "analyses": ["Median and range of key CTIS intervals"], "coverage": "strong", "maxOnly": False},
        {"title": "Sites", "analyses": ["Most active sites by country and repeat trial participation"], "coverage": "strong", "maxOnly": False},
        {"title": "Investigators", "analyses": ["Most active investigators grouped by country and site"], "coverage": "strong", "maxOnly": False},
        {"title": "Protocol detail", "analyses": ["Visit-by-visit assay schedule"], "coverage": "strong", "maxOnly": True},
    ],
}


@pytest.mark.anyio
async def test_report_plan_is_generated_by_sol_with_current_light_max_contract() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = __import__("json").loads(request.content)
        assert payload["model"] == REPORT_PLAN_MODEL
        assert "service_tier" not in payload
        assert payload["reasoning"] == {"effort": "medium"}
        schema = payload["text"]["format"]["schema"]
        assert schema["$defs"]["reportSection"]["properties"]["maxOnly"] == {"type": "boolean"}
        assert schema["$defs"]["reportSection"]["properties"]["analyses"]["maxItems"] == 4
        assert "maxOnly" in schema["$defs"]["reportSection"]["required"]

        developer_text = payload["input"][0]["content"][0]["text"]
        assert "approved Trial Profiles" in developer_text
        assert "source-document/protocol analysis" in developer_text
        assert "There is no target count" in developer_text
        assert "actively consider other useful lenses" in developer_text
        assert "Shared trials, sites, investigators or other entities do NOT make two analyses redundant" in developer_text
        assert "Merge analyses only when" in developer_text
        assert "only after checking that no other supported lens would add distinct decision value" in developer_text
        assert "Do not invent a meaningless metric merely to force a chart" in developer_text
        assert "maxOnly=true only when" in developer_text
        assert "strong coverage before source-dependent coverage" in developer_text

        # Planning has no tools; legacy MCP mechanics should not be explained to Sol here.
        for legacy_tool_name in ("start_analysis", "filter_trials", "classify_trials", "get_profiles", "get_documents", "extract_variables"):
            assert legacy_tool_name not in developer_text

        return httpx.Response(200, json={"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": __import__("json").dumps(SAMPLE_PLAN)}]}]})

    configured = replace(settings, openai_api_key="test-key", report_plan_service_token="test-service-token")
    planner = SolReportPlanner(configured, transport=httpx.MockTransport(handler))
    plan = await planner.generate(context="Phase 2 gene therapy for inherited retinal disease", insights="Eligibility, endpoints and sites")
    assert plan.model_dump() == SAMPLE_PLAN


def test_report_plan_allows_one_to_four_analyses_per_category() -> None:
    raw = {
        **SAMPLE_PLAN,
        "reportSections": [dict(section) for section in SAMPLE_PLAN["reportSections"]],
    }
    raw["reportSections"][0]["analyses"] = ["A", "B", "C", "D"]
    plan = ReportPlan.model_validate(raw)
    assert len(plan.reportSections[0].analyses) == 4

    raw["reportSections"][0]["analyses"] = ["A", "B", "C", "D", "E"]
    with pytest.raises(ValidationError):
        ReportPlan.model_validate(raw)


def test_report_plan_orders_strong_eligible_before_source_dependent_and_max() -> None:
    raw = {
        "version": 2,
        "studyCohorts": [
            {"role": "primary", "title": "Target trials", "details": ["Target setting"]},
        ],
        "exclusionSummary": "Unrelated trials excluded.",
        "reportSections": [
            {"title": "Observed recruitment", "analyses": ["Recruitment outcomes"], "coverage": "source_dependent", "maxOnly": False},
            {"title": "Endpoints", "analyses": ["Endpoint patterns"], "coverage": "strong", "maxOnly": False},
            {"title": "Protocol detail", "analyses": ["Assay schedule"], "coverage": "strong", "maxOnly": True},
            {"title": "Eligibility", "analyses": ["Eligibility patterns"], "coverage": "strong", "maxOnly": False},
            {"title": "Operational results", "analyses": ["Operational findings"], "coverage": "source_dependent", "maxOnly": False},
            {"title": "Deep results", "analyses": ["Document-only result detail"], "coverage": "source_dependent", "maxOnly": True},
        ],
    }

    plan = ReportPlan.model_validate(raw)
    assert [section.title for section in plan.reportSections] == [
        "Endpoints",
        "Eligibility",
        "Observed recruitment",
        "Operational results",
        "Protocol detail",
        "Deep results",
    ]


def test_report_plan_prompt_is_compact_and_encourages_distinct_lenses() -> None:
    assert REPORT_PLAN_MODEL == "gpt-5.6-sol"
    assert REPORT_PLAN_VERSION == 2
    assert "1 to 4 groups" in REPORT_PLAN_INSTRUCTIONS
    assert "5 to 7 categories" in REPORT_PLAN_INSTRUCTIONS
    assert "1 to 4 analyses" in REPORT_PLAN_INSTRUCTIONS
    assert "actively consider other useful lenses" in REPORT_PLAN_INSTRUCTIONS
    assert "Shared trials, sites, investigators or other entities do NOT make two analyses redundant" in REPORT_PLAN_INSTRUCTIONS
    assert "same decision question" in REPORT_PLAN_INSTRUCTIONS
    assert "Never add filler" in REPORT_PLAN_INSTRUCTIONS
    assert len(REPORT_PLAN_INSTRUCTIONS) < 7000
