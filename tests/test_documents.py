from __future__ import annotations

from intel_mcp.documents import GetDocumentsOutput


def test_get_documents_output_schema_is_text_only_and_minimal() -> None:
    assert set(GetDocumentsOutput.model_json_schema()["properties"]) == {
        "trial_id",
        "document_name",
        "document_type",
        "part",
        "text",
        "next_part",
        "analysis_allowance",
    }
