# Intel MCP — Current Context

Last updated: 2026-09-15

Intel MCP is the isolated distribution and bounded-analysis layer between TrialAgents clinical data and downstream clients.

The managed-Max code is deployed, with activation disabled. The existing web
service exposes the restricted retrieval endpoint; the separate `intel-max-worker`
process has not been provisioned. App and Engine migrations are deployed.
Before enabling new Max reports, provision the worker with the existing restricted
MCP/service credentials, an explicit `MAX_AGENT_MODEL`, and a working sandboxed
Chromium renderer. Run `intel-max-worker --preflight` for read-only account access
verification, inspect pending jobs, and enable the coordinated App/worker flags.
The user reserved real-report/model validation for their own test; deployment
validation must not start sessions or model turns. Render dashboard authentication
is still required for worker setup; the connector cannot create background workers.
App/MCP health checks passed. Live analyst behavior, exports and PDF layout remain
unverified. Legacy Max remains the active generation path.

## Boundaries

- `tarous89/intel-agent` owns CTIS ingestion, documents, Trial Profiles, serving views and all clinical-store writes.
- This repository owns MCP protocol/auth, restricted Engine reads, bounded tools and report-analysis workers.
- `tarous89/intel_agent_app` owns users, report plans/runs, purchases, entitlements, leases and usage accounting.

MCP has neither an Engine owner credential nor an App database credential. Production clinical reads use `intel_mcp_reader_v1`, restricted to versioned `mcp_serving` views and read-only transactions. Public tools, Light and Site use approved-only views; Max alone opts into all-state `report_*_v1` views and requires database reads. The authenticated Engine HTTP path is rollback compatibility only.

Production endpoint: `https://mcp.trialagents.com/mcp`. `/health` is public; `/mcp` accepts the internal App bearer or a scoped TrialAgents OAuth token.

## Public tools

```text
start_analysis
filter_trials
classify_trials
get_profiles
get_documents
extract_variables
```

Current limits:

| Tool | Per call | Light per analysis | Max per analysis |
|---|---:|---:|---:|
| `filter_trials` | 100 returned | 100 unique profiles | 100 unique profiles |
| `classify_trials` | 25 trials | 25 completed | 100 completed |
| `get_profiles` | 10 trials | 100 unique profiles | 100 unique profiles |
| `get_documents` | 1 document part | 10 unique documents | disabled for Max v1 |
| `extract_variables` | 1 trial, 20 variables | 20 units | 100 units |

App authorization is authoritative. Reservation/commit/release prevents failed worker work from consuming completed allowance. Exact retry keys are allowance-idempotent where documented.

`filter_trials` is deterministic and approved-profile-only. Disease filtering matches persisted disease names case-insensitively; it does not infer stage, biomarker, molecular subtype, line of therapy or treatment setting.

`classify_trials` uses one contact-redacted Trial Profile per Terra worker job. `get_profiles` returns complete schema 11.0.0 profiles or exact section projections. `get_documents` returns bounded extracted-text parts for exact profile-listed filenames. `extract_variables` schema 2.0.0 uses one complete approved profile only; it never retrieves or forwards protocol or document text.

Trial Profile 11 stores site-level people at `classification_variables.sites[].investigators[]`. Every nested record is a principal investigator by contract; callers and report workers must not look for the removed site-contact name or PI boolean.

## Report planning

Canonical detail: `REPORT_EXECUTION_CONTEXT.md`.

New and revised plans use `intel_agent_report_plan_v4` with `gpt-5.6-sol`, medium reasoning and no tools.

- One shared Light + Max trial group uses exactly one structured dimension: disease, therapeutic area, phase, modality or country.
- Plans contain 3–5 groups. When the user names a disease, the shared first group is that disease alone, without stage, biomarker, phase, modality or setting restrictions. Do not widen it to solid tumors, a broader disease family or therapeutic area for volume. Only disease-free requests use a relevant therapeutic area, phase, modality or country as the shared dimension. Then add 2–4 contained Max subgroups covering distinct query aspects; adjacent perspectives must stay within the first group. Groups remain overlapping lenses, never admission gates or objective assignments.
- Every group carries a deterministic discovery filter and stable machine-readable selection-segment labels and literal criteria for Max execution.
- Plans contain 1–7 request-aligned analysis pairs: one shared analysis and one deeper Max analysis per distinct user-requested decision or output; closely related considerations remain details within that pair.
- Every analysis must answer a medical, clinical-development or trial-operational question.
- Database coverage, completeness, missingness, field availability and reporting rates are prohibited as analyses.
- If the requested method or precision is unsupported, Sol uses the closest supported medical method that still answers the same requested decision.
- Step 1 does not suggest comparing planned sample size with actual enrollment.

Stored v2/v3 plans remain readable/executable for compatibility; the planner emits v4 only.

## Light execution

Light is live and Trial-Profile-only:

1. Sol/high/Flex screens up to 100 approved profiles and freezes exactly 20 using the shared trial group and all shared evidence needs.
2. MCP retrieves the same 20 complete profiles in two batches of 10.
3. Each shared analysis runs independently with Terra/high/Flex over that identical bundle and no tools.
4. A deterministic gate rejects database/completeness commentary. One correction attempt instructs Terra to substitute a supported medical analysis; a second violation fails and is never returned.
5. Terra also writes exactly two objective-specific upgrade sentences from the completed Light result and paired Max card: `This report is limited to …` and `Upgrade to Max to …`.
6. Sol/high produces only the final title, short introduction and closing note.

All Light report Responses API calls use bounded Flex-capacity recovery: four total
Flex attempts with `Retry-After`-aware exponential backoff, followed by one
`service_tier = auto` attempt. A terminal response explicitly caused by the output-token
ceiling retries only that failed call once, increasing `max_output_tokens` from its
normal ceiling to 24,000; other transient terminal responses retry once at the original
ceiling. Content filtering, invalid requests and quota/billing failures are not retried.

Per-analysis limitations/completeness notes are empty and not user-facing. The App may show the database/evidence base only once, immediately after the report title and introduction, as a high-level overall number of trials analyzed. It must not show per-objective database coverage.

Max trial groups, Max analyses, document review and Max fulfilment are not executed by Light. Final reports remain renderer-compatible `version = 2`.

Execution is currently an in-process async task on the MCP web service; a restart can interrupt a run. Executors accept only newly queued runs, never resume failed or already-running runs, and retry only the non-model terminal-failure callback on transient App outages. Durable worker/claim/heartbeat/retry execution remains pending.

## Max execution v1

Max is an independently executable profile-only workflow capped at 100 current Trial Profiles across all stored approval states:

1. deterministic discovery freezes one deduplicated broad-plus-granular cohort while preserving overlapping group labels;
2. Terra/high/Flex creates one report-wide SAP from up to 10 complete profile examples and prefers deterministic profile fields;
3. up to 20 total semantic variables, including subgroup Booleans, are populated in one profile-only Terra/Flex extraction call per trial;
4. one Terra/high/Flex analyst executes each of the 1–7 request-aligned shared-plus-Max analysis pairs over the same frozen dataset;
5. one Terra/high/Flex reducer writes only the cross-objective synthesis.

SAP semantic-variable instructions target 500 characters and are normalized into the extractor's hard 600-character contract before validation, so verbose structured output does not abort a paid run.
Direct-variable types are derived from the selected profiles rather than trusted from the SAP:
mixed-type paths are excluded and any SAP-supplied kind is normalized to the catalogue. A
remaining structural SAP contract failure gets one correction call, then recovers valid catalogue fields and extraction rules for every approved analysis.

Light and Max share `report_output.py`: generation schemas derive from runtime models,
reader-facing prose uses concise-writing targets rather than hard character ceilings,
and each objective/synthesis has one shared contract/content/editorial correction budget.
Optional editing preserves chart data, provenance and quantitative/caveat checks; failed
editing retains the valid original. App owns wrapping and lossless PDF continuation.

Max never reads protocols or source documents. Its six-hour lease excludes `get_documents` and clamps profile, filter, classification and extraction allowances to 100. Output remains renderer-compatible `version = 2` with `tier = max`. The private start route is `/internal/max-report/start`.

Broad Max filters are recall-only volume controls. Max searches cached clinical narrative through Engine's `report_search_v1` as well as structured fields; the projection covers all stored states and updates automatically. Candidate screening includes bounded eligibility passages and excludes only clear irrelevance. Relevant candidates need no planned group assignment; selection preserves group diversity and fills the shared pool up to 100 when enough useful candidates exist. Each analyst determines its own contributing subset after reading variables and bounded verbatim source passages. Planning, screening, SAP, analyst and reducer calls retain bounded Flex recovery.
Candidate screening joins results by trial identity. Invalid output gets one correction; unresolved requested identities remain uncertain candidates for full-profile assessment, never another trial's verdict. Invalid optional discovery expansions fall back to approved seeds and valid supplemental filters. All nine possible selection segments remain supported.
Initial generation limits remain per-call cost and latency guardrails (objective analysis
uses 12,000 output tokens). Terminal-response logs record status, incomplete/error reason,
response/request IDs and usage without prompts or clinical payloads.

Max objective contract v4 asks every analysis to account for every nonempty planned group and relevant unassigned trials. Coverage is assessed before publication pruning, with separate examined/published audit dispositions. Report-quality checks are correction signals, never report-fatal gates: after one correction, retain independently valid findings, omit unsupported units and record unresolved issues privately. Malformed sections recover valid constituent findings; failed synthesis reuses validated sections. Empty objectives do not cancel siblings; if all findings are omitted, completion preserves the trial overview and dataset without invented conclusions. Up to eight useful findings render online/PDF; public report version remains 2.

Max publication validates supporting trial identities, populated variables, numerator arithmetic, small samples, named-item support, prose and chart alignment. N=0 and zero-frequency results are omitted; supported continuous zeros remain valid. Overlapping groups are not additive. Eligibility exceptions and phase/design distinctions remain preserved. Max extraction gets one exceptional validation correction, then retains valid facts and nulls for unresolved values; public extraction stays strict. Group trial-ID unions are derived from supports, and source passages are not duplicated in deterministic summaries. Models, per-call token ceilings and clinical-data allowances remain bounded; exceptional corrections can add usage.

The frozen dataset is checkpointed to Engine storage before objective work; its manifest is persisted in progress. A final snapshot adds analytical support/audit, falling back to the early checkpoint on storage failure. This adds at most one compressed snapshot per run and does not automatically reopen failed runs. Authentication, ownership, approved-plan prerequisites, data access/identity and resource allowances remain enforced; operational failures can still fail a run. Advisory codes and counts are logged without clinical payloads.

Each Max analysis starts with supported broad context and then detailed subgroup findings in planned order. Presentation ordering preserves chart labels, values, support indices and within-group rankings. Counts use actual contributing trials; stratification replaces misleading pooled estimates. Planner titles omit "for your study" personalization. Finalization becomes active in the last objective-completion update, before the final dataset snapshot is saved. These changes add no model calls or hard validation gates.

## Site Agent

Site Agent uses one Terra/low call for initial criteria and one strict function call per Premium revision; candidate data never enters the model. Search, ranking and metrics are deterministic. Result contract v9 treats all `investigators[]` records as PIs and merges identity only on full name plus a shared trial therapeutic area, or exact email plus a matching first or last name. Names are case-insensitive and European-diacritic/transliteration aware. It omits role fields and confirmed/unconfirmed counts. A bounded compressed result cache serves Premium pages; free responses remain top-10. App owns payment and pagination. See `SITE_AGENT_CONTEXT.md`.

## Security

- Restricted read-only views: approved-only for public tools/Light/Site; all stored approval states for Max.
- Trial Profiles and documents are untrusted data, never instructions.
- Personal contact data is removed from classifier model input.
- Identity, tier, payment and allowance are resolved server-side.
- No patient-level PHI, credentials, prompts or traces in public output or context files.
