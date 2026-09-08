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
Its strict schema returns one to four controlled therapeutic areas, up to 16 short disease
terms, explicitly requested supported country codes, integer phase components, one controlled
modality when known, a paediatric-relevance flag and one short display-only `Prioritized
experience` sentence. Disease terms are limited to names,
synonyms/acronyms and useful anatomical or malignancy wording for literal comparison with the
Trial Profile `diseases` field. Biomarkers, products, mechanisms, prior therapy, treatment setting
and other free-text study details are intentionally excluded from deterministic criteria. The
sentence consolidates the core criteria into readable language. It retrieves no clinical data and
receives no profile.

The search route accepts stored criteria and makes no model request. Any selected therapeutic
area is required; explicitly requested countries are also required. With no requested country,
all covered EU/EEA countries remain eligible. It exhaustively pages every approved matching
Trial Profile and incrementally aggregates sites/PIs, excluding affiliations outside requested
countries. Disease, phase, modality and paediatric experience affect priority only and never remove
a candidate.

## Deterministic results

`therapeutic-area-experience-v5` returns separate Sites and PI-candidate lists. Both are ordered by
five-year indication trial count, requested-phase count, requested-modality count, paediatric
count when relevant, therapeutic-area count, recency, then stable
name/ID tie-breaks. A disease synonym can match a trial only once. The free response contains the top
10 of each list while preserving full site and person counts.

Each result retains distinct-trial counts for therapeutic area, indication, phase, modality,
paediatric experience when relevant, six-month activity, the top three recorded sponsors and up
to eight supporting trials. Experience uses a rolling five-year authorization window; activity
uses six months. Cohort bands are calculated across the full eligible Site or PI cohort before
the preview is truncated. Zero is always Bottom 25%; positive counts use tied mid-rank percentile
placement. The bands are evidence context, never performance, recruitment capacity, patient
availability or current-affiliation claims. Treatment setting is not read or scored.

Recorded email routes are returned. Confirmed PIs are ranked within each site using the same
indication, phase, modality, paediatric and TA criteria. The highest-ranked confirmed PI with an
email becomes the site-row contact, while the top three and the full confirmed-PI count are
returned as matched-investigator evidence. With no confirmed PI email, a stable site-contact
frequency/name/email tie-break is used. A named contact is a confirmed PI only when
`principal_investigator=true` or an exact PI role string is present. Null role remains
`role_unconfirmed`; explicit false is excluded from the PI-candidate list. Stable email is
not treated as the display identity because CTIS can record different addresses over time.
PI candidates are grouped by normalized recorded name, return only the most recently evidenced
affiliation, and prefer the most recent recorded email. This deliberately favors a compact
deduplicated workspace while retaining the known collision risk for different people with the
same normalized name.

Sponsor experience is consolidated deterministically before counting. Case, punctuation and
spacing variants share a key, common trailing legal suffixes are removed, and versioned curated
exceptions keep ambiguous corporate roots separate. No fuzzy or parent-company matching is used,
preventing unsupported corporate merges. Original sponsor strings remain attached to the internal
metric evidence.

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
