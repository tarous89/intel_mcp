from __future__ import annotations

import json
from dataclasses import replace

import httpx
import pytest
from pydantic import ValidationError

from intel_mcp.light_report import (
    LIGHT_MAX_SUBANALYSES,
    LIGHT_OBJECTIVE_COUNT,
    LIGHT_REPORT_MODEL,
    LIGHT_REPORT_SERVICE_TIER,
    LIGHT_REPORT_SHELL_HTML,
    LIGHT_SELECTION_MODEL,
    LIGHT_SYNTHESIS_MODEL,
    LIGHT_TRIAL_COUNT,
    LightTrialSelection,
    ObjectiveResult,
    SolLightReportRunner,
    light_objectives,
)
from intel_mcp.profiles import FullProfileItem
from intel_mcp.server import settings


PLAN = {
    "version": 2,
    "studyCohorts": [
        {"role": "primary", "title": "Resected NSCLC trials", "details": ["Adjuvant setting"]},
        {"role": "adjacent", "title": "Broader NSCLC trials", "details": ["Related settings"]},
    ],
    "exclusionSummary": "Unrelated diseases excluded.",
    "reportSections": [
        {
            "title": "Endpoints",
            "analyses": ["Endpoint frequency", "Endpoint timing", "Endpoint hierarchy", "Fourth bullet"],
            "coverage": "strong",
            "maxOnly": False,
        },
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


def _profiles() -> list[FullProfileItem]:
    return [
        FullProfileItem(
            eu_number=f"2026-{index:06d}-00-00",
            profile_schema_version="10.0.0",
            approved_at="2026-09-01T00:00:00+00:00",
            profile={
                "filtering_variables": {"phase": [3], "number_of_sites": 10 + index},
                "classification_variables": {"trial_title": f"Trial {index}", "endpoints": []},
                "ctis_lifecycle": {"overall_updates": [], "countries": []},
                "results": {},
            },
        )
        for index in range(1, 21)
    ]


def _objective_output(trial_reference: str) -> dict:
    return {
        "title": "Endpoints",
        "summary_sentences": ["PFS was the most frequent endpoint pattern across the evidence cohort."],
        "sub_analyses": [{
            "title": "Endpoint frequency",
            "visual": {"kind": "bar", "title": "Most frequent endpoints", "unit": "trials", "labels": ["PFS", "OS"], "values": [8, 5], "note": "Trial count per endpoint."},
            "interpretation": "PFS appeared most often.",
            "items": [{"label": "PFS", "value": "8 trials", "explanation": "It was the most recurrent endpoint.", "trial_ids": [trial_reference]}],
            "trial_ids": [trial_reference],
        }],
        "conclusion": "PFS is the strongest profile-supported benchmark.",
        "limitations": [],
    }


def test_light_report_uses_first_three_non_max_categories_and_three_subanalyses() -> None:
    objectives = light_objectives(PLAN)
    assert LIGHT_OBJECTIVE_COUNT == 3
    assert LIGHT_MAX_SUBANALYSES == 3
    assert [item["title"] for item in objectives] == ["Endpoints", "Eligibility", "Sites"]
    assert objectives[0]["analyses"] == ["Endpoint frequency", "Endpoint timing", "Endpoint hierarchy"]


def test_light_report_runtime_uses_sol_selection_terra_objectives_and_sol_synthesis() -> None:
    assert LIGHT_SELECTION_MODEL == "gpt-5.6-sol"
    assert LIGHT_REPORT_MODEL == "gpt-5.6-terra"
    assert LIGHT_REPORT_SERVICE_TIER == "flex"
    assert LIGHT_SYNTHESIS_MODEL == "gpt-5.6-sol"
    assert "1.1" in LIGHT_REPORT_SHELL_HTML
    assert "graph-box" in LIGHT_REPORT_SHELL_HTML


def test_light_trial_selection_requires_exactly_twenty_unique_trials() -> None:
    assert len(LightTrialSelection.model_validate(_selection()).selected_trials) == LIGHT_TRIAL_COUNT
    invalid = _selection()
    invalid["selected_trials"][-1] = invalid["selected_trials"][0]
    with pytest.raises(ValidationError):
        LightTrialSelection.model_validate(invalid)


@pytest.mark.anyio
async def test_selection_call_uses_sol_high_and_only_filter_and_profiles() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["model"] == LIGHT_SELECTION_MODEL
        assert payload["service_tier"] == LIGHT_REPORT_SERVICE_TIER
        assert payload["reasoning"] == {"effort": "high"}
        assert payload["max_tool_calls"] == 20
        tool = payload["tools"][0]
        assert tool["allowed_tools"] == ["filter_trials", "get_profiles"]
        developer = payload["input"][0]["content"][0]["text"]
        assert "candidate pool of up to 100 unique trials" in developer
        assert "Every trial in the final 20 should have been profile-reviewed" in developer
        return httpx.Response(200, json={"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(_selection())}]}]})

    configured = replace(settings, openai_api_key="test-key", mcp_inbound_service_token="internal-mcp-token", mcp_public_resource_url="https://mcp.example.test/mcp")
    runner = SolLightReportRunner(configured, transport=httpx.MockTransport(handler))
    result = await runner.select_trials(analysis_id="analysis-12345678901234567890", context="Adjuvant NSCLC", insights="Endpoints", plan=PLAN)
    assert len(result.selected_trials) == 20


@pytest.mark.anyio
async def test_objective_call_uses_terra_high_full_profiles_and_no_mcp_tools() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["model"] == LIGHT_REPORT_MODEL
        assert payload["reasoning"] == {"effort": "high"}
        assert "tools" not in payload
        assert payload["text"]["format"]["name"] == "intel_light_objective_v3"
        user = json.loads(payload["input"][1]["content"][0]["text"])
        evidence_trials = user["evidence_trials"]
        assert len(evidence_trials) == 20
        assert evidence_trials[0]["alias"] == "T01"
        assert evidence_trials[0]["trial_id"] == "2026-000001-00-00"
        assert "profile" in evidence_trials[0]
        schema = payload["text"]["format"]["schema"]
        assert schema["properties"]["summary_sentences"]["maxItems"] == 1
        assert schema["properties"]["sub_analyses"]["maxItems"] == 3
        sub_analysis = schema["properties"]["sub_analyses"]["items"]
        assert sub_analysis["properties"]["trial_ids"]["items"]["enum"] == [f"T{index:02d}" for index in range(1, 21)]
        return httpx.Response(200, json={"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(_objective_output("T01"))}]}]})

    configured = replace(settings, openai_api_key="test-key")
    runner = SolLightReportRunner(configured, transport=httpx.MockTransport(handler))
    result = await runner.analyze_objective(
        context="Adjuvant NSCLC",
        objective={"title": "Endpoints", "analyses": ["Endpoint frequency"], "coverage": "strong"},
        selected_trials=LightTrialSelection.model_validate(_selection()).selected_trials,
        full_profiles=_profiles(),
    )
    assert result.sub_analyses[0].visual.kind == "bar"
    assert result.sub_analyses[0].trial_ids == ["2026-000001-00-00"]
    assert result.sub_analyses[0].items[0].trial_ids == ["2026-000001-00-00"]
    assert len(result.summary_sentences) == 1
    assert result.qa_warnings == []


@pytest.mark.anyio
async def test_synthesis_uses_sol_high_and_binding_html_shell_without_returning_html() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["model"] == LIGHT_SYNTHESIS_MODEL
        assert payload["reasoning"] == {"effort": "high"}
        assert "tools" not in payload
        developer = payload["input"][0]["content"][0]["text"]
        assert LIGHT_REPORT_SHELL_HTML in developer
        assert "must NOT output HTML" in developer
        output = {
            "title": "NSCLC development evidence",
            "executive_summary": "The evidence supports a focused endpoint and site strategy.",
            "key_takeaways": ["Endpoint patterns are concentrated.", "Site experience is uneven."],
            "closing_note": "Use the strongest recurring patterns as the design starting point.",
        }
        return httpx.Response(200, json={"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(output)}]}]})

    configured = replace(settings, openai_api_key="test-key")
    runner = SolLightReportRunner(configured, transport=httpx.MockTransport(handler))
    result = await runner.synthesize(
        context="Adjuvant NSCLC",
        selection=LightTrialSelection.model_validate(_selection()),
        sections=[ObjectiveResult.model_validate(_objective_output("T01"))],
    )
    assert result.title == "NSCLC development evidence"


@pytest.mark.anyio
async def test_outside_provenance_reference_is_sanitized_without_failing_report() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(_objective_output("2025-999999-00-00"))}]}]})

    configured = replace(settings, openai_api_key="test-key")
    runner = SolLightReportRunner(configured, transport=httpx.MockTransport(handler))
    result = await runner.analyze_objective(
        context="Adjuvant NSCLC",
        objective={"title": "Endpoints", "analyses": ["Endpoint frequency"], "coverage": "strong"},
        selected_trials=LightTrialSelection.model_validate(_selection()).selected_trials,
        full_profiles=_profiles(),
    )
    assert result.sub_analyses[0].trial_ids == []
    assert result.sub_analyses[0].items[0].trial_ids == []
    assert result.qa_warnings == ["provenance_reference_mismatch"]
