from __future__ import annotations

import pytest
from pydantic import ValidationError

from intel_mcp.documents import GetDocumentsOutput
from intel_mcp.models import DocumentTypeFilter, FilterTrialItem, ModalityFilter


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


def test_filter_result_is_a_lean_shortlist_projection() -> None:
    assert set(FilterTrialItem.model_json_schema()["properties"]) == {
        "eu_number",
        "trial_title",
        "sponsor_name",
    }


def test_document_type_filter_uses_the_six_profile_categories() -> None:
    value = DocumentTypeFilter(
        values=["clinical_study_report", "results_summary"]
    )
    assert value.values == ["clinical_study_report", "results_summary"]
    assert "results_report" not in DocumentTypeFilter.canonical_values


def test_modality_filter_matches_trial_profile_10_scalar_vocabulary() -> None:
    assert len(ModalityFilter.canonical_values) == 18
    assert "Other biologic" in ModalityFilter.canonical_values
    assert "Biologic" not in ModalityFilter.canonical_values
    assert "Antibody" not in ModalityFilter.canonical_values
    assert ModalityFilter(values=["other biologic"]).values == ["Other biologic"]
    with pytest.raises(ValidationError):
        ModalityFilter(values=["Biologic"])
