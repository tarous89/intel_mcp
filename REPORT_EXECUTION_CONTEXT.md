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

New/revised plans use **`intel_agent_report_plan_v4`**. The planner prompt is maintained as one clean current contract; product changes should rewrite stale prompt language rather than append conflicting rules.

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

Fine-grained stage, biomarker/mutation, PD-L1, molecular subtype, line of therapy and multi-dimension combinations belong in Max groups. Max groups may recover the exact target, segment evidence or add an adjacent comparator. Prefer compact `X vs Y` groups when that is the useful comparison. Do not mention ignored dimensions with `regardless of` / `irrespective of` wording.

Internal group fields:
- shared: `role=primary`, `maxOnly=false`, one non-null `filterDimension`;
- Max: `role=adjacent`, `maxOnly=true`, `filterDimension=null`.

These role labels are implementation metadata, not user-facing labels.

### Paired analyses and action verbs

There is no user-facing Objectives layer in v4.

A v4 plan contains **5–7 analysis pairs**. Each pair contains:

1. `sharedAnalysis` — shared Light + Max descriptive work;
2. `maxAnalysis` — deeper decision work.

Shared titles intentionally use direct retrieval/calculation verbs and should normally begin with:

```text
List · Name · Count · Rank · Report · Calculate · Summarize · Show · Compare · Collect
```

These titles communicate straightforward evidence retrieval, counting, ranking or calculation. `Quantify` and `Describe` are excluded from the shared title vocabulary. High-interpretation verbs should not be used for shared titles.

Examples:
- `Rank trial sites by documented activity`
- `Name the most active principal investigators`
- `List the most-used exclusion criteria`
- `Report observed enrollment in similar trials`
- `Calculate observed country timelines`

Max titles intentionally use interpretation/decision verbs and should normally begin with:

```text
Analyze · Assess · Evaluate · Prioritize · Recommend · Estimate · Determine · Identify · Match · Synthesize
```

The verb must reflect the actual deliverable; `Analyze` should not be repeated mechanically. `Benchmark` is not used as a Max title verb.

Examples:
- `Prioritize trial sites for your planned study`
- `Identify principal investigators most relevant to your planned trial`
- `Assess exclusion criteria likely to restrict recruitment in your target population`
- `Estimate enrollment range for your planned trial`
- `Recommend countries for your planned rollout`

Generic Max labels remain invalid, including `strategy fit`, `benchmark fit`, `best-fitting` / `best fitting`, and `operational fit`. Question-style titles are also rejected.

Max analyses still add at least two distinct decision factors: exact clinical fit, segmentation, recency, competition, PI-site relationships, source/protocol detail, variability/robustness, trade-offs or supported prioritization/recommendation.

The v4 schema retains an internal top-level `title` equal to `sharedAnalysis.title` so existing progress/execution interfaces remain stable. It is not another product hierarchy level.

No fixed presentation breadth such as top 5/top 10/top 100 is embedded in the plan.

### Backward compatibility

The current planner emits v4 only. The Pydantic model retains read compatibility for stored v3 plan objects used by existing server/control flows. Legacy v2 execution remains supported by the Light executor's old path.

## Light execution for v4

Light deliberately executes the shared layer only.

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

### Evidence bundle and shared analysis execution

MCP retrieves all 20 complete approved Trial Profiles in bounded batches of 10. The same frozen 20-profile bundle is reused across every shared analysis.

Each v4 shared analysis runs independently using `gpt-5.6-terra`, high reasoning, Flex, with no MCP tools. The `sharedAnalysis.details` entries are passed as the approved analytical lenses for that row.

The existing structured Light result contract remains for renderer compatibility, including duplicate-visual and provenance guards.

### Final synthesis

Final synthesis remains `gpt-5.6-sol`, high reasoning, no tools. It produces title, short introduction and closing note only.

Completed Light reports remain `final_report.version = 2` for renderer compatibility. The analyzed-cohort summary contains only the shared trial group and exact frozen 20 trials.

## Current prompt/schema versions

- planner: `intel_agent_report_plan_v4`
- selection: `intel_light_trial_selection_v5`
- Light analysis: `intel_light_objective_v5`
- synthesis: `intel_light_synthesis_v5`

The 2026-09-07 verb refinement changed planner language/title semantics only. It did not change the v4 schema shape, Light execution projection, trial counts, allowances, or Max fulfilment state.

## Product/App boundary

The App presentation intentionally shows:
- `Trial selection` and `Analyses` headings;
- scope tags at the section level (`Light · up to 20 trials`, `Max · up to 100 trials`, plus dynamic analysis totals);
- no Light/Priority/Adjacent/coverage row labels;
- shared rows unbadged because they belong to both tiers;
- Max-exclusive rows labeled with a green `Max only` badge;
- all analysis rows in one equal-alignment list box with no Max indentation or pair/objective separators.

The App's customer-facing workspace unit is called **Report** (`New report`, `Reports`, `Report N`), while internal `projectId`/project records remain unchanged for compatibility.

MCP owns plan generation and bounded clinical analysis. App remains authoritative for identity, plan approval, tier/entitlement, report runs and UI.

## Current limitation / deferred work

- Max execution/fulfilment is not implemented.
- Stripe live mode remains blocked until Max fulfilment is ready.
- Durable worker/claim-heartbeat-retry report execution remains future work.
