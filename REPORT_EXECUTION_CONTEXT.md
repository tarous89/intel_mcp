# Intel MCP — Report Execution Current Context

Last updated: 2026-09-17 (implementation branch; production behavior below is unchanged)

## Managed Max redesign — disabled implementation

The new source path is gated by `MAX_AGENT_ENABLED=false` by default. It has not
been deployed or validated with a live managed-agent account. Legacy execution
and stored v2 reports remain the production path.

The implementation adds page/batch evidence checkpoints, a single managed
analyst session, an authenticated report-bound three-tool endpoint, source-backed
calculations, sanitized v3 HTML, deterministic XLSX and optional isolated Chromium
PDF generation. The App stores jobs, session/turn IDs and immutable report versions;
clinical evidence and work files stay in Engine artifact storage. The supervised
worker entrypoint is `python -m intel_mcp.max_agent_execution`. Web requests only
acknowledge durable jobs; they do not own the analyst task lifetime.

Configuration must agree between App and MCP: `MAX_AGENT_TRIAL_LIMIT` (default 100,
maximum 100), `MAX_AGENT_DISCOVERY_LIMIT` (10000), `MAX_AGENT_DOCUMENT_LIMIT` (20),
and `MAX_AGENT_DOCUMENT_CHARACTERS` (2000000). MCP additionally requires an explicit
`MAX_AGENT_MODEL`, `MAX_AGENT_MAX_TURNS` (12), `MAX_AGENT_MAX_MINUTES` (180), the
existing OpenAI/Engine/App service credentials, and optionally `MAX_AGENT_CHROMIUM`.
No model was selected by a live quality/cost comparison yet.

Verified locally: the full MCP suite passes with the declared `httpx` dependency.
Checks include frozen batches, document parts, scope/dispatch denial, calculation
rules, malformed-data recovery, sanitizer, lossless XLSX, idle sessions, large-input
file references, restored-turn identity, evidence-stage resume and PDF retry isolation.
App integration and TypeScript checks and the production Next build also pass;
the build used `PUBLIC_SNAPSHOTS_PREBUILT=1` to omit unrelated public-page fetching.

Release gates remain: live CRPC snapshot pilot and model/account access, semantic
quality/cost comparison with the existing report and mCRC reference, real hosted
session/environment recovery, representative 100-trial runtime/memory, Chromium
PDF visual inspection, and coordinated migration/worker deployment. Local SSH access
to Render and browser access to the local preview were unavailable during validation;
no live agent run or visual PDF acceptance is claimed. English new-evidence and
formatting-intent checks remain conservative heuristics requiring multilingual
product validation. Source-pointer checks establish traceability, not independent
clinical interpretation validation.

Large hosted inputs use Files API references with checkpointed IDs and content hashes.
Failed revisions start replacement sessions from published evidence/work rather than
reuse a session containing unpublished changes. The UI permits editing only the latest
version and resolves PDF availability for the selected historical version.
PDF failures enqueue a version-bound derivative job in App; the worker retries the exact
sanitized HTML up to three times, with no model calls or changes to report content.
The `intel-max-worker --preflight` command checks configuration/account access without
starting a session. The normal `intel-max-worker` command runs the supervised worker.
Do not enable the flag or increase the advertised-envelope runtime allowance
until these gates pass. Rollback leaves v3 rendering available and routes new
unmarked runs through the legacy executor.

This is the source of truth for report planning and Light/Max execution. Light remains capped at 20 analyzed trials. Max screens a broad candidate pool and freezes at most 100 current Trial Profiles across all stored approval states for report analysis.

## Report-plan v4

Planning uses `gpt-5.6-sol`, medium reasoning, strict structured output and no MCP tools. New/revised plans are v4; stored v2/v3 plans remain compatible.

### Trial groups

Every v4 plan has 3–5 groups. If the user names a disease, the shared Light + Max first group uses that disease alone, dropping stage, biomarker, phase, modality and setting restrictions without widening to solid tumors, a broader disease family or therapeutic area. For example, Phase II metastatic prostate cancer starts with prostate cancer; NSCLC stays NSCLC and STEMI stays STEMI. Only when no disease is named may the planner use a relevant therapeutic area, phase, modality or country. Then add 2–4 contained Max subgroups covering distinct requested aspects. Subgroups can overlap and be broader, narrower, adjacent or exact relative to the query, but cannot widen the first group. The shared group uses exactly one supported dimension:

```text
disease | therapeutic_area | phase | modality | country
```

Disease is backed by persisted approved Trial Profile disease names. Stage, biomarker, subtype, line of therapy, treatment setting and multi-dimension combinations belong to Max-only groups.

Every group also contains backend-only execution metadata: one supported high-recall `discoveryFilter` plus stable `selectionSegments` with unique keys and literal inclusion/exclusion criteria. Stored v4 plans without this metadata remain usable for Light but must be regenerated before Max execution.

### Analysis pairs

Every plan has 1–7 request-aligned pairs, each containing one shared analysis and one deeper Max analysis. Each distinct user-requested decision or output maps to one pair; closely related considerations stay inside that pair as details. There is no user-facing Objectives layer.

Shared titles normally begin with direct evidence verbs such as `List`, `Name`, `Count`, `Rank`, `Report`, `Calculate`, `Summarize`, `Show`, `Compare` or `Collect`. Max titles normally begin with decision verbs such as `Analyze`, `Assess`, `Evaluate`, `Prioritize`, `Recommend`, `Estimate`, `Determine`, `Identify`, `Match` or `Synthesize`.

Question titles, hard-coded result breadth and generic labels such as `strategy fit`, `benchmark fit`, `best fitting` and `operational fit` are rejected. Max must add at least two genuine decision factors rather than restating the shared analysis.

Every planned analysis must be medical, clinical-development or trial-operational. Database coverage, data completeness, missingness, field availability, documentation rates and “how many trials reported a field” are prohibited. When evidence cannot support the requested method or precision, the planner uses the closest supported medical method that still answers the same requested decision.

Step 1 suggested analyses do not include planned sample size versus actual enrollment.

## Light projection and cohort

Light receives only:

- the shared single-dimension trial group;
- all 1–7 request-aligned shared analyses;
- no Max group or Max analysis for execution.

The paired Max card is passed only to the objective writer after the Light result exists, solely to create upgrade copy.

Sol/high/Flex screens up to 100 approved profiles using `filter_trials` and `get_profiles`, then selects exactly 20. All shared evidence needs influence selection. MCP freezes and retrieves the same 20 complete profiles in two calls of 10; every shared analysis receives that identical bundle.

## Objective analysis

Each shared analysis runs independently with `gpt-5.6-terra`, high reasoning, Flex and no tools.

Required behavior:

- answer the approved medical/clinical/operational question using the available 20-profile evidence;
- substitute a supported medical calculation, comparison, ranking or pattern when the requested lens is unsupported;
- never return database coverage/completeness commentary, missing-field analysis, reporting-subset counts or documentation-rate analysis;
- return an empty legacy `limitations` array;
- preserve evidence-linked findings and deterministic investigator-role handling.

A deterministic content gate retries one violating draft with an explicit medical-substitution instruction. If the corrected draft still violates the rule, the section fails safely and is not returned.

After a valid Light result, the same objective writer generates exactly two objective-specific sentences:

1. `This report is limited to …`
2. `Upgrade to Max to …`

The copy may describe future Max value across up to 100 Trial Profiles but must not claim Max work or outcomes already exist.

## Final report

Sol/high/Flex final synthesis writes only the title, short introduction and closing note. It does not rewrite sections or upgrade copy.

The App is responsible for presentation:

- for Light, the only database/evidence-base mention appears once, directly after the title and introduction;
- that band states the overall number of trials analyzed and a high-level selection description;
- no per-objective completeness, coverage or “N of 20 reported” messaging is shown;
- per-analysis decision-implication blocks are replaced by the two upgrade sentences;
- completed output remains `final_report.version = 2` for renderer compatibility.

Prompt/schema names:

```text
planner:   intel_agent_report_plan_v4
selection: intel_light_trial_selection_v5
analysis:  intel_light_objective_v9
synthesis: intel_light_synthesis_v6
```

## Max execution v1

### Hard limits

- target 500 compact candidate profiles after deterministic discovery, with a hard 1,000-ID discovery ceiling;
- 100 unique trials in the final frozen report-wide cohort;
- 10 complete, untruncated, group-stratified profile examples for the SAP;
- 20 total non-deterministic profile variables, including Boolean segment membership;
- no protocol or source-document extraction;
- one profile-only semantic extraction call per selected trial;
- 1–7 objective analyst calls and one reducer call.

Candidate-filter planning and compact-profile screening use Sol/medium/Flex. SAP, final profile extraction, objective analysis and reduction use Terra/high/Flex. The shared report planner remains Sol/medium and is not constrained to deterministic screening fields.

### Stages

1. Preserve every approved group's discovery filter as an exact seed, starting with the broad umbrella, then search planned subgroups using `therapeutic_areas`, `phase`, `modalities`, `country_codes` and bounded literal `title_terms`. Max text searches also use Engine's `report_search_v1` clinical narrative projection, independently of structured intersections. Disease remains a seed rather than the sole recall gate. Broad-group membership alone is not an exact query match; useful contextual trials remain eligible.
2. Execute the seed and broad filters in bounded round-robin pages, deduplicate and stop at the 500-candidate target or when the available current-profile pool is exhausted. Max alone reads the all-state report views; approval metadata is preserved in its dataset.
3. Load compact `overview`, `population`, `trial_design` and `interventions` projections plus up to 1,200 characters of relevant eligibility excerpts per candidate. Sol screens them in batches of 25 against the approved rich disease, biomarker, treatment-setting and population segments, assigning `exact`, `close`, `adjacent` or `exclude` without changing any approved analysis. The v2 response requires one keyed assessment per trial ID. Results are joined by ID and restored to input order, not rejected for ordering. Legacy arrays must contain every expected trial exactly once. Missing, duplicate and unknown identities or conflicting segment memberships still fail with a specific, payload-free diagnostic. Screening and SAP contracts allow all nine possible planned segments.
4. Select at most 100 non-excluded profiles while preserving group diversity. Planned groups are not admission gates: useful unassigned adjacent trials remain eligible and fill unused capacity. Missing structured fields create uncertainty, not exclusion. Reload selected profiles completely and classify overlapping segments in the existing extraction call. Analysts decide objective-specific membership later.
5. Build one SAP from the approved brief/plan, an ephemeral catalogue of short fields across every selected profile and up to 10 whole profile examples. Deterministic fields are preferred; narrative interpretation uses the remaining semantic-variable budget. Trial Profile 11 investigators are exposed as one deterministic entity list per trial so names remain aligned with site, country, department and public email; every listed person is a PI by contract.
6. Populate one frozen row dataset. Deterministic values are resolved directly; all semantic values for a trial are extracted together from its complete current Trial Profile. Up to 10 extraction requests run concurrently.
7. Run one analyst per main analysis pair, then one reducer over retained clinical sections only. Analysts receive only planned variables and the frozen selected dataset; no new report objectives are introduced.

SAP semantic-variable instructions target 500 compact characters. The executor normalizes whitespace and deterministically bounds any model-produced overrun to the extractor's 600-character contract while preserving both the extraction task and trailing return/missing-value guidance. An overlong instruction therefore cannot stop an otherwise valid paid run.

Deterministic variable types are server-owned catalogue metadata. The SAP may select a
catalogued `profile_path`, but its supplied `kind` is normalized to the observed catalogue
before validation. Paths with mixed runtime types across selected profiles are excluded from
the catalogue. Remaining structural SAP contract failures receive exactly one correction call;
a second invalid plan recovers valid catalogue fields and extraction rules within the same budgets for every approved analysis. Safe logs identify variable name/path and supplied versus
expected kind without profile values or clinical payloads.

Output stays compatible with the shared App/PDF renderer:

```text
final_report.version = 2
final_report.tier = max
```

`analyzedCohort` may also carry the screened-candidate count and selected `exact`/`close`/`adjacent` composition. Existing renderers ignore unknown fields, so the version-2 output contract remains backward compatible.

### Max publication rules

Objective contract v4 asks each shared/deeper analysis pair to examine every nonempty planned group and relevant unassigned trials. Deterministic summaries omit empty groups, count repeated category tags once per trial and avoid duplicating source passages/entities. Analysts briefly compare useful group results, agreements, differences and minority precedents; compatible pooled estimates deduplicate overlapping trial identities.

Private `group_assessments` request a disposition for every group, with group-specific finding references or an objective-specific omission reason. Coverage is checked BEFORE publication pruning: removing N=0 or unsupported findings cannot erase examination. The redundant group trial-ID union is derived from supports. Incomplete coverage requests one correction and then remains advisory; it never raises `MAX_REPORT_GROUP_ANALYSIS_INCOMPLETE`. The dataset audit distinguishes assessment validity from publication status and records missing references, group supports and denominator mismatches. Logs contain advisory codes/counts, never clinical payloads.

The executor allows up to eight useful findings per objective; the App renders every retained Max finding online and in PDF. Public version 2 is unchanged. Supplied numerator identities must be nonempty and a subset of denominator identities; single count/percentage values are checked against them. N=0, zero-frequency categories and empty-group commentary are omitted, while supported continuous values/differences of zero remain valid. SAP reserves compact eligibility qualifiers within the existing semantic budget and extraction preserves exceptions, alternative routes and coherent phase/design distinctions; not stated never means not required.

Every visual value has internal support metadata with actual trial IDs, variables and an optional approved segment. Checks on counts, numerator arithmetic, populated variables, group membership, small samples, named-item support, prose and chart alignment request at most one correction. Unsupported units and stale prose are omitted; these checks never abort Max. Malformed sections recover independently valid findings without guessing metrics. N=0 stays omitted; N<5 requires a directly relevant descriptive precedent. Empty objectives do not cancel siblings. If all findings are omitted, completion preserves the trial overview and dataset with neutral text rather than invented conclusions. Synthesis validation failure falls back to validated section summaries without reanalysis.

No minimum finding count is enforced. Report prose excludes internal/source codes, workflow language and empty-group messages. Max shows the unique total, group counts of at least five and an overlap notice. Support/status remain in the dataset. Models, Flex, per-call ceilings and clinical-data allowances remain unchanged. Candidate filters/screening and Max extraction each permit one exceptional validation correction: filters recover approved seeds/valid supplements; screening retains unresolved identities as uncertain; extraction retains valid facts and nulls. No report-wide retry loop is introduced, but invalid outputs can add bounded correction usage. Public-tool extraction and Light validation remain strict.

### Control-plane boundary

The private `/internal/max-report/start` route launches Max. The six-hour lease excludes documents and permits up to 1,000 filtered IDs, 500 profiles, 500 screening classifications and 100 final extraction trials. Older 100-trial leases retain the legacy workflow. Invalid candidate model output recovers within the expanded workflow, preserving approved seeds and unresolved candidates. Operational access/API failures can still stop a run; authentication, ownership, approved-plan prerequisites, trial identity and resource limits are never bypassed. Successful completion consumes the reservation; system failure leaves it unconsumed.

## Shared output/readability contract

`report_output.py` generates strict schemas from the runtime models for Light selection,
Light/Max objective and synthesis output, and the Max SAP (with scoped enums/budgets).
Public narrative strings have no layout-driven maximum length. Shared writing guidance
targets one takeaway, 2–3 short interpretation sentences, one-sentence item explanations,
brief chart units and one short denominator note. Scientific caveats take precedence.
Internal SAP identifier/extractor limits and report scope, array, finite-number and
chart-alignment rules remain enforced; Light also rejects negative donut values.

Each objective or synthesis shares one correction attempt across structural errors,
Light's existing medical-content gate and optional verbosity editing. The edit receives
the prior draft and original evidence; charts, units, labels, ordering and provenance
must stay exact and quantitative/caveat tokens must be preserved. Unsafe or failed
optional editing retains the valid original, even if still verbose. Light retains its strict
contract behavior; Max recovers independently valid content after a second invalid contract. Completed objectives and the frozen dataset are not recomputed
during these corrections. This is not durable recovery across process restarts.

The App handles lengthy units once below the chart and splits oversized PDF blocks
without deleting text, changing numbers, shrinking fonts or cutting SVG graphics.

## Runtime boundary

New Max runs freeze the complete analyzed Trial Profiles, collected direct and semantic
variables, group membership, definitions and approved plan immediately after population, before objective work. The checkpoint manifest is persisted in `progress.datasetCheckpoint`. A final snapshot adds analytical support and publication audit; a failed final upload preserves the early snapshot. This adds at most one compressed snapshot per run. Checkpoints survive later operational failure, but do not automatically restart failed runs or introduce clinical data into App DB.
The compressed JSONL snapshot is stored by Engine under `report-datasets/v1/`; only its
version, checksum, count and timestamp enter existing report JSON. Light never stores
this dataset. Old reports cannot reconstruct their historical variables.

The private dataset endpoint loads the authoritative completed Max run. On first download,
one isolated child process writes a streaming XLSX and Engine caches it by checksum.
Later downloads reuse that workbook. App authenticates ownership and streams the file.
Exports perform no model calls. Long text uses continuation rows; full nested profiles,
array order, nulls, empty values and high-precision numbers are preserved. Formula-like
source strings remain text. Snapshot upload retries transient failures; a storage outage
marks the dataset unavailable without discarding a valid report. Export errors can be retried.
Snapshots and cached workbooks currently have no automatic expiry; revisit retention as usage grows.

The App creates and owns report runs, plan approval, tier, entitlement and progress state. MCP executes through service-authenticated internal endpoints. Executors accept only `queued` runs; failed and already-running runs are terminal at this launcher and cannot reopen model work. The terminal failure callback retries transient App outages five times with bounded backoff, without model calls. Light and Max still use an in-process async launcher and can be interrupted by a service restart; durable claim/heartbeat/retry execution remains pending.

Light report calls and Max planning, screening, SAP, analyst and reducer calls
recover from temporary Flex-capacity 429s with four total Flex attempts,
`Retry-After`-aware exponential backoff and jitter, then one automatic-tier attempt.
The ordinary Max objective ceiling is 12,000 output tokens: it is a per-call cost and
latency guardrail, not a model context limit, and hidden reasoning tokens also consume
that allowance. If the Responses API explicitly returns `incomplete` with reason
`max_output_tokens`, only that failed call retries once at 24,000. A cancelled or other
transient terminal response retries once at its original ceiling. Content filtering,
invalid requests and quota/billing exhaustion are terminal and are not retried. Logs
include the schema operation, status, incomplete/error reason, usage and OpenAI
response/request IDs; they do not include prompts or clinical payloads.

### Broad-pool source access and rollout

The planner uses the named disease alone as the first group, falling back to another shared dimension only when no disease is named, then adds 2–4 contained subgroups. Every analysis presents supported broad context before meaningful subgroup detail, using stratification when a pooled estimate would mislead. No minimum published count or assumed trial count is forced. Presentation ordering keeps labels, values and support indices aligned; within-group rankings and multi-group differences retain their order. SAP methods remain conditional on actual support within the same 20-variable/per-trial budget. Analysts receive at most 60,000 total characters of verbatim source passages without another model call. Passages and diagnostics remain in Download Dataset. The last objective-completion update activates finalization before the final snapshot upload; saving and synthesis share that active stage.

Deploy Engine migration 041 before this MCP release. Keep the testing cap at 100. Scaling final selection to 300–500 later requires coordinated extractor/lease/support-schema limits; passage input is already capped independently of trial count. More selected trials can increase actual extraction use toward the existing 100-trial ceiling; unchanged ceilings are not a promise of identical runtime cost. No additional model stage, document fetch or infrastructure is introduced.

When deterministic and enriched profiles coexist for one trial, Max retrieval deterministically keeps the enriched content regardless of approval state, then refreshes eligibility/lifecycle from CTIS. Trial IDs remain unique. This prevents unspecified database row order from replacing known endpoints/design with sparse backfill fields.
