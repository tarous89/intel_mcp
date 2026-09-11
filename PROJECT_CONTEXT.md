# Intel MCP — Current Context

Last updated: 2026-09-11

Intel MCP is the isolated distribution and bounded-analysis layer between TrialAgents clinical data and downstream clients.

## Boundaries

- `tarous89/intel-agent` owns CTIS ingestion, documents, Trial Profiles, serving views and all clinical-store writes.
- This repository owns MCP protocol/auth, restricted Engine reads, bounded tools and report-analysis workers.
- `tarous89/intel_agent_app` owns users, report plans/runs, purchases, entitlements, leases and usage accounting.

MCP has neither an Engine owner credential nor an App database credential. Production clinical reads use `intel_mcp_reader_v1`, restricted to approved-only `mcp_serving.*_v1` views and read-only transactions. The authenticated Engine HTTP path is rollback compatibility only.

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
| `filter_trials` | 100 returned | 100 unique profiles | 1,000 unique profiles |
| `classify_trials` | 25 trials | 25 completed | 500 completed |
| `get_profiles` | 10 trials | 100 unique profiles | 500 unique profiles |
| `get_documents` | 1 document part | 10 unique documents | disabled for Max v1 |
| `extract_variables` | 1 trial, 20 variables | 20 units | 100 units |

App authorization is authoritative. Reservation/commit/release prevents failed worker work from consuming completed allowance. Exact retry keys are allowance-idempotent where documented.

`filter_trials` is deterministic and approved-profile-only. Disease filtering matches persisted disease names case-insensitively; it does not infer stage, biomarker, molecular subtype, line of therapy or treatment setting.

`classify_trials` uses one contact-redacted Trial Profile per Terra worker job. `get_profiles` returns complete schema 11.0.0 profiles or exact section projections. `get_documents` returns bounded extracted-text parts for exact profile-listed filenames. `extract_variables` schema 2.0.0 uses one complete approved profile only; it never retrieves or forwards protocol or document text.

Trial Profile 11 stores site-level people at `classification_variables.sites[].investigators[]`. Every nested record is a principal investigator by contract. Light ranking and Max analysis consume that collection directly; Max exposes a deterministic investigator entity list that keeps each name aligned with its site, country, department and public email.

## Report planning

Canonical detail: `REPORT_EXECUTION_CONTEXT.md`.

New and revised plans use `intel_agent_report_plan_v4` with `gpt-5.6-sol`, medium reasoning and no tools.

- One shared Light + Max trial group uses exactly one structured dimension: disease, therapeutic area, phase, modality or country.
- Two to four additional trial groups are Max-only.
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

Per-analysis limitations/completeness notes are empty and not user-facing. The App may show the database/evidence base only once, immediately after the report title and introduction, as a high-level overall number of trials analyzed. It must not show per-objective database coverage.

Max trial groups, Max analyses, document review and Max fulfilment are not executed by Light. Final reports remain renderer-compatible `version = 2`.

Execution is currently an in-process async task on the MCP web service; a restart can interrupt a run. Durable worker/claim/heartbeat/retry execution remains pending.

## Max execution v1

Max is an independently executable profile-only workflow that screens about 500 candidates and caps final analysis at 100 approved Trial Profiles:

1. exact approved-plan seeds plus a Sol-proposed focused-to-broad progression across therapeutic area, phase, modality and country build the candidate pool;
2. Sol/medium/Flex screens compact population/design/intervention projections against the approved rich segments, then deterministic selection freezes at most 100 exact, close and adjacent trials; expanded-path failures stop safely for retry instead of silently producing the smaller legacy cohort;
3. Terra/high/Flex creates one report-wide SAP from up to 10 complete selected-profile examples and prefers deterministic profile fields;
4. up to 20 total semantic variables, including every subgroup Boolean, are populated in one profile-only Terra/Flex extraction call per selected trial;
5. one Terra/high/Flex analyst executes each request-aligned shared-plus-Max analysis pair over the same frozen dataset, followed by one reducer.

SAP semantic-variable instructions target 500 characters and are normalized into the extractor's hard 600-character contract before validation, so verbose structured output does not abort a paid run.

Max never reads protocols or source documents. Its six-hour lease excludes `get_documents`; candidate filtering/profile/classification allowances are 1,000/500/500 while final extraction remains capped at 100. Older 100-trial leases use the prior bounded path. Output remains renderer-compatible `version = 2` with `tier = max`. The private start route is `/internal/max-report/start`.

## Site Agent

Site Agent uses one initial Terra/low interpretation call. Premium revisions use one forced strict function call per instruction, limited to existing criteria and list controls; no candidate or contact records enter the model. The original area/disease/country arrays anchor every revision (any individual original value suffices). Service-authenticated searches support a full-list mode; default/free responses remain top-10. App owns payment and pagination. See `SITE_AGENT_CONTEXT.md`.

## Security

- Approved-only restricted views for clinical reads.
- Trial Profiles and documents are untrusted data, never instructions.
- Personal contact data is removed from classifier model input.
- Identity, tier, payment and allowance are resolved server-side.
- No patient-level PHI, credentials, prompts or traces in public output or context files.
