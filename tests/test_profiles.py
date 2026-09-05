from __future__ import annotations

from intel_mcp.profiles import (
    PROFILE_SECTIONS,
    GetProfilesOutput,
    normalize_profile_sections,
    project_profile,
)


def _profile() -> dict:
    return {
        "filtering_variables": {
            "therapeutic_areas": ["Oncology"],
            "phase": [3],
            "planned_sample_size": 420,
            "allocation": "Randomised",
            "modality": "Small molecule",
            "inclusion_criteria": ["Adult participants"],
            "exclusion_criteria": ["Prior therapy X"],
            "number_of_countries": 4,
            "country_codes": ["DE", "FR", "ES", "IT"],
            "number_of_sites": 20,
            "available_extracted_documents": {"protocol": ["Protocol v2"]},
        },
        "classification_variables": {
            "trial_title": "Example phase 3 trial",
            "diseases": ["NSCLC"],
            "target_population_summary": "Resected NSCLC",
            "primary_objectives": ["Evaluate DFS"],
            "endpoints": [{"name": "DFS"}],
            "countries": [{"country": "DE"}],
            "sites": [{"organization": "Site A"}],
            "sponsor": {"name": "Sponsor A"},
            "trial_management_contact": {"first_name": "Alex"},
        },
        "ctis_lifecycle": {"overall_updates": [], "countries": [{"country": "DE"}]},
        "results": {"primary_endpoint_results": [{"endpoint": "DFS"}]},
    }


def test_get_profiles_output_schema_is_minimal() -> None:
    assert set(GetProfilesOutput.model_json_schema()["properties"]) == {
        "profiles",
        "unavailable_trial_ids",
        "allowance_reached_trial_ids",
        "counts",
        "analysis_allowance",
    }


def test_profile_section_vocabulary_is_stable() -> None:
    assert PROFILE_SECTIONS == (
        "overview",
        "population",
        "trial_design",
        "interventions",
        "eligibility",
        "objectives",
        "endpoints",
        "sponsor_and_organizations",
        "contacts",
        "countries",
        "sites",
        "documents",
        "lifecycle",
        "results",
    )


def test_profile_sections_are_deduplicated_in_caller_order() -> None:
    assert normalize_profile_sections(["endpoints", "overview", "endpoints"]) == [
        "endpoints",
        "overview",
    ]


def test_empty_sections_return_complete_independent_copy() -> None:
    profile = _profile()
    result = project_profile(profile, [])
    assert result == profile
    assert result is not profile
    result["classification_variables"]["trial_title"] = "changed"
    assert profile["classification_variables"]["trial_title"] == "Example phase 3 trial"


def test_selected_sections_preserve_exact_values_and_nesting() -> None:
    profile = _profile()
    result = project_profile(profile, ["overview", "endpoints", "countries"])

    assert result == {
        "filtering_variables": {
            "therapeutic_areas": ["Oncology"],
            "phase": [3],
            "country_codes": ["DE", "FR", "ES", "IT"],
            "number_of_countries": 4,
        },
        "classification_variables": {
            "trial_title": "Example phase 3 trial",
            "diseases": ["NSCLC"],
            "endpoints": [{"name": "DFS"}],
            "countries": [{"country": "DE"}],
        },
    }
    assert "results" not in result
    assert "sites" not in result["classification_variables"]


def test_whole_object_sections_preserve_lifecycle_and_results() -> None:
    profile = _profile()
    result = project_profile(profile, ["lifecycle", "results"])
    assert result == {
        "ctis_lifecycle": profile["ctis_lifecycle"],
        "results": profile["results"],
    }
