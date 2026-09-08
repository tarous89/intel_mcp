# Site Agent MCP boundary

Updated 2026-09-07. This file describes the deterministic project slice on the current branch.
Canonical product scope: `tarous89/site-agent/PROJECT_CONTEXT.md`.

## Contract

Site Agent now has two private service-authenticated operations:

```text
POST /internal/site-agent/interpret
POST /internal/site-agent/search
```

The interpret route makes exactly one `gpt-5.6-terra` Responses request at low reasoning.
Its strict schema returns only one to four controlled therapeutic areas, up to 16 short disease
terms, explicitly requested supported country codes and one short display-only `Prioritized
experience` sentence. Disease terms are limited to names,
synonyms/acronyms and useful anatomical or malignancy wording for literal comparison with the
Trial Profile `diseases` field. Biomarkers, products, mechanisms, phase, prior therapy and other
study details are intentionally excluded from deterministic criteria. The sentence consolidates the
actual therapeutic-area, disease and country criteria into readable language. It never introduces
phase, stage or other dimensions that the current search does not use. It retrieves no clinical data
and receives no profile.

The search route accepts stored criteria and makes no model request. Any selected therapeutic
area is required; explicitly requested countries are also required. With no requested country,
all covered EU/EEA countries remain eligible. It exhaustively pages every approved matching
Trial Profile and incrementally aggregates sites/PIs, excluding affiliations outside requested
countries. Disease terms affect priority only and never remove a candidate.

## Deterministic results

`therapeutic-area-disease-country-v3` returns separate Sites and PI-candidate lists. Both are
ordered by disease-matched trial count, distinct disease-term coverage, total eligible trials,
latest recorded trial year, then stable name/ID tie-breaks. The free response contains the top
10 of each list while preserving full site and person counts.

Each result retains deterministic disease-match metrics, observed sponsors, recency and up to
eight supporting trials for downstream use. The current App intentionally displays only rank,
identity/contact and supporting trials. These are relevance signals, never performance,
recruitment capacity, patient availability or current-affiliation claims.

Recorded email routes are returned. Site contacts prefer an explicitly marked PI, then a
stable frequency/name/email tie-break. A named contact is a confirmed PI only when
`principal_investigator=true` or an exact PI role string is present. Null role remains
`role_unconfirmed`; explicit false is excluded from the PI-candidate list. Stable email is
not treated as the display identity because CTIS can record different addresses over time.
PI candidates are grouped by normalized recorded name, return only the most recently evidenced
affiliation, and prefer the most recent recorded email. This deliberately favors a compact
deduplicated workspace while retaining the known collision risk for different people with the
same normalized name.

## Reliability and boundaries

The App stores planner criteria before deterministic search. A failed search can therefore be
retried without another model call. MCP keeps a backward-compatible combined request during
the paired App rollout, but the project API uses the split routes and enforces at most one
planner attempt in its database.

The routes reuse `REPORT_PLAN_SERVICE_TOKEN`, a two-request semaphore, a 60 KB body limit and
approved-only Engine reads. Public MCP tools, report allowances, OAuth, Engine schemas and the
clinical warehouse remain unchanged. No documents, raw CTIS fallback, outreach, payment or
candidate enrichment is added.

Strict-schema list deduplication remains application-side because the Responses schema subset
does not accept `uniqueItems`. Legacy stored `{therapeutic_areas, keywords}` criteria remain
retryable: `keywords` are interpreted as disease terms, countries default to all coverage and a
short disease-based prioritized-experience sentence is derived without another model call.

## Validation and remaining work

The focused Site Agent suite passes locally. The first authenticated production search returned
more than 1,500 sites and 4,000 PI candidates and motivated disease-specific prioritization.
Exhaustive-cohort latency measurement, exact CTIS investigator-path audit, stronger
institution/person identity and candidate enrichment remain follow-up work.
