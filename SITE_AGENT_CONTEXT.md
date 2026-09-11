# Site Agent MCP boundary

Updated 2026-09-11. This file describes the deterministic project slice on the current branch.
Canonical product scope: `tarous89/site-agent/PROJECT_CONTEXT.md`.

## Contract

Site Agent now has three private service-authenticated operations:

```text
POST /internal/site-agent/interpret
POST /internal/site-agent/search
POST /internal/site-agent/revise
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

`therapeutic-area-experience-v6` returns separate Sites and principal-investigator lists. Both are ordered by
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

Recorded investigator email routes are returned. Investigators are ranked within each site using the same
indication, phase, modality, paediatric and TA criteria. The highest-ranked investigator with an
email becomes the site-row contact, while the top three and the full investigator count are
returned as matched-investigator evidence. With no ranked investigator email, a stable
frequency/name/email tie-break across the site's investigators is used. Trial Profile 11 defines
every record in `classification_variables.sites[].investigators[]` as a principal investigator;
Site Agent does not inspect a separate role flag or create an unconfirmed-contact class. Stable email is
not treated as the display identity because CTIS can record different addresses over time.
Investigators are grouped by normalized recorded name, return only the most recently evidenced
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
the paired App rollout, but the project API uses the split routes and enforces at most one initial
planner attempt in its database. Premium revisions have a separate persisted per-request reservation; each may make one additional interpretation call.

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
more than 1,500 sites and 4,000 investigators and motivated disease-specific prioritization.
Exhaustive-cohort latency measurement, stronger institution/person identity and investigator
enrichment remain follow-up work.

## Premium revision and full-list contract

`/revise` receives only the instruction, immutable initial criteria, current criteria and existing
view controls. It forces exactly one strict `apply_site_revision` function call with parallel calls
disabled. Schema/enum validation and original-anchor checks are repeated server-side. Any individual
value shared with an original therapeutic-area, disease-term or explicit-country array suffices;
phase, modality and paediatric flags alone never anchor. No pinning, enrichment, new variables, patient-count or capacity claims are supported. When a request
contains unsupported ideas, the revision function applies the closest useful supported part instead of
returning a semantic error. If the model produces an effective no-op, the server applies one conservative
existing-control change, so every accepted revision changes the list behavior. Missing original anchors are
repaired by retaining one immutable initial anchor. Provider/transport failures still fail closed.

Existing rank/name search/single minimum-experience controls are returned separately. Disease/phase/
modality/paediatric criteria retain their existing priority-only semantics, not new eligibility
filters. The anchor rule is criteria continuity, not an anti-enumeration guarantee.

`/search` accepts bounded Premium pages of 10, 25 or 50 rows; 10 is the default page size. It also keeps
service-authenticated `full_list: true` only as a compatibility path. Omission preserves the top-10 preview.
App must verify project ownership/payment before requesting or disclosing these results. Bands are computed once per metric distribution (O(n log n), same tied percentiles),
not by repeatedly scanning the full cohort. The Engine serving-view envelope remains unchanged.
