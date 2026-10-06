"""Bounded whole-cohort read on the existing approved serving views."""
from .filtering import build_where, validate_request
from .profile_retrieval import profile_with_current_lifecycle
from ..selection import MAX_COHORT, SelectionCriteria, SelectionDataset, SelectionError, clean_filters


def _where(filters):
    validated, _, _, _ = validate_request({"filters": clean_filters(filters), "limit": 1, "offset": 0})
    return build_where(validated)


def read_selection(connection, request):
    criteria = SelectionCriteria.model_validate(request)
    base, base_params = _where(criteria.base)
    direct, direct_params = _where(criteria.direct)
    related, related_params = _where(criteria.related) if criteria.related is not None else ("FALSE", [])
    # One SQL statement gives membership and content one MVCC snapshot. Never silently sample.
    records = []
    with connection.cursor(name="selection_profiles") as cursor:
        cursor.execute(f"""
            SELECT p.eu_number, source.schema_version, source.profile_json, source.ctis_data,
                   ({direct}) AS direct_match, ({related}) AS related_match
            FROM mcp_serving.profile_filter_v1 p
            JOIN mcp_serving.approved_profiles_v1 source ON source.eu_number = p.eu_number
            WHERE {base}
            ORDER BY p.eu_number
            LIMIT %s
            """, [*direct_params, *related_params, *base_params, MAX_COHORT + 1])
        while batch := cursor.fetchmany(10):
            for tid, schema, profile, ctis, direct_match, related_match in batch:
                if len(records) >= MAX_COHORT:
                    raise SelectionError("COHORT_TOO_LARGE: Narrow base criteria; no partial ranking was produced.")
                if schema != "11.0.0" or not isinstance(profile, dict) or not isinstance(profile.get("classification_variables"), dict):
                    raise SelectionError("UNSUPPORTED_PROFILE: Selection requires complete schema 11 profiles.")
                records.append({"trial_id": tid, "schema_version": schema,
                    "profile": profile_with_current_lifecycle(profile, ctis, schema),
                    "direct": bool(direct_match), "related": bool(related_match)})
    return SelectionDataset(criteria, records)
