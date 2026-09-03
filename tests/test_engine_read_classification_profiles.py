from __future__ import annotations

import pytest

from intel_mcp.engine_read.classification_profiles import (
    ClassificationProfileRequestError,
    _remove_contact_personal_data,
    validate_classification_profile_request,
)


def test_classification_profile_request_accepts_one_or_more_unique_trials() -> None:
    assert validate_classification_profile_request(
        {"trial_ids": ["2024-500001-00-00", "2023-500002-00-00"]}
    ) == ["2024-500001-00-00", "2023-500002-00-00"]


def test_classification_profile_request_rejects_duplicates() -> None:
    with pytest.raises(ClassificationProfileRequestError) as captured:
        validate_classification_profile_request(
            {"trial_ids": ["2024-500001-00-00", "2024-500001-00-00"]}
        )
    assert captured.value.code == "DUPLICATE_TRIAL_IDS"


def test_classification_profile_redacts_contact_personal_data_only() -> None:
    profile = {
        "trial_title": "Example",
        "available_extracted_documents": {
            "protocol": ["Clinical Trial Protocol v3"],
            "recruitment_arrangements": [],
        },
        "trial_recruitment_contact": {
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane@example.org",
            "department": "Oncology",
        },
        "sites": [
            {
                "site_name": "Example Hospital",
                "site_contacts": [
                    {
                        "first_name": "John",
                        "last_name": "Smith",
                        "email": "john@example.org",
                        "role": "Principal investigator",
                    }
                ],
            }
        ],
    }
    redacted = _remove_contact_personal_data(profile)
    assert redacted["trial_title"] == "Example"
    assert redacted["available_extracted_documents"] == {
        "protocol": ["Clinical Trial Protocol v3"],
        "recruitment_arrangements": [],
    }
    assert redacted["trial_recruitment_contact"] == {"department": "Oncology"}
    assert redacted["sites"][0]["site_name"] == "Example Hospital"
    assert redacted["sites"][0]["site_contacts"][0] == {"role": "Principal investigator"}

