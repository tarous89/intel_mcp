from datetime import date
import re
EU27 = frozenset("AT BE BG HR CY CZ DK EE FI FR DE GR HU IE IT LV LT LU MT NL PL PT RO SK SI ES SE".split())
def _iso(value):
    try:
        return date.fromisoformat(value).isoformat() if isinstance(value, str) else None
    except ValueError:
        return None


def display_title(trial_id, title):
    title = str(title or "").strip()
    return bool(title and title != trial_id and not re.fullmatch(r"[\d\s-]+", title))


def trial_row(trial_id, profile, groups):
    classification = profile.get("classification_variables") or {}
    filtering = profile.get("filtering_variables") or {}
    lifecycle = profile.get("ctis_lifecycle") or {}
    starts = [_iso(event.get("date")) for event in lifecycle.get("overall_updates") or []
              if isinstance(event, dict) and event.get("label") == "Trial started"]
    country_statuses = {}
    for country in lifecycle.get("countries") or []:
        if not isinstance(country, dict):
            continue
        code = country.get("country_code")
        if not isinstance(code, str) or not re.fullmatch(r"[A-Z]{2}", code):
            continue
        starts.extend(_iso(event.get("date")) for event in country.get("updates") or []
                      if isinstance(event, dict) and event.get("label") == "Trial started")
        updates = [(day, str(event["outcome"]).strip())
                   for event in country.get("updates") or [] if isinstance(event, dict)
                   and event.get("label") in {"Country regulatory status", "CTIS transition status", "Trial status"}
                   and (day := _iso(event.get("date"))) and isinstance(event.get("outcome"), str)
                   and event["outcome"].strip()]
        if updates:
            latest = max(day for day, _ in updates)
            values = {status for day, status in updates if day == latest}
            country_statuses[code] = next(iter(values)) if len(values) == 1 else None
    known_status = {value for value in country_statuses.values() if value}
    status = ("Mixed country status" if len(known_status) > 1 else next(iter(known_status))) if known_status else None
    if any(value is None for value in country_statuses.values()) or any(
            isinstance(country, dict) and re.fullmatch(r"[A-Z]{2}", str(country.get("country_code") or ""))
            and country["country_code"] not in country_statuses
            for country in lifecycle.get("countries") or []):
        status = None
    countries = sorted({code for code in filtering.get("country_codes") or []
                        if isinstance(code, str) and re.fullmatch(r"[A-Z]{2}", code)} |
                       {str(country.get("country_code")) for country in classification.get("countries") or []
                        if isinstance(country, dict) and isinstance(country.get("country_code"), str)
                        and re.fullmatch(r"[A-Z]{2}", country["country_code"])} |
                       {str(site.get("country_code")) for site in classification.get("sites") or []
                        if isinstance(site, dict) and isinstance(site.get("country_code"), str)
                        and re.fullmatch(r"[A-Z]{2}", site["country_code"])})
    enrolled = (profile.get("results") or {}).get("participant_flow") or {}
    return {"id": trial_id, "title": classification.get("trial_title") or None,
            "displayEligible": display_title(trial_id, classification.get("trial_title")),
            "operationalLearnings": list(dict.fromkeys(x.strip() for x in (profile.get("results") or {}).get("trial_operational_findings") or [] if isinstance(x, str) and x.strip())),
            "phase": filtering.get("phase"), "actualStartDate": min(filter(None, starts), default=None),
            "status": status, "countryStatuses": country_statuses,
            "countries": countries, "euCountryCount": len(EU27.intersection(countries)),
            "listedSiteCount": len(classification.get("sites") or []),
            "plannedParticipants": filtering.get("planned_sample_size"),
            "enrolledParticipants": enrolled.get("enrolled"),
            "documents": [{"label": name.replace("_", " ").capitalize(),
                           "url": "https://euclinicaltrials.eu/ctis-public/view/" + trial_id,
                           "direct": False}
                          for name, available in (filtering.get("available_extracted_documents") or {}).items()
                          if available is True or isinstance(available, list) and available], "subgroups": sorted(set(groups) - {"base"})}


