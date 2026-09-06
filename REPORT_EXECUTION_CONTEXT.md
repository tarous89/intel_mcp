# Intel MCP — Report Execution Current Context

Last updated: 2026-09-06

> Canonical current-state contract for Intel Agent report planning and Light execution. Superseded implementation history belongs in git history.

## Scope

Light is the current profile-only report path. Max execution remains separate and is not implemented yet.

Production MCP:
- `https://mcp.trialagents.com/mcp`
- service `srv-da7g4igae00c73bo6oe0`, Frankfurt

## Report planning — Sol

Planning uses `gpt-5.6-sol` with medium reasoning and no tools. The planner receives only the user brief, requested insights, and optional current plan/revision request plus a concise evidence-capability description.

New/revised plans use **`intel_agent_report_plan_v3`**.

### Trial groups

A v3 plan has **3–5 groups**:

1. one shared Light + Max group first;
2. **2–4 Max-only groups** after it.

The shared group must be realistically selectable with broad structured filtering alone. It should be as close as possible to the requested study population without pretending that fine-grained biomarker, disease-stage, line-of-therapy or protocol details are simple structured filters when they are not.

The Max groups are chosen dynamically. Useful strategies include deeper matching to the exact requested population, clinically meaningful segmentation, isolating one component of the request, or adding an adjacent comparator. These are options, not fixed group categories.

Internal fields:
- shared group: `role=primary`, `maxOnly=false`;
- later groups: `role=adjacent`, `maxOnly=true`.

Those role labels are implementation metadata and are not meant for user-facing display.

### Objectives and analyses

A v3 plan has **5–7 objectives**. Every objective contains **3–5 analyses**:

1. first analysis = shared Light + Max descriptive analysis;
2. next **2–4 analyses = Max**.

The first analysis is a direct evidence summary such as a count, rank, distribution, frequency or observed timeline comparison that can be produced from Trial Profiles.

The Max analyses add decision depth through deeper matching, clinically relevant segmentation, competition, recency, disease/phase/modality fit, PI-site relationships, protocol/source detail, robustness/variation, trade-offs, or an evidence-supported shortlist/recommendation where appropriate.

Max analyses must not simply restate the first analysis. The planner uses 2 Max analyses when sufficient and 3–4 only when each contributes distinct value. No fixed display breadth such as top 5/top 10 is written into the plan.

The old category-level `coverage` and objective-level `maxOnly` planning model is not used for v3.

### Backward compatibility

Stored v2 plans remain executable/readable. The v3 planner does not rewrite stored v2 plans unless the user requests a new/revised plan.

## Light execution for v3

Light intentionally demonstrates the evidence without performing Max work.

### Execution projection

Before execution, a v3 approved plan is projected to:
- **first/shared trial group only**;
- **first five objectives only**;
- **first analysis only** from each of those objectives.

The remaining trial groups, analyses and objectives stay in the approved plan as Max promises and are never executed by the Light path.

### Selection

The existing Sol Light selector is reused with only the shared group exposed to it. It may use only:
- `filter_trials`
- `get_profiles`

The normal Light profile allowance remains 100 unique profiles. Sol freezes exactly 20 final trials. Since v3 Light selection receives only the shared group, every selected trial maps to `cohort_index=0` / the primary internal role.

### Evidence bundle

After selection, MCP retrieves all 20 complete approved Trial Profiles in two bounded batches of 10. The same frozen profile bundle is reused for every Light objective.

### Objective analysis

The first analysis from each of the first five objectives is executed independently using `gpt-5.6-terra`, high reasoning, Flex. Terra receives the same 20 complete profiles and no tools.

The current objective output contract remains:
- one objective intro sentence;
- one retained sub-analysis for v3 Light because only one analysis is approved for Light;
- simple stat/bar/donut visual;
- concise interpretation;
- optional named items;
- one decision implication;
- bounded evidence notes.

Existing duplicate-visual/provenance guards remain in place.

### Final synthesis

Final synthesis remains `gpt-5.6-sol`, high reasoning, no tools. It produces only title, short introduction and closing note.

The completed report remains `final_report.version = 2` for renderer compatibility.

The analyzed-cohort summary for v3 Light is generated from the Light execution view, so it shows only the shared trial group and the exact 20 selected trials.

## Legacy v2 Light execution

Legacy v2 plans keep their previous execution behavior:
- coverage/maxOnly prioritization;
- first three profile-eligible objectives;
- legacy planned analysis lists;
- legacy multi-cohort selection where applicable.

This protects existing approved projects while v3 changes only new/revised plans.

## Current prompt/schema versions

- planner: `intel_agent_report_plan_v3`
- selection: `intel_light_trial_selection_v5`
- objective: `intel_light_objective_v5`
- synthesis: `intel_light_synthesis_v5`

The v3 planner prompt was rewritten from scratch as one current contract instead of adding conditions to the old Priority/Adjacent/coverage rules.

## Product boundary

The current App presentation intentionally shows:
- no Light labels;
- no Priority/Adjacent labels;
- no Strong coverage/Source dependent labels;
- only Max tags on Max groups and Max analyses.

MCP owns plan generation and bounded analysis execution. App remains authoritative for identity, plan approval, tier/entitlement, report runs and UI.

## Current limitation / deferred work

- Max execution/fulfilment is not implemented.
- Stripe live mode remains blocked until Max fulfilment is ready.
- Durable worker/claim-heartbeat-retry report execution remains future work.
