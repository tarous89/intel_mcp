from __future__ import annotations

import pytest

from intel_mcp.engine_read.extraction_source import (
    ExtractionSourceRequestError,
    get_approved_extraction_source,
    validate_extraction_source_request,
)


class _Result:
    def __init__(self, *, row=None, rows=None):
        self._row = row
        self._rows = rows or []

    def fetchone(self):
        return self._row

    def fetchall(self):
        return self._rows


class _Connection:
    def __init__(self, profile_row, protocol_rows):
        self.profile_row = profile_row
        self.protocol_rows = protocol_rows
        self.calls = []

    def execute(self, statement, parameters):
        self.calls.append((statement, parameters))
        if "FROM mcp_serving.approved_profiles_v1" in statement:
            assert parameters == ("2024-500001-00-00",)
            return _Result(row=self.profile_row)
        if "FROM mcp_serving.documents_v1" in statement:
            assert parameters == (77,)
            return _Result(rows=[row[:4] for row in self.protocol_rows])
        if "FROM mcp_serving.document_text_v1" in statement:
            document_id = parameters[0]
            source = next((row for row in self.protocol_rows if row[0] == document_id), None)
            return _Result(row=(source[4], source[5]) if source else None)
        raise AssertionError(f"Unexpected SQL: {statement}")


def _profile(protocol_names, **values):
    return {
        **values,
        "filtering_variables": {
            "available_extracted_documents": {
                "protocol": protocol_names,
                "recruitment_arrangements": [],
                "patient_information_and_informed_consent": [],
                "assessments_and_forms": [],
                "clinical_study_report": [],
                "results_summary": [],
            }
        },
    }


def test_request_accepts_only_one_trial() -> None:
    assert validate_extraction_source_request(
        {"trial_id": "2024-500001-00-00"}
    ) == "2024-500001-00-00"
    with pytest.raises(ExtractionSourceRequestError):
        validate_extraction_source_request(
            {"trial_id": "2024-500001-00-00", "document_type": "protocol"}
        )


def test_source_returns_approved_profile_and_its_listed_protocol_only() -> None:
    profile = _profile(
        ["Clinical Trial Protocol clean English"],
        classification_variables={"planned_sample_size": 420},
    )
    connection = _Connection(
        (profile, 77),
        [
            (
                10,
                "Protocol synopsis",
                "synopsis.pdf",
                "Protocol synopsis",
                "Short",
                [{"page": 1, "text": "Short"}],
            ),
            (
                11,
                "Clinical Trial Protocol clean English",
                "protocol-en.pdf",
                "Clinical trial protocol",
                "Complete protocol",
                [{"page": 1, "text": "Complete protocol"}],
            ),
        ],
    )

    result = get_approved_extraction_source(
        connection, {"trial_id": "2024-500001-00-00"}
    )

    assert result == {
        "trial_id": "2024-500001-00-00",
        "profile": profile,
        "protocol_text": "[[PROTOCOL DOCUMENT 11 PAGE 1]]\nComplete protocol",
        "schema_version": "1.0.0",
    }
    assert "document_name" not in result
    assert "page" not in result
    assert any("WHERE document_id = %s" in statement for statement, _ in connection.calls)


def test_source_uses_profile_inventory_without_reranking_other_protocol_rows() -> None:
    profile = _profile(["Protocol synopsis"])
    result = get_approved_extraction_source(
        _Connection(
            (profile, 77),
            [
                (
                    10,
                    "Protocol synopsis",
                    "synopsis.pdf",
                    "Protocol synopsis",
                    "Short",
                    [{"page": 1, "text": "Short"}],
                ),
                (
                    11,
                    "Clinical Trial Protocol clean English",
                    "protocol-en.pdf",
                    "Clinical trial protocol",
                    "Complete protocol",
                    [{"page": 1, "text": "Complete protocol"}],
                ),
            ],
        ),
        {"trial_id": "2024-500001-00-00"},
    )
    assert result["protocol_text"] == "[[PROTOCOL DOCUMENT 10 PAGE 1]]\nShort"


def test_source_allows_profile_only_when_no_protocol_is_available() -> None:
    profile = _profile([], trial_title="Profile only")
    result = get_approved_extraction_source(
        _Connection((profile, 77), []),
        {"trial_id": "2024-500001-00-00"},
    )
    assert result["profile"] == profile
    assert result["protocol_text"] is None


def test_unapproved_profile_is_unavailable() -> None:
    with pytest.raises(ExtractionSourceRequestError) as captured:
        get_approved_extraction_source(
            _Connection(None, []), {"trial_id": "2024-500001-00-00"}
        )
    assert captured.value.code == "TRIAL_PROFILE_NOT_AVAILABLE"
    assert captured.value.status_code == 404


def test_source_keeps_legacy_top_level_inventory_compatible() -> None:
    profile = _profile(["Clinical Trial Protocol clean English"])
    legacy_profile = {
        "available_extracted_documents": profile["filtering_variables"][
            "available_extracted_documents"
        ]
    }
    result = get_approved_extraction_source(
        _Connection(
            (legacy_profile, 77),
            [
                (
                    11,
                    "Clinical Trial Protocol clean English",
                    "protocol-en.pdf",
                    "Clinical trial protocol",
                    "Complete protocol",
                    [{"page": 1, "text": "Complete protocol"}],
                )
            ],
        ),
        {"trial_id": "2024-500001-00-00"},
    )
    assert result["protocol_text"] == (
        "[[PROTOCOL DOCUMENT 11 PAGE 1]]\nComplete protocol"
    )
