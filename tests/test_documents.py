from __future__ import annotations

from intel_mcp.documents import GetDocumentsOutput
from intel_mcp.models import DocumentTypeFilter, EngineFilterResponse, FilterTrialItem


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


def test_filter_result_exposes_six_document_category_arrays() -> None:
    assert set(FilterTrialItem.model_json_schema()["properties"]) == {
        "eu_number",
        "trial_title",
        "sponsor_name",
        "protocol",
        "recruitment_arrangements",
        "patient_information_and_informed_consent",
        "assessments_and_forms",
        "clinical_study_report",
        "results_summary",
    }


def test_document_type_filter_uses_the_six_profile_categories() -> None:
    value = DocumentTypeFilter(
        values=["clinical_study_report", "results_summary"]
    )
    assert value.values == ["clinical_study_report", "results_summary"]
    assert "results_report" not in DocumentTypeFilter.canonical_values


def test_engine_filter_temporarily_accepts_the_legacy_projection() -> None:
    response = EngineFilterResponse.model_validate(
        {
            "data": [
                {
                    "eu_number": "2024-500001-00-00",
                    "trial_title": "Example trial",
                    "sponsor_name": "Example sponsor",
                    "available_extracted_document_names": ["Protocol v2"],
                }
            ],
            "counts": {"total_profiles": 1, "total_matches": 1, "returned": 1},
        }
    )
    assert response.data[0].protocol == []
    assert response.data[0].available_extracted_document_names == ["Protocol v2"]
