"""Conservative recovery for model-authored Max contracts, never new evidence.

Strict validators remain useful correction signals. After the bounded correction,
retain independently valid objects and represent unresolved facts as unknown.
"""
from __future__ import annotations

import json
from collections import Counter

from pydantic import ValidationError


def object_value(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return {}
    return value if isinstance(value, dict) else {}


def list_value(value):
    return value if isinstance(value, list) else []


def recover_objective(raw, title):
    from intel_mcp.max_report import MaxObjectiveResult, MaxSubAnalysisResult, MaxGroupAssessment
    data = object_value(raw)
    findings, assessments = [], []
    for item in list_value(data.get("sub_analyses"))[:8]:
        try:
            findings.append(MaxSubAnalysisResult.model_validate(item))
        except (ValidationError, ValueError):
            continue  # Never guess a missing value, denominator or chart alignment.
    for item in list_value(data.get("group_assessments"))[:10]:
        try:
            assessments.append(MaxGroupAssessment.model_validate(item))
        except (ValidationError, ValueError):
            continue
    result = MaxObjectiveResult(
        title=title or "Clinical trial analysis", summary_sentences=[""],
        conclusion="Interpret the findings in their clinical context.", limitations=[],
        sub_analyses=findings, group_assessments=assessments,
    )
    result.qa_warnings.append("publication:objective:structural_recovery")
    return result


def fallback_synthesis(sections):
    from intel_mcp.max_report import MaxFinalSynthesis
    from intel_mcp.max_report_quality import validate_public_text
    sentences = []
    for section in sections:
        for sentence in section.summary_sentences:
            try:
                validate_public_text(sentence)
            except ValueError:
                continue
            if sentence.strip() and sentence not in sentences:
                sentences.append(sentence)
    # No inference, invented recommendation, or claim that every group was covered.
    return MaxFinalSynthesis(
        title="Clinical trial review",
        executive_summary=" ".join(sentences[:3]) or "The selected trials are summarized below.",
        closing_note="Interpret trial characteristics in their disease and treatment context.",
    )


def recover_sap(drafts, approved_plan, field_catalog, group_variables, analysis_count, segment_metadata):
    from intel_mcp.max_report import (
        AnalysisSpecification, DirectVariable, MaxAnalysisPlan, SemanticVariable,
        ensure_investigator_analysis_variable,
    )
    indices = list(range(analysis_count))
    catalogue = {item["path"]: item for item in field_catalog}
    used = {item.name for item in group_variables}
    direct, semantic, specs = [], [], {}
    for draft in reversed(drafts):
        data = object_value(draft)
        for raw in list_value(data.get("direct_variables")):
            if not isinstance(raw, dict) or not isinstance(raw.get("profile_path"), str) or raw["profile_path"] not in catalogue:
                continue
            try:
                item = DirectVariable.model_validate({**raw,
                    "kind": catalogue[raw["profile_path"]]["kind"], "analysis_indices": indices})
            except (ValidationError, ValueError):
                continue
            if item.name not in used and len(direct) < 59:
                direct.append(item)
                used.add(item.name)
        for raw in list_value(data.get("semantic_variables")):
            if not isinstance(raw, dict):
                continue
            if not isinstance(raw.get("value_type"), str):
                continue
            kind = {"number": "numeric", "integer": "numeric", "boolean": "boolean",
                    "string": "categorical", "string_array": "categorical"}.get(raw.get("value_type"))
            try:
                item = SemanticVariable.model_validate({**raw, "kind": kind, "analysis_indices": indices})
            except (ValidationError, ValueError):
                continue
            if item.name not in used and len(semantic) < 20 - len(group_variables):
                semantic.append(item)
                used.add(item.name)
        for raw in list_value(data.get("analyses")):
            if isinstance(raw, dict) and isinstance(raw.get("analysis_index"), int):
                specs.setdefault(raw["analysis_index"], raw)
    if not direct:
        # Catalogue fields are actual source paths; reserve capacity for required PIs.
        for number, field in enumerate(field_catalog[:30]):
            name = f"profile_field_{number}"
            while name in used:
                name += "_value"
            direct.append(DirectVariable(name=name, label=field.get("label", "Trial characteristic")[:120],
                description="Recorded trial characteristic.", profile_path=field["path"],
                kind=field["kind"], analysis_indices=indices))
            used.add(name)
    names = [item.name for item in [*direct, *semantic]] or [item.name for item in group_variables]
    analyses = []
    for index in indices:
        raw = specs.get(index, {})
        selected = [name for name in list_value(raw.get("variable_names")) if isinstance(name, str) and name in used]
        analyses.append(AnalysisSpecification(analysis_index=index,
            purpose="Evaluate the approved clinical question across all examined groups.",
            methods=["Describe supported trial characteristics", "Compare clinically applicable groups"],
            variable_names=(selected or names)[:60], segment_keys=[item["key"] for item in segment_metadata]))
    result = MaxAnalysisPlan(rationale="Retain valid extraction rules and recorded fields after plan correction.",
                            direct_variables=direct, semantic_variables=semantic, analyses=analyses)
    return ensure_investigator_analysis_variable(result, approved_plan)


def recover_screen(drafts, trial_ids, segment_keys):
    from intel_mcp.max_candidate_screening import CandidateAssessment
    by_id = {}
    for draft in drafts:
        data = object_value(draft).get("assessments")
        if isinstance(data, dict):
            entries = [{**value, "trial_id": key} for key, value in data.items()
                       if isinstance(value, dict) and "trial_id" not in value]
        else:
            entries = [entry for entry in list_value(data) if isinstance(entry, dict)]
        counts = Counter(entry.get("trial_id") for entry in entries if isinstance(entry.get("trial_id"), str))
        for entry in entries:
            key = entry.get("trial_id")
            if not isinstance(key, str) or key not in trial_ids:
                continue
            if counts[key] != 1:
                by_id.pop(key, None)
                continue
            try:
                item = CandidateAssessment.model_validate(entry)
            except (ValidationError, ValueError):
                by_id.pop(key, None)
                continue
            if set(item.segment_keys + item.uncertain_segment_keys).issubset(segment_keys):
                by_id[key] = item
            else:
                by_id.pop(key, None)
    return [by_id.get(key) or CandidateAssessment(trial_id=key, tier="adjacent", relevance_score=0,
            segment_keys=[], uncertain_segment_keys=segment_keys,
            rationale="Screening remains unresolved; retain for full-profile assessment.") for key in trial_ids]
