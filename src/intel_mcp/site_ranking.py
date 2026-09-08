"""Deterministic Site Agent aggregation over approved Trial Profiles.

Therapeutic area eligibility is applied before profiles reach this module. The
planner's disease terms only order the eligible sites and investigators;
they never remove a trial, site, or investigator from the cohort.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from calendar import monthrange
from collections import Counter
from collections.abc import Iterable
from datetime import UTC, date, datetime
from typing import Any

VERSION = "therapeutic-area-experience-v4"
PREVIEW_LIMIT = 10
EU_NUMBER = re.compile(r"^\d{4}-\d{6}-\d{2}-\d{2}$")
EXPERIENCE_YEARS = 5
ACTIVITY_MONTHS = 6
METRIC_FIELDS = (
    "therapeuticAreaTrials", "diseaseMatchedTrials", "phaseMatchedTrials",
    "modalityMatchedTrials", "paediatricMatchedTrials", "recentActivityTrials",
)

# Approved Trial Profile section used for literal disease evidence.
# Candidate profiles are never sent to a model.
DISEASE_FIELDS = ("diseases",)


def normalized(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return " ".join(re.findall(r"[^\W_]+", text, re.UNICODE))


def phrase_in(term: str, text: str) -> bool:
    needle = normalized(term)
    return bool(needle) and f" {needle} " in f" {normalized(text)} "


def key(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(normalized(part) for part in parts).encode()).hexdigest()[:24]


def _strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _strings(child)


def _pi_role(contact: dict) -> bool | None:
    flag = contact.get("principal_investigator")
    if isinstance(flag, bool):
        return flag
    role = normalized(contact.get("function") or contact.get("role"))
    if role in {"pi", "principal investigator", "lead principal investigator"}:
        return True
    return None


def _contact_name(contact: dict) -> str:
    first = str(contact.get("first_name") or "").strip()
    last = str(contact.get("last_name") or "").strip()
    return " ".join(part for part in (first, last) if part)


def _email(contact: dict) -> str:
    value = str(contact.get("email") or "").strip().casefold()
    return value if "@" in value and len(value) <= 320 else ""


def _date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value or "")[:10])
    except ValueError:
        return None


def _positive_authorization(value: Any) -> bool:
    outcome = "".join(character for character in str(value or "").casefold() if character.isalnum())
    return outcome in {
        "authorised", "authorisedwithconditions", "authorized",
        "authorizedwithconditions", "approved", "approvedwithconditions",
    }


def _authorization_dates(profile: dict) -> dict[str, date]:
    dates: dict[str, date] = {}
    for country in (profile.get("ctis_lifecycle") or {}).get("countries", []):
        code = str(country.get("country_code") or "").strip().upper()
        if not re.fullmatch(r"[A-Z]{2}", code):
            continue
        candidates = [
            parsed
            for update in country.get("updates", [])
            if "decision" in normalized(update.get("label"))
            and _positive_authorization(update.get("outcome"))
            and (parsed := _date(update.get("date"))) is not None
        ]
        if candidates:
            dates[code] = min(candidates)
    return dates


def _shift_months(value: date, months: int) -> date:
    total = value.year * 12 + value.month - 1 - months
    year, month_index = divmod(total, 12)
    month = month_index + 1
    return date(year, month, min(value.day, monthrange(year, month)[1]))


def _trial_year(profile: dict, trial_id: str) -> int | None:
    years: list[int] = []
    for country in (profile.get("ctis_lifecycle") or {}).get("countries", []):
        for update in country.get("updates", []):
            value = str(update.get("date") or "")[:4]
            if value.isdigit():
                year = int(value)
                if 2000 <= year <= datetime.now(UTC).year:
                    years.append(year)
    if years:
        return max(years)
    prefix = trial_id[:4]
    return int(prefix) if prefix.isdigit() else None


def _disease_hits(profile: dict, disease_terms: list[str]) -> list[str]:
    variables = profile.get("classification_variables") or {}
    text = " ".join(
        text
        for field in DISEASE_FIELDS
        for text in _strings(variables.get(field))
    )
    return [term for term in disease_terms if phrase_in(term, text)]


def _trial(profile: dict, trial_id: str, disease_terms: list[str]) -> dict:
    variables = profile.get("classification_variables") or {}
    filtering = profile.get("filtering_variables") or {}
    sponsor = variables.get("sponsor") or {}
    phases = sorted({value for value in filtering.get("phase") or [] if isinstance(value, int) and 1 <= value <= 4})
    authorization_dates = _authorization_dates(profile)
    return {
        "id": trial_id,
        "title": str(variables.get("trial_title") or trial_id),
        "disease_terms": _disease_hits(profile, disease_terms),
        "sponsor": str(sponsor.get("name") or "") if isinstance(sponsor, dict) else str(sponsor),
        "phases": phases,
        "modality": str(filtering.get("modality") or "").strip(),
        "paediatric": filtering.get("paediatric_trial") is True,
        "authorization_dates": authorization_dates,
        "authorization_date": min(authorization_dates.values(), default=None),
        "year": _trial_year(profile, trial_id),
    }


def _metrics(trials: dict[str, dict], criteria: dict, *, today: date) -> dict:
    experience_start = _shift_months(today, EXPERIENCE_YEARS * 12)
    activity_start = _shift_months(today, ACTIVITY_MONTHS)
    recent = [
        trial for trial in trials.values()
        if trial["authorization_date"] is not None and experience_start <= trial["authorization_date"] <= today
    ]
    matched = [trial for trial in recent if trial["disease_terms"]]
    disease_counts = Counter(term for trial in recent for term in trial["disease_terms"])
    target_phases = set(criteria.get("phases") or [])
    target_modalities = {normalized(value) for value in criteria.get("modalities") or []}
    phase_matched = [trial for trial in recent if target_phases.intersection(trial["phases"])]
    modality_matched = [trial for trial in recent if normalized(trial["modality"]) in target_modalities]
    paediatric_relevant = criteria.get("paediatric_relevant") is True
    paediatric_matched = [trial for trial in recent if trial["paediatric"]] if paediatric_relevant else []
    recent_activity = [
        trial for trial in trials.values()
        if trial["authorization_date"] is not None and activity_start <= trial["authorization_date"] <= today
    ]
    sponsor_counts = Counter(trial["sponsor"] for trial in recent if trial["sponsor"])
    years = [trial["year"] for trial in trials.values() if trial["year"] is not None]
    evidence = sorted(
        trials.values(),
        key=lambda trial: (-bool(trial["disease_terms"]), -(trial["year"] or 0), trial["id"]),
    )[:8]
    return {
        "therapeuticAreaTrials": len(recent),
        "diseaseMatchedTrials": len(matched),
        "phaseMatchedTrials": len(phase_matched),
        "modalityMatchedTrials": len(modality_matched),
        "paediatricMatchedTrials": len(paediatric_matched) if paediatric_relevant else None,
        "recentActivityTrials": len(recent_activity),
        "matchedDiseaseTerms": [
            {"term": term, "trials": count}
            for term, count in sorted(disease_counts.items(), key=lambda pair: (-pair[1], normalized(pair[0])))
        ],
        "sponsors": [
            {"name": name, "trials": count}
            for name, count in sorted(sponsor_counts.items(), key=lambda pair: (-pair[1], normalized(pair[0])))[:3]
        ],
        "latestTrialYear": max(years) if years else None,
        "evidence": [
            {"id": trial["id"], "title": trial["title"]}
            for trial in evidence
        ],
    }


def _band(value: int | None, values: list[int]) -> str | None:
    if value is None:
        return None
    if value == 0:
        return "bottom_25"
    lower = sum(candidate < value for candidate in values)
    equal = sum(candidate == value for candidate in values)
    percentile = 100 * (lower + 0.5 * equal) / max(1, len(values))
    if percentile >= 90:
        return "leading_10"
    if percentile >= 75:
        return "upper_25"
    if percentile < 25:
        return "bottom_25"
    return "typical"


def _apply_bands(rows: list[dict]) -> None:
    for field in METRIC_FIELDS:
        values = [row["metrics"][field] for row in rows if row["metrics"][field] is not None]
        for row in rows:
            row["metrics"].setdefault("bands", {})[field] = _band(row["metrics"][field], values)


def _rank_key(record: dict) -> tuple:
    metrics = record["metrics"]
    return (
        -metrics["diseaseMatchedTrials"],
        -metrics["phaseMatchedTrials"],
        -metrics["modalityMatchedTrials"],
        -(metrics["paediatricMatchedTrials"] or 0),
        -metrics["therapeuticAreaTrials"],
        -(metrics["latestTrialYear"] or 0),
        normalized(record["name"]),
        record["id"],
    )


class ProfileRanker:
    """Incrementally aggregate profiles so the full cohort is never held in memory."""

    def __init__(self, criteria: dict):
        self.criteria = criteria
        self.disease_terms = list(criteria.get("disease_terms") or criteria.get("keywords") or [])
        self.countries = set(criteria.get("countries") or [])
        self.sites: dict[str, dict] = {}
        self.people: dict[str, dict] = {}
        self.seen_trials: set[str] = set()

    def add(self, items: Iterable[dict]) -> None:
        for item in items:
            trial_id = str(item.get("eu_number") or "")
            if not EU_NUMBER.fullmatch(trial_id) or trial_id in self.seen_trials:
                continue
            self.seen_trials.add(trial_id)
            profile = item.get("profile") or {}
            variables = profile.get("classification_variables") or {}
            trial = _trial(profile, trial_id, self.disease_terms)
            for raw_site in variables.get("sites") or []:
                if not isinstance(raw_site, dict):
                    continue
                name = str(raw_site.get("name") or raw_site.get("site_name") or "").strip()
                country = str(raw_site.get("country_code") or "").strip().upper()
                if not name or not re.fullmatch(r"[A-Z]{2}", country) or (self.countries and country not in self.countries):
                    continue
                site_id = key(country, name)
                site = self.sites.setdefault(site_id, {
                    "id": site_id, "name": name, "country": country,
                    "trials": {}, "contacts": Counter(),
                })
                site_trial = {
                    **trial,
                    "authorization_date": trial["authorization_dates"].get(country) or trial["authorization_date"],
                }
                site["trials"][trial_id] = site_trial
                for contact in raw_site.get("site_contacts") or []:
                    if not isinstance(contact, dict):
                        continue
                    email = _email(contact)
                    contact_name = _contact_name(contact)
                    department = str(contact.get("department_or_division") or contact.get("department") or "").strip()
                    is_pi = _pi_role(contact)
                    if email:
                        role = "Principal investigator" if is_pi else str(contact.get("function") or contact.get("role") or "Site contact").strip()
                        site["contacts"][(not is_pi, contact_name, email, role)] += 1
                    # Named contacts with an unspecified role remain useful PI
                    # candidates, but are never presented as confirmed PIs.
                    if is_pi is False or not contact_name:
                        continue
                    # Site Agent presents one row per normalized recorded name.
                    # Email remains the preferred contact route, but is not used as
                    # the display identity because CTIS can record the same person
                    # with different addresses across institutions and years.
                    person_id = key("person", contact_name)
                    person = self.people.setdefault(person_id, {
                        "id": person_id, "names": Counter(), "trials": {}, "sites": {},
                        "site_trials": {}, "departments": {}, "emails": Counter(),
                        "email_years": {}, "confirmed": False,
                    })
                    person["names"][contact_name] += 1
                    existing_trial = person["trials"].get(trial_id)
                    if (
                        existing_trial is None
                        or (site_trial["authorization_date"] or date.min)
                        > (existing_trial["authorization_date"] or date.min)
                    ):
                        person["trials"][trial_id] = site_trial
                    person["sites"][site_id] = site
                    person["site_trials"].setdefault(site_id, {})[trial_id] = site_trial
                    person["confirmed"] = person["confirmed"] or is_pi is True
                    if department:
                        candidate = (trial["year"] or 0, normalized(department), department)
                        current = person["departments"].get(site_id)
                        if current is None or candidate[:2] > current[:2]:
                            person["departments"][site_id] = candidate
                    if email:
                        person["emails"][email] += 1
                        person["email_years"][email] = max(person["email_years"].get(email, 0), trial["year"] or 0)

    def result(self, limit: int = PREVIEW_LIMIT) -> dict:
        today = datetime.now(UTC).date()
        site_rows = []
        for site in self.sites.values():
            contact = None
            if site["contacts"]:
                chosen = min(site["contacts"], key=lambda value: (value[0], -site["contacts"][value], normalized(value[1]), value[2]))
                contact = {"name": chosen[1], "email": chosen[2], "role": chosen[3]}
            site_rows.append({
                "id": site["id"], "name": site["name"], "country": site["country"],
                "contact": contact, "metrics": _metrics(site["trials"], self.criteria, today=today),
            })
        _apply_bands(site_rows)
        site_rows.sort(key=_rank_key)
        for rank, record in enumerate(site_rows, 1):
            record["rank"] = rank

        pi_rows = []
        for person in self.people.values():
            affiliations = sorted(
                ({"id": site["id"], "name": site["name"], "country": site["country"],
                  "trials": len(person["site_trials"][site["id"]]),
                  "latest": max((trial["year"] or 0) for trial in person["site_trials"][site["id"]].values())}
                 for site in person["sites"].values()),
                key=lambda site: (-site["latest"], -site["trials"], normalized(site["name"]), site["country"]),
            )
            latest_affiliation = affiliations[0]
            department = person["departments"].get(latest_affiliation["id"], (0, "", ""))[2]
            public_affiliation = {key: value for key, value in latest_affiliation.items() if key != "latest"}
            email = min(
                person["emails"],
                key=lambda value: (-person["email_years"][value], -person["emails"][value], value),
            ) if person["emails"] else None
            name = min(person["names"], key=lambda value: (-person["names"][value], normalized(value), value))
            pi_rows.append({
                "id": person["id"], "name": name, "department": department,
                "email": email, "role": "confirmed_pi" if person["confirmed"] else "role_unconfirmed",
                "sites": [public_affiliation], "metrics": _metrics(person["trials"], self.criteria, today=today),
            })
        _apply_bands(pi_rows)
        pi_rows.sort(key=_rank_key)
        for rank, record in enumerate(pi_rows, 1):
            record["rank"] = rank

        return {
            "sites": site_rows[:limit],
            "pis": pi_rows[:limit],
            "scoringVersion": VERSION,
            "counts": {
                "sites": len(site_rows), "pis": len(pi_rows),
                "confirmedPIs": sum(row["role"] == "confirmed_pi" for row in pi_rows),
                "unconfirmedContacts": sum(row["role"] == "role_unconfirmed" for row in pi_rows),
                "previewSites": min(limit, len(site_rows)), "previewPIs": min(limit, len(pi_rows)),
            },
        }


def rank_profiles(items: list[dict], criteria: dict, *, preview_limit: int = PREVIEW_LIMIT) -> dict:
    ranker = ProfileRanker(criteria)
    ranker.add(items)
    return ranker.result(preview_limit)
