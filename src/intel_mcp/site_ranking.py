"""Deterministic Site.agent aggregation over approved Trial Profiles.

Therapeutic area eligibility is applied before profiles reach this module. The
planner's keywords only order and explain the eligible sites and investigators;
they never remove a trial, site, or investigator from the cohort.
"""
from __future__ import annotations

from collections import Counter
from datetime import date
import hashlib
import re
import unicodedata
from typing import Any, Iterable

VERSION = "therapeutic-area-keywords-v1"
PREVIEW_LIMIT = 10
EU_NUMBER = re.compile(r"^\d{4}-\d{6}-\d{2}-\d{2}$")

# Compact, approved Trial Profile sections used for literal keyword evidence.
# Candidate profiles are never sent to a model.
KEYWORD_FIELDS = (
    "trial_title",
    "diseases",
    "biomarkers",
    "disease_stages_or_severity",
    "interventional_products",
    "non_interventional_products",
    "mechanisms_of_action",
    "molecular_targets",
    "population_characteristics",
    "target_population_summary",
    "treatment_settings",
    "primary_objectives",
    "secondary_objectives",
    "endpoints",
)


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


def _trial_year(profile: dict, trial_id: str) -> int | None:
    years: list[int] = []
    for country in (profile.get("ctis_lifecycle") or {}).get("countries", []):
        for update in country.get("updates", []):
            value = str(update.get("date") or "")[:4]
            if value.isdigit():
                year = int(value)
                if 2000 <= year <= date.today().year:
                    years.append(year)
    if years:
        return max(years)
    prefix = trial_id[:4]
    return int(prefix) if prefix.isdigit() else None


def _keyword_hits(profile: dict, keywords: list[str]) -> list[str]:
    variables = profile.get("classification_variables") or {}
    text = " ".join(
        text
        for field in KEYWORD_FIELDS
        for text in _strings(variables.get(field))
    )
    return [keyword for keyword in keywords if phrase_in(keyword, text)]


def _trial(profile: dict, trial_id: str, keywords: list[str]) -> dict:
    variables = profile.get("classification_variables") or {}
    sponsor = variables.get("sponsor") or {}
    return {
        "id": trial_id,
        "title": str(variables.get("trial_title") or trial_id),
        "keywords": _keyword_hits(profile, keywords),
        "sponsor": str(sponsor.get("name") or "") if isinstance(sponsor, dict) else str(sponsor),
        "year": _trial_year(profile, trial_id),
    }


def _metrics(trials: dict[str, dict]) -> dict:
    matched = [trial for trial in trials.values() if trial["keywords"]]
    keyword_counts = Counter(keyword for trial in trials.values() for keyword in trial["keywords"])
    sponsor_counts = Counter(trial["sponsor"] for trial in trials.values() if trial["sponsor"])
    years = [trial["year"] for trial in trials.values() if trial["year"] is not None]
    evidence = sorted(
        trials.values(),
        key=lambda trial: (-bool(trial["keywords"]), -(trial["year"] or 0), trial["id"]),
    )[:8]
    return {
        "therapeuticAreaTrials": len(trials),
        "keywordMatchedTrials": len(matched),
        "matchedKeywords": [
            {"keyword": keyword, "trials": count}
            for keyword, count in sorted(keyword_counts.items(), key=lambda pair: (-pair[1], normalized(pair[0])))
        ],
        "sponsors": [
            {"name": name, "trials": count}
            for name, count in sorted(sponsor_counts.items(), key=lambda pair: (-pair[1], normalized(pair[0])))[:6]
        ],
        "latestTrialYear": max(years) if years else None,
        "evidence": [
            {"id": trial["id"], "title": trial["title"], "matchedKeywords": trial["keywords"]}
            for trial in evidence
        ],
    }


def _rank_key(record: dict) -> tuple:
    metrics = record["metrics"]
    return (
        -metrics["keywordMatchedTrials"],
        -len(metrics["matchedKeywords"]),
        -metrics["therapeuticAreaTrials"],
        -(metrics["latestTrialYear"] or 0),
        normalized(record["name"]),
        record["id"],
    )


class ProfileRanker:
    """Incrementally aggregate profiles so the full cohort is never held in memory."""

    def __init__(self, criteria: dict):
        self.keywords = list(criteria.get("keywords") or [])
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
            trial = _trial(profile, trial_id, self.keywords)
            for raw_site in variables.get("sites") or []:
                if not isinstance(raw_site, dict):
                    continue
                name = str(raw_site.get("name") or raw_site.get("site_name") or "").strip()
                country = str(raw_site.get("country_code") or "").strip().upper()
                if not name or not re.fullmatch(r"[A-Z]{2}", country):
                    continue
                site_id = key(country, name)
                site = self.sites.setdefault(site_id, {
                    "id": site_id, "name": name, "country": country,
                    "trials": {}, "contacts": Counter(),
                })
                site["trials"][trial_id] = trial
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
                    # A stable email is the strongest available cross-site identity.
                    # Without one, keep the identity scoped to the recorded site.
                    person_id = key("email", email) if email else key("site", site_id, contact_name, department)
                    person = self.people.setdefault(person_id, {
                        "id": person_id, "name": contact_name, "department": department,
                        "trials": {}, "sites": {}, "emails": Counter(), "confirmed": False,
                    })
                    person["trials"][trial_id] = trial
                    person["sites"][site_id] = site
                    person["confirmed"] = person["confirmed"] or is_pi is True
                    if email:
                        person["emails"][email] += 1

    def result(self, limit: int = PREVIEW_LIMIT) -> dict:
        site_rows = []
        for site in self.sites.values():
            contact = None
            if site["contacts"]:
                chosen = sorted(site["contacts"], key=lambda value: (value[0], -site["contacts"][value], normalized(value[1]), value[2]))[0]
                contact = {"name": chosen[1], "email": chosen[2], "role": chosen[3]}
            site_rows.append({
                "id": site["id"], "name": site["name"], "country": site["country"],
                "contact": contact, "metrics": _metrics(site["trials"]),
            })
        site_rows.sort(key=_rank_key)
        for rank, record in enumerate(site_rows, 1):
            record["rank"] = rank

        pi_rows = []
        for person in self.people.values():
            affiliations = sorted(
                ({"id": site["id"], "name": site["name"], "country": site["country"],
                  "trials": len(set(site["trials"]) & set(person["trials"]))} for site in person["sites"].values()),
                key=lambda site: (-site["trials"], normalized(site["name"]), site["country"]),
            )
            email = sorted(person["emails"], key=lambda value: (-person["emails"][value], value))[0] if person["emails"] else None
            pi_rows.append({
                "id": person["id"], "name": person["name"], "department": person["department"],
                "email": email, "role": "confirmed_pi" if person["confirmed"] else "role_unconfirmed",
                "sites": affiliations, "metrics": _metrics(person["trials"]),
            })
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
