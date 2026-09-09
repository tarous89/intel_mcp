from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import psycopg

EXTRACTION_SOURCE_SCHEMA_VERSION = "2.0.0"
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
    """Return one complete approved profile and never read document text."""
    trial_id = validate_extraction_source_request(request)
    profile_row = connection.execute(
        """
        SELECT profile.profile_json
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

    return {
        "trial_id": trial_id,
        "profile": profile_row[0],
        "schema_version": EXTRACTION_SOURCE_SCHEMA_VERSION,
    }
