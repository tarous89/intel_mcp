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
    "version": 3,
    "studyCohorts": [
        {
            "role": "primary",
            "title": "Phase 2 retinal gene-therapy trials",
            "details": ["Inherited retinal disease", "Phase 2", "Gene therapy"],
            "maxOnly": False,
        },
        {
            "role": "adjacent",
            "title": "Biomarker-matched inherited retinal gene-therapy trials",
            "details": ["Match the requested molecular subgroup using deeper profile evidence"],
            "maxOnly": True,
        },
        {
            "role": "adjacent",
            "title": "Inherited retinal trials with related advanced therapies",
            "details": ["Same disease space with clinically relevant advanced modalities"],
            "maxOnly": True,
        },
    ],
    "exclusionSummary": "Healthy-volunteer, non-interventional, and unrelated ophthalmology studies will be excluded.",
    "reportSections": [
        {
            "title": "Eligibility",
            "analyses": [
                "Rank the most common eligibility criteria",
                "Identify criteria that differ most in the target molecular subgroup",
                "Assess which restrictions may unnecessarily narrow recruitment",
            ],
        },
        {
            "title": "Endpoints",
            "analyses": [
                "Rank the most commonly used primary endpoints",
                "Compare endpoint choice across clinically relevant subgroups",
                "Assess protocol-level endpoint definitions and timing",
            ],
        },
        {
            "title": "Countries & timelines",
            "analyses": [
                "Compare observed CTIS timelines across countries",
                "Assess timeline consistency within the closest-matched trials",
                "Identify the country mix with the strongest evidence-supported trade-offs",
            ],
        },
        {
            "title": "Sites",
            "analyses": [
                "Rank sites by relevant trial activity",
                "Compare site experience in the closest disease and modality matches",
                "Assess competitive trial pressure around the leading sites",
            ],
        },
        {
            "title": "Investigators",
            "analyses": [
                "Rank investigators by relevant trial activity",
                "Compare investigator experience across the Max trial groups",
                "Identify the strongest evidence-supported investigator-site combinations",
            ],
        },
    ],
}


@pytest.mark.anyio
async def test_report_plan_is_generated_by_sol_with_depth_first_contract() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = __import__("json").loads(request.content)
        assert payload["model"] == REPORT_PLAN_MODEL
        assert "service_tier" not in payload
        assert payload["reasoning"] == {"effort": "medium"}
        assert payload["text"]["format"]["name"] == "intel_agent_report_plan_v3"
        schema = payload["text"]["format"]["schema"]
        assert schema["properties"]["studyCohorts"]["minItems"] == 3
        assert schema["properties"]["studyCohorts"]["maxItems"] == 5
        assert schema["$defs"]["studyCohort"]["properties"]["maxOnly"] == {"type": "boolean"}
        assert schema["$defs"]["reportSection"]["properties"]["analyses"]["minItems"] == 3
        assert schema["$defs"]["reportSection"]["properties"]["analyses"]["maxItems"] == 5

        developer_text = payload["input"][0]["content"][0]["text"]
        assert "exactly one shared group followed by 2 to 4 Max groups" in developer_text
        assert "structured filtering alone" in developer_text
        assert "do not pretend simple filtering can establish that detail" in developer_text
        assert "Create 5 to 7 objectives" in developer_text
        assert "The FIRST analysis is the shared Light/Max analysis" in developer_text
        assert "remaining 2 to 4 analyses are Max analyses" in developer_text
        assert "must not merely restate the first analysis" in developer_text
        assert "Do not hard-code presentation breadth" in developer_text
        assert "Do not use generic titles" in developer_text

        for tool_name in ("start_analysis", "filter_trials", "classify_trials", "get_profiles", "get_documents", "extract_variables"):
            assert tool_name not in developer_text

        return httpx.Response(200, json={
            "status": "completed",
            "output": [{"type": "message", "content": [{"type": "output_text", "text": __import__("json").dumps(SAMPLE_PLAN)}]}],
        })

    configured = replace(settings, openai_api_key="test-key", report_plan_service_token="test-service-token")
    planner = SolReportPlanner(configured, transport=httpx.MockTransport(handler))
    plan = await planner.generate(
        context="Phase 2 gene therapy for inherited retinal disease",
        insights="Eligibility, endpoints and sites",
    )
    assert plan.model_dump() == SAMPLE_PLAN


def test_report_plan_requires_one_shared_and_two_to_four_max_groups() -> None:
    plan = ReportPlan.model_validate(SAMPLE_PLAN)
    assert plan.studyCohorts[0].maxOnly is False
    assert all(item.maxOnly for item in plan.studyCohorts[1:])

    too_few = {**SAMPLE_PLAN, "studyCohorts": SAMPLE_PLAN["studyCohorts"][:2]}
    with pytest.raises(ValidationError):
        ReportPlan.model_validate(too_few)


def test_report_plan_requires_one_shared_plus_two_to_four_max_analyses_per_objective() -> None:
    raw = {**SAMPLE_PLAN, "reportSections": [dict(section) for section in SAMPLE_PLAN["reportSections"]]}
    raw["reportSections"][0]["analyses"] = ["Shared", "Max A", "Max B", "Max C", "Max D"]
    plan = ReportPlan.model_validate(raw)
    assert len(plan.reportSections[0].analyses) == 5

    raw["reportSections"][0]["analyses"] = ["Shared", "Max A"]
    with pytest.raises(ValidationError):
        ReportPlan.model_validate(raw)


def test_report_plan_rejects_mis_tiered_group_structure() -> None:
    raw = {**SAMPLE_PLAN, "studyCohorts": [dict(item) for item in SAMPLE_PLAN["studyCohorts"]]}
    raw["studyCohorts"][1]["maxOnly"] = False
    with pytest.raises(ValidationError):
        ReportPlan.model_validate(raw)


def test_report_plan_prompt_is_compact_and_current() -> None:
    assert REPORT_PLAN_MODEL == "gpt-5.6-sol"
    assert REPORT_PLAN_VERSION == 3
    assert "2 to 4 Max groups" in REPORT_PLAN_INSTRUCTIONS
    assert "5 to 7 objectives" in REPORT_PLAN_INSTRUCTIONS
    assert "remaining 2 to 4 analyses are Max analyses" in REPORT_PLAN_INSTRUCTIONS
    assert "Strong coverage" not in REPORT_PLAN_INSTRUCTIONS
    assert "Source dependent" not in REPORT_PLAN_INSTRUCTIONS
    assert "Priority" not in REPORT_PLAN_INSTRUCTIONS
    assert len(REPORT_PLAN_INSTRUCTIONS) < 8000
