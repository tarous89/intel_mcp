from __future__ import annotations

from dataclasses import replace

import httpx
import pytest

from intel_mcp.report_plan import (
    REPORT_PLAN_INSTRUCTIONS,
    REPORT_PLAN_MODEL,
    REPORT_PLAN_VERSION,
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
        assert "maxOnly" in schema["$defs"]["reportSection"]["required"]
        developer_text = payload["input"][0]["content"][0]["text"]
        for tool_name in ("filter_trials", "classify_trials", "get_profiles", "get_documents", "extract_variables"):
            assert tool_name in developer_text
        assert "get_profiles reads 1–10 approved Trial Profiles per call" in developer_text
        assert "Optional controlled sections return exact deterministic projections" in developer_text
        assert "omitting sections or passing an empty list returns the complete approved profile" in developer_text
        assert "Light execution can use ONLY structured filtering and complete approved Trial Profiles" in developer_text
        assert "maxOnly=true only when" in developer_text
        assert "do not use maxOnly merely because a category is fifth or later" in developer_text
        return httpx.Response(200, json={"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": __import__("json").dumps(SAMPLE_PLAN)}]}]})

    configured = replace(settings, openai_api_key="test-key", report_plan_service_token="test-service-token")
    planner = SolReportPlanner(configured, transport=httpx.MockTransport(handler))
    plan = await planner.generate(context="Phase 2 gene therapy for inherited retinal disease", insights="Eligibility, endpoints and sites")
    assert plan.model_dump() == SAMPLE_PLAN


def test_report_plan_keeps_max_sections_after_light_sections() -> None:
    assert REPORT_PLAN_MODEL == "gpt-5.6-sol"
    assert REPORT_PLAN_VERSION == 2
    assert "1 to 4 trial groups" in REPORT_PLAN_INSTRUCTIONS
    assert "Each analysis bullet should be independently answerable" in REPORT_PLAN_INSTRUCTIONS
    assert "top 3/top 5 ranking" in REPORT_PLAN_INSTRUCTIONS
    assert "Coverage is independent from maxOnly" in REPORT_PLAN_INSTRUCTIONS
