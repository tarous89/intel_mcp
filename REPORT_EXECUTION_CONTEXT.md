# Intel MCP — Report Execution Current Context

Last updated: 2026-09-08

This is the source of truth for report planning and Light execution. Light is live; Max execution is not implemented.

## Report-plan v4

Planning uses `gpt-5.6-sol`, medium reasoning, strict structured output and no MCP tools. New/revised plans are v4; stored v2/v3 plans remain compatible.

### Trial groups

Every v4 plan has one shared Light + Max group and 2–4 Max-only groups. The shared group uses exactly one supported dimension:

```text
disease | therapeutic_area | phase | modality | country
```

Disease is backed by persisted approved Trial Profile disease names. Stage, biomarker, subtype, line of therapy, treatment setting and multi-dimension combinations belong to Max-only groups.

### Analysis pairs

Every plan has 5–7 pairs, each containing one shared analysis and one deeper Max analysis. There is no user-facing Objectives layer.

Shared titles normally begin with direct evidence verbs such as `List`, `Name`, `Count`, `Rank`, `Report`, `Calculate`, `Summarize`, `Show`, `Compare` or `Collect`. Max titles normally begin with decision verbs such as `Analyze`, `Assess`, `Evaluate`, `Prioritize`, `Recommend`, `Estimate`, `Determine`, `Identify`, `Match` or `Synthesize`.

Question titles, hard-coded result breadth and generic labels such as `strategy fit`, `benchmark fit`, `best fitting` and `operational fit` are rejected. Max must add at least two genuine decision factors rather than restating the shared analysis.

Every planned analysis must be medical, clinical-development or trial-operational. Database coverage, data completeness, missingness, field availability, documentation rates and “how many trials reported a field” are prohibited. When the available evidence cannot support the requested lens, the planner must choose the closest medically relevant alternative that can be performed.

Step 1 suggested analyses do not include planned sample size versus actual enrollment.

## Light projection and cohort

Light receives only:

- the shared single-dimension trial group;
- all 5–7 shared analyses;
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

The copy may describe future Max value across up to 1,000 trials but must not claim Max work or outcomes already exist.

## Final report

Sol/high/Flex final synthesis writes only the title, short introduction and closing note. It does not rewrite sections or upgrade copy.

The App is responsible for presentation:

- the only database/evidence-base mention appears once, directly after the title and introduction;
- that band states the overall number of trials analyzed and a high-level selection description;
- no per-objective completeness, coverage or “N of 20 reported” messaging is shown;
- per-analysis decision-implication blocks are replaced by the two upgrade sentences;
- completed output remains `final_report.version = 2` for renderer compatibility.

Prompt/schema names:

```text
planner:   intel_agent_report_plan_v4
selection: intel_light_trial_selection_v5
analysis:  intel_light_objective_v8
synthesis: intel_light_synthesis_v5
```

## Runtime boundary

The App creates and owns report runs, plan approval, tier, entitlement and progress state. MCP executes through service-authenticated internal endpoints. Current execution is in-process async and can be interrupted by a service restart; durable worker execution remains pending.

