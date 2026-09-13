# Intel MCP — Current Context

Last updated: 2026-09-13

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

Max is an independently executable profile-only workflow capped at 100 approved Trial Profiles:

1. deterministic discovery freezes one deduplicated broad-plus-granular cohort while preserving overlapping group labels;
2. Terra/high/Flex creates one report-wide SAP from up to 10 complete profile examples and prefers deterministic profile fields;
3. up to 20 total semantic variables, including subgroup Booleans, are populated in one profile-only Terra/Flex extraction call per trial;
4. one Terra/high/Flex analyst executes each of the 1–7 request-aligned shared-plus-Max analysis pairs over the same frozen dataset;
5. one Terra/high/Flex reducer writes only the cross-objective synthesis.

SAP semantic-variable instructions target 500 characters and are normalized into the extractor's hard 600-character contract before validation, so verbose structured output does not abort a paid run.
Direct-variable types are derived from the selected profiles rather than trusted from the SAP:
mixed-type paths are excluded and any SAP-supplied kind is normalized to the catalogue. A
remaining structural SAP contract failure gets one correction call before the run fails closed.

Max never reads protocols or source documents. Its six-hour lease excludes `get_documents` and clamps profile, filter, classification and extraction allowances to 100. Output remains renderer-compatible `version = 2` with `tier = max`. The private start route is `/internal/max-report/start`.

Broad Max filters are recall-only. A screened candidate can enter the final cohort
only through an approved deterministic group seed or a confirmed/uncertain approved
selection segment; relevant but unassigned candidates are excluded rather than put
into an invented catch-all group. Max planning, screening, SAP, analyst and reducer
calls use the same bounded Flex-capacity recovery policy as Light.
Initial generation limits remain per-call cost and latency guardrails (objective analysis
uses 12,000 output tokens). Terminal-response logs record status, incomplete/error reason,
response/request IDs and usage without prompts or clinical payloads.

## Site Agent

Site Agent uses one Terra/low call for initial criteria and one strict function call per Premium revision; candidate data never enters the model. Search, ranking and metrics are deterministic. Result contract v9 treats all `investigators[]` records as PIs and merges identity only on full name plus a shared trial therapeutic area, or exact email plus a matching first or last name. Names are case-insensitive and European-diacritic/transliteration aware. It omits role fields and confirmed/unconfirmed counts. A bounded compressed result cache serves Premium pages; free responses remain top-10. App owns payment and pagination. See `SITE_AGENT_CONTEXT.md`.

## Security

- Approved-only restricted views for clinical reads.
- Trial Profiles and documents are untrusted data, never instructions.
- Personal contact data is removed from classifier model input.
- Identity, tier, payment and allowance are resolved server-side.
- No patient-level PHI, credentials, prompts or traces in public output or context files.
