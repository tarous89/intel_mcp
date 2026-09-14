import copy
import json

import httpx
import pytest

from intel_mcp.extraction import ExtractionVariable, TerraExtractor
from intel_mcp.max_group_analysis import examined_groups
from intel_mcp.max_report import (
    AnalysisSpecification, TerraMaxReportRunner, build_field_catalog,
    max_group_variables, summarize_dataset, validate_max_analysis_plan,
)
from intel_mcp.max_report_quality import public_section
from intel_mcp.max_report_recovery import recover_screen
from test_max_report import _settings, _plan, _profile
from test_max_group_analysis import group_fixture


def response(value):
    return httpx.Response(200, json={"status": "completed", "output": [
        {"type": "message", "content": [{"type": "output_text", "text": json.dumps(value)}]}]})


def objective_fixture():
    result, rows, definitions, metadata = group_fixture()
    draft = result.model_dump(mode="json")
    draft["group_assessments"] = [item.model_dump() for item in result.group_assessments]
    kwargs = dict(context="Endpoint choices", pair={"maxAnalysis": {"title": result.title}},
        specification=AnalysisSpecification(analysis_index=0, purpose="Assess endpoint choices",
            methods=["Count endpoints", "Compare groups"], variable_names=["endpoint"], segment_keys=[]),
        rows=[{**row, "trial_id": "trial-" + row["alias"]} for row in rows], definitions=definitions,
        segment_metadata=metadata)
    return draft, kwargs


@pytest.mark.anyio
async def test_zero_omission_preserves_examined_group_audit_without_aborting():
    draft, kwargs = objective_fixture()
    draft["sub_analyses"][0]["visual"]["values"] = [0]
    draft["sub_analyses"][0]["visual"]["unit"] = "trials"
    for support in draft["sub_analyses"][0]["visual"]["supports"]:
        support["numerator_trial_ids"] = []
    calls = []
    def handler(request):
        calls.append(json.loads(request.content))
        return response(draft)
    result = await TerraMaxReportRunner(_settings(), transport=httpx.MockTransport(handler)).analyze_objective(**kwargs)
    assert len(calls) == 2
    assert result.sub_analyses == []
    assert all(item["valid"] and item["publicationStatus"] == "omitted"
               for item in result.analysis_audit["groupAssessments"])
    assert not any("publication:groups:" in issue for issue in result.qa_warnings)
    assert result.summary_sentences == [""] and result.conclusion == ""


@pytest.mark.anyio
@pytest.mark.parametrize("problem", ["missing_support", "wrong_numerator", "unknown_variable", "null_denominator",
    "internal_prose", "small_sample", "misaligned_chart", "nonfinite_chart", "malformed_assessment", "empty_summary"])
async def test_unresolved_quality_and_contract_checks_preserve_independent_findings(problem):
    draft, kwargs = objective_fixture()
    valid = copy.deepcopy(draft["sub_analyses"][0])
    valid["title"] = "Supported endpoint pattern"
    draft["sub_analyses"].append(valid)
    bad = draft["sub_analyses"][0]
    if problem == "missing_support": bad["visual"]["supports"] = []
    if problem == "wrong_numerator": bad["visual"]["supports"][0]["numerator_trial_ids"] = ["T999"]
    if problem == "unknown_variable": bad["visual"]["supports"][0]["variable_names"] = ["unknown"]
    if problem == "null_denominator":
        kwargs["definitions"]["missing_fact"] = {"kind": "numeric"}
        kwargs["specification"].variable_names.append("missing_fact")
        bad["visual"]["supports"][0]["variable_names"] = ["missing_fact"]
    if problem == "internal_prose": bad["interpretation"] = "The dataset schema contains internal metadata."
    if problem == "small_sample": bad["visual"]["supports"][0]["trial_ids"] = ["T001"]
    if problem == "misaligned_chart": bad["visual"]["labels"].append("Unmatched label")
    if problem == "nonfinite_chart": bad["visual"]["values"] = [float("nan")]
    if problem == "malformed_assessment": draft["group_assessments"][0]["status"] = "unknown_status"
    if problem == "empty_summary": draft["summary_sentences"] = []
    calls = []
    def handler(request):
        calls.append(request)
        return response(draft)
    result = await TerraMaxReportRunner(_settings(), transport=httpx.MockTransport(handler)).analyze_objective(**kwargs)
    assert len(calls) == 2
    assert any(item.title == "Supported endpoint pattern" for item in result.sub_analyses)
    assert result.analysis_audit["attempts"]
    assert "group_assessments" not in public_section(result)


@pytest.mark.anyio
async def test_failed_correction_cannot_erase_valid_parts_of_a_malformed_draft():
    draft, kwargs = objective_fixture()
    draft["sub_analyses"].append({"title": "Incomplete chart"})
    calls = []
    def handler(request):
        calls.append(request)
        if len(calls) == 2:
            raise httpx.ConnectError("Synthetic correction outage")
        return response(draft)
    result = await TerraMaxReportRunner(_settings(), transport=httpx.MockTransport(handler)).analyze_objective(**kwargs)
    assert len(calls) == 2 and len(result.sub_analyses) == 1


@pytest.mark.anyio
async def test_synthesis_validation_falls_back_to_retained_findings_without_reanalysis():
    draft, kwargs = objective_fixture()
    calls = []
    def handler(request):
        calls.append(request)
        return response({"title": "Internal dataset", "executive_summary": "N=0 trials.", "closing_note": "schema"})
    from intel_mcp.max_report import MaxObjectiveResult
    section = MaxObjectiveResult.model_validate(draft)
    result = await TerraMaxReportRunner(_settings(), transport=httpx.MockTransport(handler)).synthesize(
        context="Endpoint decisions", analyzed_cohort={"totalTrials": 6}, sections=[section])
    assert len(calls) == 2
    assert section.summary_sentences[0] in result.executive_summary
    assert "N=0" not in result.model_dump_json() and "dataset" not in result.model_dump_json()


@pytest.mark.anyio
async def test_permanently_invalid_sap_recovers_only_catalogued_fields_and_all_analyses():
    plan = _plan()
    groups, metadata = max_group_variables(plan)
    profile = _profile("2026-000001-00-00")
    catalogue = build_field_catalog([profile])
    calls = []
    def handler(request):
        calls.append(request)
        return response({"direct_variables": [{"profile_path": ["not", "a", "path"]}], "analyses": []})
    result = await TerraMaxReportRunner(_settings(), transport=httpx.MockTransport(handler)).build_analysis_plan(
        context="Endpoint decisions", insights="Trial characteristics", approved_plan=plan,
        sample_profiles=[profile], field_catalog=catalogue, group_variables=groups, segment_metadata=metadata)
    assert len(calls) == 2
    assert len(result.analyses) == len(plan["reportSections"])
    assert {item.profile_path for item in result.direct_variables}.issubset({item["path"] for item in catalogue})
    validate_max_analysis_plan(result.model_dump_json(), approved_plan=plan, field_catalog=catalogue,
                               group_variables=groups, analysis_count=len(plan["reportSections"]))


def test_screen_recovery_never_joins_unknown_or_duplicate_identity_to_a_requested_trial():
    entry = {"tier": "exclude", "relevance_score": 99, "segment_keys": [], "uncertain_segment_keys": [], "rationale": "Excluded"}
    result = recover_screen([{"assessments": [{**entry, "trial_id": "A"}, {**entry, "trial_id": "A"},
        {**entry, "trial_id": "UNKNOWN"}]}], ["A", "B"], ["group"])
    assert [item.trial_id for item in result] == ["A", "B"]
    assert all(item.tier == "adjacent" and not item.segment_keys for item in result)


@pytest.mark.anyio
async def test_max_extraction_corrects_once_then_keeps_valid_facts_and_nulls():
    calls = []
    def handler(request):
        calls.append(json.loads(request.content))
        return response({"values": {"endpoint": "PFS", "age": "unknown", "unexpected": 123}})
    variables = [ExtractionVariable(name="endpoint", instruction="Return primary endpoint.", value_type="string"),
                 ExtractionVariable(name="age", instruction="Return minimum age.", value_type="number")]
    result = await TerraExtractor(_settings(), transport=httpx.MockTransport(handler)).extract(
        trial_id="A", profile={}, variables=variables, advisory_validation=True)
    assert result == {"endpoint": "PFS", "age": None}
    assert len(calls) == 2
    assert "Correction:" in calls[1]["input"][0]["content"][0]["text"]


def test_text_is_not_duplicated_in_group_summaries():
    text = "Long source passage. " * 1000
    summaries = summarize_dataset([{"segment_keys": ["broad"], "values": {"source_text": text}}],
        {"source_text": {"kind": "text"}}, [{"key": "broad", "label": "Broad"}])
    assert text not in json.dumps(summaries)
