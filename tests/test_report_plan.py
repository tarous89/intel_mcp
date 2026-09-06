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
async def test_report_plan_is_generated_by_sol_with_light_max_contract() -> None:
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
        for tool_name in ("filter_trials", "classify_trials", "get_profiles", "get_documents", "extract_variables"):
            assert tool_name in developer_text
        assert "get_profiles reads 1–10 approved Trial Profiles per call" in developer_text
        assert "Optional controlled sections return exact deterministic projections" in developer_text
        assert "omitting sections or passing an empty list returns the complete approved profile" in developer_text
        assert "Light execution can use ONLY structured filtering and complete approved Trial Profiles" in developer_text
        assert "maxOnly=true only when" in developer_text
        assert "at most three profile-eligible objectives" in developer_text
        assert "prioritizes Strong coverage before Source dependent coverage" in developer_text
        assert "Do not use maxOnly because of count or position" in developer_text
        assert "directly help answer the user's requested insights" in developer_text
        assert "answerable from evidence that Intel MCP can actually provide" in developer_text
        assert "Prefer graph-ready quantitative outputs" in developer_text
        assert "Do not invent a meaningless metric merely to force a chart" in developer_text
        assert "There is no target count" in developer_text
        assert "Apply a compression test" in developer_text
        assert "Silently compare the final bullets pairwise" in developer_text
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


def test_report_plan_contract_documents_current_light_priority() -> None:
    assert REPORT_PLAN_MODEL == "gpt-5.6-sol"
    assert REPORT_PLAN_VERSION == 2
    assert "1 to 4 trial groups" in REPORT_PLAN_INSTRUCTIONS
    assert "Each retained analysis bullet should be independently answerable" in REPORT_PLAN_INSTRUCTIONS
    assert "directly help answer the user's requested insights" in REPORT_PLAN_INSTRUCTIONS
    assert "answerable from evidence that Intel MCP can actually provide" in REPORT_PLAN_INSTRUCTIONS
    assert "concrete report output" in REPORT_PLAN_INSTRUCTIONS
    assert "Prefer graph-ready quantitative outputs" in REPORT_PLAN_INSTRUCTIONS
    assert "Do not invent a meaningless metric merely to force a chart" in REPORT_PLAN_INSTRUCTIONS
    assert "top 3/top 5 rankings" in REPORT_PLAN_INSTRUCTIONS
    assert "There is no target count" in REPORT_PLAN_INSTRUCTIONS
    assert "Apply a compression test" in REPORT_PLAN_INSTRUCTIONS
    assert "Silently compare the final bullets pairwise" in REPORT_PLAN_INSTRUCTIONS
    assert "Coverage is independent from maxOnly" in REPORT_PLAN_INSTRUCTIONS
    assert "at most three profile-eligible objectives" in REPORT_PLAN_INSTRUCTIONS
    assert "prioritizes Strong coverage before Source dependent coverage" in REPORT_PLAN_INSTRUCTIONS
