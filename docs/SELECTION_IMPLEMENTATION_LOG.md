# Deterministic selection implementation log

Started 2026-10-06. Scope: validate the current evidence contracts and implement deterministic CRO, site and PI selection tools. ChatGPT skill/plugin packaging is a later stage, explicitly deferred by the owner.

## 1. Repository and contract validation — in progress

Source baseline: intel_mcp 21231284009903e8be99950dfb4174fb6b9b469e; reviewed App aggregation and ranking on main.

Learnings:
- Existing MCP has OAuth and a restricted approved-only Engine reader; App owns identity and entitlements.
- Combined App admits stored profiles across approval states. Standalone MCP admits approved profiles only. These populations must not be silently mixed.
- App maps 15 CRO functions to distinct trial IDs. Current CRO default order is total trial count; site/PI ordering prioritizes disease, phase and modality counts.
- Operational findings belong to trials, not automatically to a provider.
- Existing start_analysis requires an App-created report run; current legacy allowances are not a new selection entitlement.

Decisions:
- Preserve approved-only serving and all authorization boundaries.
- Standard selection performs no backend LLM calls, no ingestion or clinical writes.
- Rank complete eligible cohorts before applying the top-10 output limit; never return a silently sampled global ranking.
- Keep direct/related/broader cohorts disjoint and report exact distinct-trial counts.
- Version the selection contract and record source fingerprints.

## 2. Deterministic selection implementation — pending

Build validated criteria, matching, aggregation, role-aware ranking and evidence retrieval; reuse proven identity logic where appropriate. Record concrete interface and access decisions after inspecting current code.

## 3. Verification and iteration — pending

Test compound criteria, function attribution, duplicates, unknowns, repeatability, authorization, complete-cohort handling, and absence of model calls. Record executed checks and unresolved live validation separately.

## 4. ChatGPT workflow packaging — deferred

Start only after the deterministic tools are ready and the owner starts this stage.
