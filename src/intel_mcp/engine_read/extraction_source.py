from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import psycopg

from .document_retrieval import (
    _available_document_inventory,
    _compact_text,
    _document_name,
)
from .source import _format_protocol_pages


EXTRACTION_SOURCE_SCHEMA_VERSION = "1.0.0"
EU_TRIAL_NUMBER_RE = re.compile(r"^\d{4}-\d{6}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class ExtractionSourceRequestError(Exception):
    code: str
    message: str
    status_code: int = 400


def validate_extraction_source_request(request: Any) -> str:
    if not isinstance(request, dict):
        raise ExtractionSourceRequestError("INVALID_REQUEST", "Request body must be an object.")
    if set(request) != {"trial_id"}:
        raise ExtractionSourceRequestError(
            "INVALID_REQUEST",
            "Only trial_id is supported by the extraction-source endpoint.",
        )
    trial_id = request.get("trial_id")
    if not isinstance(trial_id, str) or not EU_TRIAL_NUMBER_RE.fullmatch(trial_id):
        raise ExtractionSourceRequestError(
            "INVALID_TRIAL_ID", "trial_id must be a valid EU trial number."
        )
    return trial_id


def get_approved_extraction_source(
    connection: psycopg.Connection[Any], request: Any
) -> dict[str, Any]:
    """Return one approved profile plus its single profile-listed protocol.

    Protocol selection is completed upstream when the profile's deterministic
    extracted-document inventory is built. This boundary resolves only that
    protocol name and never re-ranks other stored protocol-category rows.
    """
    trial_id = validate_extraction_source_request(request)
    profile_row = connection.execute(
        """
        SELECT profile.profile_json, profile.engine_trial_id
        FROM mcp_serving.approved_profiles_v1 AS profile
        WHERE profile.approval_status = 'approved'
          AND profile.eu_number = %s
        LIMIT 1
        """,
        (trial_id,),
    ).fetchone()
    if not profile_row:
        raise ExtractionSourceRequestError(
            "TRIAL_PROFILE_NOT_AVAILABLE",
            "Variable extraction requires a current approved Trial Profile.",
            404,
        )

    profile = profile_row[0]
    inventory = _available_document_inventory(profile)
    protocol_names = (
        inventory.get("protocol")
        if isinstance(inventory, dict)
        and isinstance(inventory.get("protocol"), list)
        else []
    )
    protocol_name = next(
        (
            _compact_text(name)
            for name in protocol_names
            if isinstance(name, str) and _compact_text(name)
        ),
        None,
    )

    protocol_text: str | None = None
    if protocol_name is not None:
        rows = connection.execute(
            """
            SELECT d.document_id,
                   d.title_raw,
                   d.filename_raw,
                   d.document_type_label_raw,
                   x.full_text,
                   x.pages_json
            FROM mcp_serving.documents_v1 AS d
            JOIN mcp_serving.document_text_v1 AS x
              ON x.document_id = d.document_id
            WHERE d.trial_id = %s
              AND d.document_category = 'protocol'
              AND x.extraction_status IN ('success', 'partial')
              AND COALESCE(length(x.full_text), 0) > 0
            ORDER BY d.document_id
            """,
            (int(profile_row[1]),),
        ).fetchall()
        requested_identity = protocol_name.casefold()
        for row in rows:
            name = _document_name(int(row[0]), row[1], row[2], row[3])
            if name.casefold() != requested_identity:
                continue
            protocol_text = _format_protocol_pages(int(row[0]), list(row[5] or []))
            if not protocol_text:
                protocol_text = str(row[4] or "").strip() or None
            break

    return {
        "trial_id": trial_id,
        "profile": profile,
        "protocol_text": protocol_text,
        "schema_version": EXTRACTION_SOURCE_SCHEMA_VERSION,
    }
