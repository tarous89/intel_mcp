# Intel MCP — Report Execution Current Context

Last updated: 2026-09-06

> Canonical current-state contract for Intel Agent report planning and Light execution. Superseded implementation history belongs in git history.

## Scope

Light Report is the current profile-only report path. Max execution is separate and not implemented yet.

Production MCP service:
- `https://mcp.trialagents.com/mcp`
- Render service `srv-da7g4igae00c73bo6oe0`, Frankfurt

## Report planning — Sol

Planning uses `gpt-5.6-sol`.

The planner receives only the user brief, requested insights, optional existing plan/revision request, and a concise description of what Trial Profiles can support. It does **not** receive MCP tool mechanics, call limits, section-read rules, or other execution details.

The planner returns:
- 1–4 study cohorts, exactly one Primary;
- 5–7 report categories;
- 1–4 analyses per category;
- `coverage` (`strong` or `source_dependent`);
- `maxOnly`.

### Analysis breadth rule

There is no target analysis count, but one-analysis categories are not the default safe answer.

Before settling on one analysis, Sol must actively consider other useful lenses supported by the Trial Profile data. Relevant dimensions can include disease fit, treatment setting, phase, modality, recency, sponsor diversity, geography, design, population, endpoints, eligibility, site/investigator history and partner relationships.

Keep another analysis when it answers a materially different decision question or uses a meaningfully different measure, comparison or evidence dimension.

**Shared entities do not make analyses redundant.** The same sites, investigators, sponsors or trials may legitimately appear in more than one analysis when a different metric reveals a different decision-relevant insight.

Merge analyses only when they substantially answer the same decision question and lead to the same practical implication, or when both insights can be preserved clearly in one richer result.

One analysis is valid only after checking that no other supported lens adds distinct decision value. Never add filler to reach two, three or four analyses.

## Light versus Max

Light can use approved Trial Profiles, including profile-supported trial identity/sponsor, disease/population/setting, phase/design/interventions, endpoints/eligibility, countries/lifecycle, sites/investigators, partner organisations and structured results when present.

Set `maxOnly=false` when the category can be completed credibly from Trial Profiles alone.

Set `maxOnly=true` only when the category genuinely requires source-document/protocol detail beyond the Trial Profile.

Published results already stored in Trial Profiles remain valid Light evidence.

Profile-eligible Strong categories are ordered first, then profile-eligible Source-dependent categories, then Max categories. The first three profile-eligible objectives become Light.

## Light execution

### Stage 1 — Sol trial selection

One `gpt-5.6-sol` call with high reasoning selects exactly 20 EU trials for the whole report.

The selection call may use only:
- `filter_trials`
- `get_profiles`

Its prompt is intentionally short. It tells Sol to:
1. start from the Primary cohort and broaden into Adjacent cohorts only when useful;
2. build a clinically plausible candidate pool of at most 100 trials;
3. profile-review every final selected trial;
4. choose one coherent 20-trial set that balances target relevance and usefulness across all Light objectives;
5. label each trial `priority` or `adjacent` with no quota.

The user payload contains only:
- analysis ID;
- trial context;
- requested insights;
- study cohorts;
- exclusion summary;
- the three Light objectives.

The redundant full approved plan and duplicated numeric count fields are no longer sent.

### Frozen complete-profile bundle

After selection, the executor retrieves the complete approved Trial Profiles for the frozen 20 trials. The same 20-profile bundle is reused unchanged for every Light objective.

### Stage 2 — Terra objective analysis

Each objective runs as one independent `gpt-5.6-terra` Flex call with high reasoning.

Terra receives directly in context:
- target trial/project context;
- one objective with its 1–4 planned analyses;
- all 20 complete Trial Profiles using aliases `T01`–`T20`.

Terra receives no tools.

The prompt is intentionally compact:
- consider all 20 profiles before cohort-level conclusions;
- use only supplied evidence;
- planned analyses are candidate lenses, not mandatory slots;
- return 1 to the number planned;
- before collapsing to one, test whether each planned lens produces a materially different decision question, metric/comparison or practical implication;
- shared top entities are not duplication by themselves;
- merge only when decision question and practical implication substantially overlap;
- do not invent analyses outside the approved objective.

Each retained sub-analysis uses one simple `stat`, `bar` or `donut` visual with at most five items, plus concise interpretation and optional named-item context.

Terra payload no longer includes EU trial IDs or profile schema versions because those are not needed for analysis. Provenance uses only `T01`–`T20` aliases and is mapped back internally after the model call.

### Exact duplicate safety guard

A deterministic post-model guard compares visual kind, unit, labels and values. If two returned sub-analyses contain the exact same chart data, only the first is kept and useful unique item/provenance context is merged into it.

This guard prevents literal duplicate charts without suppressing genuinely different analyses that happen to involve the same entities.

### Stage 3 — Sol final synthesis

A final `gpt-5.6-sol` call with high reasoning receives the completed structured objective sections and no tools.

It returns only:
- report title;
- one short introductory paragraph;
- one short decision-facing closing note.

The HTML/layout shell is no longer sent to Sol. The App already owns layout and numbering, so sending the shell was redundant context.

Sol must not introduce new facts or repeat the objectives as a separate takeaway section.

## Final report contract

`report_runs.final_report.version = 2` remains structurally compatible.

New reports contain:
- title;
- short introduction in the existing `executiveSummary` compatibility field;
- up to three Light objective sections;
- 1–4 retained analyses per objective when genuinely distinct;
- closing note.

There is no `keyTakeaways` generation for new reports.

Objectives, sub-analyses and ranked items are not numbered. The App renderer controls typography, colors and layout; graphs are the only boxed elements inside objective content.

## Prompt versions after 2026-09-06 cleanup

- planner schema: `intel_agent_report_plan_v2`
- selection schema: `intel_light_trial_selection_v4`
- objective schema: `intel_light_objective_v5`
- synthesis schema: `intel_light_synthesis_v5`

The prompt cleanup is implemented in MCP PR #41.

## Current operational limitation

Execution still runs as an in-process async task on the MCP web service. A service restart can interrupt an active run. Durable worker/claim-heartbeat-retry execution remains future work.