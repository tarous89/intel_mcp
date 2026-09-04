# Intel MCP — Report Execution Current Context

Last updated: 2026-09-04

> This file is the current source of truth for Intel Agent report execution and supersedes older report-execution statements in `PROJECT_CONTEXT.md` where they conflict. General MCP tool/data-plane rules in `PROJECT_CONTEXT.md` remain authoritative.

## Current scope

Light Report v1 is implemented and live for product testing. Max Report execution is intentionally not implemented yet.

Production MCP service:
- `https://mcp.trialagents.com/mcp`
- Render service `srv-da7g4igae00c73bo6oe0`, Frankfurt
- Light execution shipped in MCP PR #28, squash `2b8b35c3f3b4d1ad61433f0e5c0b54f29216c87c`
- Deep document/classification reliability fixes shipped in MCP PR #29, squash `8e7930ee3abc91002a86ca6cab16d41335027708`
- Terra Flex report runtime shipped in MCP PR #30, squash `fa1673d78b37305c2726c848d830c49e711f37c5`
- Current production deploy: `dep-dadbjmrncjis738nu540`
- MCP CI run #69 passed

## Light Report v1 execution contract

A Light Report uses exactly four report categories: the first four `reportSections` in the approved Report-plan v2 payload. The user-facing plan itself remains the full compact plan; package limits determine execution depth.

All Step 3 report-generation model work runs on `gpt-5.6-terra` with Responses API `service_tier=flex`:
- trial-selection orchestration;
- the four objective-analysis calls;
- final report synthesis;
- `classify_trials` Terra workers;
- `extract_variables` Terra workers.

The Step 2 Report-plan generator is intentionally unchanged and remains a separate planning call.

### Stage 1 — trial selection

One `gpt-5.6-terra` Flex Responses API request selects exactly 20 unique trials for the complete Light report. The selected set is frozen and reused by every analysis category.

The selection call receives the approved plan, full brief/context, requested insights, four Light report categories, and an active `analysis_id`.

It may use only these remote MCP tools:
- `filter_trials`
- `classify_trials`
- `get_profiles`

It must not use document text or variable extraction during selection. It is instructed to start with deterministic database filtering, use semantic classification/profile review as useful, and choose the 20 trials that collectively make the four requested analyses strongest. Relevance and objective usefulness are both considered. Objective usefulness may outweigh small similarity differences, but clearly irrelevant trials must not be included.

The selected 20 are labeled `priority` or `adjacent` according to which approved plan group they best represent. There is no quota for either label and no backup/reserve list.

Light server-side allowances remain authoritative: up to 100 unique filtered trial IDs, 25 classified trials, and 50 unique profiles across the analysis lease.

### Stage 2 — four objective calls

One separate `gpt-5.6-terra` Flex call runs for each of the four report categories. All four receive the same frozen 20 trial IDs. They cannot discover, replace, add, or remove trials.

Objective calls may use only:
- `get_profiles`
- `get_documents`
- `extract_variables`

Profiles are the main evidence source. Documents/extraction are used only when the requested analysis genuinely requires detail not established by the profile. Existing Light document/extraction allowances remain shared across the entire report run.

`classify_trials` and `extract_variables` also use `gpt-5.6-terra` on Flex processing. Their production service-tier environment values are explicitly set to `flex`, and the code defaults to Flex if those variables are absent.

Each objective returns strict structured data containing:
- title and overview;
- evidence-linked findings;
- a supported implication/recommendation when warranted;
- chart datasets for substantial quantitative findings when useful;
- limitations.

Findings may cite only the frozen selected trial IDs. Missing evidence stays missing. Causal delay/recruitment/site-performance explanations require explicit source evidence. Do not call sites/CROs/partners “best” without validated quality evidence.

### Stage 3 — final synthesis

A final `gpt-5.6-terra` Flex call receives only the frozen selection and four completed structured section outputs. It has no clinical MCP tools. It creates the report title, executive summary, cross-section key takeaways, and closing note without introducing new facts, numbers, trials, or recommendations.

The App safely renders the structured report online. Full production HTML/PDF artifact generation and report-ready notification delivery are not part of this first Light canary.

## MCP deep-evidence reliability

The first Light report exposed two independent MCP failures, now fixed in PR #29:

- `classify_trials`: legacy `standard` service-tier configuration produced invalid Responses API requests. Valid service tiers are now used; report workers run Flex.
- `get_documents` / `extract_variables`: document retrieval previously joined two security-barrier serving views and could exceed the restricted reader's 15-second statement timeout. Deep reads now resolve the document identity first and then fetch extracted text by exact `document_id`.

Regression tests cover the Terra request tier and the two-stage document/extraction lookup paths.

## Execution lifecycle

The App creates the stable report run and approved plan snapshot. MCP starts/reuses the bounded `analysis_id`, executes the stages above, and writes progress/final output back through the App's private service-authenticated report-execution endpoint.

Progress steps are:
1. Finding the best 20 trials
2. Analyzing objective 1
3. Analyzing objective 2
4. Analyzing objective 3
5. Analyzing objective 4
6. Preparing final report

The App persists progress in `report_runs.progress` and the final structured output in `report_runs.final_report`. Successful completion consumes the reserved Light entitlement. System failure cancels the active analysis lease and restores the reserved Light entitlement.

An active analysis lease is reusable only for the same `report_run_id`; another active report for the same user returns `ANOTHER_ANALYSIS_ACTIVE`.

## Canary implementation limitation

For the first Light-quality test, report execution is started as an in-process async task in the MCP web service through protected route `POST /internal/light-report/start`. This is adequate for a controlled canary but is not the final durable worker architecture: a service restart during execution can interrupt the task. Before broad production use, move execution to a dedicated durable worker/claim-heartbeat-retry loop and revisit the current 60-minute lease duration.

No paid report was automatically generated as part of deployment validation. The next validation step is a user-initiated Light Report from the live App so trial-selection quality, tool usage, report quality, runtime, and cost can be inspected before Max is built.
