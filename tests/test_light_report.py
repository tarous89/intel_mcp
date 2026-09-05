from __future__ import annotations

import json
from dataclasses import replace

import httpx
import pytest
from pydantic import ValidationError

from intel_mcp.light_report import (
    LIGHT_OBJECTIVE_COUNT,
    LIGHT_REPORT_MODEL,
    LIGHT_REPORT_SERVICE_TIER,
    LIGHT_SYNTHESIS_MODEL,
    LIGHT_TRIAL_COUNT,
    LightTrialSelection,
    SolLightReportRunner,
    light_objectives,
)
from intel_mcp.server import settings


PLAN = {
    "version": 2,
    "studyCohorts": [
        {"role": "primary", "title": "Resected NSCLC trials", "details": ["Adjuvant setting"]},
        {"role": "adjacent", "title": "Broader NSCLC trials", "details": ["Related settings"]},
    ],
    "exclusionSummary": "Unrelated diseases excluded.",
    "reportSections": [
        {"title": "Endpoints", "analyses": ["Endpoint frequency"], "coverage": "strong", "maxOnly": False},
        {"title": "Protocol detail", "analyses": ["Assay schedule"], "coverage": "strong", "maxOnly": True},
        {"title": "Eligibility", "analyses": ["Eligibility patterns"], "coverage": "strong", "maxOnly": False},
        {"title": "Sites", "analyses": ["Active sites"], "coverage": "strong", "maxOnly": False},
        {"title": "Investigators", "analyses": ["Active investigators"], "coverage": "strong", "maxOnly": False},
        {"title": "Countries & timelines", "analyses": ["Country timing"], "coverage": "strong", "maxOnly": False},
    ],
}


def _selection() -> dict:
    return {
        "selected_trials": [
            {"trial_id": f"2026-{index:06d}-00-00", "group": "priority" if index <= 12 else "adjacent"}
            for index in range(1, 21)
        ]
    }


def test_light_report_uses_first_four_non_max_categories() -> None:
    objectives = light_objectives(PLAN)
    assert LIGHT_OBJECTIVE_COUNT == 4
    assert [item["title"] for item in objectives] == ["Endpoints", "Eligibility", "Sites", "Investigators"]


def test_light_report_runtime_uses_terra_for_analysis_and_sol_for_synthesis() -> None:
    assert LIGHT_REPORT_MODEL == "gpt-5.6-terra"
    assert LIGHT_REPORT_SERVICE_TIER == "flex"
    assert LIGHT_SYNTHESIS_MODEL == "gpt-5.6-sol"


def test_light_trial_selection_requires_exactly_twenty_unique_trials() -> None:
    assert len(LightTrialSelection.model_validate(_selection()).selected_trials) == LIGHT_TRIAL_COUNT
    invalid = _selection()
    invalid["selected_trials"][-1] = invalid["selected_trials"][0]
    with pytest.raises(ValidationError):
        LightTrialSelection.model_validate(invalid)


@pytest.mark.anyio
async def test_selection_call_only_exposes_filter_and_profiles() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["model"] == LIGHT_REPORT_MODEL
        assert payload["service_tier"] == LIGHT_REPORT_SERVICE_TIER
        tool = payload["tools"][0]
        assert tool["allowed_tools"] == ["filter_trials", "get_profiles"]
        assert "classify_trials" not in tool["allowed_tools"]
        assert "extract_variables" not in tool["allowed_tools"]
        return httpx.Response(200, json={"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(_selection())}]}]})

    configured = replace(settings, openai_api_key="test-key", mcp_inbound_service_token="internal-mcp-token", mcp_public_resource_url="https://mcp.example.test/mcp")
    runner = SolLightReportRunner(configured, transport=httpx.MockTransport(handler))
    result = await runner.select_trials(analysis_id="analysis-12345678901234567890", context="Adjuvant NSCLC", insights="Endpoints", plan=PLAN)
    assert len(result.selected_trials) == 20


@pytest.mark.anyio
async def test_objective_call_only_exposes_profiles_and_is_visual_first() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["tools"][0]["allowed_tools"] == ["get_profiles"]
        assert payload["text"]["format"]["name"] == "intel_light_objective_v2"
        output = {
            "title": "Endpoints",
            "summary_sentences": ["PFS was the most frequent endpoint pattern."],
            "sub_analyses": [{
                "title": "Endpoint frequency",
                "visual": {"kind": "bar", "title": "Most frequent endpoints", "unit": "trials", "labels": ["PFS", "OS"], "values": [8, 5], "note": "Trial count per endpoint."},
                "interpretation": "PFS appeared most often.",
                "items": [{"label": "PFS", "value": "8 trials", "explanation": "It was the most recurrent endpoint.", "trial_ids": ["2026-000001-00-00"]}],
                "trial_ids": ["2026-000001-00-00"],
            }],
            "conclusion": "PFS is the strongest profile-supported benchmark.",
            "limitations": [],
        }
        return httpx.Response(200, json={"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(output)}]}]})

    configured = replace(settings, openai_api_key="test-key", mcp_inbound_service_token="internal-mcp-token", mcp_public_resource_url="https://mcp.example.test/mcp")
    runner = SolLightReportRunner(configured, transport=httpx.MockTransport(handler))
    result = await runner.analyze_objective(
        analysis_id="analysis-12345678901234567890",
        context="Adjuvant NSCLC",
        objective={"title": "Endpoints", "analyses": ["Endpoint frequency"], "coverage": "strong"},
        selected_trials=LightTrialSelection.model_validate(_selection()).selected_trials,
    )
    assert result.sub_analyses[0].visual.kind == "bar"
