"""Model-free publication gates; detailed support remains in the frozen dataset."""
from __future__ import annotations

import re

# Clinical qualifications remain allowed. Execution/audit detail and source IDs do not.
INTERNAL = re.compile(
    r"\bT\d{3,}\b|\bNCT\d{8}\b|\b\d{4}-\d{6}-\d{2}(?:-\d{2})?\b|"
    r"\b(?:dataset|database|schema|json|boolean|tokens?|workflow|backfill|LLM|GPT|"
    r"supplied rows?|frozen cohort|trial profiles?|profile extraction|"
    r"semantic (?:segment|classification)|rule-based|identity (?:normalization|resolution|sensitivity)|"
    r"email-defined|normalized.name|nonmissing|missingness|field availability|"
    r"documentation recency|lifecycle (?:update|documentation|label)|"
    r"evidence (?:notes|base|groups)|approved plan|system (?:message|prompt)|"
    r"instructions?|lowercased|alphabetical tie.breaker)\b|"
    r"\b[a-z][a-z0-9]*_[a-z0-9_]+\b|```|https?://|\b(?:N|sample size|denominator)\s*(?:=|:|of|is)?\s*0\b|"
    r"\b(?:zero|0|no)\s+(?:(?:direct|exact|eligible|matching|available|relevant|phase[ -]?\d|single.arm|ADC|CRPC)\s+){0,8}(?:trials?|analogues?|comparators?|matches)\b",
    re.I,
)
SMALL_COMPARISON = re.compile(r"%|percentage|prevalence|correlat|p[ -]?value|significan|\bvs\.?\b|versus|compared|higher|lower|gap", re.I)


def validate_public_text(text: str) -> None:
    if INTERNAL.search(text):
        raise ValueError("Remove internal processing language, source identifiers and empty-group commentary from reader-facing text.")


def _text(sub):
    return " ".join([sub.title, sub.interpretation, sub.visual.title, sub.visual.unit, sub.visual.note,
                     *sub.visual.labels, *[s for item in sub.items for s in (item.label, item.value, item.explanation)]])


def _present(value):
    return value is not None and value != "" and value != [] and value != {}


def _small_precedent(sub, actual):
    reason = sub.small_sample_reason.strip()
    if not reason or not actual:
        return False
    if all(row.get("relevance_tier") in {"exact", "close"} for row in actual):
        return True
    # Global adjacency does not decide objective-specific usefulness. Require a
    # concrete rationale grounded in each trial's supplied facts, not a slogan.
    terms = set(re.findall(r"[a-z]{4,}", reason.casefold())) - {
        "very", "relevant", "trial", "trials", "study", "studies", "direct",
        "directly", "clinical", "objective", "evidence", "important", "supports",
    }
    return len(reason) >= 40 and all(
        row.get("relevance_tier") != "exclude" and len(terms & set(
            re.findall(r"[a-z]{4,}", str(row.get("values", {})).casefold())
        )) >= 2 for row in actual
    )


def filter_objective(result, rows, definitions):
    """Prune unsupported units; request bounded repair through private QA reasons.

    Never silently change an analytical denominator while retaining its metric.
    Invalid series can be removed only when remaining prose is independent.
    """
    by_id = {row["alias"]: row for row in rows}
    retained = []
    changed = False
    def reject(location, reason):
        nonlocal changed
        changed = True
        result.qa_warnings.append(f"publication:{location}:{reason}")

    for sub_index, sub in enumerate(result.sub_analyses):
        location = f"finding_{sub_index}"
        try:
            validate_public_text(" ".join([sub.title, sub.interpretation, sub.visual.title,
                                          sub.visual.unit, sub.visual.note]))
        except ValueError:
            reject(location, "internal_or_empty_group_prose")
            continue
        valid_indices, valid_supports = [], []
        for index, (label, value) in enumerate(zip(sub.visual.labels, sub.visual.values)):
            supports = [support for support in sub.visual.supports if support.value_index == index]
            reason = None
            try:
                validate_public_text(label)
            except ValueError:
                reason = "invalid_series_label"
            if not supports:
                reason = "missing_denominator"
            for support in supports:
                ids = set(support.trial_ids)
                names = support.variable_names
                if not ids or not ids.issubset(by_id) or not set(names).issubset(definitions):
                    reason = "empty_or_unknown_support"
                    break
                numerator = support.numerator_trial_ids
                if numerator is not None:
                    numerator_ids = set(numerator)
                    if not numerator_ids:
                        reason = "empty_numerator"
                        break
                    if not numerator_ids.issubset(ids):
                        reason = "numerator_outside_denominator"
                        break
                    # A single frequency/count must agree with the supplied
                    # distinct trial identities. Differences have null numerators.
                    if len(supports) == 1:
                        expected = None
                        tolerance = 1e-9
                        if re.search(r"%|percent", sub.visual.unit, re.I):
                            expected = 100 * len(numerator_ids) / len(ids)
                            tolerance = 0.50000001
                        elif re.fullmatch(r"(?:trials?|studies|n|count)", sub.visual.unit.strip(), re.I):
                            expected = len(numerator_ids)
                        if expected is not None and abs(value - expected) > tolerance:
                            reason = "metric_does_not_match_support"
                            break
                if support.segment_key is not None and any(support.segment_key not in by_id[i].get("segment_keys", []) for i in ids):
                    reason = "incorrect_segment_denominator"
                    break
                actual = [by_id[i] for i in ids if all(_present(by_id[i].get("values", {}).get(n)) for n in names)]
                if len(actual) != len(ids):
                    reason = "denominator_contains_missing_values"
                    break
                if len(actual) < 5 and (not _small_precedent(sub, actual)
                    or len(supports) > 1 or len(sub.visual.values) > 1
                    or SMALL_COMPARISON.search(_text(sub))):
                    reason = "insufficient_support"
                    break
            if value == 0 and (re.search(r"\b(?:trials?|studies|count|n)\b|%|percent", sub.visual.unit, re.I)) and not re.search(r"difference|change|delta|points", sub.visual.unit, re.I):
                reason = "empty_trial_count"
            if reason:
                reject(f"{location}.series_{index}", reason)
            else:
                valid_indices.append(index)
                valid_supports.extend(supports)
        if not valid_indices:
            continue
        if len(valid_indices) != len(sub.visual.values):
            removed_labels = [label for index, label in enumerate(sub.visual.labels) if index not in valid_indices]
            prose = " ".join([sub.title, sub.interpretation, sub.visual.title, sub.visual.note])
            # A percentage/donut or contrast could change meaning when a series
            # disappears. Preserve only independent descriptive values.
            if sub.visual.kind == "donut" or sub.visual.unit == "%" or SMALL_COMPARISON.search(prose) or re.search(r"\d", prose) or any(label.casefold() in prose.casefold() for label in removed_labels):
                reject(location, "series_removal_requires_prose_repair")
                continue
            remap = {old: new for new, old in enumerate(valid_indices)}
            sub.visual.labels = [sub.visual.labels[i] for i in valid_indices]
            sub.visual.values = [sub.visual.values[i] for i in valid_indices]
            for support in valid_supports:
                support.value_index = remap[support.value_index]
        sub.visual.supports = valid_supports
        supporting_ids = {i for support in valid_supports for i in support.trial_ids}
        kept_items = []
        for index, item in enumerate(sub.items):
            ids = set(item.trial_ids)
            text = " ".join([item.label, item.value, item.explanation])
            reason = None
            try:
                validate_public_text(text)
            except ValueError:
                reason = "internal_item_prose"
            if not ids or not ids.issubset(supporting_ids):
                reason = "unsupported_named_item"
            elif len(ids) < 5 and (not _small_precedent(sub, [by_id[i] for i in ids]) or SMALL_COMPARISON.search(text)):
                reason = "insufficient_named_item_support"
            if reason:
                reject(f"{location}.item_{index}", reason)
                # Item-dependent interpretation needs repair; independent findings survive.
                if item.label.casefold() in sub.interpretation.casefold():
                    reject(location, "item_removal_requires_prose_repair")
                    break
            else:
                kept_items.append(item)
        else:
            sub.items = kept_items
            sub.trial_ids = sorted(supporting_ids)
            retained.append(sub)
    result.sub_analyses = retained
    result.limitations = []
    if changed or not retained:
        result.summary_sentences = [""]
        result.conclusion = ""
    else:
        try:
            validate_public_text(" ".join([*result.summary_sentences, result.conclusion]))
        except ValueError:
            reject("objective", "internal_or_empty_summary")
            result.summary_sentences = [""]
            result.conclusion = ""
    try:
        validate_public_text(result.title)
    except ValueError:
        reject("objective", "invalid_title")
        result.sub_analyses = []
        result.summary_sentences = [""]
        result.conclusion = ""
    return result


def public_cohort_summary(cohort):
    groups = []
    for group in cohort.get("cohorts", []):
        if group.get("trialCount", 0) < 5:
            continue
        try:
            validate_public_text(group.get("title", ""))
        except ValueError:
            continue
        groups.append(group)
    return {"totalTrials": cohort["totalTrials"], "cohorts": groups, "overlapping": True}


def public_section(result):
    """Remove support metadata from both report JSON and reducer inputs."""
    private = {"trial_ids", "numerator_trial_ids", "supports", "small_sample_reason", "limitations", "qa_warnings", "group_assessments", "analysis_audit"}
    def clean(value):
        if isinstance(value, dict):
            return {k: clean(v) for k, v in value.items() if k not in private}
        if isinstance(value, list):
            return [clean(v) for v in value]
        return value
    return clean(result.model_dump(mode="json"))
