from __future__ import annotations

import hashlib
import json
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from intel_mcp.models import CountryCode, Modality, TherapeuticArea
from intel_mcp.report_output import report_schema


CANDIDATE_POOL_TARGET = 500
MAX_CANDIDATE_POOL = 1_000
MAX_CANDIDATE_FILTERS = 8
MAX_CANDIDATE_SCREEN_BATCH = 25
MAX_CANDIDATE_SCREEN_CONCURRENCY = 5
CANDIDATE_SCREENING_SCHEMA_VERSION = "1.2.0"
MAX_SELECTION_SEGMENTS = 9  # one shared group plus four two-segment Max groups

CandidateTier = Literal["exact", "close", "adjacent", "exclude"]


class CandidateFilter(BaseModel):
    """One deterministic, profile-backed candidate-pool query.

    Different populated dimensions combine with AND. Values within one dimension
    use contains-any semantics, matching the public filtering contract.
    """

    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=120)
    therapeutic_areas: list[TherapeuticArea] | None = Field(default=None, min_length=1, max_length=34)
    phase: list[Literal[1, 2, 3, 4]] | None = Field(default=None, min_length=1, max_length=4)
    modalities: list[Modality] | None = Field(default=None, min_length=1, max_length=18)
    country_codes: list[CountryCode] | None = Field(default=None, min_length=1, max_length=50)
    title_terms: list[Annotated[str, Field(min_length=2, max_length=100)]] | None = Field(default=None, min_length=1, max_length=5)

    @model_validator(mode="after")
    def contains_a_filter(self) -> "CandidateFilter":
        if not any((self.therapeutic_areas, self.phase, self.modalities, self.country_codes, self.title_terms)):
            raise ValueError("A candidate filter must contain at least one deterministic dimension.")
        return self


class CandidateFilterPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rationale: str = Field(min_length=1, max_length=800)
    filters: list[CandidateFilter] = Field(min_length=3, max_length=MAX_CANDIDATE_FILTERS)


class CandidateAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trial_id: str = Field(min_length=1, max_length=80)
    tier: CandidateTier
    relevance_score: int = Field(ge=0, le=100)
    segment_keys: list[str] = Field(max_length=MAX_SELECTION_SEGMENTS)
    uncertain_segment_keys: list[str] = Field(max_length=MAX_SELECTION_SEGMENTS)
    rationale: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def unique_segments(self) -> "CandidateAssessment":
        if len(self.segment_keys) != len(set(self.segment_keys)):
            raise ValueError("Confirmed segment keys must be unique.")
        if len(self.uncertain_segment_keys) != len(set(self.uncertain_segment_keys)):
            raise ValueError("Uncertain segment keys must be unique.")
        if set(self.segment_keys) & set(self.uncertain_segment_keys):
            raise ValueError("A segment cannot be both confirmed and uncertain.")
        return self


class CandidateScreenBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assessments: list[CandidateAssessment]


def _nullable_array(items: dict[str, Any], maximum: int) -> dict[str, Any]:
    return {
        "anyOf": [
            {"type": "array", "minItems": 1, "maxItems": maximum, "items": items},
            {"type": "null"},
        ]
    }


def candidate_filter_plan_schema(
    *,
    therapeutic_areas: list[str],
    modalities: list[str],
) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "rationale": {"type": "string"},
            "filters": {
                "type": "array",
                "minItems": 3,
                "maxItems": MAX_CANDIDATE_FILTERS,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "label": {"type": "string"},
                        "therapeutic_areas": _nullable_array(
                            {"type": "string", "enum": therapeutic_areas}, 34
                        ),
                        "phase": _nullable_array({"type": "integer", "enum": [1, 2, 3, 4]}, 4),
                        "modalities": _nullable_array(
                            {"type": "string", "enum": modalities}, 18
                        ),
                        "country_codes": _nullable_array(
                            {"type": "string", "pattern": "^[A-Za-z]{2}$"}, 50
                        ),
                        "title_terms": _nullable_array({"type": "string", "minLength": 2, "maxLength": 100}, 5),
                    },
                    "required": [
                        "label",
                        "therapeutic_areas",
                        "phase",
                        "modalities",
                        "country_codes",
                        "title_terms",
                    ],
                },
            },
        },
        "required": ["rationale", "filters"],
    }


def candidate_screen_schema(trial_ids: list[str], segment_keys: list[str]) -> dict[str, Any]:
    """Require one assessment per ID in the wire contract, independent of order."""
    assessment = report_schema(CandidateAssessment)
    assessment["properties"].pop("trial_id")
    assessment["required"].remove("trial_id")
    for field in ("segment_keys", "uncertain_segment_keys"):
        assessment["properties"][field]["maxItems"] = min(len(segment_keys), MAX_SELECTION_SEGMENTS)
        assessment["properties"][field]["items"] = {"type": "string", "enum": segment_keys}
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "assessments": {
                "type": "object",
                "additionalProperties": False,
                "properties": {trial_id: {"$ref": "#/$defs/assessment"} for trial_id in trial_ids},
                "required": trial_ids,
            }
        },
        "required": ["assessments"],
        "$defs": {"assessment": assessment},
    }


def validate_candidate_screen(
    payload: dict[str, Any],
    *,
    trial_ids: list[str],
    segment_keys: list[str],
) -> list[CandidateAssessment]:
    """Join by identity, accepting legacy arrays only with exact unique coverage.

    Reordering is harmless. Missing, duplicate or unknown trials are not, and
    must never silently shrink the shared pool or attach another trial's verdict.
    """
    if len(trial_ids) != len(set(trial_ids)):
        raise ValueError("Candidate screening input contains duplicate trial IDs.")
    if isinstance(payload, dict) and isinstance(payload.get("assessments"), dict):
        entries = []
        for trial_id, assessment in payload["assessments"].items():
            if not isinstance(assessment, dict) or "trial_id" in assessment:
                raise ValueError("Candidate screening returned an invalid keyed assessment.")
            entries.append({"trial_id": trial_id, **assessment})
        payload = {**payload, "assessments": entries}
    result = CandidateScreenBatch.model_validate(payload)
    returned_ids = [item.trial_id for item in result.assessments]
    if len(returned_ids) != len(set(returned_ids)):
        raise ValueError("Candidate screening returned duplicate trial assessments.")
    if set(returned_ids) - set(trial_ids):
        raise ValueError("Candidate screening returned unknown trial IDs.")
    if set(trial_ids) - set(returned_ids):
        raise ValueError("Candidate screening omitted requested trials.")
    allowed_segments = set(segment_keys)
    if any(
        not set([*item.segment_keys, *item.uncertain_segment_keys]).issubset(allowed_segments)
        for item in result.assessments
    ):
        raise ValueError("Candidate screening returned an unknown segment.")
    by_id = {item.trial_id: item for item in result.assessments}
    return [by_id[trial_id] for trial_id in trial_ids]


def candidate_screening_key(trial_id: str, segments: list[dict[str, Any]]) -> str:
    canonical = json.dumps(
        {
            "schema_version": CANDIDATE_SCREENING_SCHEMA_VERSION,
            "trial_id": trial_id,
            "segments": segments,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def select_screened_candidates(
    assessments: list[CandidateAssessment],
    *,
    segment_cohort_indices: dict[str, int],
    maximum: int,
    trial_cohort_indices: dict[str, set[int]] | None = None,
) -> list[CandidateAssessment]:
    """Select one broad pool; planned group labels diversify, never gate admission."""

    if maximum <= 0:
        return []
    input_order = {item.trial_id: index for index, item in enumerate(assessments)}
    tier_order = {"exact": 0, "close": 1, "adjacent": 2, "exclude": 3}

    def rank(item: CandidateAssessment) -> tuple[Any, ...]:
        return (
            tier_order[item.tier],
            -item.relevance_score,
            -len(item.segment_keys),
            -len(item.uncertain_segment_keys),
            input_order[item.trial_id],
            item.trial_id,
        )

    def approved_cohort_indices(item: CandidateAssessment) -> set[int]:
        indices = set(
            segment_cohort_indices[key]
            for key in [*item.segment_keys, *item.uncertain_segment_keys]
            if key in segment_cohort_indices
        )
        if trial_cohort_indices is not None:
            indices.update(trial_cohort_indices.get(item.trial_id, set()))
        return indices

    eligible = sorted(
        (
            item
            for item in assessments
            if item.tier != "exclude"
        ),
        key=rank,
    )
    cohort_indices = sorted(set(segment_cohort_indices.values()))
    if not cohort_indices:
        return eligible[:maximum]

    adjacent_count = max(0, len(cohort_indices) - 1)
    primary = maximum if adjacent_count == 0 else min(maximum, max(40, maximum - 15 * adjacent_count))
    remaining = max(0, maximum - primary)
    base, extra = divmod(remaining, adjacent_count) if adjacent_count else (0, 0)
    quotas = {
        cohort_index: (
            primary
            if position == 0
            else base + (1 if position - 1 < extra else 0)
        )
        for position, cohort_index in enumerate(cohort_indices)
    }

    selected: list[CandidateAssessment] = []
    selected_ids: set[str] = set()
    for cohort_index in cohort_indices:
        candidates = [
            item
            for item in eligible
            if item.trial_id not in selected_ids
            and cohort_index in approved_cohort_indices(item)
        ]
        for item in candidates[: quotas[cohort_index]]:
            selected.append(item)
            selected_ids.add(item.trial_id)

    for item in eligible:
        if len(selected) >= maximum:
            break
        if item.trial_id not in selected_ids:
            selected.append(item)
            selected_ids.add(item.trial_id)
    return selected


def screening_summary(
    assessments: list[CandidateAssessment],
    selected: list[CandidateAssessment],
) -> dict[str, Any]:
    return {
        "screenedCandidates": len(assessments),
        "selectedTrials": len(selected),
        "selectionTiers": [
            {
                "tier": tier,
                "trialCount": sum(1 for item in selected if item.tier == tier),
            }
            for tier in ("exact", "close", "adjacent")
        ],
    }
