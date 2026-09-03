from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import psycopg

from .profile_retrieval import profile_with_current_lifecycle


CLASSIFICATION_PROFILE_SCHEMA_VERSION = "1.0.0"
MAX_CLASSIFICATION_TRIALS = 25
EU_TRIAL_NUMBER_RE = re.compile(r"^\d{4}-\d{6}-\d{2}-\d{2}$")
PERSONAL_CONTACT_KEYS = {
    "first_name",
    "last_name",
    "email",
    "phone",
    "telephone",
    "fax",
}


@dataclass(frozen=True)
class ClassificationProfileRequestError(Exception):
    code: str
    message: str
    status_code: int = 400


def validate_classification_profile_request(request: Any) -> list[str]:
    if not isinstance(request, dict):
        raise ClassificationProfileRequestError("INVALID_REQUEST", "Request body must be an object.")
    if set(request) != {"trial_ids"}:
        raise ClassificationProfileRequestError(
            "INVALID_REQUEST",
            "Only trial_ids is supported by the classification-profile endpoint.",
        )

    trial_ids = request.get("trial_ids")
    if not isinstance(trial_ids, list) or not trial_ids or len(trial_ids) > MAX_CLASSIFICATION_TRIALS:
        raise ClassificationProfileRequestError(
            "INVALID_TRIAL_IDS",
            f"trial_ids must contain 1 to {MAX_CLASSIFICATION_TRIALS} EU trial numbers.",
        )
    if any(not isinstance(value, str) or not EU_TRIAL_NUMBER_RE.fullmatch(value) for value in trial_ids):
        raise ClassificationProfileRequestError(
            "INVALID_TRIAL_IDS",
            "Every trial_id must be a valid EU trial number.",
        )
    if len(set(trial_ids)) != len(trial_ids):
        raise ClassificationProfileRequestError(
            "DUPLICATE_TRIAL_IDS",
            "trial_ids must not contain duplicates.",
        )
    return trial_ids


def _remove_contact_personal_data(value: Any) -> Any:
    """Return an analysis-safe copy without contact personal data.

    Classification needs the complete Trial Profile, including its document
    inventory, but not contact personal data. Keep non-personal fields (for
    example role, department, site and organisation) so criteria can use them.
    """
    if isinstance(value, list):
        return [_remove_contact_personal_data(item) for item in value]
    if isinstance(value, dict):
        return {
            key: _remove_contact_personal_data(item)
            for key, item in value.items()
            if key not in PERSONAL_CONTACT_KEYS
        }
    return value


def get_approved_classification_profiles(
    connection: psycopg.Connection[Any], request: Any
) -> dict[str, Any]:
    trial_ids = validate_classification_profile_request(request)
    rows = connection.execute(
        """
        SELECT profile.eu_number, profile.profile_json, profile.ctis_data,
               profile.schema_version
        FROM mcp_serving.approved_profiles_v1 AS profile
        WHERE profile.approval_status = 'approved'
          AND profile.eu_number = ANY(%s::text[])
        """,
        (trial_ids,),
    ).fetchall()
    by_id = {
        str(row[0]): profile_with_current_lifecycle(row[1], row[2], str(row[3]))
        for row in rows
    }
    missing = [trial_id for trial_id in trial_ids if trial_id not in by_id]
    if missing:
        raise ClassificationProfileRequestError(
            "TRIAL_PROFILE_NOT_AVAILABLE",
            "Classification requires an approved Trial Profile for every requested trial. "
            f"Unavailable trial(s): {', '.join(missing)}.",
            404,
        )

    return {
        "data": [
            {
                "eu_number": trial_id,
                "profile": _remove_contact_personal_data(by_id[trial_id]),
            }
            for trial_id in trial_ids
        ],
        "schema_version": CLASSIFICATION_PROFILE_SCHEMA_VERSION,
    }
