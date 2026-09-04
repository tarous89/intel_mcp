from __future__ import annotations

from typing import Any

from intel_mcp.config import Settings, _openai_service_tier
from intel_mcp.engine_read.document_retrieval import get_approved_document_text
from intel_mcp.engine_read.extraction_source import get_approved_extraction_source


class FakeResult:
    def __init__(self, *, one: tuple[Any, ...] | None = None, many: list[tuple[Any, ...]] | None = None) -> None:
        self._one = one
        self._many = many or []

    def fetchone(self):
        return self._one

    def fetchall(self):
        return self._many


class SequencedConnection:
    def __init__(self, results: list[FakeResult]) -> None:
        self.results = list(results)
        self.statements: list[str] = []
        self.params: list[tuple[Any, ...] | None] = []

    def execute(self, statement: str, params: tuple[Any, ...] | None = None):
        self.statements.append(" ".join(statement.split()))
        self.params.append(params)
        if not self.results:
            raise AssertionError("Unexpected SQL statement")
        return self.results.pop(0)


def _profile(protocol_name: str = "Protocol") -> dict[str, Any]:
    return {
        "filtering_variables": {
            "available_extracted_documents": {
                "protocol": [protocol_name],
                "recruitment_arrangements": [],
                "patient_information_and_informed_consent": [],
                "assessments_and_forms": [],
                "clinical_study_report": [],
                "results_summary": [],
            }
        }
    }


def test_legacy_standard_service_tier_is_normalized_to_default() -> None:
    assert _openai_service_tier("standard") == "default"
    assert _openai_service_tier(" DEFAULT ") == "default"
    assert Settings.__dataclass_fields__["classifier_service_tier"].default == "default"
    assert Settings.__dataclass_fields__["extractor_service_tier"].default == "default"


def test_document_retrieval_resolves_catalogue_then_reads_exact_text_row() -> None:
    connection = SequencedConnection(
        [
            FakeResult(one=(_profile(),)),
            FakeResult(
                many=[
                    (7, "uuid-7", "protocol", "Protocol", "Protocol", "protocol.pdf"),
                ]
            ),
            FakeResult(one=("Protocol body", [])),
        ]
    )

    result = get_approved_document_text(
        connection,  # type: ignore[arg-type]
        {
            "trial_id": "2024-500001-00-00",
            "document_name": "Protocol",
            "part": 1,
        },
    )

    assert result["document_name"] == "Protocol"
    assert "Protocol body" in result["text"]
    assert connection.params[-1] == (7,)
    assert "WHERE document_id = %s" in connection.statements[-1]
    assert not any(
        "mcp_serving.documents_v1" in statement
        and "mcp_serving.document_text_v1" in statement
        for statement in connection.statements
    )


def test_extraction_source_resolves_protocol_then_reads_exact_text_row() -> None:
    connection = SequencedConnection(
        [
            FakeResult(one=(_profile(), 42)),
            FakeResult(many=[(7, "Protocol", "protocol.pdf", "Protocol")]),
            FakeResult(one=("Protocol body", [])),
        ]
    )

    result = get_approved_extraction_source(
        connection,  # type: ignore[arg-type]
        {"trial_id": "2024-500001-00-00"},
    )

    assert result["protocol_text"] == "Protocol body"
    assert connection.params[-1] == (7,)
    assert "WHERE document_id = %s" in connection.statements[-1]
    assert not any(
        "mcp_serving.documents_v1" in statement
        and "mcp_serving.document_text_v1" in statement
        for statement in connection.statements
    )
