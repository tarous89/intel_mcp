import copy
import json
from dataclasses import replace

import httpx
import pytest
from pydantic import ValidationError

from intel_mcp.light_report import LightVisual, ObjectiveResult, FinalSynthesis, _objective_schema_for_aliases
from intel_mcp.max_report import (
    MaxVisual, MaxObjectiveResult, MaxFinalSynthesis, MaxAnalysisPlan, objective_schema, sap_schema,
    TerraMaxReportRunner, AnalysisSpecification,
)
from intel_mcp.server import settings
from intel_mcp.report_output import generate_report_output, report_schema, safe_editorial_change


@pytest.fixture
def anyio_backend():
    return "asyncio"


def draft(tier):
    sub = {
        "title": "Trial activity", "interpretation": "Activity may inform the site discussion.",
        "visual": {"kind": "bar", "title": "Trials by investigator", "unit": "trials",
                   "labels": ["A", "B"], "values": [10, 20], "note": "Count per investigator."},
        "items": [], "trial_ids": ["T01"],
    }
    value = {"title": "Investigators", "summary_sentences": ["Activity differs between investigators."],
             "sub_analyses": [sub, copy.deepcopy(sub)], "conclusion": "Discuss capacity before selection.",
             "limitations": []}
    if tier == "light":
        value["max_upgrade"] = "This report is limited to trial activity. Upgrade to Max to compare additional decision factors."
    return value


@pytest.mark.parametrize("model", [LightVisual, MaxVisual])
def test_long_units_preserved_but_invalid_numbers_and_shapes_rejected(model):
    visual = draft("max")["sub_analyses"][0]["visual"]
    visual["unit"] = "distinct prostate cancer trials per deduplicated investigator identity"
    assert model.model_validate(visual).unit == visual["unit"]
    for updates in [{"values": [1]}, {"values": [float("nan"), 1]},
                    {"values": [float("inf"), 1]}, {"kind": "donut", "values": [-1, 2]},
                    {"kind": "stat"}]:
        with pytest.raises(ValidationError):
            model.model_validate({**visual, **updates})


@pytest.mark.parametrize("model", [ObjectiveResult, MaxObjectiveResult, FinalSynthesis, MaxFinalSynthesis])
def test_wire_schema_keeps_all_public_fields_and_has_no_cosmetic_limits(model):
    schema = report_schema(model)
    assert "title" in schema["properties"]
    assert "qa_warnings" not in schema["properties"]
    assert set(schema["required"]) == set(schema["properties"])
    assert "maxLength" not in json.dumps(schema)
    assert "$ref" not in json.dumps(schema)
    assert '"default"' not in json.dumps(schema)


def test_dynamic_schemas_keep_runtime_constraints_and_aliases():
    for schema in (objective_schema(["T01"]), _objective_schema_for_aliases(["T01"])):
        sub = schema["properties"]["sub_analyses"]["items"]["properties"]
        assert sub["visual"]["properties"]["values"]["maxItems"] == 5
        assert sub["trial_ids"]["items"]["enum"] == ["T01"]
        assert sub["items"]["items"]["properties"]["trial_ids"]["items"]["enum"] == ["T01"]
    schema = sap_schema(profile_paths=["p"], analysis_count=3, segment_keys=["a"], semantic_budget=2)
    direct = schema["properties"]["direct_variables"]["items"]["properties"]
    assert direct["name"]["maxLength"] == 64
    assert direct["profile_path"]["enum"] == ["p"]
    assert schema["properties"]["analyses"]["maxItems"] == 3
    assert schema["properties"]["semantic_variables"]["maxItems"] == 2
    assert schema["properties"]["rationale"] == report_schema(MaxAnalysisPlan)["properties"]["rationale"]


@pytest.mark.anyio
@pytest.mark.parametrize("tier,model", [("light", ObjectiveResult), ("max", MaxObjectiveResult)])
async def test_one_structural_correction_then_stop(tier, model):
    valid = draft(tier)
    invalid = copy.deepcopy(valid)
    invalid["sub_analyses"][0]["visual"]["values"] = [1]
    for second in [valid, invalid]:
        calls = []

        async def request(instruction, payload):
            calls.append(instruction)
            if len(calls) == 2:
                assert payload["previous_draft"] == invalid
                assert payload["validation_issues"]
            return json.dumps(invalid if len(calls) == 1 else second)

        if second == valid:
            result = await generate_report_output(request=request, payload={}, validate=model.model_validate, operation=tier)
            assert result.sub_analyses[0].visual.values == [10, 20]
        else:
            with pytest.raises(ValidationError):
                await generate_report_output(request=request, payload={}, validate=model.model_validate, operation=tier)
        assert len(calls) == 2


@pytest.mark.anyio
@pytest.mark.parametrize("tier,model", [("light", ObjectiveResult), ("max", MaxObjectiveResult)])
@pytest.mark.parametrize("change", ["safe", "numbers", "chart", "caveat", "failure", "still_verbose"])
async def test_optional_edit_preserves_valid_content(tier, model, change):
    original = draft(tier)
    original["sub_analyses"][0]["interpretation"] = "10 trials may inform decisions. " + "Additional context repeats this finding. " * 30
    edited = copy.deepcopy(original)
    edited["sub_analyses"][0]["interpretation"] = "10 trials may inform decisions."
    if change == "numbers": edited["sub_analyses"][0]["interpretation"] = "20 trials may inform decisions."
    if change == "chart": edited["sub_analyses"][0]["visual"]["values"] = [20, 10]
    if change == "caveat": edited["sub_analyses"][0]["interpretation"] = "10 trials inform decisions."
    if change == "still_verbose": edited = original
    calls = []

    async def request(instruction, payload):
        calls.append(instruction)
        if len(calls) == 2 and change == "failure": raise RuntimeError("API unavailable")
        return json.dumps(original if len(calls) == 1 else edited)

    result = await generate_report_output(request=request, payload={}, validate=model.model_validate, operation=tier)
    expected = edited if change in {"safe", "still_verbose"} else original
    assert result.sub_analyses[0].interpretation == expected["sub_analyses"][0]["interpretation"]
    assert result.sub_analyses[0].visual.values == [10, 20]
    assert len(calls) == 2


@pytest.mark.anyio
@pytest.mark.parametrize("model", [FinalSynthesis, MaxFinalSynthesis])
async def test_synthesis_uses_one_correction_without_recomputing_sections(model):
    calls = []
    valid = {"title": "Evidence", "executive_summary": "Discuss capacity.", "closing_note": "Confirm suitability."}

    async def request(instruction, payload):
        calls.append(instruction)
        assert payload["sections"] == ["completed section"]
        return json.dumps({} if len(calls) == 1 else valid)

    result = await generate_report_output(request=request, payload={"sections": ["completed section"]},
                                          validate=model.model_validate, operation="synthesis")
    assert result.title == "Evidence"
    assert len(calls) == 2


def test_editor_cannot_swap_denominators_or_drop_named_items():
    assert not safe_editorial_change({"note": "10 of 20"}, {"note": "20 of 10"})
    assert not safe_editorial_change({"label": "Dr A"}, {"label": "Dr B"})
    assert not safe_editorial_change({"trial_ids": ["T01"]}, {"trial_ids": []})


@pytest.mark.anyio
@pytest.mark.parametrize("invalid_first", [False, True])
async def test_max_runner_handles_long_units_and_repairs_only_failed_objective(invalid_first):
    calls = []
    original = draft("max")
    original["sub_analyses"][0]["visual"]["unit"] = "distinct prostate cancer trials per deduplicated investigator identity"

    async def handler(request):
        payload = json.loads(request.content)
        calls.append(payload["text"]["format"]["name"])
        assert "Write for a busy clinical professional" in payload["input"][0]["content"][0]["text"]
        output = copy.deepcopy(original)
        if invalid_first and len(calls) == 1:
            output["sub_analyses"][0]["visual"]["values"] = [10]
        return httpx.Response(200, json={"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(output)}]}]})

    runner = TerraMaxReportRunner(replace(settings, openai_api_key="test-key"), transport=httpx.MockTransport(handler))
    result = await runner.analyze_objective(
        context="Investigator activity", pair={"maxAnalysis": {"title": "Approved title", "details": ["Activity", "Capacity"]}},
        specification=AnalysisSpecification(analysis_index=0, purpose="Activity", methods=["Count", "Compare"], variable_names=["count"], segment_keys=[]),
        rows=[{"trial_id": "2026-000001-00-00", "values": {"count": 10}}],
        definitions={"count": {"kind": "numeric", "label": "Count"}}, segment_metadata=[],
    )
    assert result.title == "Approved title"
    assert result.sub_analyses[0].visual.unit == original["sub_analyses"][0]["visual"]["unit"]
    assert len(calls) == (2 if invalid_first else 1)
    assert set(calls) == {"intel_max_objective_v2_0"}
