# Intel MCP — Report Execution Current Context

Last updated: 2026-09-06

> This file is the current source of truth for Intel Agent report execution and supersedes older report-execution statements in `PROJECT_CONTEXT.md` where they conflict. General MCP tool/data-plane rules in `PROJECT_CONTEXT.md` remain authoritative.

## Current scope

Light Report is the free, profile-only report path. Max execution is intentionally separate and is not implemented yet.

Production MCP service:
- `https://mcp.trialagents.com/mcp`
- Render service `srv-da7g4igae00c73bo6oe0`, Frankfurt
- Light Report v2 baseline: MCP PR #31 / squash `ff3ac13e241e7ee1aedd1af1493de97abde7b00a`
- Non-blocking provenance hardening: MCP PR #33 / squash `886c47d0952df8575462c2594db7966e0b367f46`
- Section-aware profile retrieval: MCP PR #34 / squash `b75039ca0ed2d13ce908c5888c24a5e8fd979976`
- Unified ten-profile call limit: MCP PR #35 / squash `f3fa55b078f21d43b2a54cf9e34b2a4cfc5c127c`
- MCP contract/documentation coherence audit: MCP PR #36 / squash `4a91f4b4352cd1e7064deedf6212f41383fd1015`
- Light Report v3 execution: MCP PR #37 / squash `ad87d301ab33371dfb07bbae915d438d5ec51894`
- Coverage-prioritized Light execution: MCP PR #38 / squash `a61e84a3b994c2a082895cdf1fb0033aad77a087`
- Coverage-prioritized Report-plan output: MCP PR #39 / squash `5b7084a96de8c91df6e96fdc896b3364c374a333`
- Insight-compression / non-overlap contract: MCP PR #40
- Current production deploy before PR #40: `dep-daeklh3bc2fs73cegu60`

## `get_profiles` contract used by report selection

`get_profiles` accepts **1–10 trial IDs per call**. A non-empty `sections` list returns exact deterministic Trial Profile 10.0.0 projections; omitted or empty `sections` returns the complete approved profile. There is no section-versus-complete per-call tier.

Controlled sections: `overview`, `population`, `trial_design`, `interventions`, `eligibility`, `objectives`, `endpoints`, `sponsor_and_organizations`, `contacts`, `countries`, `sites`, `documents`, `lifecycle`, `results`.

The public output contract remains unchanged: `profiles`, `unavailable_trial_ids`, `allowance_reached_trial_ids`, `counts`, and `analysis_allowance`. Each returned item still contains `eu_number`, `profile_schema_version`, `approved_at`, and `profile`.

Light has **100 unique profile IDs per analysis**; Max remains 500. Re-reading the same trial with different sections or later as a complete profile is allowance-idempotent.

## Planning and Light eligibility

Step 2 planning remains `gpt-5.6-sol`. It returns 5–7 report categories with evidence-based `maxOnly` and `coverage`.

### Planner objective quality and distinctness gate

Every planned category and analysis must satisfy all of the following:

1. **Direct user utility:** it directly answers the requested insight or materially supports the decision the user is trying to make. Generic benchmarking, landscape review or adjacent analysis is omitted unless it advances that query.
2. **Evidence answerability:** the requested result can actually be supported by the evidence available to the relevant tier. The planner must not promise inaccessible facts, unsupported causal conclusions or rankings that the available Trial Profile/document evidence cannot establish.
3. **Concrete output:** the analysis implies an answer the report can deliver, such as a count, rate, distribution, ranking, timeline, shortlist, evidence-backed option or recommendation, rather than a vague research activity.
4. **Graph-first when natural:** quantitative, graph-ready outputs are preferred whenever the evidence supports them. Do not invent a meaningless metric solely to force a chart.
5. **Incremental value / compression:** each analysis after the first must add a genuinely different decision question, measure/outcome, comparison unit, evidence dimension or analytical method. Different wording is not sufficient. If two proposed analyses can be represented clearly in one richer result without losing interpretability, they are merged.

Each category contains **1–4 planned analyses, with no target count**. One is a complete category when further analyses would only repeat the same evidence, entities, denominator, graph or practical implication. The planner performs a pairwise overlap check before returning the plan and rewrites, merges or removes overlapping bullets rather than filling slots.

This gate is domain-agnostic: it applies to Sites, Endpoints, Eligibility, Countries, Investigators and every other objective. It applies equally to new plans and revisions.

`maxOnly=true` means the category cannot be completed credibly from Trial Profile data alone and needs deeper protocol/document/extraction capability. Those categories are always Max regardless of coverage or original plan position. Published results already stored in Trial Profile are valid Light evidence and are not automatically Max.

New and revised plans are normalized into the same stable order used by the App and Light executor:
1. profile-eligible (`maxOnly != true`) objectives with `coverage=strong`, preserving planner order within that bucket;
2. profile-eligible objectives with `coverage=source_dependent`, preserving planner order within that bucket;
3. planner-declared `maxOnly=true` objectives, which remain outside Light.

The first **three** profile-eligible objectives after this prioritization become Light. This prevents an earlier Source-dependent objective from consuming a Light slot while a later Strong-coverage objective is available. `maxOnly` remains evidence-capability based only and is never set because of count or position.

## Light Report v4 analysis-compression execution contract

Light still executes up to three coverage-prioritized profile-eligible objectives. Each objective may carry **1–4 planned analyses**. The approved stored plan may contain more categories for Max; execution prioritization does not mutate the stored plan object.

The number of planned analyses is now an upper bound on scope, not a required number of output blocks. This is intentional: redundancy can become visible only after the actual evidence is loaded.

### Stage 1 — Sol high evidence selection

One `gpt-5.6-sol` Flex call with **high reasoning** selects exactly 20 relevant EU trials for the whole report. It may use only:
- `filter_trials`
- `get_profiles`

Before the model call, the executor builds a stable prioritized execution view of the approved plan using the same Light rules above. Both `light_objectives` and the Sol selector therefore receive the same three Strong-first Light objectives.

Selection workflow:
1. use structured filtering across the Primary group first, then Adjacent groups where useful;
2. build a clinically plausible candidate pool of up to **100 unique trials**; fewer is valid when the evidence space is smaller;
3. inspect objective-relevant Trial Profile sections for candidates with `get_profiles` in batches of up to 10;
4. keep retrieving the sections needed to distinguish candidates until the best overall 20 can be chosen;
5. every final selected trial should have profile-level review rather than being selected from the lean filter row alone;
6. optimize the final cohort for target-study relevance and collective usefulness across all three Light objectives.

Selection has no access to `classify_trials`, `get_documents` or `extract_variables`.

### Frozen complete-profile bundle

After selection is persisted, the App control plane freezes profile authorization to those 20 trial IDs. MCP orchestration then retrieves the **complete 20 approved Trial Profiles exactly once**, in two bounded Engine-read batches of 10.

This orchestration read still goes through the ordinary App `profile-access` authorization. Selection-time section reads and the later complete read are allowance-idempotent for the same trial ID.

The complete 20-profile bundle is then reused unchanged for every objective model call.

### Stage 2 — Terra high objective analysis, no MCP

One independent `gpt-5.6-terra` Flex call with **high reasoning** runs for each Light objective.

Each Terra call receives directly in context:
- the target trial/project context;
- the objective and its **1–4 planned analysis lenses**;
- all **20 complete Trial Profiles** with stable internal aliases `T01`–`T20`.

Objective calls receive **no MCP tool and no other tool**. They cannot discover, replace, remove or add trials. This makes evidence completeness deterministic and removes repeated profile-tool behavior from objective execution.

The objective model treats planned analyses as approved scope, not mandatory slots. It returns between **1 and the number planned** after comparing the actual evidence. It must consolidate prompts that would substantially repeat the same evidence, graph, top entities, denominator or decision implication. It is explicitly valid to return one result when one information-dense result captures all non-redundant value available for that objective.

For each retained result:
- exactly one plain-text summary sentence summarizes the objective overall;
- each retained sub-analysis uses one simple visual (`stat`, `bar`, or `donut`) with at most five displayed items;
- related context should be packed into labels, values, notes, interpretation or named-item explanations when readable rather than split into another overlapping graph;
- interpretation is concise;
- named/ranked items may include up to five plain-text entries with value and explanation;
- the objective may contain one decision implication and bounded evidence notes.

A deterministic post-model safety guard compares visual kind, unit, labels and values. If two returned sub-analyses contain the **exact same chart data**, only the first result is kept; useful unique named-item context and provenance from the duplicate are merged into it. This guarantees the concrete repeated-graph failure cannot reach the rendered report even if semantic consolidation is missed by the model.

Internal provenance remains restricted to aliases `T01`–`T20`. Unknown/out-of-set references are sanitized non-blockingly: invalid references are dropped while report content is retained and `provenance_reference_mismatch` is logged. A report never fails solely because a provenance reference cannot be validated.

### Stage 3 — Sol high final editorial structure

A final `gpt-5.6-sol` call with **high reasoning** receives the completed structured objective sections and no clinical tools. It creates only:
- report title;
- one short introductory paragraph;
- closing decision-facing note.

There is **no executive-takeaways section**. Sol is given a binding shell/layout contract, but it does not emit executable HTML; it returns structured fields and the App owns the renderer.

Binding layout rules:
- objectives are **not numbered**;
- sub-analyses are **not numbered**;
- individual ranked items are not numbered;
- objective intro is one plain-text sentence, never a summary card/box;
- ranked items are normal text with differentiated name/value formatting, not cards;
- decision implication and evidence notes are plain text;
- within objective content, **graphs are the only boxed elements**;
- no boxes inside boxes and no nested card grids;
- each objective has its own graph color theme, with shades of that theme across its retained analyses; other objectives use different theme colors.

## Final report contract

`report_runs.final_report.version = 2` remains structurally compatible. New reports contain:
- title;
- short introduction in the existing `executiveSummary` compatibility field;
- up to three structured objective sections, each with 1–4 non-redundant retained analyses;
- closing note.

New reports no longer generate `keyTakeaways`. The App renderer remains tolerant of that legacy field on older stored reports but does not need it for current output.

The selected-trial evidence IDs remain internal progress/provenance and are not presented as the report subject.

## Execution lifecycle

The App creates the stable report run and approved-plan snapshot. MCP starts/reuses the bounded `analysis_id`, applies coverage-prioritized Light objective selection, executes the stages above, and writes progress/final output through the private report-execution endpoint.

Progress is dynamic: trial selection, one step per executed Light objective, then final report preparation. Only one active analysis lease per account is allowed at a time.

## Current implementation limitation

Execution still runs as an in-process async task on the MCP web service. A service restart can interrupt an active run. Before broad production use, move execution to a durable worker/claim-heartbeat-retry loop and revisit the 60-minute lease.
