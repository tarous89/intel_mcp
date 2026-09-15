"""Deterministic group accounting for every Max objective, without extra model calls."""
from __future__ import annotations

from collections import Counter
from typing import Any


def examined_groups(rows: list[dict], metadata: list[dict]) -> list[dict]:
    groups = []
    for segment in metadata:
        members = [row["alias"] for row in rows if segment["key"] in row.get("segment_keys", [])]
        if members:
            groups.append({"key": segment["key"], "label": segment["label"], "trial_ids": members})
    unassigned = [row["alias"] for row in rows if not row.get("segment_keys")]
    if unassigned and metadata:
        groups.append({"key": "unassigned_trials", "label": "Other relevant trials", "trial_ids": unassigned})
    return groups


def check_group_assessments(result: Any, groups: list[dict]) -> list[dict]:
    """Assess model-authored coverage before any publication filtering.

    These records are private correction signals, never report-fatal gates.
    A shared finding may cover overlapping groups,
    but merely including one of their members in a pooled denominator is not a
    group comparison. The analyst must supply a separate segment support.
    """
    expected = {group["key"]: set(group["trial_ids"]) for group in groups}
    reviews = result.group_assessments
    counts = Counter(review.segment_key for review in reviews)
    issues = []
    audit = []
    if set(counts) != set(expected) or any(count != 1 for count in counts.values()):
        issues.append("publication:groups:missing_duplicate_or_unknown_assessment")
        for key in expected:
            if counts[key] != 1:
                issues.append(f"publication:groups:{key}:assessment_count_{counts[key]}")
    findings = {finding.title: finding for finding in result.sub_analyses}
    if groups and len(findings) != len(result.sub_analyses):
        issues.append("publication:groups:ambiguous_finding_titles")
    for review in reviews:
        key = review.segment_key
        ids = set(review.trial_ids)
        invalid = key not in expected or not ids.issubset(expected.get(key, set()))
        reasons = ["unknown_group_or_member"] if invalid else []
        supported_titles = []
        if review.status == "reported":
            invalid |= not review.finding_titles
            if not review.finding_titles:
                reasons.append("missing_finding_references")
            supporting_ids = set()
            for title in review.finding_titles:
                finding = findings.get(title)
                supports = [] if finding is None else [
                    support for support in finding.visual.supports
                    if support.segment_key == (None if key == "unassigned_trials" else key)
                    and set(support.trial_ids).issubset(expected.get(key, set()))
                    and support.trial_ids
                ]
                if not supports:
                    invalid = True
                    reasons.append("missing_finding" if finding is None else "missing_group_support")
                else:
                    supported_titles.append(title)
                    supporting_ids.update(i for support in supports for i in support.trial_ids)
            # New wire responses omit this redundant union. Derive it from the
            # group-specific supports; validate it only when legacy drafts supply it.
            if ids and ids != supporting_ids:
                invalid = True
                reasons.append("denominator_union_mismatch")
            ids = supporting_ids
        else:
            # A reason must explain clinical non-applicability or unavailable
            # analytical evidence, not silently assign the group elsewhere.
            invalid |= bool(review.finding_titles) or bool(ids) or len(review.reason.strip()) < 40
            if invalid:
                reasons.append("invalid_nonpublication_disposition")
        if invalid:
            location = key if key in expected else "unknown_group"
            issues.append(f"publication:groups:{location}:unsupported_assessment:{','.join(sorted(set(reasons)))}")
        audit.append({"segment_key": key, "status": review.status, "reason": review.reason,
                      "trial_ids": sorted(ids), "finding_titles": supported_titles,
                      "valid": not invalid, "issues": sorted(set(reasons))})
    result.qa_warnings.extend(issues)
    return audit


def publication_dispositions(audit, result, groups):
    """Publication omission does not erase the fact that a group was examined."""
    assessments = {item["segment_key"]: item for item in audit}
    published = []
    for group in groups:
        key = group["key"]
        item = dict(assessments.get(key, {"segment_key": key, "status": "unresolved",
                    "reason": "No valid assessment returned after bounded correction.",
                    "trial_ids": [], "finding_titles": [], "valid": False}))
        titles = [finding.title for finding in result.sub_analyses if any(
            support.segment_key == (None if key == "unassigned_trials" else key)
            and support.trial_ids and set(support.trial_ids).issubset(group["trial_ids"])
            for support in finding.visual.supports)]
        item["publishedFindingTitles"] = titles
        item["publicationStatus"] = "published" if titles else "omitted"
        published.append(item)
    return published


def order_group_findings(result, metadata):
    """Keep the planned broad-to-specific order without changing any measure.

    Only reorder chart values when each has one explicit group identity. Ranked
    categories within a group and differences supported by multiple groups retain
    their original order. Remap support indices together with labels and values.
    """
    ranks = {item["key"]: index for index, item in enumerate(metadata)}
    unknown = len(ranks)
    for finding in result.sub_analyses:
        visual = finding.visual
        value_groups = [
            {support.segment_key for support in visual.supports if support.value_index == index}
            for index in range(len(visual.values))
        ]
        if value_groups and all(len(keys) == 1 and next(iter(keys)) in ranks for keys in value_groups):
            order = sorted(range(len(value_groups)), key=lambda index: ranks[next(iter(value_groups[index]))])
            if order != list(range(len(order))):
                visual.labels = [visual.labels[index] for index in order]
                visual.values = [visual.values[index] for index in order]
                new_indices = {old: new for new, old in enumerate(order)}
                for support in visual.supports:
                    support.value_index = new_indices[support.value_index]
                visual.supports.sort(key=lambda support: support.value_index)
    result.sub_analyses.sort(key=lambda finding: min(
        (ranks.get(support.segment_key, unknown) for support in finding.visual.supports),
        default=unknown,
    ))
    return result


def group_accounting_complete(result: Any) -> bool:
    return not any(issue.startswith("publication:groups:") for issue in result.qa_warnings)
