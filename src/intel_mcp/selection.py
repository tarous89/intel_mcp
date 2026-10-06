"""Deterministic evidence-first selection; no model or network dependency."""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from .models import TrialFilters
from .site_ranking import (ProfileRanker, normalized, normalized_name, _canonical_sponsor,
                           _authorization_dates, _shift_months)

VERSION = "entity-selection-1"
MAX_COHORT = 500
DUTIES = {
    1: "On site monitoring", 2: "Investigator recruitment",
    3: "Interactive response technologies (IRT)", 4: "Laboratory analysis",
    5: "Project management", 6: "Data management", 7: "E-data capture",
    8: "Safety reporting", 9: "Q/A auditing", 10: "Statistical analysis",
    11: "Medical writing", 12: "Regulatory expertise", 13: "Medical expertise",
    14: "Medicinal product management", 15: "Other",
}
BUCKETS = ("direct", "related", "broader")
Country = Annotated[str, Field(pattern=r"^[A-Z]{2}$")]


class SelectionError(ValueError):
    pass


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


def clean_filters(filters: TrialFilters) -> dict:
    return {k: v for k, v in filters.model_dump(mode="json", exclude_none=True).items() if v != []}


class SelectionCriteria(Contract):
    base: TrialFilters = Field(description="Mandatory trial constraints; positive therapeutic areas required.")
    direct: TrialFilters = Field(default_factory=TrialFilters, description="Additional AND conditions for direct matches. Empty means all base trials.")
    related: TrialFilters | None = Field(default=None, description="Explicit alternative conditions within base; direct matches take precedence.")
    entity_type: Literal["cros", "sites", "pis"]
    entity_countries: list[Country] = Field(default_factory=list, max_length=30, description="CRO registered country or site/PI recorded affiliation country; not service coverage.")
    function_code: Annotated[int, Field(strict=True, ge=1, le=15)] | None = None
    include_broader: bool = False
    as_of: date = Field(description="Explicit reference date for recent-authorization metrics; not recruitment capacity.")

    @model_validator(mode="after")
    def validate_scope(self):
        area = self.base.therapeutic_areas
        if area is None or area.operator == "contains_none":
            raise ValueError("A positive therapeutic-area base filter is required")
        if self.function_code is not None and self.entity_type != "cros":
            raise ValueError("function_code applies only to CROs/providers")
        self.entity_countries = sorted(set(self.entity_countries))
        if self.related is not None and not clean_filters(self.related):
            raise ValueError("Related criteria must be explicit; use include_broader for the remaining base")
        return self


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


class CohortSummary(Contract):
    version: str = VERSION
    snapshot: str
    criteria: SelectionCriteria
    counts: dict[str, int]
    coverage: Literal["complete_approved_base"] = "complete_approved_base"
    limitations: list[str]


class SelectionCatalogue(Contract):
    version: str = VERSION
    entity_types: list[str]
    function_codes: dict[str, str]
    filter_fields: list[str]
    max_base_profiles: int = MAX_COHORT
    max_results: int = 10
    profile_policy: str = "approved schema 11 only"
    authorization: str = "Existing App analysis lease with filter_trials and get_profiles permissions"
    limitations: list[str]


class EntityResult(Contract):
    id: str
    rank: int
    name: str
    countries: list[str]
    organization_types: list[str]
    affiliations: list[dict]
    trial_counts: dict[str, int]
    function_counts: dict[str, int]
    sponsors: list[dict]
    recent_authorization_trials: int
    evidence: list[dict]
    rationale: str


class RankingResult(Contract):
    cohort: CohortSummary
    total_entities: int
    returned: int
    ranking_order: list[str]
    entities: list[EntityResult]


class EvidenceResult(Contract):
    snapshot: str
    entity_id: str
    total_trials: int
    next_offset: int | None
    trials: list[dict]


LIMITATIONS = [
    "Approved stored profiles only; this population can differ from the combined App.",
    "Structured matching is literal; disease synonyms and semantic similarity are not inferred.",
    "Recorded participation is not verified capacity, recruitment performance or availability.",
    "Trial operational findings are not attributed to an entity without separate evidence.",
    "Sponsor co-occurrence is not proof of a direct contractual collaboration.",
    "CROs include CTIS-listed third-party laboratories and vendors; full-service status is not inferred.",
]


class SelectionDataset:
    """One bounded complete read, identified by criteria plus exact source content."""
    def __init__(self, criteria: SelectionCriteria, records: list[dict]):
        if len(records) > MAX_COHORT:
            raise SelectionError("COHORT_TOO_LARGE: Narrow base criteria; no partial ranking was produced.")
        if len(json.dumps(records, ensure_ascii=False).encode()) > 16 * 1024 * 1024:
            raise SelectionError("COHORT_BYTES_EXCEEDED: Narrow the cohort; no partial ranking was produced.")
        ids = [r["trial_id"] for r in records]
        if len(set(ids)) != len(ids):
            raise SelectionError("AMBIGUOUS_PROFILE: Multiple approved source rows for a trial.")
        self.criteria = criteria
        self.records = {r["trial_id"]: r for r in sorted(records, key=lambda r: r["trial_id"])}
        self.snapshot = digest({"version": VERSION, "criteria": criteria.model_dump(mode="json"), "records": list(self.records.values())})
        self.buckets = {tid: "direct" if r["direct"] else "related" if r["related"] else "broader" for tid, r in self.records.items()}
        self._entities = None

    def check_snapshot(self, expected: str):
        if expected != self.snapshot:
            raise SelectionError("SELECTION_CHANGED: Source or criteria changed; search again before ranking or evidence retrieval.")

    def summary(self):
        counts = Counter(self.buckets.values())
        return CohortSummary(snapshot=self.snapshot, criteria=self.criteria,
            counts={"base": len(self.records), **{bucket: counts[bucket] for bucket in BUCKETS}}, limitations=LIMITATIONS)

    def _included(self, tid):
        return self.criteria.include_broader or self.buckets[tid] != "broader"

    def _entities_for_selection(self):
        if self._entities is not None:
            return self._entities
        entities = {}
        if self.criteria.entity_type == "cros":
            duty_keys = {normalized(label).replace(" ", ""): code for code, label in DUTIES.items()}
            for tid, record in self.records.items():
                if not self._included(tid):
                    continue
                for provider in record["profile"].get("classification_variables", {}).get("third_party_organizations") or []:
                    name = str(provider.get("name") or "").strip()
                    country = provider.get("country_code")
                    if not name or self.criteria.entity_countries and country not in self.criteria.entity_countries:
                        continue
                    identity_name, _ = _canonical_sponsor(normalized_name(name))
                    identity = digest(["cro", identity_name, country])[:24]
                    labels = [s.strip() for s in str(provider.get("function") or "").split(";") if s.strip()]
                    codes = {duty_keys[key] for label in labels if (key := normalized(label).replace(" ", "")) in duty_keys}
                    row = entities.setdefault(identity, {"id": identity, "names": set(), "countries": set(), "types": set(), "affiliations": [], "trials": set(), "roles": defaultdict(set), "functions": defaultdict(set)})
                    row["names"].add(name)
                    if provider.get("organisation_type"):
                        row["types"].add(provider["organisation_type"])
                    if country:
                        row["countries"].add(country)
                    row["trials"].add(tid)
                    row["roles"][tid].update(labels)
                    for code in codes:
                        row["functions"][str(code)].add(tid)
            if self.criteria.function_code is not None:
                for identity in list(entities):
                    row = entities[identity]
                    eligible = row["functions"].get(str(self.criteria.function_code), set())
                    if not eligible:
                        del entities[identity]
                        continue
                    row["trials"] = set(eligible)
                    row["roles"] = {tid: roles for tid, roles in row["roles"].items() if tid in eligible}
                    row["functions"] = {code: tids & eligible for code, tids in row["functions"].items() if tids & eligible}
        else:
            ranker = ProfileRanker({"countries": self.criteria.entity_countries})
            for tid, record in self.records.items():
                if not self._included(tid):
                    continue
                profile = deepcopy(record["profile"])
                for site in profile.get("classification_variables", {}).get("sites") or []:
                    for person in site.get("investigators") or []:
                        email = str(person.get("email") or "").strip()
                        if not re.fullmatch(r"[^\s@*<>]+@[^\s@*<>]+\.[^\s@*<>]+", email) or any(x in email.lower() for x in ("redacted", "masked")):
                            person["email"] = ""
                ranker.add([{"eu_number": tid, "profile": profile}])
            values = ranker.sites if self.criteria.entity_type == "sites" else ranker.people
            for identity, item in values.items():
                names = {item["name"]} if self.criteria.entity_type == "sites" else set(item["names"])
                countries = {item["country"]} if self.criteria.entity_type == "sites" else {s["country"] for s in item["sites"].values()}
                entities[identity] = {"id": identity, "names": names, "countries": countries,
                    "trials": set(item["trials"]), "roles": {}, "functions": {}, "types": set(),
                    "affiliations": ([] if self.criteria.entity_type == "sites" else sorted(
                        [{"name": site["name"], "country": site["country"], "relationship": "recorded_trial_affiliation"}
                         for site in item["sites"].values()], key=lambda x: (x["country"], x["name"]))),
                    "trial_countries": ({tid: {item["country"]} for tid in item["trials"]}
                        if self.criteria.entity_type == "sites" else {
                            tid: {item["sites"][sid]["country"] for sid, trials in item["site_trials"].items() if tid in trials}
                            for tid in item["trials"]})}
        self._entities = entities
        return entities

    def _trial_evidence(self, tid, entity):
        record = self.records[tid]
        profile = record["profile"]
        c = profile.get("classification_variables") or {}
        return {"trial_id": tid, "title": c.get("trial_title"), "match": self.buckets[tid],
            "url": "https://euclinicaltrials.eu/ctis-public/view/" + tid,
            "profile_sha256": digest(profile), "schema_version": record["schema_version"],
            "roles": sorted(entity["roles"].get(tid, [])),
            "operational_findings": list(dict.fromkeys(x for x in (profile.get("results") or {}).get("trial_operational_findings") or [] if isinstance(x, str) and x.strip())),
            "findings_attribution": "trial_only"}

    def _ordered_trials(self, row):
        return sorted(row["trials"], key=lambda tid: (BUCKETS.index(self.buckets[tid]), tid))

    def rank(self, limit=10):
        rows = []
        for row in self._entities_for_selection().values():
            counts = Counter(self.buckets[tid] for tid in row["trials"])
            sponsors = defaultdict(set)
            sponsor_labels = {}
            recent = set()
            for tid in row["trials"]:
                profile = self.records[tid]["profile"]
                sponsor = (profile.get("classification_variables") or {}).get("sponsor") or {}
                name = sponsor.get("name") if isinstance(sponsor, dict) else sponsor
                if name:
                    key, label = _canonical_sponsor(name)
                    sponsors[key].add(tid)
                    sponsor_labels[key] = min(sponsor_labels.get(key, label), label)
                dates = _authorization_dates(profile)
                relevant_dates = [d for country, d in dates.items() if self.criteria.entity_type == "cros" or country in row["trial_countries"][tid]]
                if any(_shift_months(self.criteria.as_of, 6) <= d <= self.criteria.as_of for d in relevant_dates):
                    recent.add(tid)
            trial_counts = {bucket: counts[bucket] for bucket in BUCKETS}
            trial_counts["total"] = len(row["trials"])
            name = min(row["names"], key=lambda x: (normalized_name(x), x))
            rows.append(EntityResult(id=row["id"], rank=0, name=name, countries=sorted(row["countries"]),
                organization_types=sorted(row["types"]), affiliations=row["affiliations"],
                trial_counts=trial_counts, function_counts={k: len(v) for k, v in sorted(row["functions"].items())},
                sponsors=[{"name": sponsor_labels[k], "trial_count": len(v), "relationship": "recorded_same_trial"} for k, v in sorted(sponsors.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:5]],
                recent_authorization_trials=len(recent), evidence=[self._trial_evidence(tid, row) for tid in self._ordered_trials(row)[:3]],
                rationale=f"{counts['direct']} direct, {counts['related']} related and {counts['broader']} broader distinct trials" + (f" with recorded function {self.criteria.function_code}." if self.criteria.function_code else ".")))
        rows.sort(key=lambda r: (-r.trial_counts["direct"], -r.trial_counts["related"], -r.recent_authorization_trials,
                                 -r.trial_counts["broader"], normalized_name(r.name), r.id))
        for i, row in enumerate(rows, 1):
            row.rank = i
        return RankingResult(cohort=self.summary(), total_entities=len(rows), returned=min(limit, len(rows)),
            ranking_order=["direct_trials_desc", "related_trials_desc", "recent_authorization_trials_desc", "broader_trials_desc", "name_asc", "id_asc"], entities=rows[:limit])

    def evidence(self, entity_id, offset=0, limit=10):
        row = self._entities_for_selection().get(entity_id)
        if row is None:
            raise SelectionError("ENTITY_NOT_IN_SELECTION: Entity is not eligible in this selection.")
        ids = self._ordered_trials(row)
        return EvidenceResult(snapshot=self.snapshot, entity_id=entity_id, total_trials=len(ids),
            next_offset=offset + limit if offset + limit < len(ids) else None,
            trials=[self._trial_evidence(tid, row) for tid in ids[offset:offset + limit]])
