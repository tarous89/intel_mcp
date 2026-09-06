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
    "version": 4,
    "studyCohorts": [
        {
            "role": "primary",
            "title": "Inherited retinal disease trials",
            "details": ["Disease contains inherited retinal disease"],
            "maxOnly": False,
            "filterDimension": "disease",
        },
        {
            "role": "adjacent",
            "title": "Gene-therapy inherited retinal disease trials",
            "details": ["Combine inherited retinal disease with gene therapy"],
            "maxOnly": True,
            "filterDimension": None,
        },
        {
            "role": "adjacent",
            "title": "Pediatric vs adult inherited retinal disease trials",
            "details": ["Compare age-defined populations"],
            "maxOnly": True,
            "filterDimension": None,
        },
    ],
    "exclusionSummary": "Healthy-volunteer and unrelated ophthalmology studies will be excluded.",
    "reportSections": [
        {
            "title": "Most-used eligibility criteria",
            "sharedAnalysis": {
                "title": "Most-used eligibility criteria",
                "details": ["Rank recurring inclusion and exclusion criteria across selected trials"],
            },
            "maxAnalysis": {
                "title": "Eligibility strategy fit",
                "details": [
                    "Compare restrictions across the closest disease and treatment matches",
                    "Identify protocol-level criteria most likely to narrow recruitment",
                ],
            },
        },
        {
            "title": "Most common primary endpoints",
            "sharedAnalysis": {
                "title": "Most common primary endpoints",
                "details": ["Rank primary endpoints across selected trials"],
            },
            "maxAnalysis": {
                "title": "Endpoint strategy fit",
                "details": [
                    "Compare endpoint choice across clinically relevant segments",
                    "Assess endpoint definitions and timing from source documents where needed",
                ],
            },
        },
        {
            "title": "Shortest observed country timelines",
            "sharedAnalysis": {
                "title": "Shortest observed country timelines",
                "details": ["Compare observed CTIS timelines across represented countries"],
            },
            "maxAnalysis": {
                "title": "Country strategy fit",
                "details": [
                    "Compare timeline consistency within closest-matched trials",
                    "Balance relevant experience, variability and operational trade-offs",
                ],
            },
        },
        {
            "title": "Most active trial sites",
            "sharedAnalysis": {
                "title": "Most active trial sites",
                "details": ["Rank sites by documented participation in selected trials"],
            },
            "maxAnalysis": {
                "title": "Best-fitting trial sites",
                "details": [
                    "Compare exact disease, phase and modality experience",
                    "Assess recency, competition and investigator-site relationships",
                ],
            },
        },
        {
            "title": "Most active principal investigators",
            "sharedAnalysis": {
                "title": "Most active principal investigators",
                "details": ["Rank investigators by documented participation in selected trials"],
            },
            "maxAnalysis": {
                "title": "Most relevant principal investigators",
                "details": [
                    "Compare experience in the closest clinical setting",
                    "Assess recency, modality experience and site relationships",
                ],
            },
        },
    ],
}


@pytest.mark.anyio
async def test_report_plan_is_generated_by_sol_with_paired_v4_contract() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = __import__("json").loads(request.content)
        assert payload["model"] == REPORT_PLAN_MODEL
        assert "service_tier" not in payload
        assert payload["reasoning"] == {"effort": "medium"}
        assert payload["text"]["format"]["name"] == "intel_agent_report_plan_v4"
        schema = payload["text"]["format"]["schema"]
        assert schema["properties"]["studyCohorts"]["minItems"] == 3
        assert schema["properties"]["studyCohorts"]["maxItems"] == 5
        assert "filterDimension" in schema["$defs"]["studyCohort"]["required"]
        assert set(schema["$defs"]["reportSection"]["required"]) == {"title", "sharedAnalysis", "maxAnalysis"}
        assert schema["$defs"]["maxAnalysisCard"]["properties"]["details"]["minItems"] == 2

        developer_text = payload["input"][0]["content"][0]["text"]
        assert "Use exactly ONE selection dimension" in developer_text
        assert "Prefer disease when a meaningful disease is specified" in developer_text
        assert "Do not use disease stage, biomarker, mutation, PD-L1" in developer_text
        assert "prefer a compact \"X vs Y\" group" in developer_text
        assert "Do not say \"regardless of\"" in developer_text
        assert "There is no user-facing objective layer" in developer_text
        assert "one shared analysis and one Max analysis" in developer_text
        assert "Never phrase the title as a question" in developer_text
        assert "Do not hard-code result breadth" in developer_text

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


def test_v4_requires_one_single_dimension_shared_group_and_two_to_four_max_groups() -> None:
    plan = ReportPlan.model_validate(SAMPLE_PLAN)
    assert plan.studyCohorts[0].filterDimension == "disease"
    assert plan.studyCohorts[0].maxOnly is False
    assert all(item.maxOnly and item.filterDimension is None for item in plan.studyCohorts[1:])

    too_few = {**SAMPLE_PLAN, "studyCohorts": SAMPLE_PLAN["studyCohorts"][:2]}
    with pytest.raises(ValidationError):
        ReportPlan.model_validate(too_few)

    bad_shared = {**SAMPLE_PLAN, "studyCohorts": [dict(item) for item in SAMPLE_PLAN["studyCohorts"]]}
    bad_shared["studyCohorts"][0]["filterDimension"] = None
    with pytest.raises(ValidationError):
        ReportPlan.model_validate(bad_shared)


def test_v4_analysis_pairs_require_matching_internal_title_and_decision_depth() -> None:
    raw = {**SAMPLE_PLAN, "reportSections": [dict(section) for section in SAMPLE_PLAN["reportSections"]]}
    raw["reportSections"][0] = {
        **raw["reportSections"][0],
        "title": "Different title",
    }
    with pytest.raises(ValidationError):
        ReportPlan.model_validate(raw)

    shallow = {**SAMPLE_PLAN, "reportSections": [dict(section) for section in SAMPLE_PLAN["reportSections"]]}
    shallow["reportSections"][0] = {
        **shallow["reportSections"][0],
        "maxAnalysis": {"title": "Eligibility strategy fit", "details": ["Only one factor"]},
    }
    with pytest.raises(ValidationError):
        ReportPlan.model_validate(shallow)


def test_v4_rejects_question_titles() -> None:
    raw = {**SAMPLE_PLAN, "reportSections": [dict(section) for section in SAMPLE_PLAN["reportSections"]]}
    raw["reportSections"][0] = {
        **raw["reportSections"][0],
        "sharedAnalysis": {
            "title": "Which sites should we use?",
            "details": ["Rank sites"],
        },
        "title": "Which sites should we use?",
    }
    with pytest.raises(ValidationError):
        ReportPlan.model_validate(raw)


def test_report_plan_prompt_is_compact_and_current() -> None:
    assert REPORT_PLAN_MODEL == "gpt-5.6-sol"
    assert REPORT_PLAN_VERSION == 4
    assert "2 to 4 Max groups" in REPORT_PLAN_INSTRUCTIONS
    assert "Create 5 to 7 analysis pairs" in REPORT_PLAN_INSTRUCTIONS
    assert "Strong coverage" not in REPORT_PLAN_INSTRUCTIONS
    assert "Source dependent" not in REPORT_PLAN_INSTRUCTIONS
    assert len(REPORT_PLAN_INSTRUCTIONS) < 9000
