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
    r"\b[a-z][a-z0-9]*_[a-z0-9_]+\b|```|https?://|\bN\s*(?:=|:)\s*0\b|"
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


def filter_objective(result, rows, definitions):
    """Validate denominators from real rows; discard invalid findings before synthesis.

    Missing support is never inferred from an LLM's N or from overall cohort size.
    A contrast must identify every compared group. Small-N exceptions are restricted
    to directly relevant descriptive precedents, not comparative statistics.
    """
    by_id = {row["alias"]: row for row in rows}
    retained = []
    for sub in result.sub_analyses:
        try:
            validate_public_text(_text(sub))
            supports = sub.visual.supports
            if {s.value_index for s in supports} != set(range(len(sub.visual.values))):
                continue
            small = False
            valid = True
            for support in supports:
                ids = set(support.trial_ids)
                names = support.variable_names
                if not ids or not ids.issubset(by_id) or not set(names).issubset(definitions):
                    valid = False
                    break
                if support.segment_key is not None and any(support.segment_key not in by_id[i].get("segment_keys", []) for i in ids):
                    valid = False
                    break
                # Every listed supporting trial must actually supply these variables.
                actual = [by_id[i] for i in ids if all(_present(by_id[i].get("values", {}).get(n)) for n in names)]
                if len(actual) != len(ids):
                    valid = False
                    break
                if len(actual) < 5:
                    small = True
                    if not sub.small_sample_reason.strip() or any(r.get("relevance_tier") not in {"exact", "close"} for r in actual):
                        valid = False
                        break
            if not valid:
                continue
            if small and (len(sub.visual.values) > 1 or len(supports) > 1 or SMALL_COMPARISON.search(_text(sub))):
                continue
            # Named recommendations cannot borrow the chart's larger denominator.
            supporting_ids = {i for support in supports for i in support.trial_ids}
            for item in sub.items:
                ids = set(item.trial_ids)
                if not ids or not ids.issubset(supporting_ids):
                    valid = False
                    break
                if len(ids) < 5 and (not sub.small_sample_reason.strip()
                    or any(by_id[i].get("relevance_tier") not in {"exact", "close"} for i in ids)
                    or SMALL_COMPARISON.search(" ".join([item.label, item.value, item.explanation]))):
                    valid = False
                    break
            if not valid:
                continue
            # A zero trial-count category is an empty result, not a graph slot.
            if re.search(r"\b(?:trials?|studies)\b", sub.visual.unit, re.I) and any(v == 0 for v in sub.visual.values):
                continue
            retained.append(sub)
        except ValueError:
            continue
    changed = len(retained) != len(result.sub_analyses)
    result.sub_analyses = retained
    result.limitations = []
    if changed:
        result.qa_warnings.append("publication_findings_omitted")
        # Draft-level prose could refer to removed findings. Reuse a retained,
        # validated interpretation instead; synthesis runs later on retained work.
        result.summary_sentences = [retained[0].interpretation if retained else ""]
        result.conclusion = ""
    else:
        try:
            validate_public_text(" ".join([*result.summary_sentences, result.conclusion]))
        except ValueError:
            result.summary_sentences = [retained[0].interpretation if retained else ""]
            result.conclusion = ""
    try:
        validate_public_text(result.title)
    except ValueError:
        result.sub_analyses = []
        result.summary_sentences = [""]
        result.conclusion = ""
    return result


def public_section(result):
    """Remove support metadata from both report JSON and reducer inputs."""
    private = {"trial_ids", "supports", "small_sample_reason", "limitations", "qa_warnings"}
    def clean(value):
        if isinstance(value, dict):
            return {k: clean(v) for k, v in value.items() if k not in private}
        if isinstance(value, list):
            return [clean(v) for v in value]
        return value
    return clean(result.model_dump(mode="json"))
