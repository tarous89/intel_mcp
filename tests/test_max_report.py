from __future__ import annotations

import json

import httpx
import pytest

from intel_mcp.config import Settings
from intel_mcp.max_report import (
    MAX_NONDETERMINISTIC_VARIABLES,
    MAX_REPORT_MODEL,
    MAX_REPORT_SERVICE_TIER,
    MAX_REPORT_TRIAL_COUNT,
    INVESTIGATOR_PROFILE_PATH,
    MaxAnalysisPlan,
    MaxVisual,
    MaxReportError,
    SemanticVariable,
    TerraMaxReportRunner,
    build_field_catalog,
    ensure_investigator_analysis_variable,
    max_group_variables,
    resolve_profile_path,
    sap_schema,
    summarize_dataset,
)
from intel_mcp.profiles import FullProfileItem


def _settings() -> Settings:
    return Settings(
        app_control_url="https://intel.example.test",
        app_service_token="test-app-token",
        engine_api_url="https://engine.example.test",
        engine_service_token="test-engine-token",
        mcp_inbound_service_token="test-mcp-token",
        allowed_hosts=("localhost",),
        port=8000,
        request_timeout_seconds=1,
        openai_api_key="test-openai-key",
    )


def _profile(trial_id: str, sample_size: int = 100) -> FullProfileItem:
    return FullProfileItem.model_validate(
        {
            "eu_number": trial_id,
            "profile_schema_version": "11.0.0",
            "approved_at": "2026-09-01T00:00:00+00:00",
            "profile": {
                "filtering_variables": {
                    "planned_sample_size": sample_size,
                    "phase": [2],
                },
                "classification_variables": {
                    "trial_title": f"Study {trial_id}",
                    "sites": [
                        {
                            "site_name": "Central Hospital",
                            "investigators": [{
                                "first_name": "Ada",
                                "last_name": "Example",
                                "email": "ada@example.org",
                                "department_or_division": "Oncology",
                                "function": None,
                            }],
                        }
                    ],
                    "long_narrative": "x" * 800,
                },
            },
        }
    )


def test_semantic_variable_compacts_and_bounds_verbose_instructions() -> None:
    instruction = (
        "Extract whether the complete Trial Profile establishes the requested operational characteristic. "
        + "Use all relevant structured and narrative evidence while avoiding unsupported inference. " * 8
        + "Return null when the available evidence is insufficient."
    )

    variable = SemanticVariable(
        name="operational_characteristic",
        label="Operational characteristic",
        instruction=instruction,
        value_type="boolean",
        kind="boolean",
        analysis_indices=[0],
    )

    assert len(variable.instruction) <= 600
    assert variable.instruction.startswith("Extract whether")
    assert variable.instruction.endswith("Return null when the available evidence is insufficient.")


def _plan() -> dict:
    sections = [
        {
            "title": f"Shared analysis {index}",
            "sharedAnalysis": {
                "title": f"Shared analysis {index}",
                "details": ["Count the supplied evidence"],
            },
            "maxAnalysis": {
                "title": f"Analyze decision area {index}",
                "details": ["Compare segments", "Assess cross-variable patterns"],
            },
        }
        for index in range(5)
    ]
    return {
        "version": 4,
        "studyCohorts": [
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
                        "inclusionCriteria": ["The Trial Profile concerns NSCLC"],
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
                "discoveryFilter": {"field": "diseases", "values": ["NSCLC"]},
                "selectionSegments": [
                    {
                        "key": "early_nsclc",
                        "label": "Early-stage NSCLC",
                        "inclusionCriteria": ["The Trial Profile establishes early-stage NSCLC"],
                        "exclusionCriteria": ["Metastatic-only population"],
                    }
                ],
            },
            {
                "role": "adjacent",
                "title": "Biomarker comparison",
                "details": ["EGFR versus non-EGFR"],
                "maxOnly": True,
                "filterDimension": None,
                "discoveryFilter": {"field": "diseases", "values": ["NSCLC"]},
                "selectionSegments": [
                    {
                        "key": "egfr_positive",
                        "label": "EGFR-positive",
                        "inclusionCriteria": ["The Trial Profile requires an EGFR alteration"],
                        "exclusionCriteria": [],
                    },
                    {
                        "key": "egfr_unselected",
                        "label": "EGFR-unselected",
                        "inclusionCriteria": ["The Trial Profile does not select for EGFR"],
                        "exclusionCriteria": [],
                    },
                ],
            },
        ],
        "exclusionSummary": "Unrelated trials are excluded.",
        "reportSections": sections,
    }


def test_max_v1_hard_limits_and_profile_catalogue() -> None:
    assert MAX_REPORT_MODEL == "gpt-5.6-terra"
    assert MAX_REPORT_SERVICE_TIER == "flex"
    assert MAX_REPORT_TRIAL_COUNT == 100
    assert MAX_NONDETERMINISTIC_VARIABLES == 20

    catalogue = build_field_catalog([_profile("2026-000001-00-00")])
    paths = {item["path"] for item in catalogue}
    assert "$trial_id" in paths
    assert "filtering_variables.planned_sample_size" in paths
    assert INVESTIGATOR_PROFILE_PATH in paths
    assert "classification_variables.sites[].investigators[].first_name" in paths
    assert "classification_variables.long_narrative" not in paths
    assert resolve_profile_path(
        _profile("2026-000001-00-00").profile,
        "classification_variables.sites[].investigators[].first_name",
        "2026-000001-00-00",
    ) == "Ada"
    assert resolve_profile_path(
        _profile("2026-000001-00-00").profile,
        INVESTIGATOR_PROFILE_PATH,
        "2026-000001-00-00",
    ) == [{
        "name": "Ada Example",
        "email": "ada@example.org",
        "department_or_division": "Oncology",
        "function": None,
        "site_name": "Central Hospital",
        "country_code": None,
    }]


def test_profile_catalogue_excludes_paths_with_mixed_observed_types() -> None:
    first = _profile("2026-000001-00-00")
    second = _profile("2026-000002-00-00")
    first.profile["classification_variables"]["mixed_value"] = "category"
    second.profile["classification_variables"]["mixed_value"] = 42

    catalogue = build_field_catalog([first, second])

    assert "classification_variables.mixed_value" not in {
        item["path"] for item in catalogue
    }


def test_profile_catalogue_assigns_stable_runtime_kinds() -> None:
    profile = _profile("2026-000001-00-00")
    profile.profile["classification_variables"].update(
        {
            "category_value": "randomized",
            "numeric_values": [1, 2],
            "date_value": "2026-09-13",
            "boolean_value": True,
            "category_values": ["phase_2", "phase_3"],
        }
    )

    kinds = {item["path"]: item["kind"] for item in build_field_catalog([profile])}

    assert kinds["classification_variables.category_value"] == "categorical"
    assert kinds["classification_variables.numeric_values"] == "numeric"
    assert kinds["classification_variables.date_value"] == "date"
    assert kinds["classification_variables.boolean_value"] == "boolean"
    assert kinds["classification_variables.category_values"] == "entity_list"
    assert kinds[INVESTIGATOR_PROFILE_PATH] == "entity_list"


def test_investigator_objectives_always_receive_the_v11_investigator_entity_list() -> None:
    approved_plan = _plan()
    approved_plan["reportSections"][2]["maxAnalysis"] = {
        "title": "Prioritize principal investigators",
        "details": ["Rank documented investigator activity"],
    }
    analysis_plan = {
        "rationale": "Use structured evidence.",
        "direct_variables": [{
            "name": "trial_id",
            "label": "Trial",
            "description": "Trial identifier",
            "profile_path": "$trial_id",
            "kind": "categorical",
            "analysis_indices": [0, 1, 2, 3, 4],
        }],
        "semantic_variables": [],
        "analyses": [
            {
                "analysis_index": index,
                "purpose": f"Execute analysis {index}",
                "methods": ["Count", "Rank"],
                "variable_names": ["trial_id"],
                "segment_keys": [],
            }
            for index in range(5)
        ],
    }
    normalized = ensure_investigator_analysis_variable(
        MaxAnalysisPlan.model_validate(analysis_plan),
        approved_plan,
    )
    variable = next(
        item for item in normalized.direct_variables
        if item.profile_path == INVESTIGATOR_PROFILE_PATH
    )
    assert variable.analysis_indices == [2]
    assert variable.name in normalized.analyses[2].variable_names
    assert variable.name not in normalized.analyses[1].variable_names


def test_group_classification_is_reserved_inside_the_twenty_variable_budget() -> None:
    variables, metadata = max_group_variables(_plan())
    assert [item.name for item in variables] == [
        "segment_early_nsclc",
        "segment_egfr_positive",
        "segment_egfr_unselected",
    ]
    assert all(item.value_type == "boolean" for item in variables)
    assert all(len(item.instruction) <= 600 for item in variables)
    assert metadata[0]["inclusion_criteria"] == [
        "The Trial Profile establishes early-stage NSCLC"
    ]
    schema = sap_schema(
        profile_paths=["$trial_id", "filtering_variables.planned_sample_size"],
        analysis_count=5,
        segment_keys=[item["key"] for item in metadata],
        semantic_budget=MAX_NONDETERMINISTIC_VARIABLES - len(variables),
    )
    assert schema["properties"]["semantic_variables"]["maxItems"] == 17

    candidate_variables, candidate_metadata = max_group_variables(
        _plan(),
        include_primary=True,
    )
    assert candidate_variables[0].name == "segment_nsclc"
    assert candidate_metadata[0]["cohort_index"] == 0
    assert candidate_metadata[0]["membership_source"] == "profile_extraction"


def test_group_classification_never_silently_truncates_criteria() -> None:
    plan = _plan()
    plan["studyCohorts"][1]["selectionSegments"][0]["inclusionCriteria"] = ["x" * 500]
    with pytest.raises(MaxReportError) as captured:
        max_group_variables(plan)
    assert captured.value.code == "MAX_REPORT_PLAN_INVALID"


def test_max_visual_rejects_nonfinite_and_negative_donut_values() -> None:
    with pytest.raises(ValueError):
        MaxVisual(kind="bar", title="Invalid", unit="", labels=["A"], values=[float("nan")], note="Invalid.")
    with pytest.raises(ValueError):
        MaxVisual(kind="donut", title="Invalid", unit="trials", labels=["A"], values=[-1], note="Invalid.")


def test_dataset_summary_keeps_overlapping_labeled_segments() -> None:
    rows = [
        {
            "segment_keys": ["early_nsclc", "egfr_positive"],
            "values": {"sample_size": 80, "segment_early_nsclc": True},
        },
        {
            "segment_keys": ["early_nsclc"],
            "values": {"sample_size": 120, "segment_early_nsclc": True},
        },
    ]
    summary = summarize_dataset(
        rows,
        {
            "sample_size": {"label": "Sample size", "kind": "numeric"},
            "segment_early_nsclc": {"label": "Early NSCLC", "kind": "boolean"},
        },
        [
            {"key": "early_nsclc", "label": "Early-stage NSCLC"},
            {"key": "egfr_positive", "label": "EGFR-positive"},
        ],
    )
    assert summary["total_trials"] == 2
    assert [item["trial_count"] for item in summary["segments"]] == [2, 2, 1]
    numeric = summary["segments"][0]["variables"][0]["summary"]
    assert numeric["mean"] == 100
    assert numeric["median"] == 100


def test_dataset_summary_precomputes_bounded_numeric_correlations() -> None:
    summary = summarize_dataset(
        [
            {"segment_keys": [], "values": {"planned": 100, "actual": 80}},
            {"segment_keys": [], "values": {"planned": 200, "actual": 160}},
            {"segment_keys": [], "values": {"planned": 300, "actual": 240}},
        ],
        {
            "planned": {"label": "Planned", "kind": "numeric"},
            "actual": {"label": "Actual", "kind": "numeric"},
        },
        [],
    )
    assert summary["strongest_numeric_correlations"] == [
        {"left": "planned", "right": "actual", "paired_rows": 3, "pearson_r": 1.0}
    ]


@pytest.mark.anyio
async def test_sap_uses_terra_flex_and_one_shared_variable_plan(
    caplog: pytest.LogCaptureFixture,
) -> None:
    plan = _plan()
    group_variables, extracted_segment_metadata = max_group_variables(plan)
    segment_metadata = [
        {
            "key": "nsclc",
            "label": "NSCLC",
            "cohort_index": 0,
            "cohort_title": "NSCLC trials",
            "membership_source": "deterministic_discovery",
        },
        *extracted_segment_metadata,
    ]

    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["model"] == "gpt-5.6-terra"
        assert payload["service_tier"] == "flex"
        assert payload["reasoning"] == {"effort": "high"}
        assert "tools" not in payload
        assert payload["text"]["format"]["schema"]["properties"]["semantic_variables"]["maxItems"] == 17
        assert "nsclc" in payload["text"]["format"]["schema"]["properties"]["analyses"]["items"]["properties"]["segment_keys"]["items"]["enum"]
        user = json.loads(payload["input"][1]["content"][0]["text"])
        assert len(user["complete_profile_examples"]) == 1
        assert user["constraints"]["evidence_source"] == "complete_approved_trial_profiles_only"
        assert user["segment_definitions"][0]["membership_source"] == "deterministic_discovery"
        assert len(user["reserved_group_variables"]) == 3
        result = {
            "rationale": "Reuse structured sample size and reserve interpretation for segment membership.",
            "direct_variables": [
                {
                    "name": "sample_size",
                    "label": "Planned sample size",
                    "description": "Planned enrollment from the Trial Profile.",
                    "profile_path": "filtering_variables.planned_sample_size",
                    # The model may use the semantic interpretation instead of the
                    # catalogue's observed runtime type. The backend owns this value.
                    "kind": "categorical",
                    "analysis_indices": [0, 1, 2, 3, 4],
                }
            ],
            "semantic_variables": [],
            "analyses": [
                {
                    "analysis_index": index,
                    "purpose": f"Execute pair {index}",
                    "methods": ["Summarize sample size", "Compare labeled segments"],
                    "variable_names": ["sample_size", "segment_early_nsclc"],
                    "segment_keys": ["early_nsclc"],
                }
                for index in range(5)
            ],
        }
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": json.dumps(result)}],
                    }
                ],
            },
        )

    runner = TerraMaxReportRunner(_settings(), transport=httpx.MockTransport(handler))
    result = await runner.build_analysis_plan(
        context="Phase 2 NSCLC study",
        insights="Endpoints, sites and enrollment",
        approved_plan=plan,
        sample_profiles=[_profile("2026-000001-00-00")],
        field_catalog=build_field_catalog([_profile("2026-000001-00-00")]),
        group_variables=group_variables,
        segment_metadata=segment_metadata,
    )
    assert len(result.analyses) == 5
    assert result.direct_variables[0].profile_path == "filtering_variables.planned_sample_size"
    assert result.direct_variables[0].kind == "numeric"
    assert "supplied_kind=categorical expected_kind=numeric" in caplog.text


@pytest.mark.anyio
async def test_sap_retries_one_structurally_invalid_plan() -> None:
    plan = _plan()
    group_variables, extracted_segment_metadata = max_group_variables(plan)
    segment_metadata = [
        {
            "key": "nsclc",
            "label": "NSCLC",
            "cohort_index": 0,
            "cohort_title": "NSCLC trials",
            "membership_source": "deterministic_discovery",
        },
        *extracted_segment_metadata,
    ]
    calls: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        calls.append(payload["text"]["format"]["name"])
        variable_name = "unknown_variable" if len(calls) == 1 else "sample_size"
        result = {
            "rationale": "Use the deterministic sample size.",
            "direct_variables": [
                {
                    "name": "sample_size",
                    "label": "Planned sample size",
                    "description": "Planned enrollment from the Trial Profile.",
                    "profile_path": "filtering_variables.planned_sample_size",
                    "kind": "numeric",
                    "analysis_indices": [0, 1, 2, 3, 4],
                }
            ],
            "semantic_variables": [],
            "analyses": [
                {
                    "analysis_index": index,
                    "purpose": f"Execute pair {index}",
                    "methods": ["Summarize sample size", "Compare labeled segments"],
                    "variable_names": [variable_name],
                    "segment_keys": [],
                }
                for index in range(5)
            ],
        }
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": json.dumps(result)}],
                    }
                ],
            },
        )

    runner = TerraMaxReportRunner(_settings(), transport=httpx.MockTransport(handler))
    result = await runner.build_analysis_plan(
        context="Phase 2 NSCLC study",
        insights="Endpoints, sites and enrollment",
        approved_plan=plan,
        sample_profiles=[_profile("2026-000001-00-00")],
        field_catalog=build_field_catalog([_profile("2026-000001-00-00")]),
        group_variables=group_variables,
        segment_metadata=segment_metadata,
    )

    assert result.direct_variables[0].name == "sample_size"
    assert calls == ["intel_max_sap_v1", "intel_max_sap_correction_v1"]


@pytest.mark.anyio
async def test_candidate_planning_uses_reliable_fields_without_rewriting_the_report_plan() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["model"] == "gpt-5.6-sol"
        assert payload["service_tier"] == "flex"
        assert payload["reasoning"] == {"effort": "medium"}
        item = payload["text"]["format"]["schema"]["properties"]["filters"]["items"]
        assert "diseases" not in item["properties"]
        user = json.loads(payload["input"][1]["content"][0]["text"])
        assert user["approved_report_plan"] == _plan()
        result = {
            "rationale": "Start focused, then broaden to the therapeutic area.",
            "filters": [
                {
                    "label": "Phase 2 solid-tumor ADCs",
                    "therapeutic_areas": ["Solid Tumor Oncology"],
                    "phase": [2],
                    "modalities": ["ADC"],
                    "country_codes": None,
                },
                {
                    "label": "Solid-tumor ADCs",
                    "therapeutic_areas": ["Solid Tumor Oncology"],
                    "phase": None,
                    "modalities": ["ADC"],
                    "country_codes": None,
                },
                {
                    "label": "All solid-tumor oncology",
                    "therapeutic_areas": ["Solid Tumor Oncology"],
                    "phase": None,
                    "modalities": None,
                    "country_codes": None,
                },
            ],
        }
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": json.dumps(result)}],
                    }
                ],
            },
        )

    runner = TerraMaxReportRunner(_settings(), transport=httpx.MockTransport(handler))
    result = await runner.build_candidate_filter_plan(
        context="Phase 2 NSCLC study",
        insights="Endpoints and enrollment",
        approved_plan=_plan(),
    )
    assert len(result.filters) == 3
    assert result.filters[-1].therapeutic_areas == ["Solid Tumor Oncology"]


@pytest.mark.anyio
async def test_candidate_screening_returns_every_trial_and_keeps_system_names_out_of_errors() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["model"] == "gpt-5.6-sol"
        assert payload["reasoning"] == {"effort": "medium"}
        result = {
            "assessments": [
                {
                    "trial_id": "T1",
                    "tier": "exact",
                    "relevance_score": 96,
                    "segment_keys": ["nsclc"],
                    "uncertain_segment_keys": [],
                    "rationale": "The compact profile supports the primary segment.",
                }
            ]
        }
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": json.dumps(result)}],
                    }
                ],
            },
        )

    runner = TerraMaxReportRunner(_settings(), transport=httpx.MockTransport(handler))
    segments = [
        {
            "key": "nsclc",
            "label": "NSCLC",
            "cohort_index": 0,
            "cohort_title": "NSCLC trials",
            "inclusion_criteria": ["The Trial Profile concerns NSCLC"],
            "exclusion_criteria": [],
        }
    ]
    result = await runner.screen_candidate_batch(
        context="Phase 2 NSCLC study",
        insights="Endpoints and enrollment",
        approved_plan=_plan(),
        segment_metadata=segments,
        candidates=[{"trial_id": "T1", "profile": {"classification_variables": {}}}],
    )
    assert result[0].tier == "exact"

    async def invalid_handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "{}"}],
                    }
                ],
            },
        )

    invalid_runner = TerraMaxReportRunner(
        _settings(),
        transport=httpx.MockTransport(invalid_handler),
    )
    with pytest.raises(MaxReportError) as captured:
        await invalid_runner.build_candidate_filter_plan(
            context="Phase 2 NSCLC study",
            insights="Endpoints and enrollment",
            approved_plan=_plan(),
        )
    assert "terra" not in captured.value.message.casefold()
    assert "gpt" not in captured.value.message.casefold()
