from __future__ import annotations

import re
from copy import deepcopy
from typing import Any


_KEY_RE = re.compile(r"[^a-z0-9]+")
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_PLACEHOLDER_EMAILS = {
    "na@na.com",
    "nn@nn.com",
    "test@test.com",
    "invalid@invalid.invalid",
    "unknown@unknown.com",
}


def _key(value: Any) -> str:
    return _KEY_RE.sub("", str(value or "").casefold())


def _text(value: Any) -> str | None:
    if isinstance(value, (str, int, float)) and not isinstance(value, bool):
        result = str(value).strip()
        return result or None
    return None


def _email(value: Any) -> str | None:
    result = _text(value)
    if not result:
        return None
    result = result.strip()
    if not _EMAIL_RE.fullmatch(result):
        return None
    if result.casefold() in _PLACEHOLDER_EMAILS:
        return None
    domain = result.rsplit("@", 1)[-1].casefold()
    if domain.endswith((".invalid", ".example", ".test", ".localhost")):
        return None
    return result


def eligibility_criteria(ctis_json: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Return principal CTIS criteria as two exact ordered string arrays."""
    authorized = ctis_json.get("authorizedApplication")
    part_i = authorized.get("authorizedPartI") if isinstance(authorized, dict) else None
    details = part_i.get("trialDetails") if isinstance(part_i, dict) else None
    information = details.get("trialInformation") if isinstance(details, dict) else None
    eligibility = (
        information.get("eligibilityCriteria")
        if isinstance(information, dict)
        else None
    )
    if not isinstance(eligibility, dict):
        return [], []

    def extract(array_name: str, text_field: str) -> list[str]:
        values = eligibility.get(array_name)
        if not isinstance(values, list):
            return []
        result: list[str] = []
        for item in values:
            value = item.get(text_field) if isinstance(item, dict) else item
            if isinstance(value, str) and value.strip():
                result.append(value)
        return result

    return (
        extract("principalInclusionCriteria", "principalInclusionCriteria"),
        extract("principalExclusionCriteria", "principalExclusionCriteria"),
    )


def reconcile_derived_fields(profile: dict[str, Any]) -> dict[str, Any]:
    """Recompute deterministic projections after the CTIS lifecycle refresh."""
    result = deepcopy(profile)

    def sanitize_emails(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if _key(key) == "email" and isinstance(child, str):
                    value[key] = _email(child)
                    continue
                sanitize_emails(child)
        elif isinstance(value, list):
            for child in value:
                sanitize_emails(child)

    sanitize_emails(result)
    filtering = result["filtering_variables"]
    classification = result["classification_variables"]

    entity_country_codes: list[str] = []
    seen_codes: set[str] = set()
    for country in classification.get("countries") or []:
        if not isinstance(country, dict):
            continue
        for retired_field in (
            "initial_submission_date",
            "latest_submission_date",
            "decision_date",
            "decision_outcome",
            "latest_submission_result_date",
            "latest_submission_result",
            "recruitment_status",
        ):
            country.pop(retired_field, None)
        for field in ("number_of_sites", "planned_sample_size"):
            country.setdefault(field, None)
        code = _text(country.get("country_code"))
        if code and code not in seen_codes:
            seen_codes.add(code)
            entity_country_codes.append(code)

    country_codes = entity_country_codes
    if not country_codes:
        country_codes = []
        for value in filtering.get("country_codes") or []:
            code = _text(value)
            if code and code not in seen_codes:
                seen_codes.add(code)
                country_codes.append(code)

    filtering["country_codes"] = country_codes
    filtering["number_of_countries"] = len(country_codes)
    sites = classification.get("sites") or []
    filtering["number_of_sites"] = len(sites)
    site_counts: dict[str, int] = {}
    for site in sites:
        if not isinstance(site, dict):
            continue
        code = _text(site.get("country_code"))
        if code:
            site_counts[code] = site_counts.get(code, 0) + 1
    for country in classification.get("countries") or []:
        if not isinstance(country, dict):
            continue
        code = _text(country.get("country_code"))
        if code in site_counts or country.get("number_of_sites") is not None:
            country["number_of_sites"] = site_counts.get(code, 0)
    return result
