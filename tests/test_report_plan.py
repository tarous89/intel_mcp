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
        {
            "role": "primary",
            "title": "Inherited retinal gene-therapy trials",
            "details": [
                "Adults with inherited retinal disorders",
                "European phase 1/2 and phase 2 studies",
            ],
        },
        {
            "role": "adjacent",
            "title": "Inherited retinal disease trials",
            "details": ["Broader treatment modalities in the same disease space"],
        },
        {
            "role": "adjacent",
            "title": "Rare-disease gene-therapy trials",
            "details": ["Cross-disease gene-therapy studies with transferable operational lessons"],
        },
    ],
    "exclusionSummary": "Healthy-volunteer, non-interventional, and unrelated ophthalmology studies will be excluded.",
    "reportSections": [
        {
            "title": "Eligibility",
            "analyses": [
                "Most frequent inclusion and exclusion criteria",
                "Exact eligibility definitions and thresholds",
            ],
            "coverage": "strong",
        },
        {
            "title": "Endpoints",
            "analyses": [
                "Most frequent primary endpoints and trial count per endpoint",
                "Exact endpoint definitions and assessment timing",
                "Supported endpoint options for the planned trial",
            ],
            "coverage": "strong",
        },
        {
            "title": "Countries & timelines",
            "analyses": [
                "Trial counts by country",
                "Median and range of key CTIS intervals",
            ],
            "coverage": "strong",
        },
        {
            "title": "Sites",
            "analyses": ["Most active sites by country and repeat trial participation"],
            "coverage": "strong",
        },
        {
            "title": "Investigators",
            "analyses": [
                "Most active investigators grouped by country and site",
                "Available investigator contact details",
            ],
            "coverage": "strong",
        },
        {
            "title": "Operational lessons",
            "analyses": [
                "Reported recruitment shortfalls and documented reasons",
                "Reported country or site performance problems",
            ],
            "coverage": "source_dependent",
        },
    ],
}


@pytest.mark.anyio
async def test_report_plan_is_generated_by_sol_with_all_mcp_capabilities() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = __import__("json").loads(request.content)
        assert payload["model"] == REPORT_PLAN_MODEL
        assert "service_tier" not in payload
        assert payload["reasoning"] == {"effort": "medium"}
        assert payload["text"]["format"]["strict"] is True
        assert payload["text"]["format"]["name"] == "intel_agent_report_plan_v2"
        assert payload["text"]["format"]["schema"]["properties"]["version"]["const"] == 2
        assert payload["text"]["format"]["schema"]["properties"]["studyCohorts"]["maxItems"] == 4
        assert "maxLength" not in __import__("json").dumps(payload["text"]["format"]["schema"])
        developer_text = payload["input"][0]["content"][0]["text"]
        for tool_name in (
            "start_analysis",
            "filter_trials",
            "classify_trials",
            "get_profiles",
            "get_documents",
            "extract_variables",
        ):
            assert tool_name in developer_text
        assert "premium specialist consulting engagement" in developer_text
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": __import__("json").dumps(SAMPLE_PLAN),
                            }
                        ],
                    }
                ],
            },
        )

    configured = replace(
        settings,
        openai_api_key="test-key",
        report_plan_service_token="test-service-token",
    )
    planner = SolReportPlanner(configured, transport=httpx.MockTransport(handler))
    plan = await planner.generate(
        context="Phase 2 gene therapy for inherited retinal disease in adults",
        insights="Compare eligibility, endpoints, countries, sites and investigators",
    )

    assert plan.model_dump() == SAMPLE_PLAN


def test_report_plan_prompt_requires_simple_groups_consolidated_categories_and_coverage_logic() -> None:
    assert REPORT_PLAN_MODEL == "gpt-5.6-sol"
    assert REPORT_PLAN_VERSION == 2
    assert "1 to 4 trial groups" in REPORT_PLAN_INSTRUCTIONS
    assert "one Primary group and 2 to 3 Adjacent groups" in REPORT_PLAN_INSTRUCTIONS
    assert 'Exactly one group must have role "primary"' in REPORT_PLAN_INSTRUCTIONS
    assert "scannable headline" in REPORT_PLAN_INSTRUCTIONS
    assert "Consolidate related work into one category" in REPORT_PLAN_INSTRUCTIONS
    assert 'both belong under "Endpoints"' in REPORT_PLAN_INSTRUCTIONS
    assert "exact analyses or outputs" in REPORT_PLAN_INSTRUCTIONS
    assert "Most frequent primary endpoints and trial count per endpoint" in REPORT_PLAN_INSTRUCTIONS
    assert "Most active sites by country and repeat trial participation" in REPORT_PLAN_INSTRUCTIONS
    assert "Investigators grouped by country and site, with available contact details" in REPORT_PLAN_INSTRUCTIONS
    assert "AT LEAST ONE planned analysis" in REPORT_PLAN_INSTRUCTIONS
    assert "Protocol-based planned study information counts as strong coverage" in REPORT_PLAN_INSTRUCTIONS
    assert "only when ALL useful analyses" in REPORT_PLAN_INSTRUCTIONS
    assert "endpoints that were met or missed" in REPORT_PLAN_INSTRUCTIONS
    assert "causal delay claims require documented reasons" in REPORT_PLAN_INSTRUCTIONS
