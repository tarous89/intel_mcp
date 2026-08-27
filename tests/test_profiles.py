from __future__ import annotations

from intel_mcp.profiles import FullProfileItem, select_complete_profile_batch


def _profile(trial_id: str, size: int) -> FullProfileItem:
    return FullProfileItem(
        eu_number=trial_id,
        profile_schema_version="8.4.0",
        approved_at=None,
        profile={"value": "x" * size},
    )


def test_complete_profile_batch_defers_whole_profiles_only() -> None:
    profiles = [
        _profile("2024-500001-00-00", 60),
        _profile("2024-500002-00-00", 60),
        _profile("2024-500003-00-00", 60),
    ]
    selected, deferred, oversized = select_complete_profile_batch(profiles, max_bytes=300)

    assert [item.eu_number for item in selected] == ["2024-500001-00-00"]
    assert [item.eu_number for item in deferred] == [
        "2024-500002-00-00",
        "2024-500003-00-00",
    ]
    assert oversized is False
    assert selected[0].profile["value"] == "x" * 60


def test_single_oversized_profile_is_still_returned_complete() -> None:
    profiles = [
        _profile("2024-500001-00-00", 1_000),
        _profile("2024-500002-00-00", 10),
    ]
    selected, deferred, oversized = select_complete_profile_batch(profiles, max_bytes=100)

    assert [item.eu_number for item in selected] == ["2024-500001-00-00"]
    assert selected[0].profile["value"] == "x" * 1_000
    assert [item.eu_number for item in deferred] == ["2024-500002-00-00"]
    assert oversized is True
