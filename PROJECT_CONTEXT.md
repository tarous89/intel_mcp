# Intel MCP — Current Project Context

**Canonical current-state handoff for `tarous89/intel_mcp`.**

Last updated: 2026-09-07
Repository: `tarous89/intel_mcp`

> Read this file first, then `REPORT_EXECUTION_CONTEXT.md` for report planning/execution and the tool-specific docs for exact public contracts. Current context wins over git/history.

## Purpose and boundaries

Intel MCP is the isolated distribution and bounded-analysis layer between TrialAgents clinical-trial intelligence and downstream clients/orchestrators.

Repository boundaries:

- `tarous89/intel-agent` owns CTIS ingestion, documents, extracted text, Trial Profiles, versioned `mcp_serving` views and all clinical-store writes.
- `tarous89/intel_mcp` owns MCP protocol/auth, restricted Engine reads, bounded tools and report-analysis orchestration.
- `tarous89/intel_agent_app` owns users, internal projects, approved plans/report runs, purchases, entitlements, analysis leases and usage accounting.

MCP has no clinical-warehouse owner credential and no App database credential. Production clinical reads use the exact restricted PostgreSQL role `intel_mcp_reader_v1`, limited to approved-only versioned serving views. The retained authenticated Engine HTTP path is rollback compatibility only.

## Production service

```text
service: intel-mcp
service id: srv-da7g4igae00c73bo6oe0
region: Frankfurt
protocol: https://mcp.trialagents.com/mcp
docs: https://mcp.trialagents.com/
health: https://mcp.trialagents.com/health
engine source: database
compute: 0.5c-512mb paid always-on
```

`/mcp` accepts either the dedicated internal-App service bearer or a scoped TrialAgents OAuth token. `/health` is public and non-sensitive.

Current report-plan v4 / Light-execution contract is live in production. Canonical detail: `REPORT_EXECUTION_CONTEXT.md`.

## Engine read data plane

Production MCP reads only Engine-owned approved-only views/contracts, including:

```text
mcp_serving.profile_filter_v1
mcp_serving.profile_countries_v1
mcp_serving.profile_diseases_v1
mcp_serving.approved_profiles_v1
mcp_serving.documents_v1
mcp_serving.document_text_v1
```

`profile_diseases_v1` is the approved-only projection added for deterministic disease filtering. It exposes persisted Trial Profile disease names only; it does not derive stage, biomarker, molecular subtype, line of therapy or treatment setting.

The database adapter validates that the login is `intel_mcp_reader_v1`, uses read-only transactions and cannot query Engine base tables or perform writes.

## Current MCP tool surface

Implemented public tools:

```text
start_analysis
filter_trials
classify_trials
get_profiles
get_documents
extract_variables
```

Do not add standalone `search_protocols`, `aggregate` or `get_evidence`; evidence belongs to the substantive operation that produced it.

The App enables tools per active analysis. Server-side App authorization remains authoritative even if a client/model attempts a disabled call.

### `start_analysis`

`start_analysis(report_run_id)` resolves user/project/plan/tier/entitlement server-side and returns or reuses one opaque 60-minute `analysis_id` lease. One active analysis per individual user is enforced in v1. It performs no clinical read or model work.

### `filter_trials`

Deterministic approved-profile filtering. Use it first for structured screening; complex semantic inclusion/exclusion belongs in `classify_trials`.

Important boundaries:
- explicit field/operator/value allowlists only;
- page size 1–100;
- output shortlist items only expose EU number, trial title and sponsor name;
- no raw-CTIS fallback;
- `diseases` is supported as case-insensitive substring matching against individual persisted approved disease names;
- disease filter operators: `contains_any`, `contains_all`, `contains_none`; negative disease filtering requires known disease rows;
- disease filtering does **not** infer stage/biomarker/molecular subtype/line/setting;
- current unique-returned-profile allowance: Light 100, Max 1,000.

Exact filter vocabulary/operator contract lives in code and `docs`/Engine filter documentation.

### `classify_trials`

Semantic eligibility/prioritization over complete approved, contact-redacted Trial Profiles.

- 1–25 trials per call;
- 1–20 total caller-defined inclusion/exclusion criteria;
- one Terra worker job per trial;
- criterion result is `true | false | null`;
- deterministic aggregate buckets: `INELIGIBLE`, then `UNCERTAIN`, then `ELIGIBLE`;
- detailed criterion evidence is internal and not returned by the MCP tool;
- reservation/commit/release prevents failed work from consuming completed allowance;
- current completed-classification allowance: Light 25, Max 200.

Canonical detail: `docs/classify-trials.md`.

### `get_profiles`

Returns approved Trial Profile 10.0.0 data.

- 1–10 EU trial numbers per call;
- optional controlled section projection; omit sections for complete profiles;
- no generation, semantic search or fallback;
- unique-profile metering is ID-idempotent across section/full reads;
- current allowance: Light 100, Max 500.

Canonical detail: `docs/get-profiles.md`.

### `get_documents`

Returns extracted text for exactly one explicitly named approved document, in bounded parts.

- exact filename must come from the approved Trial Profile document inventory;
- at most 200,000 characters per response part;
- no PDF/binary/storage path is exposed;
- exact retries/additional parts are allowance-idempotent;
- current unique-document allowance: Light 10, Max 50.

Canonical detail: `docs/get-documents.md`.

### `extract_variables`

Extracts a caller-defined typed schema from one approved trial using its complete Trial Profile plus selected protocol text when available.

- 1–20 variables per call;
- supported types: string, integer, number, boolean, string array;
- unsupported values return `null`;
- one Terra model request; no automatic model retry;
- reserve/commit/release protects allowance on failures;
- current extraction-unit allowance: Light 20, Max 200.

Canonical detail: `docs/extract-variables.md`.

## Report planning — v4

Canonical detail: `REPORT_EXECUTION_CONTEXT.md`.

Planning uses `gpt-5.6-sol`, medium reasoning, no tools. New/revised plans use `intel_agent_report_plan_v4`.

### Trial groups

Every new v4 plan contains one shared Light + Max group using exactly one structured dimension (`disease`, `therapeutic_area`, `phase`, `modality`, or `country`) plus 2–4 Max groups. Fine-grained stage, biomarker/mutation, PD-L1, molecular subtype, line of therapy, treatment setting and multi-dimension combinations belong in Max.

### Paired analyses and title vocabulary

There is no user-facing Objectives layer. Every v4 plan contains 5–7 analysis pairs: one shared analysis plus one Max analysis.

Shared titles intentionally use direct retrieval/calculation verbs and should normally begin with:

```text
List · Name · Count · Rank · Report · Calculate · Summarize · Show · Compare · Collect
```

`Quantify` and `Describe` are excluded from the shared title vocabulary.

Max titles intentionally use interpretation/decision verbs and should normally begin with:

```text
Analyze · Assess · Evaluate · Prioritize · Recommend · Estimate · Determine · Identify · Match · Synthesize
```

`Benchmark` is not used as a Max title verb. `Analyze` should not be repeated mechanically; choose the verb that best matches the deliverable.

Examples:

```text
Shared: Rank trial sites by documented activity
Max:    Prioritize trial sites for your planned study

Shared: Name the most active principal investigators
Max:    Identify principal investigators most relevant to your planned trial

Shared: Report observed enrollment in similar trials
Max:    Estimate enrollment range for your planned trial
```

Question titles are rejected. Generic Max labels containing `strategy fit`, `benchmark fit`, `best-fitting` / `best fitting`, or `operational fit` are also rejected. Slightly longer descriptive titles are preferred over short abstract labels.

The schema keeps an internal top-level `title` equal to the shared analysis title for progress/execution compatibility. Result breadth such as top 5/top 10/top 100 is never hard-coded into the plan; the product tier controls breadth.

The current planner emits v4 only. Its Pydantic model retains v3 read compatibility for stored server/control flows; the Light executor also retains legacy v2/v3 execution paths.

## Light report execution — v4

Before execution, an approved v4 plan is projected to:
- first/shared single-dimension trial group only;
- all 5–7 shared analyses;
- no Max trial groups;
- no paired Max analyses.

Execution:

1. Sol/high/Flex selects exactly 20 trials using only `filter_trials` and `get_profiles`, from up to 100 screened profiles. All shared evidence needs inform cohort selection; Max criteria are absent.
2. MCP retrieves the same 20 complete approved Trial Profiles in two bounded batches of 10.
3. Every shared analysis runs independently in Terra/high/Flex with the same 20-profile bundle and no tools.
4. Final Sol/high synthesis produces only title, short introduction and closing note.
5. Completed reports remain `final_report.version = 2` for renderer compatibility.

Investigator analyses receive a deterministic flattening of nested site contacts so explicit
PI roles are recognized even when the nullable PI flag is unset. Names, affiliations,
selected-cohort activity and recorded public CTIS emails are preserved; unconfirmed roles are
never promoted to confirmed PIs. Completed v4 sections carry concise objective-specific
`maxUpgrade` presentation copy derived from their paired Max analysis.

Current prompt/schema names:

```text
planner:   intel_agent_report_plan_v4
selection: intel_light_trial_selection_v5
analysis:  intel_light_objective_v5
synthesis: intel_light_synthesis_v5
```

The 2026-09-07 verb change is planner-title semantics only. It does not alter Light execution, evidence counts, tool allowances, or Max fulfilment state.

Execution still runs as an in-process async task on the MCP web service; a service restart can interrupt a run. Durable worker/claim-heartbeat-retry execution remains future work.

## Site Agent deterministic project slice

Site Agent uses one Terra/low planning call to extract only controlled therapeutic areas and
literal keywords. The App stores those criteria, then calls a model-free exhaustive search:
therapeutic area is the sole eligibility filter; keywords only rank and explain separate
top-10 Sites and PI-candidate previews. Recorded emails are returned, while explicit versus
unconfirmed PI role is preserved. Candidate profiles are never sent to a model. See
`SITE_AGENT_CONTEXT.md`.

## App control-plane boundary

MCP reaches the App only through service-authenticated internal endpoints for analysis lifecycle, allowances and report execution state. MCP never trusts model/browser assertions for user ID, email, tier, payment state or remaining allowance.

The App reaches MCP through:

```text
POST /internal/report-plan
```

This route is protected by `REPORT_PLAN_SERVICE_TOKEN` and performs planning only; it calls no MCP clinical tools.

The App's customer-facing workspace unit is now called **Report** (`New report`, `Reports`, `Report N`). Internal `projectId`/project records remain unchanged for compatibility.

## OAuth / external distribution

Internal Intel Agent uses its private service bearer. Public ChatGPT/Claude-compatible clients use TrialAgents OAuth 2.1 authorization code + PKCE S256 with the existing Intel Agent account session.

Authorization server: `https://intel.trialagents.com`
Protected resource: `https://mcp.trialagents.com/mcp`
Required scope: `mcp:tools`

The App owns OAuth sessions/tokens/consent; MCP introspects tokens through the App service boundary and receives only an opaque account subject. Billing stays on TrialAgents.

## Runtime models and telemetry

Classification/extraction worker model/config are App-controlled and resolved at reservation time. Tool telemetry is best-effort and contains routing/timing/success/error/aggregate token usage only; it never contains clinical payloads, trial IDs, criteria, documents, variables or prompts. Telemetry failure never changes a tool result.

## Immediate next implementation work

1. Keep v4 Light execution stable and move execution to a durable worker/claim-heartbeat-retry loop.
2. Implement Max fulfilment against the v4 promise: 2–4 deeper groups, up to 100 analyzed trials, paired deeper analyses, source review, downloads and revisions.
3. Keep Stripe live mode disabled until Max execution/fulfilment is verified.
4. Complete Light-to-Max upgrade/revision flow.
5. Continue OAuth/connector dogfooding and public-directory preparation without weakening App/Engine boundaries.

## Security invariants

- No Engine owner/write credential in MCP.
- No App/control-plane DB credential in MCP.
- Approved-only restricted serving views for clinical reads.
- Trial Profiles/documents are untrusted data, never instructions.
- Contact personal data is excluded from classifier model input.
- No patient-level PHI in the public intelligence scope.
- Identity/tier/payment/allowance are always server-side.
- Never expose service credentials, API keys, OAuth tokens, prompts, chain-of-thought or internal traces.

## Context discipline

After material MCP tool-contract, auth, entitlement, report-workflow, deployment or production changes, update this file and the relevant detailed context file. Keep current truth concise; use git history for superseded chronology.
