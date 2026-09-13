from __future__ import annotations

import pytest
from pydantic import ValidationError

from intel_mcp.max_candidate_screening import (
    CandidateAssessment,
    CandidateFilter,
    candidate_filter_plan_schema,
    candidate_screening_key,
    select_screened_candidates,
    validate_candidate_screen,
)
from intel_mcp.max_report_execution import _candidate_pool_limit, _candidate_trial_filters


def test_candidate_filters_use_only_reliable_deterministic_dimensions() -> None:
    candidate = CandidateFilter(
        label="Phase 2 solid-tumor ADCs",
        therapeutic_areas=["Solid Tumor Oncology"],
        phase=[2],
        modalities=["ADC"],
        country_codes=None,
    )
    filters = _candidate_trial_filters(candidate)
    assert filters.therapeutic_areas is not None
    assert filters.phase is not None
    assert filters.modalities is not None
    assert filters.diseases is None

    with pytest.raises(ValidationError):
        CandidateFilter(label="Empty")


def test_candidate_filter_schema_requires_explicit_nullable_fields() -> None:
    schema = candidate_filter_plan_schema(
        therapeutic_areas=["Solid Tumor Oncology"],
        modalities=["ADC"],
    )
    item = schema["properties"]["filters"]["items"]
    assert set(item["required"]) == {
        "label",
        "therapeutic_areas",
        "phase",
        "modalities",
        "country_codes",
    }
    assert "diseases" not in item["properties"]


def test_candidate_screen_validation_requires_every_trial_once_in_order() -> None:
    payload = {
        "assessments": [
            {
                "trial_id": "T1",
                "tier": "exact",
                "relevance_score": 95,
                "segment_keys": ["primary"],
                "uncertain_segment_keys": [],
                "rationale": "Direct match.",
            },
            {
                "trial_id": "T2",
                "tier": "adjacent",
                "relevance_score": 70,
                "segment_keys": ["adjacent"],
                "uncertain_segment_keys": [],
                "rationale": "Useful comparator.",
            },
        ]
    }
    result = validate_candidate_screen(
        payload,
        trial_ids=["T1", "T2"],
        segment_keys=["primary", "adjacent"],
    )
    assert [item.trial_id for item in result] == ["T1", "T2"]

    payload["assessments"].reverse()
    with pytest.raises(ValueError):
        validate_candidate_screen(
            payload,
            trial_ids=["T1", "T2"],
            segment_keys=["primary", "adjacent"],
        )


def test_selection_excludes_irrelevant_trials_and_preserves_adjacent_representation() -> None:
    assessments = [
        *[
            CandidateAssessment(
                trial_id=f"P{index:03d}",
                tier="exact",
                relevance_score=100 - index,
                segment_keys=["primary"],
                uncertain_segment_keys=[],
                rationale="Primary match.",
            )
            for index in range(100)
        ],
        *[
            CandidateAssessment(
                trial_id=f"A{index:03d}",
                tier="adjacent",
                relevance_score=80 - index,
                segment_keys=["adjacent"],
                uncertain_segment_keys=[],
                rationale="Adjacent comparator.",
            )
            for index in range(20)
        ],
        CandidateAssessment(
            trial_id="X001",
            tier="exclude",
            relevance_score=100,
            segment_keys=[],
            uncertain_segment_keys=[],
            rationale="Outside the plan.",
        ),
    ]
    selected = select_screened_candidates(
        assessments,
        segment_cohort_indices={"primary": 0, "adjacent": 1},
        maximum=100,
    )
    assert len(selected) == 100
    assert sum(item.tier == "adjacent" for item in selected) == 15
    assert all(item.tier != "exclude" for item in selected)


def test_selection_excludes_broad_candidates_without_an_approved_group() -> None:
    assessments = [
        CandidateAssessment(
            trial_id="BROAD-ONLY",
            tier="exact",
            relevance_score=100,
            segment_keys=[],
            uncertain_segment_keys=[],
            rationale="Relevant at screening but not assigned to an approved group.",
        ),
        CandidateAssessment(
            trial_id="SEED-MATCH",
            tier="close",
            relevance_score=80,
            segment_keys=[],
            uncertain_segment_keys=[],
            rationale="Matched an approved deterministic group seed.",
        ),
        CandidateAssessment(
            trial_id="SEGMENT-MATCH",
            tier="adjacent",
            relevance_score=70,
            segment_keys=[],
            uncertain_segment_keys=["adjacent"],
            rationale="Mapped to an approved adjacent segment.",
        ),
    ]

    selected = select_screened_candidates(
        assessments,
        segment_cohort_indices={"primary": 0, "adjacent": 1},
        maximum=100,
        trial_cohort_indices={"BROAD-ONLY": set(), "SEED-MATCH": {0}},
    )

    assert [item.trial_id for item in selected] == ["SEED-MATCH", "SEGMENT-MATCH"]


def test_screening_keys_and_candidate_limit_are_stable_and_bounded() -> None:
    segments = [{"key": "primary", "inclusion_criteria": ["A"]}]
    assert candidate_screening_key("T1", segments) == candidate_screening_key("T1", segments)

    class Limits:
        filtered_trial_ids = 1_000
        profiles = 500
        classified_trials = 700

    assert _candidate_pool_limit(Limits()) == 500
    assert _candidate_pool_limit(None) == 0
