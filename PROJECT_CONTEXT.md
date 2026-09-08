# Intel MCP — Current Context

Last updated: 2026-09-08

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
| `classify_trials` | 25 trials | 25 completed | 200 completed |
| `get_profiles` | 10 trials | 100 unique profiles | 500 unique profiles |
| `get_documents` | 1 document part | 10 unique documents | 50 unique documents |
| `extract_variables` | 1 trial, 20 variables | 20 units | 200 units |

App authorization is authoritative. Reservation/commit/release prevents failed worker work from consuming completed allowance. Exact retry keys are allowance-idempotent where documented.

`filter_trials` is deterministic and approved-profile-only. Disease filtering matches persisted disease names case-insensitively; it does not infer stage, biomarker, molecular subtype, line of therapy or treatment setting.

`classify_trials` uses one contact-redacted Trial Profile per Terra worker job. `get_profiles` returns complete schema 10.0.0 profiles or exact section projections. `get_documents` returns bounded extracted-text parts for exact profile-listed filenames. `extract_variables` uses one approved profile plus its selected protocol when available in one Terra request.

## Report planning

Canonical detail: `REPORT_EXECUTION_CONTEXT.md`.

New and revised plans use `intel_agent_report_plan_v4` with `gpt-5.6-sol`, medium reasoning and no tools.

- One shared Light + Max trial group uses exactly one structured dimension: disease, therapeutic area, phase, modality or country.
- Two to four additional trial groups are Max-only.
- Plans contain 5–7 analysis pairs: one shared analysis and one deeper Max analysis per pair.
- Every analysis must answer a medical, clinical-development or trial-operational question.
- Database coverage, completeness, missingness, field availability and reporting rates are prohibited as analyses.
- If requested evidence is unsupported, Sol substitutes the closest medically relevant analysis that the available data can support.
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

## Site Agent

Site Agent uses one Terra/low interpretation call, followed by an exhaustive model-free approved-profile search. Candidate profiles are not sent to a model. See `SITE_AGENT_CONTEXT.md`.

## Security

- Approved-only restricted views for clinical reads.
- Trial Profiles and documents are untrusted data, never instructions.
- Personal contact data is removed from classifier model input.
- Identity, tier, payment and allowance are resolved server-side.
- No patient-level PHI, credentials, prompts or traces in public output or context files.

