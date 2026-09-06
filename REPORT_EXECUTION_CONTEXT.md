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

## `get_profiles` contract used by report selection

`get_profiles` accepts **1–10 trial IDs per call**. A non-empty `sections` list returns exact deterministic Trial Profile 10.0.0 projections; omitted or empty `sections` returns the complete approved profile. There is no section-versus-complete per-call tier.

Controlled sections: `overview`, `population`, `trial_design`, `interventions`, `eligibility`, `objectives`, `endpoints`, `sponsor_and_organizations`, `contacts`, `countries`, `sites`, `documents`, `lifecycle`, `results`.

The public output contract remains unchanged: `profiles`, `unavailable_trial_ids`, `allowance_reached_trial_ids`, `counts`, and `analysis_allowance`. Each returned item still contains `eu_number`, `profile_schema_version`, `approved_at`, and `profile`.

Light has **100 unique profile IDs per analysis**; Max remains 500. Re-reading the same trial with different sections or later as a complete profile is allowance-idempotent.

## Planning and Light eligibility

Step 2 planning remains `gpt-5.6-sol`. It returns 5–7 report categories with evidence-based `maxOnly`; the App applies the separate Light commercial/display limit.

`maxOnly=true` means the category cannot be completed credibly from Trial Profile data alone and needs deeper protocol/document/extraction capability. Published results already stored in Trial Profile are valid Light evidence and are not automatically Max.

## Light Report v3 execution contract

Light executes the first **three** categories with `maxOnly != true`, and each executed objective uses at most the first **three** planned sub-analyses. The approved plan itself may contain more categories/bullets for Max.

### Stage 1 — Sol high evidence selection

One `gpt-5.6-sol` Flex call with **high reasoning** selects exactly 20 relevant EU trials for the whole report. It may use only:
- `filter_trials`
- `get_profiles`

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

One independent `gpt-5.6-terra` Flex call with **high reasoning** runs for each of the three Light objectives.

Each Terra call receives directly in context:
- the target trial/project context;
- the objective and its maximum three planned sub-analyses;
- all **20 complete Trial Profiles** with stable internal aliases `T01`–`T20`.

Objective calls receive **no MCP tool and no other tool**. They cannot discover, replace, remove or add trials. This makes evidence completeness deterministic and removes repeated profile-tool behavior from objective execution.

For each objective:
- exactly one plain-text summary sentence summarizes the objective overall;
- one structured result is returned for each planned sub-analysis, maximum three;
- each sub-analysis uses one simple visual (`stat`, `bar`, or `donut`) with at most five displayed items;
- interpretation is concise;
- named/ranked items may include up to five plain-text entries with value and explanation;
- the objective may contain one decision implication and bounded evidence notes.

Internal provenance remains restricted to aliases `T01`–`T20`. Unknown/out-of-set references are sanitized non-blockingly: invalid references are dropped while report content is retained and `provenance_reference_mismatch` is logged. A report never fails solely because a provenance reference cannot be validated.

### Stage 3 — Sol high final editorial structure

A final `gpt-5.6-sol` call with **high reasoning** receives the completed structured objective sections and no clinical tools. It creates only:
- report title;
- executive summary;
- cross-objective key takeaways;
- closing decision-facing note.

Sol is given a **binding HTML shell/layout contract** that defines the desired report hierarchy, numbering and allowed containers. For safety and consistency, Sol does **not** emit executable HTML. It returns structured fields only; the App renders those fields into the fixed shell.

Binding layout rules:
- objectives are numbered `1.`, `2.`, `3.`;
- sub-analyses are numbered `1.1`, `1.2`, etc.;
- individual ranked items are not numbered;
- objective intro is one plain-text sentence, never a summary card/box;
- ranked items are normal text with a bold item name, not cards;
- decision implication and evidence notes are plain text;
- within objective content, **graphs are the only boxed elements**;
- no boxes inside boxes and no nested card grids;
- each objective has its own graph color theme, with shades of that theme across its sub-analyses; other objectives use different theme colors.

## Final report contract

`report_runs.final_report.version = 2` remains structurally compatible and contains:
- title;
- executive summary;
- key takeaways;
- up to three structured objective sections;
- closing note.

The selected-trial evidence IDs remain internal progress/provenance and are not presented as the report subject.

## Execution lifecycle

The App creates the stable report run and approved-plan snapshot. MCP starts/reuses the bounded `analysis_id`, executes the stages above, and writes progress/final output through the private report-execution endpoint.

Progress is dynamic: trial selection, one step per executed Light objective, then final report preparation. Only one active analysis lease per account is allowed at a time.

## Current implementation limitation

Execution still runs as an in-process async task on the MCP web service. A service restart can interrupt an active run. Before broad production use, move execution to a durable worker/claim-heartbeat-retry loop and revisit the 60-minute lease.
