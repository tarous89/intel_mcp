from __future__ import annotations

from typing import Any


def _normalized_extracted_document_type(
    document_category: str | None,
    document_type_label_raw: str | None,
) -> str | None:
    category = str(document_category or "").strip().lower()
    if category in {
        "protocol",
        "patient_information_and_informed_consent",
        "assessments_and_forms",
        "clinical_study_report",
        "results_summary",
    }:
        return category

    label = " ".join(str(document_type_label_raw or "").lower().split())
    if category == "results_report":
        if "clinical study report" in label:
            return "clinical_study_report"
        return "results_summary"
    if category != "recruitment_arrangements":
        return None
    patient_information_markers = (
        "subject information",
        "patient information",
        "participant information",
        "informed consent",
        "information sheet",
        "consent form",
    )
    if any(marker in label for marker in patient_information_markers):
        return "patient_information_and_informed_consent"
    return "recruitment_arrangements"


def _format_protocol_pages(document_id: int, pages: list[dict[str, Any]]) -> str:
    chunks: list[str] = []
    for fallback_page, page in enumerate(pages, start=1):
        text = str(page.get("text") or "").strip()
        if not text or page.get("extraction_status") == "failed":
            continue
        page_number = int(page.get("page") or fallback_page)
        chunks.append(
            f"[[PROTOCOL DOCUMENT {document_id} PAGE {page_number}]]\n{text}"
        )
    return "\n\n".join(chunks)
