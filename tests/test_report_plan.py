from __future__ import annotations

from dataclasses import replace

import httpx
import pytest

from intel_mcp.report_plan import REPORT_PLAN_MODEL, TerraReportPlanner
from intel_mcp.server import settings


SAMPLE_PLAN = {
    "studyCohorts": [
        {
            "title": "Inherited retinal gene-therapy trials",
            "description": "Phase 1/2 and Phase 2 European gene-therapy trials in inherited retinal disorders with comparable adult populations.",
        },
        {
            "title": "Rare retinal disease trials using other modalities",
            "description": "Adjacent rare retinal studies add endpoint and recruitment evidence where gene-therapy comparators are limited.",
        },
    ],
    "exclusionSummary": "Healthy-volunteer, non-interventional, and unrelated ophthalmology studies will be excluded.",
    "reportSections": [
        {"title": "Eligibility and recruitability", "description": "Compare recurring criteria and their likely effect on the addressable population.", "coverage": "strong"},
        {"title": "Endpoint strategy", "description": "Compare functional and anatomical endpoint patterns and assessment timing.", "coverage": "strong"},
        {"title": "EU countries and timelines", "description": "Benchmark country participation and CTIS submission-to-authorisation timing.", "coverage": "strong"},
        {"title": "Sites and investigators", "description": "Identify European sites and investigators with relevant inherited retinal trial experience.", "coverage": "strong"},
        {"title": "Design choices", "description": "Compare masking, controls, dosing, follow-up duration, and sample-size patterns.", "coverage": "strong"},
        {"title": "Operational and safety lessons", "description": "Summarize explicit execution and serious-safety findings where published sources exist.", "coverage": "source_dependent"},
    ],
}


@pytest.mark.anyio
async def test_report_plan_is_generated_by_terra_with_all_mcp_capabilities() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = __import__("json").loads(request.content)
        assert payload["model"] == REPORT_PLAN_MODEL
        assert payload["reasoning"] == {"effort": "medium"}
        assert payload["text"]["format"]["strict"] is True
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
        assert "generic placeholders" in developer_text
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
    planner = TerraReportPlanner(configured, transport=httpx.MockTransport(handler))
    plan = await planner.generate(
        context="Phase 2 gene therapy for inherited retinal disease in adults",
        insights="Compare eligibility, endpoints, countries, sites and investigators",
    )

    assert plan.model_dump() == SAMPLE_PLAN
