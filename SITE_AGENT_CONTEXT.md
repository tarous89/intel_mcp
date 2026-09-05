# Site Agent MCP boundary

Updated 2026-09-05. Backend deployed; paired App/landing release is being validated.
Canonical product scope: `tarous89/site-agent/PROJECT_CONTEXT.md`.

## Production status

PR #32 was squash-merged as `69512b3eea7adacec5b745b102544abb3e6ed649`.
Render deploy `dep-dae7u9favr4c73b0r1u0` reached `live` at
2026-09-05T20:45:04Z on the existing `intel-mcp` service. Both MCP CI workflows
passed for implementation commit `7d313061b699f325f65e53edd482a6881c2f9455`
(runs 33988761957 and 33988761947). No extra service or database was created.
This confirms the backend rollout, not an authenticated production Site Agent search.

## Contract

The user approved a PI-first product with exactly Context -> PI list. The private
`POST /internal/site-agent/search` route is registered by the production bootstrap.
It reuses `REPORT_PLAN_SERVICE_TOKEN`; public OAuth/report tools and allowances are unchanged.
Only the authenticated App calls it, after reserving a Site Agent search in the shared
control database. No database owner credential or app database credential is added to MCP.

One existing Sol-model Responses request turns context into schema-validated indication
synonyms, therapeutic areas, country constraints and phase/modality preferences. The
same MCP approved-only read adapter filters therapeutic areas/countries, reads at most
500 approved profiles in batches of ten, and aggregates matching PI-at-site evidence.
No raw-CTIS fallback, document/model enrichment, outreach or payment occurs.

Scores are deterministic versioned relevance heuristics, not clinical performance or
available capacity. PI role must be explicit on each trial record; unknown contacts get
no PI score. Site experience is independent. Country recruitment events are labelled
country-level proxies. Missing activity is not zero competition. All totals refer to the
reviewed bounded cohort. Free output has at most 50 rows and ten per country; email and
phone values are never returned. A site can occur more than once with different PIs.

Limits: context 10–12,000 characters, body 60KB, two concurrent searches, 150-second
route timeout, one AI call. App additionally enforces owner isolation, five attempts per
24 hours, one running search per account, saved-result reuse and contact redaction.

## Remaining validation

The paired App PR #71 includes the migration, workspace and Intel-style shared landing.
Its current release status belongs in the App's `SITE_AGENT_CONTEXT.md` and
`SITE_AGENT_LANDING_CONTEXT.md`. A real authenticated end-to-end search has not been
performed as part of this landing update. PI exact-source-field mapping and coverage
expansion remain separate work; never blanket-promote profile contacts to PI merely
because they appear beneath a site.
