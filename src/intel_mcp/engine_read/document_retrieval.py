from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

import psycopg

from .source import _normalized_extracted_document_type


DOCUMENT_RETRIEVAL_SCHEMA_VERSION = "1.0.0"
MAX_TEXT_PART_CHARACTERS = 200_000
MAX_DOCUMENT_NAME_CHARACTERS = 1_000
MAX_DOCUMENT_PART = 10_000
EU_TRIAL_NUMBER_RE = re.compile(r"^\d{4}-\d{6}-\d{2}-\d{2}$")
DOCUMENT_INVENTORY_FIELDS = (
    "protocol",
    "recruitment_arrangements",
    "patient_information_and_informed_consent",
    "assessments_and_forms",
    "clinical_study_report",
    "results_summary",
)


@dataclass(frozen=True)
class DocumentRetrievalRequest:
    trial_id: str
    document_name: str
    part: int


@dataclass(frozen=True)
class DocumentRetrievalRequestError(Exception):
    code: str
    message: str
    status_code: int = 400


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _document_name(
    document_id: int,
    title_raw: Any,
    filename_raw: Any,
    document_type_label_raw: Any,
) -> str:
    title = _compact_text(title_raw)
    if title:
        return title
    filename = _compact_text(filename_raw)
    if filename:
        return filename
    label = _compact_text(document_type_label_raw)
    return f"{label} [document {document_id}]" if label else f"Document {document_id}"


def _available_document_inventory(profile_json: Any) -> dict[str, Any]:
    if not isinstance(profile_json, dict):
        return {}
    filtering = profile_json.get("filtering_variables")
    if isinstance(filtering, dict):
        inventory = filtering.get("available_extracted_documents")
        if isinstance(inventory, dict):
            return inventory
    legacy_inventory = profile_json.get("available_extracted_documents")
    return legacy_inventory if isinstance(legacy_inventory, dict) else {}


def _available_document_types(profile_json: Any, requested_identity: str) -> set[str]:
    inventory = _available_document_inventory(profile_json)
    return {
        document_type
        for document_type in DOCUMENT_INVENTORY_FIELDS
        for name in (
            inventory.get(document_type)
            if isinstance(inventory.get(document_type), list)
            else []
        )
        if isinstance(name, str) and _compact_text(name).casefold() == requested_identity
    }


def validate_document_retrieval_request(request: Any) -> DocumentRetrievalRequest:
    if not isinstance(request, dict):
        raise DocumentRetrievalRequestError("INVALID_REQUEST", "Request body must be an object.")
    if set(request) != {"trial_id", "document_name", "part"}:
        raise DocumentRetrievalRequestError(
            "INVALID_REQUEST",
            "Only trial_id, document_name and part are supported by the document-retrieval endpoint.",
        )

    trial_id = request.get("trial_id")
    document_name = request.get("document_name")
    part = request.get("part")
    if not isinstance(trial_id, str) or not EU_TRIAL_NUMBER_RE.fullmatch(trial_id):
        raise DocumentRetrievalRequestError(
            "INVALID_TRIAL_ID", "trial_id must be a valid EU trial number."
        )
    if (
        not isinstance(document_name, str)
        or not document_name.strip()
        or len(document_name) > MAX_DOCUMENT_NAME_CHARACTERS
    ):
        raise DocumentRetrievalRequestError(
            "INVALID_DOCUMENT_NAME",
            f"document_name must contain 1 to {MAX_DOCUMENT_NAME_CHARACTERS} characters.",
        )
    if isinstance(part, bool) or not isinstance(part, int) or part < 1 or part > MAX_DOCUMENT_PART:
        raise DocumentRetrievalRequestError(
            "INVALID_DOCUMENT_PART", f"part must be an integer from 1 to {MAX_DOCUMENT_PART}."
        )
    return DocumentRetrievalRequest(
        trial_id=trial_id,
        document_name=_compact_text(document_name),
        part=part,
    )


def _split_content(text: str, limit: int) -> list[str]:
    """Split without losing text, preferring paragraph or line boundaries."""
    parts: list[str] = []
    remaining = text
    while len(remaining) > limit:
        minimum_boundary = limit // 2
        boundary = remaining.rfind("\n\n", minimum_boundary, limit + 1)
        delimiter_length = 2
        if boundary < 0:
            boundary = remaining.rfind("\n", minimum_boundary, limit + 1)
            delimiter_length = 1
        if boundary < 0:
            boundary = remaining.rfind(" ", minimum_boundary, limit + 1)
            delimiter_length = 1
        cut = boundary + delimiter_length if boundary >= 0 else limit
        parts.append(remaining[:cut])
        remaining = remaining[cut:]
    if remaining:
        parts.append(remaining)
    return parts


def _page_blocks(pages: Any, full_text: str) -> list[str]:
    source_pages = pages if isinstance(pages, list) else []
    blocks: list[str] = []
    if not source_pages and full_text.strip():
        source_pages = [{"page": 1, "text": full_text}]

    for fallback_page, page in enumerate(source_pages, start=1):
        if not isinstance(page, dict) or page.get("extraction_status") == "failed":
            continue
        text = str(page.get("text") or "").strip()
        if not text:
            continue
        try:
            page_number = int(page.get("page") or fallback_page)
        except (TypeError, ValueError):
            page_number = fallback_page

        first_marker = f"[[PAGE {page_number}]]\n"
        continuation_marker = f"[[PAGE {page_number} CONTINUED]]\n"
        content_limit = MAX_TEXT_PART_CHARACTERS - max(
            len(first_marker), len(continuation_marker)
        )
        for index, content in enumerate(_split_content(text, content_limit)):
            marker = first_marker if index == 0 else continuation_marker
            blocks.append(marker + content)
    return blocks


def _pack_parts(blocks: list[str]) -> list[str]:
    parts: list[str] = []
    current = ""
    for block in blocks:
        candidate = block if not current else f"{current}\n\n{block}"
        if current and len(candidate) > MAX_TEXT_PART_CHARACTERS:
            parts.append(current)
            current = block
        else:
            current = candidate
    if current:
        parts.append(current)
    return parts


def get_approved_document_text(
    connection: psycopg.Connection[Any], request: Any
) -> dict[str, Any]:
    selection = validate_document_retrieval_request(request)

    profile = connection.execute(
        """
        SELECT profile_json
        FROM mcp_serving.approved_profiles_v1
        WHERE approval_status = 'approved'
          AND eu_number = %s
        LIMIT 1
        """,
        (selection.trial_id,),
    ).fetchone()
    requested_identity = selection.document_name.casefold()
    available_types = (
        _available_document_types(profile[0], requested_identity) if profile else set()
    )
    if not available_types:
        raise DocumentRetrievalRequestError(
            "DOCUMENT_UNAVAILABLE",
            "The requested document is not available as extracted text for an approved Trial Profile.",
            404,
        )

    # Resolve the document identity from the lightweight catalogue first. Do not join
    # the catalogue and text serving views: both are security-barrier views and that
    # join can force a broad document-text scan under the restricted role's 15s timeout.
    rows = connection.execute(
        """
        SELECT document_id,
               ctis_uuid,
               document_category,
               document_type_label_raw,
               title_raw,
               filename_raw
        FROM mcp_serving.documents_v1
        WHERE eu_number = %s
        ORDER BY document_id
        """,
        (selection.trial_id,),
    ).fetchall()

    matched: tuple[Any, ...] | None = None
    matched_name = ""
    matched_type: str | None = None
    for row in rows:
        name = _document_name(int(row[0]), row[4], row[5], row[3])
        document_type = _normalized_extracted_document_type(row[2], row[3])
        if name.casefold() == requested_identity and document_type in available_types:
            matched = row
            matched_name = name
            matched_type = document_type
            break
    if matched is None:
        raise DocumentRetrievalRequestError(
            "DOCUMENT_UNAVAILABLE",
            "The requested document is not available as extracted text for an approved Trial Profile.",
            404,
        )

    text_row = connection.execute(
        """
        SELECT full_text, pages_json
        FROM mcp_serving.document_text_v1
        WHERE document_id = %s
          AND extraction_status IN ('success', 'partial')
          AND COALESCE(length(full_text), 0) > 0
        LIMIT 1
        """,
        (int(matched[0]),),
    ).fetchone()
    if text_row is None:
        raise DocumentRetrievalRequestError(
            "DOCUMENT_UNAVAILABLE",
            "The requested document is not available as extracted text for an approved Trial Profile.",
            404,
        )

    assert matched_type is not None
    parts = _pack_parts(_page_blocks(text_row[1], str(text_row[0] or "")))
    if selection.part > len(parts):
        raise DocumentRetrievalRequestError(
            "DOCUMENT_PART_UNAVAILABLE",
            "The requested document part does not exist. Stop when next_part is null.",
            416,
        )

    document_identity = str(matched[1] or matched[0])
    access_key = sha256(
        f"{selection.trial_id}\n{document_identity}".encode("utf-8")
    ).hexdigest()
    next_part = selection.part + 1 if selection.part < len(parts) else None
    return {
        "trial_id": selection.trial_id,
        "document_name": matched_name,
        "document_type": matched_type,
        "part": selection.part,
        "text": parts[selection.part - 1],
        "next_part": next_part,
        "document_access_key": access_key,
        "schema_version": DOCUMENT_RETRIEVAL_SCHEMA_VERSION,
    }
