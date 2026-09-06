from __future__ import annotations

import pytest

from intel_mcp.light_report import LightTrialSelection
from intel_mcp.light_report_execution import (
    LightReportExecutor,
    _analyzed_cohort_summary,
    _v3_light_execution_view,
    _v4_light_execution_view,
)
from intel_mcp.profiles import AppProfileAccessResponse, EngineProfilesResponse
from intel_mcp.server import settings


class StubEngine:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    async def get_profiles(self, trial_ids: list[str]) -> EngineProfilesResponse:
        self.calls.append(list(trial_ids))
        return EngineProfilesResponse.model_validate(
            {
                "data": [
                    {
                        "eu_number": trial_id,
                        "profile_schema_version": "10.0.0",
                        "approved_at": "2026-09-01T00:00:00+00:00",
                        "profile": {
                            "filtering_variables": {"phase": [3]},
                            "classification_variables": {"trial_title": trial_id},
                            "ctis_lifecycle": {"overall_updates": [], "countries": []},
                            "results": {},
                        },
                    }
                    for trial_id in trial_ids
                ],
                "unavailable_trial_ids": [],
                "schema_version": "1.0.0",
            }
        )


class StubProfileControl:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    async def authorize_profiles(
        self,
        analysis_id: str,
        trial_ids: list[str],
    ) -> AppProfileAccessResponse:
        assert analysis_id == "ana_123456789012345678901234"
        self.calls.append(list(trial_ids))
        return AppProfileAccessResponse.model_validate(
            {
                "access": {
                    "allowedTrialIds": trial_ids,
                    "limit": 100,
                    "used": 20,
                    "remaining": 80,
                    "exhausted": False,
                }
            }
        )


def _selection() -> LightTrialSelection:
    return LightTrialSelection.model_validate(
        {
            "selected_trials": [
                {
                    "trial_id": f"2026-{index:06d}-00-00",
                    "group": "priority" if index <= 12 else "adjacent",
                    "cohort_index": 0 if index <= 12 else 1,
                }
                for index in range(1, 21)
            ]
        }
    )


def test_analyzed_cohort_summary_uses_final_selection_and_plan_titles() -> None:
    plan = {
        "studyCohorts": [
            {"role": "primary", "title": "Resected NSCLC trials"},
            {"role": "adjacent", "title": "Broader NSCLC trials"},
            {"role": "adjacent", "title": "Cross-setting lung trials"},
        ]
    }
    summary = _analyzed_cohort_summary(plan, _selection().selected_trials)
    assert summary == {
        "totalTrials": 20,
        "cohorts": [
            {"title": "Resected NSCLC trials", "role": "primary", "trialCount": 12},
            {"title": "Broader NSCLC trials", "role": "adjacent", "trialCount": 8},
            {"title": "Cross-setting lung trials", "role": "adjacent", "trialCount": 0},
        ],
    }


def test_v3_light_execution_uses_only_shared_group_and_first_analysis_of_five_objectives() -> None:
    plan = {
        "version": 3,
        "studyCohorts": [
            {"role": "primary", "title": "Phase 2 oncology trials", "details": ["Phase 2", "Oncology"], "maxOnly": False},
            {"role": "adjacent", "title": "Biomarker-matched trials", "details": ["Biomarker match"], "maxOnly": True},
            {"role": "adjacent", "title": "Metastatic trials", "details": ["Metastatic setting"], "maxOnly": True},
        ],
        "exclusionSummary": "Unrelated trials excluded.",
        "reportSections": [
            {"title": f"Objective {index}", "analyses": [f"Shared {index}", f"Max A {index}", f"Max B {index}"]}
            for index in range(1, 7)
        ],
    }

    selection_plan, objectives = _v3_light_execution_view(plan)
    assert len(selection_plan["studyCohorts"]) == 1
    assert selection_plan["studyCohorts"][0]["title"] == "Phase 2 oncology trials"

    assert len(objectives) == 5
    assert objectives[0] == {"title": "Objective 1", "analyses": ["Shared 1"]}
    assert objectives[-1] == {"title": "Objective 5", "analyses": ["Shared 5"]}
    assert all(len(item["analyses"]) == 1 for item in objectives)

    assert len(selection_plan["reportSections"]) == 3
    selection_analysis_text = [
        analysis
        for section in selection_plan["reportSections"]
        for analysis in section["analyses"]
    ]
    assert selection_analysis_text == [
        "Shared 1",
        "Objective 4: Shared 4",
        "Shared 2",
        "Objective 5: Shared 5",
        "Shared 3",
    ]


def test_v4_light_execution_runs_all_shared_analyses_and_no_max_work() -> None:
    plan = {
        "version": 4,
        "studyCohorts": [
            {
                "role": "primary",
                "title": "NSCLC trials",
                "details": ["Disease contains NSCLC"],
                "maxOnly": False,
                "filterDimension": "disease",
            },
            {
                "role": "adjacent",
                "title": "Mutation-positive vs mutation-negative NSCLC",
                "details": ["Compare oncogenic mutation status"],
                "maxOnly": True,
                "filterDimension": None,
            },
            {
                "role": "adjacent",
                "title": "Low vs high PD-L1 NSCLC",
                "details": ["Compare PD-L1 expression groups"],
                "maxOnly": True,
                "filterDimension": None,
            },
        ],
        "exclusionSummary": "Unrelated trials excluded.",
        "reportSections": [
            {
                "title": f"Shared analysis {index}",
                "sharedAnalysis": {
                    "title": f"Shared analysis {index}",
                    "details": [f"Shared metric {index}A", f"Shared metric {index}B"],
                },
                "maxAnalysis": {
                    "title": f"Max decision analysis {index}",
                    "details": [f"Max factor {index}A", f"Max factor {index}B"],
                },
            }
            for index in range(1, 8)
        ],
    }

    selection_plan, objectives = _v4_light_execution_view(plan)

    assert selection_plan["studyCohorts"] == [plan["studyCohorts"][0]]
    assert len(objectives) == 7
    assert objectives[0] == {
        "title": "Shared analysis 1",
        "analyses": ["Shared metric 1A", "Shared metric 1B"],
    }
    assert objectives[-1]["title"] == "Shared analysis 7"

    # The selector still receives every shared evidence need, compacted into three
    # legacy-compatible containers. No Max group or Max analysis text crosses the
    # Light execution boundary.
    assert len(selection_plan["reportSections"]) == 3
    selection_text = " ".join(
        analysis
        for section in selection_plan["reportSections"]
        for analysis in section["analyses"]
    )
    for index in range(1, 8):
        assert f"Shared analysis {index}" in selection_text
        assert f"Shared metric {index}A" in selection_text
    assert "Max decision analysis" not in selection_text
    assert "Max factor" not in selection_text
    assert "mutation" not in selection_text.casefold()
    assert "pd-l1" not in selection_text.casefold()
    assert max(len(section["analyses"]) for section in selection_plan["reportSections"]) <= 4


@pytest.mark.anyio
async def test_executor_loads_complete_frozen_evidence_once_in_two_ten_profile_batches() -> None:
    executor = LightReportExecutor(settings)
    engine = StubEngine()
    control = StubProfileControl()
    executor._engine = engine  # type: ignore[assignment]
    executor._analysis_control = control  # type: ignore[assignment]

    profiles = await executor._load_complete_evidence_profiles(
        "ana_123456789012345678901234",
        _selection().selected_trials,
    )

    expected_ids = [f"2026-{index:06d}-00-00" for index in range(1, 21)]
    assert [item.eu_number for item in profiles] == expected_ids
    assert engine.calls == [expected_ids[:10], expected_ids[10:]]
    assert control.calls == [expected_ids[:10], expected_ids[10:]]
