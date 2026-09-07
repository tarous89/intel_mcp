# Intel MCP — Report Execution Current Context

Last updated: 2026-09-07

> Canonical current-state contract for Intel Agent report planning and Light execution. Superseded implementation history belongs in git history.

## Scope

Light is the live Trial-Profile-only report path. Max execution remains separate and is not implemented yet.

Production MCP:
- `https://mcp.trialagents.com/mcp`
- service `srv-da7g4igae00c73bo6oe0`, Frankfurt
- production Engine source = restricted read-only database adapter

## Report planning — Sol

Planning uses `gpt-5.6-sol`, medium reasoning, no tools. The planner receives the user brief, requested insights, optional current plan/revision request and a concise evidence-capability description.

New/revised plans use **`intel_agent_report_plan_v4`**. The planner prompt is one clean current contract rather than accumulated amendments to v3.

### Trial groups

A v4 plan contains **3–5 groups**:

1. one shared Light + Max group;
2. **2–4 Max groups**.

The shared group uses exactly one structured selection dimension:

```text
disease | therapeutic_area | phase | modality | country
```

Selection priority is disease when a meaningful disease is specified, then therapeutic area, then the more informative of phase/modality, with country as fallback. Multiple dimensions must not be combined in the shared group.

`disease` is a real `filter_trials` field. It matches individual persisted approved Trial Profile disease names case-insensitively through `mcp_serving.profile_diseases_v1`. Disease filtering does not infer stage, biomarker, molecular subtype, line of therapy or treatment setting.

Fine-grained disease stage, biomarker/mutation, PD-L1, molecular subtype, line of therapy and multi-dimension combinations belong in Max groups. Max groups may recover the exact target, segment the evidence or add an adjacent comparator. Prefer compact `X vs Y` groups when that is the useful comparison and do not mention ignored dimensions with wording such as `regardless of` or `irrespective of`.

Internal group fields:
- shared: `role=primary`, `maxOnly=false`, one non-null `filterDimension`;
- Max: `role=adjacent`, `maxOnly=true`, `filterDimension=null`.

These role labels are implementation metadata, not user-facing labels.

### Paired analyses

There is no user-facing Objectives layer in v4.

A v4 plan contains **5–7 analysis pairs**. Each pair contains:

1. `sharedAnalysis` — shared Light + Max descriptive work;
2. `maxAnalysis` — deeper decision work.

Shared titles state what will actually be counted, ranked, compared or summarized. They describe the visible output rather than the methodology. Examples: `Most active trial sites`, `Most-used exclusion criteria`, `Observed enrollment in similar trials`, `Most common primary endpoints`.

Max titles state the concrete result/deliverable the deeper analysis gives the user for their own trial, project, target population or rollout. Slightly longer titles are preferred when they make the outcome understandable before expansion. Examples: `Recommended trial sites for your planned study`, `Principal investigators most relevant to your planned trial`, `Exclusion criteria most likely to restrict recruitment in your target population`, `Expected enrollment range for your planned trial`, `Countries most suitable for your planned rollout`.

Do not use abstract consultant-style labels such as `Eligibility strategy fit`, `Enrollment benchmark fit`, `Endpoint strategy fit`, `Country strategy fit`, `Best-fitting trial sites`, or `Operational fit`. The current v4 Pydantic validator rejects `strategy fit`, `benchmark fit`, `best-fitting` / `best fitting`, and `operational fit` in Max titles. Question-style titles are also rejected.

Max analyses still add at least two distinct decision factors: exact clinical fit, segmentation, recency, competition, PI-site relationships, source/protocol detail, variability/robustness, trade-offs or supported prioritization/recommendation.

The v4 schema retains an internal top-level `title` equal to `sharedAnalysis.title` so existing progress/execution interfaces remain stable. It is not another product hierarchy level.

No fixed presentation breadth such as top 5/top 10/top 100 is embedded in the plan.

### Backward compatibility

The current planner emits v4 only. The Pydantic model retains read compatibility for stored v3 plan objects used by existing server/control flows. Legacy v2 execution remains supported by the Light executor's old path.

## Light execution for v4

Light deliberately executes the shared layer only.

### Execution projection

Before execution, an approved v4 plan is projected to:

- the first/shared single-dimension trial group only;
- **all 5–7 shared analyses**;
- no Max trial groups;
- no paired Max analyses.

All shared analysis requirements inform selection of the frozen evidence cohort. Max titles, Max detail and Max group criteria do not cross the Light execution boundary.

### Selection

The existing Sol Light selector is reused with only:

- `filter_trials`
- `get_profiles`

The Light profile/filter allowance remains 100 unique candidates. Sol freezes exactly 20 trials. Because the Light execution view contains only the shared group, selected trials map to that group only.

Internally, the 5–7 shared evidence needs are compacted into three legacy-compatible selection containers so the existing selector helper can consider all of them without receiving Max work. This container shape is not user-facing.

### Evidence bundle

MCP retrieves all 20 complete approved Trial Profiles in bounded batches of 10. The same frozen 20-profile bundle is reused across every shared analysis.

### Shared analysis execution

Each v4 shared analysis runs independently using `gpt-5.6-terra`, high reasoning, Flex, with no MCP tools. The `sharedAnalysis.details` entries are passed as the approved analytical lenses for that row.

The existing structured Light result contract remains for renderer compatibility:
- one short analysis intro sentence;
- 1–N retained sub-analyses within the approved shared details;
- simple stat/bar/donut visuals;
- concise interpretation and optional named items;
- one decision implication;
- bounded evidence notes.

Duplicate-visual and provenance guards remain active.

### Final synthesis

Final synthesis remains `gpt-5.6-sol`, high reasoning, no tools. It produces title, short introduction and closing note only.

Completed Light reports remain `final_report.version = 2` for renderer compatibility. The analyzed-cohort summary contains only the shared trial group and exact frozen 20 trials.

## Legacy v2/v3 execution

Stored v2/v3 plans retain their previous execution projection. New/revised plans use v4 and do not alter already-approved legacy plans.

## Current filter addition

`filter_trials` accepts `diseases` as a structured string-set filter with `contains_any | contains_all | contains_none` semantics. Matching is against persisted approved disease rows and is case-insensitive substring matching per disease name. Negative disease filtering requires known disease data.

No Trial Profile schema/generation change was required; the Engine added the approved-only serving view `mcp_serving.profile_diseases_v1` and the MCP restricted reader receives SELECT access only.

## Current prompt/schema versions

- planner: `intel_agent_report_plan_v4`
- selection: `intel_light_trial_selection_v5`
- Light analysis: `intel_light_objective_v5`
- synthesis: `intel_light_synthesis_v5`

The 2026-09-07 planner refinement changed title semantics/validation only. It did not change the v4 schema shape, Light execution projection, trial counts, allowances, or Max fulfilment state.

## Product/App boundary

The App presentation intentionally shows:
- heading `Trial selection` for trial groups;
- no Light labels;
- no Priority/Adjacent labels;
- no Strong coverage/Source dependent labels;
- shared trial group unlabelled;
- Max trial groups labelled `Max`;
- v4 analysis pairs in one compact continuous list;
- shared row followed immediately by a slightly indented Max row;
- neutral gray Max badge and no yellow Max-row background;
- evidence breadth only inside expanded shared rows: `Evidence scope: 20 selected trials in Light · up to 100 trials in Max.`.

MCP owns plan generation and bounded clinical analysis. App remains authoritative for identity, plan approval, tier/entitlement, report runs and UI.

## Current limitation / deferred work

- Max execution/fulfilment is not implemented.
- Stripe live mode remains blocked until Max fulfilment is ready.
- Durable worker/claim-heartbeat-retry report execution remains future work.
