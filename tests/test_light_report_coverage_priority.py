from __future__ import annotations

from intel_mcp.light_report import light_objectives
from intel_mcp.light_report_execution import prioritize_light_plan


def test_light_report_prioritizes_strong_coverage_before_source_dependent() -> None:
    plan = {
        "version": 2,
        "studyCohorts": [{"role": "primary", "title": "Target trials", "details": ["Target setting"]}],
        "exclusionSummary": "Unrelated trials excluded.",
        "reportSections": [
            {"title": "Observed recruitment", "analyses": ["Observed recruitment"], "coverage": "source_dependent", "maxOnly": False},
            {"title": "Endpoints", "analyses": ["Endpoint patterns"], "coverage": "strong", "maxOnly": False},
            {"title": "Protocol detail", "analyses": ["Assay schedule"], "coverage": "strong", "maxOnly": True},
            {"title": "Eligibility", "analyses": ["Eligibility patterns"], "coverage": "strong", "maxOnly": False},
            {"title": "Operational results", "analyses": ["Operational findings"], "coverage": "source_dependent", "maxOnly": False},
            {"title": "Countries", "analyses": ["Country timelines"], "coverage": "strong", "maxOnly": False},
        ],
    }

    prioritized = prioritize_light_plan(plan)

    assert [section["title"] for section in prioritized["reportSections"]] == [
        "Endpoints",
        "Eligibility",
        "Countries",
        "Observed recruitment",
        "Operational results",
        "Protocol detail",
    ]
    assert [item["title"] for item in light_objectives(prioritized)] == [
        "Endpoints",
        "Eligibility",
        "Countries",
    ]
    # The approved stored plan object is not mutated by execution prioritization.
    assert plan["reportSections"][0]["title"] == "Observed recruitment"


def test_planner_max_only_objective_never_consumes_a_light_slot() -> None:
    plan = {
        "reportSections": [
            {"title": "Deep protocol", "analyses": ["Protocol detail"], "coverage": "strong", "maxOnly": True},
            {"title": "Results", "analyses": ["Results"], "coverage": "source_dependent", "maxOnly": False},
            {"title": "Endpoints", "analyses": ["Endpoints"], "coverage": "strong", "maxOnly": False},
            {"title": "Eligibility", "analyses": ["Eligibility"], "coverage": "strong", "maxOnly": False},
            {"title": "Countries", "analyses": ["Countries"], "coverage": "strong", "maxOnly": False},
        ]
    }

    objectives = light_objectives(prioritize_light_plan(plan))
    assert [item["title"] for item in objectives] == ["Endpoints", "Eligibility", "Countries"]
