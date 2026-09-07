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
Its strict schema returns only one to four controlled therapeutic areas and up to 24 literal
search keywords. Keywords may cover the indication, precise synonyms/acronyms, subtype,
biomarker, molecular target, named intervention, mechanism and distinctive population terms.
It retrieves no clinical data and receives no candidate profile.

The search route accepts stored criteria and makes no model request. Therapeutic area is the
only eligibility filter. It exhaustively pages every available approved Trial Profile matching
any selected area, reads profiles in batches of ten, and incrementally aggregates them so the
full profile cohort is not retained in memory. No country, phase, modality or keyword filter
removes a trial.

## Deterministic results

`therapeutic-area-keywords-v1` returns separate Sites and PI-candidate lists. Both are ordered
by keyword-matched trial count, distinct keyword coverage, total therapeutic-area trials,
latest recorded trial year, then stable name/ID tie-breaks. The free response contains the top
10 of each list while preserving full site and person counts.

Each result explains therapeutic-area trial count, keyword-matched trial count, matched
keywords, observed sponsors, latest trial year and up to eight supporting trials. These are
relevance signals, never performance, recruitment capacity, patient availability or current
affiliation claims.

Recorded email routes are returned. Site contacts prefer an explicitly marked PI, then a
stable frequency/name/email tie-break. A named contact is a confirmed PI only when
`principal_investigator=true` or an exact PI role string is present. Null role remains
`role_unconfirmed`; explicit false is excluded from the PI-candidate list. Stable email is
used for cross-site identity; without email, a person remains site-scoped.

## Reliability and boundaries

The App stores planner criteria before deterministic search. A failed search can therefore be
retried without another model call. MCP keeps a backward-compatible combined request during
the paired App rollout, but the project API uses the split routes and enforces at most one
planner attempt in its database.

The routes reuse `REPORT_PLAN_SERVICE_TOKEN`, a two-request semaphore, a 60 KB body limit and
approved-only Engine reads. Public MCP tools, report allowances, OAuth, Engine schemas and the
clinical warehouse remain unchanged. No documents, raw CTIS fallback, outreach, payment or
candidate enrichment is added.

The first authenticated production attempt on 2026-09-07 exposed an OpenAI 400 before any
criteria were returned: the v2 strict schema used the unsupported `uniqueItems` keyword.
The schema now leaves deduplication to `_clean_criteria`, which already normalizes both lists,
while retaining application-side count and value validation. Projects that failed before this
fix have no stored criteria and must be recreated; they cannot accidentally spend a second
planner attempt under the same project ID.

## Validation and remaining work

The focused Site Agent suite and the complete MCP suite pass locally. A representative stored
Trial Profile confirmed current site/contact field shapes and the prevalence of null PI flags.
A real authenticated production search, exhaustive-cohort latency measurement, exact CTIS
investigator-path audit, stronger institution/person identity and any candidate enrichment
remain follow-up work.
