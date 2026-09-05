# Site.agent MCP boundary

Updated 2026-09-05. Implementation branch; not yet a verified production release.
Canonical product scope: `tarous89/site-agent/PROJECT_CONTEXT.md`.

The user approved a PI-first product with exactly Context -> PI list. The private
`POST /internal/site-agent/search` route is registered by the production bootstrap.
It reuses `REPORT_PLAN_SERVICE_TOKEN`; public OAuth/report tools and allowances are unchanged.
Only the authenticated App calls it, after reserving a Site.agent search in the shared
control database. No database owner credential or app database credential is added to MCP.

One existing Sol-model Responses request turns context into schema-validated indication
synonyms, therapeutic areas, country constraints and phase/modality preferences. The
same MCP approved-only read adapter filters therapeutic areas/countries, reads at most
500 approved profiles in batches of ten, and aggregates matching PI-at-site evidence.
No raw-CTIS fallback, document/model enrichment, outreach or payment occurs.

Scores are deterministic versioned relevance heuristics, not clinical performance or
available capacity. PI role must be explicit on each trial record; unknown contacts get
no PI score. Site experience is independent. Country recruitment events are labeled
country-level proxies. Missing activity is not zero competition. All totals refer to the
reviewed bounded cohort. Free output has at most 50 rows and ten per country; email and
phone values are never returned. A site can occur more than once with different PIs.

Limits: context 10-12,000 characters, body 60KB, two concurrent searches, 150-second
route timeout, one AI call. App additionally enforces owner isolation, five attempts per
24 hours, one running search per account, saved-result reuse and contact redaction.

Release requires the paired App migration/route/workspace, regression tests and deployed
smoke checks. PI exact-source-field mapping and coverage expansion remain separate work;
never blanket-promote profile contacts to PI based only on their presence under a site.
