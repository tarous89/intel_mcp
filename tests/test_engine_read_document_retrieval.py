from __future__ import annotations

import pytest

from intel_mcp.engine_read.document_retrieval import (
    MAX_TEXT_PART_CHARACTERS,
    DocumentRetrievalRequestError,
    get_approved_document_text,
    validate_document_retrieval_request,
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
    def __init__(self, profile_row, document_rows):
        self.profile_row = profile_row
        self.document_rows = document_rows
        self.calls = []

    def execute(self, statement, parameters):
        self.calls.append((statement, parameters))
        if "FROM mcp_serving.approved_profiles_v1" in statement:
            return _Result(row=self.profile_row)
        if "FROM mcp_serving.documents_v1" in statement:
            return _Result(rows=[row[:6] for row in self.document_rows])
        if "FROM mcp_serving.document_text_v1" in statement:
            document_id = parameters[0]
            source = next((row for row in self.document_rows if row[0] == document_id), None)
            return _Result(row=(source[6], source[7]) if source else None)
        raise AssertionError(f"Unexpected SQL: {statement}")


def _request(part=1):
    return {
        "trial_id": "2024-500001-00-00",
        "document_name": "Clinical Trial Protocol v3",
        "part": part,
    }


def _profile_row(category="protocol"):
    inventory = {
        "protocol": [],
        "recruitment_arrangements": [],
        "patient_information_and_informed_consent": [],
        "assessments_and_forms": [],
        "clinical_study_report": [],
        "results_summary": [],
    }
    inventory[category] = ["Clinical Trial Protocol v3"]
    return (
        {
            "filtering_variables": {
                "available_extracted_documents": inventory,
            }
        },
    )


def _document_row(text, pages):
    return (
        42,
        "ctis-document-uuid",
        "protocol",
        "Clinical trial protocol",
        "Clinical Trial Protocol v3",
        "protocol-v3.pdf",
        text,
        pages,
    )


def test_request_accepts_only_the_three_contract_fields() -> None:
    assert validate_document_retrieval_request(_request()).part == 1
    with pytest.raises(DocumentRetrievalRequestError) as captured:
        validate_document_retrieval_request({**_request(), "limit": 10})
    assert captured.value.code == "INVALID_REQUEST"


def test_get_document_returns_simple_text_only_contract_and_case_insensitive_name() -> None:
    connection = _Connection(
        _profile_row(),
        [_document_row("First page\n\nSecond page", [{"page": 1, "text": "First page"}, {"page": 2, "text": "Second page"}])],
    )
    request = _request()
    request["document_name"] = "clinical trial protocol V3"

    result = get_approved_document_text(connection, request)

    assert result["document_name"] == "Clinical Trial Protocol v3"
    assert result["document_type"] == "protocol"
    assert result["part"] == 1
    assert result["text"] == "[[PAGE 1]]\nFirst page\n\n[[PAGE 2]]\nSecond page"
    assert result["next_part"] is None
    assert len(result["document_access_key"]) == 64
    assert "page_count" not in result
    assert "text_characters" not in result
    assert any("WHERE document_id = %s" in statement for statement, _ in connection.calls)


def test_oversized_page_is_split_into_numbered_parts_without_silent_loss() -> None:
    source_text = "A" * (MAX_TEXT_PART_CHARACTERS + 25_000)
    connection = _Connection(
        _profile_row(),
        [_document_row(source_text, [{"page": 7, "text": source_text}])],
    )

    first = get_approved_document_text(connection, _request(part=1))
    second = get_approved_document_text(connection, _request(part=2))

    assert len(first["text"]) <= MAX_TEXT_PART_CHARACTERS
    assert len(second["text"]) <= MAX_TEXT_PART_CHARACTERS
    assert first["text"].startswith("[[PAGE 7]]\n")
    assert second["text"].startswith("[[PAGE 7 CONTINUED]]\n")
    assert first["next_part"] == 2
    assert second["next_part"] is None
    reconstructed = first["text"].split("\n", 1)[1] + second["text"].split("\n", 1)[1]
    assert reconstructed == source_text


def test_unapproved_or_unlisted_document_is_unavailable() -> None:
    connection = _Connection(None, [])
    with pytest.raises(DocumentRetrievalRequestError) as captured:
        get_approved_document_text(connection, _request())
    assert captured.value.code == "DOCUMENT_UNAVAILABLE"
    assert captured.value.status_code == 404


def test_profile_category_must_match_the_stored_document_category() -> None:
    connection = _Connection(
        _profile_row("results_summary"),
        [_document_row("Short", [{"page": 1, "text": "Short"}])],
    )
    with pytest.raises(DocumentRetrievalRequestError) as captured:
        get_approved_document_text(connection, _request())
    assert captured.value.code == "DOCUMENT_UNAVAILABLE"


def test_part_after_end_is_unavailable() -> None:
    connection = _Connection(
        _profile_row(),
        [_document_row("Short", [{"page": 1, "text": "Short"}])],
    )
    with pytest.raises(DocumentRetrievalRequestError) as captured:
        get_approved_document_text(connection, _request(part=2))
    assert captured.value.code == "DOCUMENT_PART_UNAVAILABLE"
    assert captured.value.status_code == 416


def test_legacy_top_level_profile_inventory_remains_readable() -> None:
    inventory = _profile_row()[0]["filtering_variables"][
        "available_extracted_documents"
    ]
    connection = _Connection(
        ({"available_extracted_documents": inventory},),
        [_document_row("Short", [{"page": 1, "text": "Short"}])],
    )
    result = get_approved_document_text(connection, _request())
    assert result["document_name"] == "Clinical Trial Protocol v3"
