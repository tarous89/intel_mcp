"""Bounded whole-cohort read on the existing available-profile serving views."""
from .filtering import build_where, validate_request, _escape_like
from .profile_retrieval import profile_with_current_lifecycle
from ..selection import MAX_COHORT, SelectionCriteria, SelectionDataset, SelectionError, clean_filters
from ..selection_discovery import TEXT_PATHS, text_evidence


def _where(filters):
    validated, _, _, _ = validate_request({"filters": clean_filters(filters), "limit": 1, "offset": 0})
    return build_where(validated)


def _text_where(query):
    if query is None:
        return "TRUE", []
    # Paths are closed enums, while all user search terms remain bound parameters.
    columns = ["COALESCE(source.profile_json #>> '{" + ",".join(TEXT_PATHS[field]) + "}', '')" for field in query.fields]
    params = []
    def term_clause(term):
        params.extend(["%" + _escape_like(term) + "%"] * len(columns))
        return "(" + " OR ".join(f"{column} ILIKE %s ESCAPE E'\\\\'" for column in columns) + ")"
    clauses = [term_clause(term) for term in query.terms]
    positive = (" OR " if query.operator == "any" else " AND ").join(clauses)
    negative = ["NOT " + term_clause(term) for term in query.exclude_terms]
    return "(" + positive + ")" + (" AND " + " AND ".join(negative) if negative else ""), params


def _group_where(group):
    filters = group.filters
    if not group.phase_title_fallback:
        structured, params = _where(filters)
    else:
        phase = filters.phase
        if phase.operator != "contains_any":
            raise SelectionError("INVALID_PHASE_FALLBACK: Title fallback supports positive contains_any phase rules only.")
        structured, params = _where(filters.model_copy(update={"phase": None}))
        phase_sql, phase_params = _where(type(filters)(phase=phase))
        romans = {1: "i", 2: "ii", 3: "iii", 4: "iv"}
        choices = "|".join(str(v) + "|" + romans[v] for v in sorted(set(phase.values)))
        pattern = r"\mphase[[:space:]-]*(" + choices + r")\M"
        structured += f" AND (({phase_sql}) OR (COALESCE(cardinality(p.phase), 0) = 0 AND COALESCE(source.profile_json #>> '{{classification_variables,trial_title}}', '') ~* %s))"
        params += [*phase_params, pattern]
    text_sql, text_params = _text_where(group.text)
    return f"({structured}) AND ({text_sql})", params + text_params


def read_selection(connection, request):
    criteria = SelectionCriteria.model_validate(request)
    base, base_params = _where(criteria.base)
    text_sql, text_params = _text_where(criteria.base_text)
    base = f"({base}) AND ({text_sql})"
    base_params += text_params
    direct, direct_params = _where(criteria.direct)
    related, related_params = _where(criteria.related) if criteria.related is not None else ("FALSE", [])
    group_columns, group_params = [], []
    for group in criteria.subgroups:
        sql, params = _group_where(group)
        group_columns.append(f", COALESCE(({sql}), FALSE)")
        group_params.extend(params)
    records = []
    with connection.cursor(name="selection_profiles") as cursor:
        cursor.execute(f"""
            SELECT p.eu_number, source.schema_version, source.profile_json, source.ctis_data,
                   ({direct}) AS direct_match, ({related}) AS related_match
                   {''.join(group_columns)}
            FROM mcp_serving.profile_filter_v1 p
            JOIN mcp_serving.approved_profiles_v1 source ON source.eu_number = p.eu_number
            WHERE {base}
            ORDER BY p.eu_number
            LIMIT %s
            """, [*direct_params, *related_params, *group_params, *base_params, MAX_COHORT + 1])
        while batch := cursor.fetchmany(10):
            for tid, schema, profile, ctis, direct_match, related_match, *matches in batch:
                if len(records) >= MAX_COHORT:
                    raise SelectionError("COHORT_TOO_LARGE: Narrow base criteria; no partial ranking was produced.")
                if schema != "11.0.0" or not isinstance(profile, dict) or not isinstance(profile.get("classification_variables"), dict):
                    raise SelectionError("UNSUPPORTED_PROFILE: Selection requires complete schema 11 profiles.")
                evidence = [{"rule": "base", **e} for e in text_evidence(profile, criteria.base_text)]
                for group, matched in zip(criteria.subgroups, matches):
                    if matched:
                        evidence.extend({"rule": group.id, **e} for e in text_evidence(profile, group.text))
                        if group.filters.phase:
                            phase = (profile.get("filtering_variables") or {}).get("phase")
                            evidence.append({"rule": group.id, "field": "phase", "basis": "structured" if phase else "title_fallback", "value": phase or profile["classification_variables"].get("trial_title")})
                records.append({"trial_id": tid, "schema_version": schema,
                    "profile": profile_with_current_lifecycle(profile, ctis, schema),
                    "direct": bool(direct_match), "related": bool(related_match),
                    "subgroup_matches": [bool(m) for m in matches], "discovery_evidence": evidence})
    return SelectionDataset(criteria, records)
