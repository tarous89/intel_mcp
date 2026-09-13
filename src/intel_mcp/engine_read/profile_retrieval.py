from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import psycopg

from .lifecycle import build_ctis_lifecycle
from .prepopulate import eligibility_criteria, reconcile_derived_fields
from .schema import SCHEMA_VERSION


PROFILE_RETRIEVAL_SCHEMA_VERSION = "1.0.0"
MAX_PROFILES_PER_REQUEST = 10
EU_TRIAL_NUMBER_RE = re.compile(r"^\d{4}-\d{6}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class ProfileRetrievalRequestError(Exception):
    code: str
    message: str
    status_code: int = 400


def validate_profile_retrieval_request(request: Any) -> list[str]:
    if not isinstance(request, dict):
        raise ProfileRetrievalRequestError("INVALID_REQUEST", "Request body must be an object.")
    if set(request) != {"trial_ids"}:
        raise ProfileRetrievalRequestError(
            "INVALID_REQUEST",
            "Only trial_ids is supported by the profile-retrieval endpoint.",
        )

    trial_ids = request.get("trial_ids")
    if not isinstance(trial_ids, list) or not trial_ids or len(trial_ids) > MAX_PROFILES_PER_REQUEST:
        raise ProfileRetrievalRequestError(
            "INVALID_TRIAL_IDS",
            f"trial_ids must contain 1 to {MAX_PROFILES_PER_REQUEST} EU trial numbers.",
        )
    if any(not isinstance(value, str) or not EU_TRIAL_NUMBER_RE.fullmatch(value) for value in trial_ids):
        raise ProfileRetrievalRequestError(
            "INVALID_TRIAL_IDS",
            "Every trial_id must be a valid EU trial number.",
        )

    # The public MCP contract de-duplicates while preserving caller order. Keep
    # the local read boundary equally safe when called directly.
    return list(dict.fromkeys(trial_ids))


def _isoformat(value: date | datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def profile_with_current_lifecycle(
    profile: dict[str, Any],
    ctis_json: dict[str, Any] | None,
    profile_schema_version: str | None = None,
) -> dict[str, Any]:
    """Refresh deterministic fields without runtime-migrating profile JSON."""
    result = deepcopy(profile)
    if (
        isinstance(ctis_json, dict)
        and profile_schema_version in {"9.0.0", "10.0.0", SCHEMA_VERSION}
    ):
        result["ctis_lifecycle"] = build_ctis_lifecycle(ctis_json)
        inclusion, exclusion = eligibility_criteria(ctis_json)
        filtering = result.get("filtering_variables")
        if isinstance(filtering, dict):
            filtering["inclusion_criteria"] = inclusion
            filtering["exclusion_criteria"] = exclusion
        # Retrieval uses the same final reconciliation as generation and
        # refresh, removing any stale public country-status scalars while the
        # rebuilt lifecycle remains the dated source of truth.
        result = reconcile_derived_fields(result)
    return result


def get_approved_profiles(
    connection: psycopg.Connection[Any], request: Any, *, all_profiles: bool = False
) -> dict[str, Any]:
    """Return current Trial Profiles without model work.

    Missing or unapproved profiles are reported as unavailable rather than
    failing the whole batch. Candidate/rejected state is deliberately not
    disclosed to the caller. Public MCP projection, when requested, is applied
    only after the read and control-plane authorization. Max alone opts into
    the separate all-state report view and receives status for its dataset.
    """
    trial_ids = validate_profile_retrieval_request(request)
    view = "mcp_serving.report_profiles_v1" if all_profiles else "mcp_serving.approved_profiles_v1"
    rows = connection.execute(
        f"""
        SELECT profile.eu_number,
               profile.schema_version,
               profile.approved_at,
               profile.profile_json,
               profile.ctis_data,
               profile.approval_status
        FROM {view} AS profile
        WHERE profile.eu_number = ANY(%s::text[])
        """,
        (trial_ids,),
    ).fetchall()
    if all_profiles:
        # A deterministic backfill can coexist with an enriched profile for the
        # same trial. Prefer enriched content regardless of approval state;
        # retrieval below refreshes its eligibility/lifecycle from current CTIS.
        # Keep one trial and never let database row order discard richer data.
        rows = sorted(rows, key=lambda row: (
            len(row) > 5 and str(row[5]) != "deterministic",
            _isoformat(row[2]) or "",
        ))
    by_id = {
        str(row[0]): {
            "eu_number": str(row[0]),
            "profile_schema_version": str(row[1]),
            "approved_at": _isoformat(row[2]),
            **({"approval_status": str(row[5])} if all_profiles and len(row) > 5 else {}),
            "profile": profile_with_current_lifecycle(
                row[3], row[4] if len(row) > 4 else None, str(row[1])
            ),
        }
        for row in rows
    }

    return {
        "data": [by_id[trial_id] for trial_id in trial_ids if trial_id in by_id],
        "unavailable_trial_ids": [trial_id for trial_id in trial_ids if trial_id not in by_id],
        "schema_version": PROFILE_RETRIEVAL_SCHEMA_VERSION,
    }
