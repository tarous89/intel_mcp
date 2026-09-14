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
    """Require an explicit disposition and retained, group-specific support.

    These records are private. A shared finding may cover overlapping groups,
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
    findings = {finding.title: finding for finding in result.sub_analyses}
    if groups and len(findings) != len(result.sub_analyses):
        issues.append("publication:groups:ambiguous_finding_titles")
    for review in reviews:
        key = review.segment_key
        ids = set(review.trial_ids)
        invalid = key not in expected or not ids.issubset(expected.get(key, set()))
        supported_titles = []
        if review.status == "reported":
            invalid |= not ids or not review.finding_titles
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
                else:
                    supported_titles.append(title)
                    supporting_ids.update(i for support in supports for i in support.trial_ids)
            invalid |= ids != supporting_ids
        else:
            # A reason must explain clinical non-applicability or unavailable
            # analytical evidence, not silently assign the group elsewhere.
            invalid |= bool(review.finding_titles) or bool(ids) or len(review.reason.strip()) < 40
        if invalid:
            issues.append(f"publication:groups:{key}:unsupported_assessment")
        audit.append({"segment_key": key, "status": review.status, "reason": review.reason,
                      "trial_ids": sorted(ids), "finding_titles": supported_titles,
                      "valid": not invalid})
    result.qa_warnings.extend(issues)
    return audit


def group_accounting_complete(result: Any) -> bool:
    return not any(issue.startswith("publication:groups:") for issue in result.qa_warnings)
