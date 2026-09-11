from __future__ import annotations

from types import SimpleNamespace

import pytest

from intel_mcp.extraction import ExtractionVariable
from intel_mcp.max_report import (
    MaxAnalysisPlan,
    MaxFinalSynthesis,
    MaxObjectiveResult,
    MaxReportError,
)
from intel_mcp.max_report_execution import (
    MaxReportExecutor,
    _discovery_quotas,
    _execution_plan,
    _trial_filters,
)
from intel_mcp.profiles import FullProfileItem


def _plan() -> dict:
    cohorts = [
        {
            "role": "primary",
            "title": "NSCLC trials",
            "details": ["Disease is NSCLC"],
            "maxOnly": False,
            "filterDimension": "disease",
            "discoveryFilter": {"field": "diseases", "values": ["NSCLC"]},
            "selectionSegments": [
                {
                    "key": "nsclc",
                    "label": "NSCLC",
                    "inclusionCriteria": ["Trial Profile concerns NSCLC"],
                    "exclusionCriteria": [],
                }
            ],
        },
        {
            "role": "adjacent",
            "title": "Early-stage NSCLC",
            "details": ["Early-stage disease"],
            "maxOnly": True,
            "filterDimension": None,
            "discoveryFilter": {"field": "phase", "values": ["2", "3"]},
            "selectionSegments": [
                {
                    "key": "early_nsclc",
                    "label": "Early-stage NSCLC",
                    "inclusionCriteria": ["Trial Profile establishes early-stage NSCLC"],
                    "exclusionCriteria": [],
                }
            ],
        },
        {
            "role": "adjacent",
            "title": "Biomarker comparison",
            "details": ["Biomarker-selected versus unselected"],
            "maxOnly": True,
            "filterDimension": None,
            "discoveryFilter": {"field": "modalities", "values": ["Small molecule"]},
            "selectionSegments": [
                {
                    "key": "selected",
                    "label": "Biomarker-selected",
                    "inclusionCriteria": ["Trial Profile requires a biomarker"],
                    "exclusionCriteria": [],
                },
                {
                    "key": "unselected",
                    "label": "Biomarker-unselected",
                    "inclusionCriteria": ["Trial Profile does not require a biomarker"],
                    "exclusionCriteria": [],
                },
            ],
        },
    ]
    sections = [
        {
            "title": f"Shared {index}",
            "sharedAnalysis": {"title": f"Shared {index}", "details": ["Count"]},
            "maxAnalysis": {
                "title": f"Analyze {index}",
                "details": ["Compare", "Interpret"],
            },
        }
        for index in range(5)
    ]
    return {
        "version": 4,
        "studyCohorts": cohorts,
        "exclusionSummary": "Unrelated trials excluded.",
        "reportSections": sections,
    }


def test_discovery_quotas_are_bounded_and_preserve_a_large_primary_pool() -> None:
    for cohort_count in range(3, 6):
        quotas = _discovery_quotas(cohort_count)
        assert len(quotas) == cohort_count
        assert sum(quotas) == 100
        assert quotas[0] >= 40
        assert all(value > 0 for value in quotas)


def test_execution_requires_machine_readable_group_metadata() -> None:
    plan = _plan()
    cohorts, sections = _execution_plan(plan)
    assert len(cohorts) == 3
    assert len(sections) == 5

    old_plan = _plan()
    old_plan["studyCohorts"][1].pop("discoveryFilter")
    with pytest.raises(MaxReportError) as captured:
        _execution_plan(old_plan)
    assert captured.value.code == "MAX_REPORT_PLAN_METADATA_REQUIRED"


def test_discovery_filter_maps_only_supported_structured_fields() -> None:
    phase = _trial_filters({"field": "phase", "values": ["2", "3"]})
    assert phase.phase is not None
    assert phase.phase.values == [2, 3]

    disease = _trial_filters({"field": "diseases", "values": ["NSCLC"]})
    assert disease.diseases is not None
    assert disease.diseases.values == ["NSCLC"]

    with pytest.raises(MaxReportError):
        _trial_filters({"field": "unsupported", "values": ["value"]})


def test_cohort_summary_keeps_overlapping_labels() -> None:
    rows = [
        {"segment_keys": ["nsclc", "early_nsclc", "selected"]},
        {"segment_keys": ["nsclc", "early_nsclc"]},
        {"segment_keys": ["unselected"]},
    ]
    metadata = [
        {"key": "nsclc", "label": "NSCLC", "cohort_title": "NSCLC trials", "cohort_index": 0},
        {"key": "early_nsclc", "label": "Early-stage NSCLC", "cohort_index": 1},
        {"key": "selected", "label": "Biomarker-selected", "cohort_index": 2},
        {"key": "unselected", "label": "Biomarker-unselected", "cohort_index": 2},
    ]
    summary = MaxReportExecutor._cohort_summary(rows, metadata)
    assert summary == {
        "totalTrials": 3,
        "cohorts": [
            {"title": "NSCLC trials", "role": "primary", "trialCount": 2},
            {"title": "Early-stage NSCLC", "role": "adjacent", "trialCount": 2},
            {"title": "Biomarker-selected", "role": "adjacent", "trialCount": 1},
            {"title": "Biomarker-unselected", "role": "adjacent", "trialCount": 1},
        ],
        "overlapping": True,
    }


@pytest.mark.anyio
async def test_dataset_population_fuses_group_classification_and_semantic_extraction() -> None:
    class ExtractionControl:
        def __init__(self) -> None:
            self.operations: list[tuple[str, str]] = []

        async def authorize_extraction(
            self,
            _analysis_id: str,
            key: str,
            _variable_count: int,
            operation: str,
        ) -> SimpleNamespace:
            self.operations.append((key, operation))
            return SimpleNamespace(access=SimpleNamespace(extraction_key=key))

    class Extractor:
        def __init__(self) -> None:
            self.calls: list[tuple[str, list[str]]] = []

        async def extract(self, *, trial_id, profile, variables, model):
            assert model == "gpt-5.6-terra"
            assert "filtering_variables" in profile
            self.calls.append((trial_id, [item.name for item in variables]))
            return {
                "segment_early_nsclc": trial_id.endswith("01-00-00"),
                "endpoint_strategy": "PFS",
            }

    class ReportControl:
        def __init__(self) -> None:
            self.progress_updates = 0

        async def progress(self, _report_run_id: str, _progress: dict) -> None:
            self.progress_updates += 1

    profiles = [
        FullProfileItem.model_validate(
            {
                "eu_number": trial_id,
                "profile_schema_version": "11.0.0",
                "approved_at": None,
                "profile": {
                    "filtering_variables": {"planned_sample_size": sample_size},
                    "classification_variables": {"trial_title": trial_id},
                },
            }
        )
        for trial_id, sample_size in (
            ("2026-000001-00-00", 80),
            ("2026-000002-00-00", 120),
        )
    ]
    analysis_plan = MaxAnalysisPlan.model_validate(
        {
            "rationale": "Reuse structured enrollment and extract one endpoint category.",
            "direct_variables": [
                {
                    "name": "sample_size",
                    "label": "Planned sample size",
                    "description": "Structured planned sample size.",
                    "profile_path": "filtering_variables.planned_sample_size",
                    "kind": "numeric",
                    "analysis_indices": [0, 1, 2, 3, 4],
                }
            ],
            "semantic_variables": [
                {
                    "name": "endpoint_strategy",
                    "label": "Endpoint strategy",
                    "instruction": "Return the canonical primary endpoint strategy.",
                    "value_type": "string",
                    "kind": "categorical",
                    "analysis_indices": [0],
                }
            ],
            "analyses": [
                {
                    "analysis_index": index,
                    "purpose": f"Analysis {index}",
                    "methods": ["Count", "Compare"],
                    "variable_names": ["sample_size"],
                    "segment_keys": ["early_nsclc"],
                }
                for index in range(5)
            ],
        }
    )
    group_variables = [
        ExtractionVariable(
            name="segment_early_nsclc",
            instruction="Return true when the complete profile establishes early-stage NSCLC.",
            value_type="boolean",
        )
    ]
    segment_metadata = [
        {
            "key": "early_nsclc",
            "variable_name": "segment_early_nsclc",
            "label": "Early-stage NSCLC",
        }
    ]

    executor = object.__new__(MaxReportExecutor)
    executor._analysis_control = ExtractionControl()
    executor._extractor = Extractor()
    executor._control = ReportControl()
    rows, _ = await executor._populate_dataset(
        report_run_id="run-123",
        analysis_id="ana_12345678901234567890",
        profiles=profiles,
        discovery_indices={profile.eu_number: {0} for profile in profiles},
        analysis_plan=analysis_plan,
        group_variables=group_variables,
        segment_metadata=segment_metadata,
        primary_segment_key="nsclc",
        progress={"steps": [{"key": "dataset_population", "status": "in_progress"}]},
    )

    assert executor._extractor.calls == [
        ("2026-000001-00-00", ["segment_early_nsclc", "endpoint_strategy"]),
        ("2026-000002-00-00", ["segment_early_nsclc", "endpoint_strategy"]),
    ]
    assert len(executor._analysis_control.operations) == 4
    assert rows[0]["values"]["sample_size"] == 80
    assert rows[0]["segment_keys"] == ["nsclc", "early_nsclc"]
    assert rows[1]["segment_keys"] == ["nsclc"]


@pytest.mark.anyio
async def test_max_executor_runs_the_complete_profile_only_pipeline() -> None:
    plan = _plan()
    profiles = [
        FullProfileItem.model_validate(
            {
                "eu_number": trial_id,
                "profile_schema_version": "11.0.0",
                "approved_at": None,
                "profile": {
                    "filtering_variables": {"planned_sample_size": sample_size},
                    "classification_variables": {"trial_title": trial_id},
                },
            }
        )
        for trial_id, sample_size in (
            ("2026-000001-00-00", 80),
            ("2026-000002-00-00", 120),
        )
    ]

    class ReportControl:
        def __init__(self) -> None:
            self.completed: dict | None = None
            self.failed: tuple | None = None

        async def load(self, _report_run_id: str) -> dict:
            return {
                "status": "queued",
                "tier": "max",
                "context": "Phase 2 NSCLC study",
                "insights": "Endpoints and enrollment",
                "plan": plan,
            }

        async def progress(self, _report_run_id: str, _progress: dict) -> None:
            return None

        async def complete(self, _report_run_id: str, progress: dict, final_report: dict) -> None:
            self.completed = {"progress": progress, "final_report": final_report}

        async def fail(self, _report_run_id: str, code: str, message: str, _progress: dict) -> None:
            self.failed = (code, message)

    class AnalysisControl:
        async def start_analysis(self, _report_run_id: str) -> SimpleNamespace:
            return SimpleNamespace(analysis=SimpleNamespace(analysis_id="ana_12345678901234567890"))

        async def authorize_extraction(
            self,
            _analysis_id: str,
            key: str,
            _variable_count: int,
            _operation: str,
        ) -> SimpleNamespace:
            return SimpleNamespace(access=SimpleNamespace(extraction_key=key))

    class Extractor:
        async def extract(self, *, trial_id, profile, variables, model):
            assert model == "gpt-5.6-terra"
            assert "filtering_variables" in profile
            return {
                variable.name: (
                    trial_id == "2026-000001-00-00"
                    if variable.value_type == "boolean"
                    else "PFS"
                )
                for variable in variables
            }

    class Runner:
        async def build_analysis_plan(self, **kwargs) -> MaxAnalysisPlan:
            assert kwargs["sample_profiles"]
            assert kwargs["segment_metadata"][0]["membership_source"] == "deterministic_discovery"
            return MaxAnalysisPlan.model_validate(
                {
                    "rationale": "Reuse sample size and extract endpoint strategy.",
                    "direct_variables": [
                        {
                            "name": "sample_size",
                            "label": "Planned sample size",
                            "description": "Structured planned sample size.",
                            "profile_path": "filtering_variables.planned_sample_size",
                            "kind": "numeric",
                            "analysis_indices": [0, 1, 2, 3, 4],
                        }
                    ],
                    "semantic_variables": [
                        {
                            "name": "endpoint_strategy",
                            "label": "Endpoint strategy",
                            "instruction": "Return the canonical primary endpoint strategy.",
                            "value_type": "string",
                            "kind": "categorical",
                            "analysis_indices": [0, 1, 2, 3, 4],
                        }
                    ],
                    "analyses": [
                        {
                            "analysis_index": index,
                            "purpose": f"Execute pair {index}",
                            "methods": ["Count", "Compare"],
                            "variable_names": ["sample_size", "endpoint_strategy"],
                            "segment_keys": ["nsclc", "early_nsclc"],
                        }
                        for index in range(5)
                    ],
                }
            )

        async def analyze_objective(self, **kwargs) -> MaxObjectiveResult:
            assert len(kwargs["rows"]) == 2
            return MaxObjectiveResult.model_validate(
                {
                    "title": kwargs["pair"]["maxAnalysis"]["title"],
                    "summary_sentences": ["The frozen evidence supports a bounded comparison."],
                    "sub_analyses": [
                        {
                            "title": f"Result {index + 1}",
                            "visual": {
                                "kind": "stat",
                                "title": "Trials",
                                "unit": "trials",
                                "labels": ["Analyzed"],
                                "values": [2],
                                "note": "Two frozen Trial Profiles.",
                            },
                            "interpretation": "This is a bounded test result.",
                            "items": [],
                            "trial_ids": [],
                        }
                        for index in range(2)
                    ],
                    "conclusion": "Use the profile-supported comparison.",
                    "limitations": [],
                }
            )

        async def synthesize(self, **kwargs) -> MaxFinalSynthesis:
            assert len(kwargs["sections"]) == 5
            assert kwargs["analyzed_cohort"]["cohorts"][0]["trialCount"] == 1
            return MaxFinalSynthesis(
                title="Max report",
                executive_summary="Five paired analyses completed.",
                closing_note="Use the findings with their stated evidence limits.",
            )

    executor = object.__new__(MaxReportExecutor)
    executor._control = ReportControl()
    executor._analysis_control = AnalysisControl()
    executor._extractor = Extractor()
    executor._runner = Runner()

    async def discover(_analysis_id: str, _cohorts: list[dict]) -> tuple[list[str], dict[str, set[int]]]:
        return [item.eu_number for item in profiles], {
            profiles[0].eu_number: {0, 1},
            profiles[1].eu_number: {1},
        }

    async def load_profiles(_analysis_id: str, _trial_ids: list[str]) -> list[FullProfileItem]:
        return profiles

    executor._discover = discover
    executor._load_profiles = load_profiles
    await executor.execute("run-123")

    assert executor._control.failed is None
    assert executor._control.completed is not None
    final_report = executor._control.completed["final_report"]
    assert final_report["tier"] == "max"
    assert len(final_report["sections"]) == 5
    assert final_report["analyzedCohort"]["totalTrials"] == 2

