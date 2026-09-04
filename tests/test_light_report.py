from __future__ import annotations

import json
from dataclasses import replace

import httpx
import pytest
from pydantic import ValidationError

from intel_mcp.light_report import (
    LIGHT_OBJECTIVE_COUNT,
    LIGHT_REPORT_MODEL,
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
        {"title": "Endpoints", "analyses": ["Endpoint frequency"], "coverage": "strong"},
        {"title": "Eligibility", "analyses": ["Eligibility patterns"], "coverage": "strong"},
        {"title": "Sites", "analyses": ["Active sites"], "coverage": "strong"},
        {"title": "Investigators", "analyses": ["Active investigators"], "coverage": "strong"},
        {"title": "Countries & timelines", "analyses": ["Country timing"], "coverage": "strong"},
    ],
}


def _selection() -> dict:
    return {
        "selected_trials": [
            {
                "trial_id": f"2026-{index:06d}-00-00",
                "group": "priority" if index <= 12 else "adjacent",
            }
            for index in range(1, 21)
        ]
    }


def test_light_report_uses_first_four_plan_categories() -> None:
    objectives = light_objectives(PLAN)
    assert LIGHT_OBJECTIVE_COUNT == 4
    assert [item["title"] for item in objectives] == ["Endpoints", "Eligibility", "Sites", "Investigators"]


def test_light_trial_selection_requires_exactly_twenty_unique_trials() -> None:
    assert len(LightTrialSelection.model_validate(_selection()).selected_trials) == LIGHT_TRIAL_COUNT
    invalid = _selection()
    invalid["selected_trials"][-1] = invalid["selected_trials"][0]
    with pytest.raises(ValidationError):
        LightTrialSelection.model_validate(invalid)


@pytest.mark.anyio
async def test_selection_sol_call_only_exposes_screening_tools() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["model"] == LIGHT_REPORT_MODEL
        assert payload["store"] is False
        tool = payload["tools"][0]
        assert tool["type"] == "mcp"
        assert tool["allowed_tools"] == ["filter_trials", "classify_trials", "get_profiles"]
        assert tool["require_approval"] == "never"
        assert tool["authorization"] == "internal-mcp-token"
        assert payload["max_tool_calls"] == 16
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": json.dumps(_selection())}],
                    }
                ],
            },
        )

    configured = replace(
        settings,
        openai_api_key="test-key",
        mcp_inbound_service_token="internal-mcp-token",
        mcp_public_resource_url="https://mcp.example.test/mcp",
    )
    runner = SolLightReportRunner(configured, transport=httpx.MockTransport(handler))
    result = await runner.select_trials(
        analysis_id="analysis-12345678901234567890",
        context="Adjuvant resected NSCLC phase 2/3 study",
        insights="Endpoints, eligibility, sites, investigators",
        plan=PLAN,
    )
    assert len(result.selected_trials) == 20
