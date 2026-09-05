from __future__ import annotations

from datetime import UTC, datetime

import pytest

from intel_mcp.engine_read.profile_retrieval import (
    ProfileRetrievalRequestError,
    get_approved_profiles,
    validate_profile_retrieval_request,
)


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _Connection:
    def __init__(self, rows):
        self.rows = rows
        self.parameters = None

    def execute(self, _statement, parameters):
        self.parameters = parameters
        return _Result(self.rows)


def test_profile_request_deduplicates_and_preserves_order() -> None:
    assert validate_profile_retrieval_request(
        {
            "trial_ids": [
                "2024-500002-00-00",
                "2024-500001-00-00",
                "2024-500002-00-00",
            ]
        }
    ) == ["2024-500002-00-00", "2024-500001-00-00"]


def test_profile_request_accepts_only_trial_ids() -> None:
    with pytest.raises(ProfileRetrievalRequestError) as captured:
        validate_profile_retrieval_request(
            {"trial_ids": ["2024-500001-00-00"], "projection": "overview"}
        )
    assert captured.value.code == "INVALID_REQUEST"


def test_profile_request_accepts_up_to_one_hundred_trials() -> None:
    trial_ids = [f"2024-{index:06d}-00-00" for index in range(100)]
    assert validate_profile_retrieval_request({"trial_ids": trial_ids}) == trial_ids


def test_profile_request_rejects_more_than_one_hundred_trials() -> None:
    with pytest.raises(ProfileRetrievalRequestError) as captured:
        validate_profile_retrieval_request(
            {"trial_ids": [f"2024-{index:06d}-00-00" for index in range(101)]}
        )
    assert captured.value.code == "INVALID_TRIAL_IDS"


def test_get_profiles_returns_complete_profiles_in_request_order_and_unavailable_ids() -> None:
    approved_at = datetime(2026, 8, 27, 12, 0, tzinfo=UTC)
    connection = _Connection(
        [
            ("2024-500001-00-00", "10.0.0", approved_at, {"complete": "first"}),
            ("2024-500003-00-00", "10.0.0", approved_at, {"complete": "third"}),
        ]
    )

    result = get_approved_profiles(
        connection,
        {
            "trial_ids": [
                "2024-500003-00-00",
                "2024-500002-00-00",
                "2024-500001-00-00",
            ]
        },
    )

    assert connection.parameters == (
        ["2024-500003-00-00", "2024-500002-00-00", "2024-500001-00-00"],
    )
    assert [item["eu_number"] for item in result["data"]] == [
        "2024-500003-00-00",
        "2024-500001-00-00",
    ]
    assert result["data"][0]["profile"] == {"complete": "third"}
    assert result["unavailable_trial_ids"] == ["2024-500002-00-00"]
    assert result["schema_version"] == "1.0.0"
