from __future__ import annotations

from intel_mcp.profiles import GetProfilesOutput


def test_get_profiles_output_schema_is_minimal() -> None:
    assert set(GetProfilesOutput.model_json_schema()["properties"]) == {
        "profiles",
        "unavailable_trial_ids",
        "allowance_reached_trial_ids",
        "counts",
        "analysis_allowance",
    }
