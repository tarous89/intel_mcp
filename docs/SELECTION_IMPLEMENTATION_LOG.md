# Deterministic selection implementation log

Started 2026-10-06. Owner scope: first validate and build deterministic CRO/site/PI selection tools; package ChatGPT workflows only in a later stage.

## 1. Source and access contract validation — code and live aggregate audit complete

Inspected MCP baseline `21231284009903e8be99950dfb4174fb6b9b469e`, App `combined_dataset_tables.py`, `combined_site_ranking.py`, table indexes, profile/filter authorization routes, and Engine `035_mcp_serving_v1.sql`.

Learnings:
- Existing MCP has OAuth and a dedicated read-only Engine login. App owns identity, ownership, leases and allowances.
- Combined App includes stored profiles across approval states; public MCP serves approved profiles. These are different populations.
- App maps 15 provider functions to distinct trial IDs. Its initial CRO rank is total trial count. Site/PI rank prioritizes disease, phase and modality counts.
- Operational findings belong to trials. Sponsor co-occurrence does not prove a direct commercial relationship.
- Empty filter-access requests support lease preflight. Profile-access requires 1–10 IDs and can partially admit a batch. A new endpoint is required for atomic whole-cohort admission.
- Multiple subgroup App requests can fall back to artifact scans. New tools use the existing validated SQL predicate compiler for compound structured criteria.

Decisions:
- Preserve approved-only views and exact restricted database role; do not broaden privileges or modify Engine/App production behavior.
- Use an existing App analysis lease for this backend pilot. Do not reinterpret existing paid entitlements or create a new session implicitly.
- No model-backed classification/extraction, ingestion, document extraction or clinical writes in selection.
- Core query reads memberships and profile content in one SQL statement, ensuring one MVCC snapshot.

Live validation status:
- Workspace confirmed by the owner on 2026-10-06; live read-only aggregate audit completed (see step 5).
- No real customer analyses, emails or payments have been run. End-to-end selection latency remains unmeasured.

## 2. Deterministic tools — implemented, disabled by default

Opt-in flag: `MCP_SELECTION_ENABLED=true`; requires existing database source and App authorization. The original six tools retain their behavior.

Tools:
1. `get_selection_catalogue`: static filters, 15 functions and pilot limitations.
2. `search_trial_cohort`: complete approved base, disjoint direct/related/broader counts and content fingerprint.
3. `rank_entities`: top 1–10 CROs/sites/PIs after complete eligible-cohort aggregation.
4. `get_entity_evidence`: paged supporting trials, role attribution, trial findings and optional exact profile sections.

Decisions:
- Base requires positive therapeutic areas; additional direct predicates combine with AND. Related criteria must be explicit. Direct membership takes precedence; broader evidence is opt-in.
- Require unchanged criteria/content fingerprint for ranking and evidence. A fingerprint detects drift; it is NOT a persisted snapshot or authorization token.
- Reuse existing Site/PI identity aggregation with malformed/redacted email keys removed. This retains the existing name/therapeutic-area identity assumptions; false merges remain a data-quality risk.
- CRO identity remains country-specific. Function restrictions apply per distinct trial before ranking.
- Rank by direct counts, related counts, recent authorization counts, broader counts, then stable name/ID tie-breakers. This is a new versioned method, not a silent change to App rankings.
- Report counts over the explicit selected cohort. Unlike legacy Site/PI five-year metrics, no hidden five-year exclusion is applied. Users may apply date filters explicitly.
- Six-month recency uses authorization dates, not recruitment capacity; site/PI recency uses its recorded affiliation country in each trial.
- Operational findings do not boost or penalize rank. Sponsor co-occurrence is explanatory only.

Pilot bounds and costs:
- At most 500 base profiles and 16 MiB serialized cohort content. Overflow fails, never samples or returns a partial top ten. Existing plan allowances may be lower.
- Every base trial/profile must be authorized, including broader base records used for cohort counts. Filter batches are at most 100 and profile batches at most 10.
- Partial authorization returns no cohort/ranking/evidence. Already admitted unique IDs remain metered; the old API cannot roll back an entire selection. Exact retries do not consume IDs again.
- Each call rereads/revalidates the bounded cohort. No new database, background worker or model service. This favors correctness and compatibility over production-scale latency.
- No persistent project/session store or full-cohort index migration is added in this phase.

## 3. Verification and iterations — local checks complete

Iteration A: Implemented strict criteria, SQL membership, aggregation and evidence.

Iteration B: Tests exposed the need to combine separate provider rows before applying the function restriction. Fixed: monitoring and data-management rows for the same provider/trial retain both roles, while trials without monitoring remain excluded from monitoring rankings.

Iteration C: Restricted PI recency to affiliation countries in the individual trial, avoiding attribution from unrelated trial countries.

Iteration D: Added MCP transport/schema tests and opt-in registration. Standard selection imports no model worker and telemetry reports zero worker calls/tokens in the tested workflow.

Verification on 2026-10-06:
- `python -m pytest -q`: 395 passed (including 20 new selection tests).
- Real in-process MCP client exercised search → rank → evidence, output schemas, invalid result bounds, source drift and zero model-call telemetry.
- `git diff --check` and Python compilation passed.
- Tests use synthetic data and mocked authorization/DB reads, not production data. No live SQL execution or benchmark has been claimed.
- Added `scripts/validate_selection_read.py` for a later restricted-reader aggregate audit; it prints schema/count alignment only, never profile contents or credentials.
- Changes are delivered on `feat/deterministic-selection` for review. Tools remain disabled by default; no deployment or merge performed.

## 4. Rollout gates and later work — pending

1. Completed: confirmed workspace and audited live approved-profile coverage, schema versions, reader grants and source consistency. Actual restricted-login execution remains part of the staging gate.
2. Run SQL integration/latency checks in staging with the restricted role. Local SQL tests validate compilation and parameters, not a real PostgreSQL execution plan.
3. Add App-owned selection sessions and atomic full-cohort admission before a self-contained public ChatGPT journey. Current tools intentionally still require `start_analysis` with an App-created report run.
4. Validate representative clinical briefs and top-10 evidence with the owner; evaluate terminology expansion and identity quality.
5. For larger cohorts, add authorized indexed entity/trial/function relationships or durable prepared selections. Do not raise bounds or silently sample without resource measurements.
6. Only then package ChatGPT skills/workflows, as separately requested. No plugin manifest or skills created in this phase.

## 5. Live read-only audit — completed

The owner confirmed the Render workspace. Read-only aggregate checks confirmed that the approved profile and filter populations align, required profile structures are present, and the expected schema version is in use. Reader permissions were inspected; the connector used its own database identity, so actual restricted-login execution remains a staging requirement. A representative selection statement passed PostgreSQL EXPLAIN; no end-to-end latency was measured.

Learnings and decisions:
- Approved-only selection and all-state App results have different coverage. Preserve the approved-only boundary.
- Broad therapeutic-area cohorts can exceed the pilot cap. Keep explicit narrowing and fail-closed overflow; never sample to manufacture a top ten.
- Provider evidence is incomplete even when site/investigator evidence is present. Missing provider records do not prove absence of participation.
- Some recorded provider functions are outside the supported taxonomy. Preserve those labels as evidence; do not invent mappings.
- The serialized-record size guard runs after lifecycle projection and does not bound raw database transfer. Reduce source payload and measure performance before production rollout; do not simply increase the limits.
- Implementation CI passed. Tools remain disabled until restricted-login/staging workflow validation and clinical review are complete.

Detailed operational inventory is intentionally omitted from repository documentation. No database mutations, privilege changes, merges, deployments or workflow packaging were performed.
