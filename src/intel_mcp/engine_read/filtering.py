from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Any

import psycopg


MAX_PAGE_SIZE = 100
COUNTRY_CODE_RE = re.compile(r"^[A-Za-z]{2}$")

TEXT_FIELDS = {"eu_number", "trial_title", "trial_acronym", "sponsor_name"}
DATE_FIELDS = {
    "latest_country_submission_or_approval_date",
    "initial_ctis_submission_date",
    "first_ctis_authorization_date",
    "latest_ctis_authorization_date",
}
NUMBER_FIELDS = {"planned_sample_size", "number_of_countries", "number_of_sites"}
BOOLEAN_FIELDS = {"rare_disease_trial", "orphan_designation", "paediatric_trial", "first_in_human"}
CONTROLLED_SCALAR_FIELDS = {"allocation", "masking", "intervention_model"}
ARRAY_FIELDS = {
    "available_extracted_document_types",
    "available_extracted_document_names",
    "therapeutic_areas",
    "modalities",
    "routes_of_administration",
    "country_codes",
    "eligible_sexes",
    "comparator_types",
}
SORT_FIELDS = DATE_FIELDS | NUMBER_FIELDS | {"eu_number"}

CONTROLLED_VALUES: dict[str, set[str]] = {
    "available_extracted_document_types": {
        "protocol", "recruitment_arrangements", "patient_information_and_informed_consent",
        "assessments_and_forms", "clinical_study_report", "results_summary",
    },
    "therapeutic_areas": {
        "Solid Tumor Oncology", "Haematological Malignancies", "Blood Disorders",
        "Cardiology", "Neurology", "Immunology", "Rheumatology", "Allergy",
        "Infectious Disease", "Endocrinology", "Metabolic Disorders", "Respiratory",
        "Gastroenterology", "Hepatology", "Dermatology", "Musculoskeletal",
        "Ophthalmology", "Otolaryngology", "Oral Health and Dentistry", "Nephrology",
        "Psychiatry", "Pain Medicine", "Gynecology", "Obstetrics",
        "Reproductive Medicine", "Urology", "Emergency Medicine", "Critical Care",
        "Surgery and Perioperative Care", "Transplantation", "Trauma and Injury",
        "Genetic and Congenital Disorders", "Nutrition", "Other",
    },
    "modalities": {
        "Biologic", "Antibody", "Small molecule", "Monoclonal antibody", "Bispecific antibody",
        "Other antibody", "ADC", "Cell therapy", "Gene therapy", "mRNA", "Other RNA",
        "Peptide/protein/enzyme", "Oligonucleotide", "Vaccine", "Radiopharmaceutical",
        "Diagnostic agent", "Medical device", "Procedure", "Other",
    },
    "routes_of_administration": {
        "Oral", "Intravenous", "Subcutaneous", "Intramuscular", "Intratumoral", "Inhaled",
        "Topical", "Ophthalmic", "Intrathecal", "Other",
    },
    "eligible_sexes": {"Female", "Male"},
    "comparator_types": {
        "Placebo", "Active comparator", "Standard of care", "Historical control",
        "External or real-world control", "No comparator", "Other",
    },
    "allocation": {"Randomised", "Non-randomised", "Not applicable"},
    "masking": {
        "Open label", "Single blind", "Double blind", "Triple blind", "Quadruple blind", "Other",
    },
    "intervention_model": {"Parallel", "Single group", "Crossover", "Factorial", "Sequential", "Other"},
    "recruitment_statuses": {
        "Authorised", "Not authorised", "Under evaluation", "Ended", "Halted", "Lapsed",
        "Withdrawn", "Expired", "Suspended", "Not valid", "Pending", "Revoked",
    },
}


@dataclass(frozen=True)
class FilterRequestError(Exception):
    code: str
    message: str
    status_code: int = 400


def _require_object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise FilterRequestError("INVALID_FILTER", f"{name} must be an object.")
    return value


def _casefold_member(value: str, allowed: set[str]) -> bool:
    return value.casefold() in {item.casefold() for item in allowed}


def _canonical_value(value: str, allowed: set[str]) -> str:
    return {item.casefold(): item for item in allowed}[value.casefold()]


def _validate_text_filter(field: str, condition: Any) -> None:
    item = _require_object(condition, field)
    if set(item) - {"operator", "value"}:
        raise FilterRequestError("INVALID_FILTER", f"{field} contains unsupported properties.")
    operator = item.get("operator", "contains")
    if operator not in {"contains", "is", "does_not_contain", "is_not"}:
        raise FilterRequestError("INVALID_OPERATOR", f"{operator!r} is not valid for {field}.")
    value = item.get("value")
    if not isinstance(value, str) or not value.strip() or len(value) > 500:
        raise FilterRequestError("INVALID_FILTER", f"{field}.value must be 1 to 500 characters.")


def _validate_set_filter(field: str, condition: Any, *, numeric: bool = False) -> None:
    item = _require_object(condition, field)
    if set(item) - {"operator", "values"}:
        raise FilterRequestError("INVALID_FILTER", f"{field} contains unsupported properties.")
    operator = item.get("operator", "contains_any")
    if operator not in {"contains_any", "contains_all", "contains_none"}:
        raise FilterRequestError("INVALID_OPERATOR", f"{operator!r} is not valid for {field}.")
    values = item.get("values")
    if not isinstance(values, list) or not values or len(values) > 50:
        raise FilterRequestError("INVALID_FILTER", f"{field}.values must contain 1 to 50 values.")
    if numeric:
        if any(type(value) is not int or value not in {1, 2, 3, 4} for value in values):
            raise FilterRequestError("INVALID_CONTROLLED_VALUE", "phase values must be integers 1, 2, 3 or 4.")
        return
    if any(not isinstance(value, str) or not value.strip() or len(value) > 500 for value in values):
        raise FilterRequestError("INVALID_FILTER", f"Every {field} value must be a non-empty string.")
    if field in {"country_codes"} and any(not COUNTRY_CODE_RE.fullmatch(value) for value in values):
        raise FilterRequestError("INVALID_CONTROLLED_VALUE", f"{field} values must be ISO alpha-2 codes.")
    if field == "country_codes":
        item["values"] = [value.upper() for value in values]
    allowed = CONTROLLED_VALUES.get(field)
    if allowed:
        invalid = [value for value in values if not _casefold_member(value, allowed)]
        if invalid:
            raise FilterRequestError(
                "INVALID_CONTROLLED_VALUE",
                f"Unsupported {field} value(s): {', '.join(invalid)}. Use the values advertised in the tool schema.",
            )
        item["values"] = [_canonical_value(value, allowed) for value in values]


def _validate_boolean_filter(field: str, condition: Any) -> None:
    item = _require_object(condition, field)
    if set(item) - {"operator", "value"}:
        raise FilterRequestError("INVALID_FILTER", f"{field} contains unsupported properties.")
    if item.get("operator", "is") not in {"is", "is_not"}:
        raise FilterRequestError("INVALID_OPERATOR", f"Only is and is_not are valid for {field}.")
    if item.get("value") not in {True, False, "unknown"}:
        raise FilterRequestError("INVALID_FILTER", f"{field}.value must be true, false or unknown.")


def _validate_comparison_filter(field: str, condition: Any, *, is_date: bool = False) -> None:
    item = _require_object(condition, field)
    if set(item) - {"operator", "value", "minimum", "maximum"}:
        raise FilterRequestError("INVALID_FILTER", f"{field} contains unsupported properties.")
    operator = item.get("operator", "is")
    allowed = {"is", "is_not", "greater_than", "greater_than_or_equal", "less_than", "less_than_or_equal", "between"}
    if operator not in allowed:
        raise FilterRequestError("INVALID_OPERATOR", f"{operator!r} is not valid for {field}.")

    def valid(value: Any) -> bool:
        if is_date:
            if not isinstance(value, str):
                return False
            try:
                date.fromisoformat(value)
                return True
            except ValueError:
                return False
        return type(value) is int and value >= 0

    if operator == "between":
        if not valid(item.get("minimum")) or not valid(item.get("maximum")):
            raise FilterRequestError("INVALID_FILTER", f"{field}.minimum and maximum are required for between.")
        if item["minimum"] > item["maximum"]:
            raise FilterRequestError("INVALID_FILTER", f"{field}.minimum cannot exceed maximum.")
    elif not valid(item.get("value")):
        raise FilterRequestError("INVALID_FILTER", f"{field}.value is required for {operator}.")


def validate_request(request: Any) -> tuple[dict[str, Any], dict[str, str], int, int]:
    body = _require_object(request, "request")
    if set(body) - {"filters", "sort", "limit", "offset"}:
        raise FilterRequestError("INVALID_REQUEST", "The request contains unsupported properties.")
    filters = _require_object(body.get("filters", {}), "filters")
    allowed_fields = TEXT_FIELDS | DATE_FIELDS | NUMBER_FIELDS | BOOLEAN_FIELDS | CONTROLLED_SCALAR_FIELDS | ARRAY_FIELDS | {"phase", "countries"}
    unknown = sorted(set(filters) - allowed_fields)
    if unknown:
        raise FilterRequestError("UNSUPPORTED_FILTER_FIELD", f"Unsupported filter field(s): {', '.join(unknown)}.")
    for field, condition in filters.items():
        if field in TEXT_FIELDS:
            _validate_text_filter(field, condition)
        elif field in DATE_FIELDS:
            _validate_comparison_filter(field, condition, is_date=True)
        elif field in NUMBER_FIELDS:
            _validate_comparison_filter(field, condition)
        elif field in BOOLEAN_FIELDS:
            _validate_boolean_filter(field, condition)
        elif field in CONTROLLED_SCALAR_FIELDS:
            _validate_text_filter(field, condition)
            if condition.get("operator", "is") not in {"is", "is_not"}:
                raise FilterRequestError("INVALID_OPERATOR", f"Only is and is_not are valid for {field}.")
            if not _casefold_member(condition["value"], CONTROLLED_VALUES[field]):
                raise FilterRequestError("INVALID_CONTROLLED_VALUE", f"Use a controlled {field} value advertised in the tool schema.")
            condition["value"] = _canonical_value(condition["value"], CONTROLLED_VALUES[field])
        elif field == "phase":
            _validate_set_filter(field, condition, numeric=True)
        elif field in ARRAY_FIELDS:
            _validate_set_filter(field, condition)
        elif field == "countries":
            if not isinstance(condition, list) or len(condition) > 20:
                raise FilterRequestError("INVALID_FILTER", "countries must contain at most 20 country groups.")
            for position, group_value in enumerate(condition):
                group = _require_object(group_value, f"countries[{position}]")
                allowed_country = {
                    "country_codes", "recruitment_statuses", "initial_submission_date",
                    "latest_submission_date", "decision_date", "latest_submission_result_date",
                    "number_of_sites", "planned_sample_size",
                }
                if not group or set(group) - allowed_country:
                    raise FilterRequestError("INVALID_FILTER", f"countries[{position}] is empty or contains unsupported fields.")
                for child, child_condition in group.items():
                    child_name = f"countries[{position}].{child}"
                    if child in {"country_codes", "recruitment_statuses"}:
                        _validate_set_filter(child, child_condition)
                        if child_condition.get("operator", "contains_any") == "contains_all" and len(child_condition["values"]) > 1:
                            raise FilterRequestError(
                                "INVALID_FILTER",
                                f"{child_name} cannot contain_all multiple scalar values; use separate country groups.",
                            )
                    elif child.endswith("_date"):
                        _validate_comparison_filter(child_name, child_condition, is_date=True)
                    else:
                        _validate_comparison_filter(child_name, child_condition)

    sort = _require_object(body.get("sort", {}), "sort")
    if set(sort) - {"field", "direction"}:
        raise FilterRequestError("INVALID_SORT", "sort contains unsupported properties.")
    sort_field = sort.get("field", "latest_country_submission_or_approval_date")
    sort_direction = sort.get("direction", "desc")
    if sort_field not in SORT_FIELDS or sort_direction not in {"asc", "desc"}:
        raise FilterRequestError("INVALID_SORT", "Use an advertised sort field and asc or desc direction.")
    limit = body.get("limit", 20)
    if type(limit) is not int or not 1 <= limit <= MAX_PAGE_SIZE:
        raise FilterRequestError("INVALID_LIMIT", f"limit must be between 1 and {MAX_PAGE_SIZE}.")
    offset = body.get("offset", 0)
    if type(offset) is not int or not 0 <= offset <= 1_000_000:
        raise FilterRequestError("INVALID_OFFSET", "offset must be an integer between 0 and 1000000.")
    return filters, {"field": sort_field, "direction": sort_direction}, limit, offset


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _text_sql(alias: str, field: str, condition: dict[str, Any], params: list[Any]) -> str:
    column = f"{alias}.{field}"
    operator = condition.get("operator", "contains")
    value = condition["value"]
    if operator in {"contains", "does_not_contain"}:
        params.append(f"%{_escape_like(value)}%")
        match = f"{column} ILIKE %s ESCAPE E'\\\\'"
    else:
        params.append(value)
        match = f"lower({column}) = lower(%s)"
    if operator in {"does_not_contain", "is_not"}:
        return f"({column} IS NOT NULL AND NOT ({match}))"
    return f"({column} IS NOT NULL AND {match})"


def _set_sql(alias: str, field: str, condition: dict[str, Any], params: list[Any], *, numeric: bool = False) -> str:
    column = f"{alias}.{field}"
    operator = condition.get("operator", "contains_any")
    values = list(dict.fromkeys(condition["values"]))
    if field != "available_extracted_document_names":
        params.append(values)
        cast = "integer[]" if numeric else "text[]"
        if operator == "contains_all":
            return f"({column} @> %s::{cast})"
        overlap = f"({column} && %s::{cast})"
        if operator == "contains_none":
            return f"(cardinality({column}) > 0 AND NOT {overlap})"
        return overlap

    matches: list[str] = []
    for value in values:
        params.append(f"%{_escape_like(value)}%")
        matches.append(
            f"EXISTS (SELECT 1 FROM unnest({column}) AS member(value) "
            "WHERE member.value ILIKE %s ESCAPE E'\\\\')"
        )
    joiner = " AND " if operator == "contains_all" else " OR "
    combined = f"({joiner.join(matches)})"
    if operator == "contains_none":
        return f"(cardinality({column}) > 0 AND NOT {combined})"
    return combined


def _scalar_set_sql(column: str, condition: dict[str, Any], params: list[Any]) -> str:
    operator = condition.get("operator", "contains_any")
    values = list(dict.fromkeys(condition["values"]))
    params.append(values)
    combined = f"({column} = ANY(%s::text[]))"
    if operator == "contains_none":
        return f"({column} IS NOT NULL AND NOT {combined})"
    return f"({column} IS NOT NULL AND {combined})"


def _boolean_sql(alias: str, field: str, condition: dict[str, Any]) -> str:
    column = f"{alias}.{field}"
    operator = condition.get("operator", "is")
    value = condition["value"]
    if value == "unknown":
        return f"{column} IS {'NOT ' if operator == 'is_not' else ''}NULL"
    expected = "TRUE" if value else "FALSE"
    if operator == "is_not":
        return f"({column} IS NOT NULL AND {column} IS DISTINCT FROM {expected})"
    return f"{column} IS {expected}"


def _comparison_sql(column: str, condition: dict[str, Any], params: list[Any]) -> str:
    operator = condition.get("operator", "is")
    if operator == "between":
        params.extend([condition["minimum"], condition["maximum"]])
        return f"({column} IS NOT NULL AND {column} BETWEEN %s AND %s)"
    sql_operator = {
        "is": "=", "is_not": "<>", "greater_than": ">", "greater_than_or_equal": ">=",
        "less_than": "<", "less_than_or_equal": "<=",
    }[operator]
    params.append(condition["value"])
    return f"({column} IS NOT NULL AND {column} {sql_operator} %s)"


def build_where(filters: dict[str, Any]) -> tuple[str, list[Any]]:
    conditions = ["p.approval_status = 'approved'"]
    params: list[Any] = []
    for field, condition in filters.items():
        if field in TEXT_FIELDS or field in CONTROLLED_SCALAR_FIELDS:
            conditions.append(_text_sql("p", field, condition, params))
        elif field in DATE_FIELDS or field in NUMBER_FIELDS:
            conditions.append(_comparison_sql(f"p.{field}", condition, params))
        elif field in BOOLEAN_FIELDS:
            conditions.append(_boolean_sql("p", field, condition))
        elif field == "phase":
            conditions.append(_set_sql("p", field, condition, params, numeric=True))
        elif field in ARRAY_FIELDS:
            conditions.append(_set_sql("p", field, condition, params))
        elif field == "countries":
            for group in condition:
                child_sql = ["c.profile_id = p.id"]
                for child, child_condition in group.items():
                    if child in {"country_codes", "recruitment_statuses"}:
                        column = "c.country_code" if child == "country_codes" else "c.recruitment_status"
                        child_sql.append(_scalar_set_sql(column, child_condition, params))
                    else:
                        child_sql.append(_comparison_sql(f"c.{child}", child_condition, params))
                conditions.append(
                    f"EXISTS (SELECT 1 FROM mcp_serving.profile_countries_v1 c "
                    f"WHERE {' AND '.join(child_sql)})"
                )
    return " AND ".join(conditions), params


def filter_approved_trials(connection: psycopg.Connection[Any], request: Any) -> dict[str, Any]:
    filters, sort, limit, offset = validate_request(request)
    where_sql, params = build_where(filters)
    direction = "ASC" if sort["direction"] == "asc" else "DESC"
    order_sql = f"p.{sort['field']} {direction} NULLS LAST, p.eu_number ASC"

    approved_profiles = connection.execute(
        "SELECT COUNT(*) FROM mcp_serving.profile_filter_v1 WHERE approval_status = 'approved'"
    ).fetchone()[0]
    total_matches = connection.execute(
        f"SELECT COUNT(*) FROM mcp_serving.profile_filter_v1 p WHERE {where_sql}", params
    ).fetchone()[0]
    rows = connection.execute(
        f"""
        SELECT p.eu_number, p.trial_title, p.sponsor_name
        FROM mcp_serving.profile_filter_v1 p
        WHERE {where_sql}
        ORDER BY {order_sql}
        LIMIT %s OFFSET %s
        """,
        [*params, limit, offset],
    ).fetchall()
    data = [
        {
            "eu_number": row[0],
            "trial_title": row[1],
            "sponsor_name": row[2],
        }
        for row in rows
    ]
    return {
        "data": data,
        "counts": {
            "total_profiles": int(approved_profiles),
            "total_matches": int(total_matches),
            "returned": len(data),
        },
    }
