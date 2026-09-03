from __future__ import annotations

import pytest

from intel_mcp.engine_read.filtering import (
    FilterRequestError,
    build_where,
    filter_approved_trials,
    validate_request,
)


def test_filter_contract_rejects_unstructured_profile_search() -> None:
    with pytest.raises(FilterRequestError) as captured:
        validate_request({"filters": {"profile_contains": {"value": "oncology"}}})
    assert captured.value.code == "UNSUPPORTED_FILTER_FIELD"


def test_filter_contract_accepts_case_insensitive_structured_filters() -> None:
    filters, sort, limit, offset = validate_request(
        {
            "filters": {
                "sponsor_name": {"operator": "contains", "value": "janssen"},
                "phase": {"operator": "contains_any", "values": [2]},
                "countries": [
                    {
                        "country_codes": {"operator": "contains_any", "values": ["de"]},
                        "recruitment_statuses": {"operator": "contains_any", "values": ["authorised"]},
                    }
                ],
            }
        }
    )
    where_sql, params = build_where(filters)
    assert "p.approval_status = 'approved'" in where_sql
    assert "EXISTS (SELECT 1 FROM mcp_serving.profile_countries_v1 c" in where_sql
    assert "c.country_code" in where_sql
    assert "c.recruitment_status" in where_sql
    assert params == ["%janssen%", [2], ["DE"], ["Authorised"]]
    assert sort == {"field": "latest_country_submission_or_approval_date", "direction": "desc"}
    assert limit == 20
    assert offset == 0


def test_negative_text_filter_excludes_missing_values() -> None:
    where_sql, _ = build_where(
        {"trial_title": {"operator": "does_not_contain", "value": "cancer"}}
    )
    assert "p.trial_title IS NOT NULL" in where_sql


def test_controlled_value_error_is_specific() -> None:
    with pytest.raises(FilterRequestError) as captured:
        validate_request(
            {"filters": {"allocation": {"operator": "is", "value": "Random maybe"}}}
        )
    assert captured.value.code == "INVALID_CONTROLLED_VALUE"


def test_filter_offset_is_bounded() -> None:
    assert validate_request({"offset": 100})[3] == 100
    with pytest.raises(FilterRequestError) as captured:
        validate_request({"offset": -1})
    assert captured.value.code == "INVALID_OFFSET"


def test_filter_response_uses_minimal_shortlist_projection() -> None:
    class Result:
        def __init__(self, *, one=None, all_rows=None):
            self.one = one
            self.all_rows = all_rows

        def fetchone(self):
            return self.one

        def fetchall(self):
            return self.all_rows

    class Connection:
        def __init__(self):
            self.results = iter(
                [
                    Result(one=(7,)),
                    Result(one=(1,)),
                    Result(
                        all_rows=[
                            (
                                "2024-500001-00-00",
                                "Example trial",
                                "Example sponsor",
                            )
                        ]
                    ),
                ]
            )

        def execute(self, *_args, **_kwargs):
            return next(self.results)

    response = filter_approved_trials(Connection(), {"filters": {}, "limit": 20})

    assert response["data"] == [
        {
            "eu_number": "2024-500001-00-00",
            "trial_title": "Example trial",
            "sponsor_name": "Example sponsor",
        }
    ]
    assert response["counts"] == {
        "total_profiles": 7,
        "total_matches": 1,
        "returned": 1,
    }
