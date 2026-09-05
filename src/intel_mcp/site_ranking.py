"""PI-first, contact-redacted aggregation of approved Trial Profile evidence.

No warehouse access or model calls live here. Scores measure observed relevance,
not performance, patient availability, exclusivity, or site-level recruitment.
"""
from __future__ import annotations

from collections import Counter
from datetime import date
import hashlib
import re
import unicodedata
from typing import Any

VERSION = "pi-site-relevance-v1"
EU_NUMBER = re.compile(r"^\d{4}-\d{6}-\d{2}-\d{2}$")


def normalized(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return " ".join(re.findall(r"[^\W_]+", text, re.UNICODE))


def phrase_in(term: str, text: str) -> bool:
    needle = normalized(term)
    return bool(needle) and f" {needle} " in f" {normalized(text)} "


def key(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(normalized(p) for p in parts).encode()).hexdigest()[:24]


def pi_role(contact: dict) -> bool | None:
    flag = contact.get("principal_investigator")
    if isinstance(flag, bool):
        return flag
    if normalized(contact.get("function")) in {"pi", "principal investigator", "lead principal investigator"}:
        return True
    return None


def country_activity(profile: dict, country: str, today: date) -> tuple[bool | None, int | None]:
    """Only actual country recruitment/operation events; authorisation is not recruitment."""
    entries = [entry for item in profile.get("ctis_lifecycle", {}).get("countries", [])
               if item.get("country_code") == country for entry in item.get("updates", [])]
    events = []
    starts = []
    for entry in entries:
        try:
            day = date.fromisoformat(str(entry.get("date", ""))[:10])
        except ValueError:
            continue
        if day > today:
            continue
        label = normalized(entry.get("label"))
        if "estimated" in label or "planned" in label:
            continue
        if label in {"start of trial", "trial started", "start of clinical trial"}:
            starts.append(day)
        if label in {"recruitment started", "start of recruitment", "recruitment restarted", "restart of recruitment"}:
            events.append((day, True))
        elif label in {"recruitment ended", "end of recruitment", "trial ended", "end of trial", "early termination", "trial temporarily halted", "temporary halt"}:
            events.append((day, False))
    # A stopping event wins a same-day ambiguity. Never treat an authorisation as active.
    events.sort(key=lambda item: (item[0], not item[1]))
    return (events[-1][1] if events else None, min(starts).year if starts else None)


def relevance(profile: dict, criteria: dict) -> tuple[bool, bool, bool]:
    variables = profile.get("classification_variables", {})
    filters = profile.get("filtering_variables", {})
    text = " ".join([str(variables.get("trial_title") or ""), *map(str, variables.get("diseases", []))])
    relevant = any(phrase_in(term, text) for term in criteria.get("indication_terms", []))
    phase = bool(set(filters.get("phase", [])) & set(criteria.get("phases", [])))
    modality = bool(criteria.get("modality")) and normalized(filters.get("modality")) == normalized(criteria["modality"])
    return relevant, phase, modality


def metrics(trials: dict[str, dict], criteria: dict) -> dict:
    relevant = [t for t in trials.values() if t["relevant"]]
    phase = sum(t["phase"] for t in relevant)
    modality = sum(t["modality"] for t in relevant)
    weights = [(60, min(len(relevant) / 5, 1), "Indication experience", len(relevant))]
    if criteria.get("phases"):
        weights.append((20, min(phase / 3, 1), "Same-phase indication experience", phase))
    if criteria.get("modality"):
        weights.append((20, min(modality / 3, 1), "Same-modality indication experience", modality))
    score = round(100 * sum(w * value for w, value, _, _ in weights) / sum(w for w, _, _, _ in weights))
    sponsors = Counter(t["sponsor"] for t in trials.values() if t["sponsor"])
    years = Counter(str(t["start_year"]) for t in trials.values() if t["start_year"] is not None)
    return {
        "total": len(trials), "relevant": len(relevant), "samePhase": phase,
        "sameModality": modality, "score": score,
        "recruitingInCountry": sum(t["active"] is True for t in trials.values()),
        "potentialOverlap": sum(t["active"] is True for t in relevant),
        "unknownActivity": sum(t["active"] is None for t in relevant),
        "sponsors": [{"name": name, "trials": count} for name, count in sorted(sponsors.items(), key=lambda p: (-p[1], p[0]))[:8]],
        "countryTrialStartsByYear": dict(sorted(years.items())),
        "scoreComponents": [{"label": label, "trials": count, "weight": round(100 * w / sum(x[0] for x in weights))} for w, _, label, count in weights],
        "evidence": [{"id": t["id"], "title": t["title"], "relevant": t["relevant"], "recruitingInCountry": t["active"]} for t in sorted(trials.values(), key=lambda t: (not t["relevant"], t["id"]))[:12]],
    }


def rank_profiles(items: list[dict], criteria: dict, *, today: date | None = None,
                  preview_limit: int = 50, per_country: int = 10) -> dict:
    today = today or date.today()
    institutions: dict[str, dict] = {}
    people: dict[str, dict] = {}
    seen_trials: set[str] = set()
    country_filter = set(criteria.get("countries", []))
    for item in items:
        trial_id = str(item.get("eu_number", ""))
        if not EU_NUMBER.fullmatch(trial_id) or trial_id in seen_trials:
            continue
        seen_trials.add(trial_id)
        profile = item.get("profile") or {}
        variables = profile.get("classification_variables") or {}
        similar, phase, modality = relevance(profile, criteria)
        sponsor = (variables.get("sponsor") or {}).get("name") or ""
        for site in variables.get("sites", []):
            name, country = str(site.get("name") or "").strip(), str(site.get("country_code") or "").upper()
            if not name or not re.fullmatch(r"[A-Z]{2}", country) or (country_filter and country not in country_filter):
                continue
            site_id = key(country, name)
            institution = institutions.setdefault(site_id, {"id": site_id, "name": name, "country": country, "trials": {}})
            active, start_year = country_activity(profile, country, today)
            trial = {"id": trial_id, "title": str(variables.get("trial_title") or trial_id),
                     "sponsor": str(sponsor), "relevant": similar, "phase": phase,
                     "modality": modality, "active": active, "start_year": start_year}
            institution["trials"][trial_id] = trial
            for contact in site.get("site_contacts", []):
                first, last = str(contact.get("first_name") or "").strip(), str(contact.get("last_name") or "").strip()
                role = pi_role(contact)
                # A department mailbox or explicitly non-PI contact is not a candidate PI.
                if not first or not last or role is False:
                    continue
                department = str(contact.get("department_or_division") or "").strip()
                person_id = key(site_id, first, last, department)
                person = people.setdefault(person_id, {
                    "id": person_id, "name": f"{first} {last}", "department": department,
                    "siteId": site_id, "confirmed": {}, "linked": {}, "contactAvailable": False,
                })
                person["linked"][trial_id] = trial
                if role is True:
                    person["confirmed"][trial_id] = trial
                person["contactAvailable"] = person["contactAvailable"] or bool(contact.get("email"))
    rows = []
    site_metrics = {site_id: metrics(site["trials"], criteria) for site_id, site in institutions.items()}
    for person in people.values():
        if not any(t["relevant"] for t in person["linked"].values()):
            continue
        institution = institutions[person["siteId"]]
        confirmed = bool(person["confirmed"])
        pi = metrics(person["confirmed"], criteria) if confirmed else None
        rows.append({
            "id": person["id"], "name": person["name"], "department": person["department"],
            "role": "confirmed_pi" if confirmed else "unconfirmed_contact",
            "pi": pi, "linkedRelevantTrials": sum(t["relevant"] for t in person["linked"].values()),
            "site": {"id": institution["id"], "name": institution["name"], "country": institution["country"], "metrics": site_metrics[institution["id"]]},
            "contactAvailable": person["contactAvailable"], "contactsLocked": True,
        })
    rows.sort(key=lambda r: (r["pi"] is None, -(r["pi"]["score"] if r["pi"] else -1),
                             -(r["pi"]["relevant"] if r["pi"] else 0), -r["site"]["metrics"]["score"],
                             r["name"].casefold(), r["id"]))
    selected = []
    countries: Counter = Counter()
    for index, row in enumerate(rows, 1):
        row["rank"] = index
        country = row["site"]["country"]
        if countries[country] >= per_country:
            continue
        selected.append(row)
        countries[country] += 1
        if len(selected) >= preview_limit:
            break
    return {"rows": selected, "scoringVersion": VERSION, "counts": {
        "matchedRecords": len(rows), "confirmedPIRecords": sum(r["pi"] is not None for r in rows),
        "unconfirmedContacts": sum(r["pi"] is None for r in rows),
        "uniqueSites": len({r["site"]["id"] for r in rows}), "previewRows": len(selected),
    }}
