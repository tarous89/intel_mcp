# Intel MCP — Report Execution Current Context

Last updated: 2026-09-05

> This file is the current source of truth for Intel Agent report execution and supersedes older report-execution statements in `PROJECT_CONTEXT.md` where they conflict. General MCP tool/data-plane rules in `PROJECT_CONTEXT.md` remain authoritative.

## Current scope

Light Report is the free, profile-only report path. Max execution is intentionally separate and is not implemented yet.

Production MCP service:
- `https://mcp.trialagents.com/mcp`
- Render service `srv-da7g4igae00c73bo6oe0`, Frankfurt
- Light Report v2: MCP PR #31 / squash `ff3ac13e241e7ee1aedd1af1493de97abde7b00a`
- Non-blocking provenance hardening: MCP PR #33 / squash `886c47d0952df8575462c2594db7966e0b367f46`
- Section-aware profile retrieval: MCP PR #34 / squash `b75039ca0ed2d13ce908c5888c24a5e8fd979976`
- Current production deploy: `dep-dae9fq142hec73c7g9n0`

## Profile-retrieval capability for the next report iteration

MCP PR #34 is live and adds section-aware `get_profiles` without changing the report runner in this release. The tool supports exact deterministic Trial Profile 10.0.0 projections for up to 100 trial IDs when a non-empty `sections` list is supplied, and complete profiles for up to 20 trial IDs when `sections` is omitted or empty.

The controlled sections are: `overview`, `population`, `trial_design`, `interventions`, `eligibility`, `objectives`, `endpoints`, `sponsor_and_organizations`, `contacts`, `countries`, `sites`, `documents`, `lifecycle`, and `results`. These are field projections of the approved stored profile, not generated cards or summaries.

The paired App control-plane change is live in App PR #78 / squash `733bf38dd4a02ad5a9d336485bf924b1916d94f7`, Render deploy `dep-dae9errm8hqs73cufdh0`, raising the Light unique-profile allowance from 50 to 100. Re-reading the same trial with different sections or later as a complete profile remains allowance-idempotent.

**Important:** the current Light execution stages below are intentionally unchanged by MCP PR #34. Stage 1 still selects one frozen 20-trial evidence set and Stage 2 still analyzes that same set. The 100-candidate section-projection workflow discussed for the next report iteration will be implemented separately after this MCP capability rollout.

## Planning and Max eligibility

Step 2 uses `gpt-5.6-sol`. The planner receives the complete Trial Profile 10.0.0 capability boundary and returns 5–7 report categories with `maxOnly` on each category.

`maxOnly=true` means the category cannot be completed credibly from complete Trial Profile data alone and needs deeper protocol/document/extraction capability. Published results already stored in Trial Profile are valid Light evidence and are not automatically Max. Profile-supported categories are ordered before source-document-only categories.

`maxOnly` is evidence-capability based only. The App separately enforces the Light commercial cap of four categories; any additional otherwise-Light category is also presented as Max. The user sees only the Max badge, not the internal reason.

## Light execution contract

Light executes up to the first four categories with `maxOnly != true`.

### Stage 1 — evidence selection

One `gpt-5.6-terra` Flex call selects exactly 20 relevant EU trials for the report. It may use only:
- `filter_trials`
- `get_profiles`

Light selection has no access to `classify_trials`, `get_documents` or `extract_variables`.

### Stage 2 — objective calls

One independent `gpt-5.6-terra` Flex call runs for each Light category against the same 20-trial evidence set. Each objective may use only `get_profiles`.

Each planned analysis bullet becomes exactly one visual-first sub-analysis. The structured output requires:
- one concise summary sentence per sub-analysis;
- one simple visual per sub-analysis (`stat`, `bar` or `donut`);
- no more than five displayed values/items;
- a short interpretation;
- optional ranked items, each with one sentence explaining why it ranks/matters;
- an objective-level decision implication;
- bounded evidence notes/limitations.

The 20 selected trials are the complete and exclusive evidence set for objective execution. The objective prompt supplies stable aliases `T01`–`T20`; provenance fields are schema-constrained to those aliases and may be empty when a finding cannot be confidently tied to one trial. Aliases are mapped back to the real selected EU trial numbers after generation.

The App control plane independently freezes Light `get_profiles` access to the selected 20-trial set as soon as selection is persisted. During Stage 1, before a selected set exists, profile access remains available for evidence selection. During Stage 2, an out-of-set profile request is not returned to the model and does not consume additional profile allowance. This paired boundary shipped in App PR #73 / squash `005cd1abca44e6c7963e831d8fb52ca3a6ffcb43`.

**Provenance/reference validation is non-blocking.** If objective output still contains an unknown or out-of-set provenance reference, MCP drops only that invalid internal reference, retains the finding/report content, logs `provenance_reference_mismatch`, and continues report generation. A Light Report must never fail solely because a source/provenance reference does not validate against the frozen report trial set. Structural/model/service failures remain ordinary execution failures.

Trial IDs are internal provenance and are not intended as visible report mechanics. Objective prompts prohibit discussion of screening, shortlisting, frozen/selected-trial counts, MCP, tools, calls, allowances or report-generation methodology.

### Stage 3 — final synthesis

A final `gpt-5.6-sol` call receives the completed structured sections and no clinical tools. It creates only the title, executive summary, cross-section takeaways and closing decision-facing note. It must not introduce new facts or discuss report mechanics. The model never emits executable HTML; the App safely renders structured report data.

## Final report contract v2

`report_runs.final_report.version = 2` contains:
- title;
- executive summary;
- key takeaways;
- structured visual-first objective sections;
- closing note.

The public report payload no longer needs the selected-trial summary. Evidence-set IDs remain in internal progress/provenance rather than being presented as the report's subject.

## Execution lifecycle

The App creates the stable report run and approved-plan snapshot. MCP starts/reuses the bounded `analysis_id`, executes the stages above, and writes progress/final output through the private report-execution endpoint.

Progress is dynamic: trial selection, one step per executed Light category, then final report preparation. Light reports are no longer entitlement-count gated; only one active analysis lease per account is allowed at a time.

## Current implementation limitation

Execution still runs as an in-process async task on the MCP web service. A service restart can interrupt an active run. Before broad production use, move execution to a durable worker/claim-heartbeat-retry loop and revisit the 60-minute lease.
