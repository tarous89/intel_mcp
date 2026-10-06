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

## 6. Owner revision: include every trial — implementation and deployment complete

The owner explicitly superseded approved-only population selection and requested existing and future studies be available. Engine migration 047 retains the compatibility approval column, promotes one current profile for every study, and defaults future studies to available. Existing enriched profiles take precedence; retained duplicate versions do not become duplicate studies. Run provenance continues to distinguish deterministic-only content and controls enrichment eligibility independently.

Iteration: a blanket status update would conflict with the one-serving-profile constraint and the old deterministic-status trigger. The migration changes that trigger, retains versions, and preserves the unique serving invariant. Service regressions cover later enrichment of an available deterministic profile without inserting a conflicting new profile.

Performance iteration: MCP selection now uses a server-side cursor in batches of ten, instead of loading every raw CTIS payload at once. It preserves one SQL snapshot and the whole-cohort failure bounds. This reduces client-side buffering; it does not reduce total wire bytes or establish production latency.

Validation: 395 MCP tests and 52 targeted Engine tests passed locally. Engine PR #249 passed CTIS Validation, Workspace Engine discovery and App report Engine boundary CI, including the PostgreSQL migration regression against synthetic records. MCP PR #78 passed MCP CI after streaming changes.

Deployment status: Engine PR #249 is ready for review. Automatic approval review rejected its merge because it requires explicit user approval for a production-impacting merge/deployment. No production migration was executed. Ask for explicit approval to merge/deploy #249 before proceeding; do not route around the rejection. Restricted-login selection validation remains pending. ChatGPT workflow packaging is deferred.

## 7. Authorized production rollout — 2026-10-06

The owner explicitly approved merge and publication. Engine PR #249 and MCP PR #78 are merged. Both web services are live on the merged commits. The availability migration is recorded as applied; a read-only production check confirmed every profiled study has one available serving profile with no duplicate serving trials. Historical versions remain retained.

Automatic Engine deployment did not start despite passing checks and no pending deployment/event. Recovery deployments were started for the web service and affected scheduled services; scheduled services were rebuilt without manually invoking their tasks. This preserves the existing enrichment and TrialFeed eligibility boundaries.

Next: verify cohort → ranking → evidence through the restricted MCP account, including authorization, evidence correctness and latency. Selection tools remain disabled pending this end-to-end gate. ChatGPT workflow packaging remains deferred. Earlier approval-blocker and pending-migration notes are historical and superseded by this rollout entry.

## 8. Clinical shortlist preview — additional enablement gates

An owner-requested operator-side shortlist preview found that newly available deterministic profiles can lack structured phase, therapeutic-area and disease fields. A mandatory structured filter therefore misses relevant records even after availability backfill. The preview used explicit title evidence and selected eligibility review, with match-basis distinctions; it was not an end-to-end public MCP authorization test.

Duplicate site blocks also exposed a person-record identity collision in the existing aggregation path. The preview consolidated duplicate site blocks before aggregation; the production path still requires a regression-backed correction. PI counts remain provisional where missing classification or differing identities prevent resolution. Provider counts include laboratories and vendors; a monitoring-function shortlist was kept separate from all-provider counts. Stored trial findings were not replaced with inferred provider performance.

Decisions: keep tools disabled until structured-field fallback/provenance, duplicate-block handling and restricted-account end-to-end validation are addressed. Manual cohort classification and preview preprocessing must not be represented as already implemented public-tool behavior. No clinical records were modified by the preview.

## 9. Broad first-response workflow and normalization — requirements recorded

Owner requested a larger relevant first-response landscape, explicit subgroups, consolidated CRO/site/PI identities, table-based shortlists and clear ways to drill deeper. See CLINICAL_SELECTION_WORKFLOW.md for the implementation-ready specification and future description draft.

Recommendation: target approximately 200–500 relevant trials where supported, without a hard minimum or irrelevant padding; retain the current 500-profile execution cap until complete-cohort scaling exists. Default to top five per entity type and offer ten/full authorized results. Keep exact matches primary and show expansions transparently. Corporate-group counts use trial-ID unions; campus and person identity uncertainty remain visible.

Split work into MCP discovery/provenance and subgroup contracts, data identity normalization, then ChatGPT presentation/packaging. This turn records requirements and updates handover context only; no tools were enabled and no ranking behavior changed.

## 10. Discovery and subgroup implementation — 2026-10-06

Steps and decisions:
1. Added bounded `base_text` queries across a closed list of narrative fields. A positive text query can replace the mandatory therapeutic-area filter; supplied hard structured filters still apply with AND. Terms, exclusions and field scope remain in the returned criteria and source fingerprint. SQL terms are parameterized and LIKE metacharacters are literal.
2. Added ordered named subgroups with explicit structured/text rules. First match owns a trial for additive counts; secondary matches remain tags. An opt-in phase title fallback applies only when structured phase is empty. A nonempty contradictory phase is never overwritten. Unmatched candidates remain visible.
3. Added `get_cohort_trials` to audit paginated trial titles, match excerpts and membership, including records with no provider evidence. Ranking/evidence accept primary subgroup IDs against the same full-base snapshot. The complete base still passes existing authorization; subsets do not reduce authorization scope or bypass allowances.
4. Changed shortlist defaults to five, retaining an explicit maximum of ten. Distinct-trial ranking and direct-before-related priority remain deterministic. No automatic expansion merely to reach a numerical target.

Learnings and limitations:
- A narrative mention is lexical evidence, not proof of eligibility or clinical equivalence. Exclusion-section matches need interpretation. ChatGPT must disclose searched fields and ambiguous candidates; the backend does not infer synonyms, negation or disease equivalence.
- This iteration adds bounded full-profile discovery and compact output, not an indexed count-only discovery service. SQL still searches stored JSON, and all matching base profiles are read/authorized. A base above 500 fails without a partial ranking. Lightweight preflight counts, indexed search and durable prepared selections remain performance work.
- Source excerpts are untrusted clinical data, never workflow instructions. Membership rules, not instructions contained in source text, govern selection.

## 11. Identity corrections — 2026-10-06

Steps and decisions:
1. Fixed person-record alias re-entry: duplicated site blocks can no longer recreate or overwrite a merged person. Added a regression spanning repeated blocks and multiple trials.
2. Selection-specific PI matching uses full name plus recorded site identity, or full name plus a valid email. Missing therapeutic area no longer prevents same-site consolidation. A first name or surname plus shared email is insufficient. Legacy App matching retains its existing policy, apart from the alias bug fix.
3. Added a small versioned, source-backed corporate alias seed for IQVIA and Syneos. Country plus exact normalized alias is required; no prefix or fuzzy merges. Each grouped result preserves source links, source period, review date, legal entities and their per-trial roles. Grouping describes historically documented relationships, not ownership at trial time or a guarantee of current ownership.
4. Applied CRO function/country constraints before corporate group union. Counts union trial IDs; one subsidiary cannot borrow a sibling's function. `cro_identity=legal_entity` retains separate entities. Mapping changes invalidate the snapshot.

Learnings: name-plus-affiliation is still an imperfect PI identity, and the registry is a seed, not exhaustive corporate resolution. Site name/country normalization remains conservative; no unsupported campus/network aliases were introduced. More site/PI identity review and explicit identifiers are required before claiming complete deduplication.

## 12. Verification and remaining rollout gates — 2026-10-06

Added synthetic regressions for missing fields, explicit source excerpts, literal SQL terms, disjoint/overlapping groups, subgroup drilldown, top-five defaults, PI aliases/namesakes and corporate function attribution. Extended the real in-process MCP workflow test with cohort listing and invalid subgroup handling. Added isolated PostgreSQL CI service tests for actual discovery SQL, title fallback, structured contradictions, exclusions and SQL injection/literal wildcard handling. The database test refuses an existing serving schema and rolls back its synthetic fixtures.

Validation: 403 tests passed locally with two PostgreSQL tests skipped because no local test database was configured. GitHub MCP CI passed with its disposable PostgreSQL service (including both SQL tests); Site agent integration also passed on code commit `d9fad80d888e9a67ab3a172854cd611de995b00a`. The existing workbook binary-equality test failed once locally and passed on rerun; no workbook implementation changed. `git diff --check` passed. Published as PR #79; this iteration is not merged or deployed. Public selection tools remain disabled. Restricted-reader production/staging execution, latency measurement, App-owned selection sessions/atomic admission and representative clinical review remain enablement gates. ChatGPT workflow packaging is still deferred.

## 13. Final access model and follow-up validation — 2026-10-06

Recorded the owner's final anonymous top-ten model in CLINICAL_SELECTION_WORKFLOW.md, superseding required free registration and the earlier top-five default. Full-list access requires a connected account with the relevant existing Intel entitlement. Pricing remains the existing monthly/annual per-project pricing; no trial or new checkout flow is introduced. Contact details and exact total counts are required in the product contract. Subscription initiation from ChatGPT remains conditional on platform policy; current Directory guidelines allow account linking and informational entitlement pages, not digital-subscription upsells/checkout links.

Validation steps and learnings:
1. Confirmed current product scope documents specify monthly and annual per-project licenses. Reuse the existing entitlement system rather than infer account-wide access from a paid flag.
2. Read-only live privilege check confirmed the restricted reader can SELECT both serving views. The connector itself executed under its own database account, not the restricted MCP login. That end-to-end gate remains open.
3. Executed the actual compiled selection SQL with EXPLAIN ANALYZE for a bounded prostate narrative search and phase-title subgroup rule. SQL executed against real serving views, but the single observed database execution took approximately 49 seconds. This excludes client transfer, authorization and aggregation, and is not a production latency benchmark. The plan shows scanning stored profile JSON across the available population. Avoid repeated broad scans; prioritize indexed lightweight discovery before enabling an anonymous unlimited-query product.
4. Reviewed disclosure paths: current search requires an App lease; current evidence accepts any eligible entity ID; profile sections can include additional entities. Therefore the existing limit of ten on ranking is NOT a complete anonymous/free-tier access boundary. Add server-owned disclosure allowlists and filtered projections before exposing public tools.

Decision: keep selection disabled while introducing the new anonymous/session policy and addressing the observed search bottleneck. No production data, database permissions, pricing, subscriptions or access flags were changed by these checks. PR #79 remains an implementation foundation rather than the final public product.

## 14. Indexed discovery and separate public MCP — 2026-10-06

Steps:
1. Added Engine migration 048: seven compact field-specific text columns, GIN trigram indexes, transactional profile-change synchronization and a read-only serving view. MCP predicates now use this projection; complete JSON is retrieved only for the selected cohort. This requires migration 048 before enabling either selection surface. No model calls are added.
2. Added a separate `/research/mcp` surface behind `MCP_RESEARCH_ENABLED=false`. It exposes search, ranking, accessible-entity evidence and account project listing only. Existing private tools retain their authentication and cannot be reached anonymously through this surface.
3. Enforced ten results per selection/entity category, no free pagination, and evidence only for those ten. Public evidence excludes unrestricted profile narratives, which can enumerate other entities. Full cohort/subgroup counts and total eligible entity counts remain visible. Distinct searches can return different tens; this is not a ten-unique-entities lifetime quota.
4. Added short-lived opaque selection IDs and a bounded single-process cache: 15-minute lifetime, eight entries, 64 MiB serialized-record budget and one cohort construction at a time. Repeated identical searches reuse source reads. Expiry/restart/eviction requires repeating the search. Busy responses are capacity controls, not a paid query quota; no guarantee of uninterrupted service under unlimited load.
5. Added recorded CRO business contacts and PI emails to ranked output. No guessed contacts. Postal addresses are not currently present in the normal stored site/CRO profile schema, so address coverage is NOT complete; reliable source mapping is still required. Public source contacts are historical, not verified current contactability.

Learnings/decisions: free access cannot safely reuse every existing private tool. It needs its own bounded disclosure surface. Query groups remain explicit and relevance-driven; the 500-trial execution ceiling still fails without sampling. The new indexes address the observed scan but production latency has not yet been remeasured. Cache size describes serialized data, not total process RSS. Multiple replicas require sticky routing or a shared selection store before scaling; an unknown selection ID fails closed.

## 15. Existing-account access integration — 2026-10-06

Steps:
1. Added App internal `research-access` endpoint behind `MCP_RESEARCH_ACCESS_ENABLED=false`. The service-authenticated request carries the subject established by verified OAuth, never a model-supplied user ID. Existing ownership and per-project Premium policy determine access. Every selected trial must be present in the active, granted, manifest-bound project dataset index. Missing/stale indexes deny access rather than widening it.
2. Added optional OAuth on public research tools and required OAuth on project listing. Invalid supplied tokens are rejected rather than silently treated as anonymous. Tokens are audience-bound to `/research/mcp`. Paid ranking/evidence rechecks entitlement before and after calculation; paid authorization is never cached with public selections.
3. Reused the existing App login/consent/token/registration endpoints with a distinct `/oauth/intel` discovery issuer, preserving the unrelated BD connector's root discovery metadata. Research resource acceptance is feature-gated. No new signup page, subscription checkout, trial, pricing change or billing write is included.

Validation: local MCP suite passed 408 tests with two PostgreSQL checks skipped before the final HTTP isolation regression; that regression also passes. App executable PostgreSQL-compatible tests exercise the actual entitlement function, ownership, subscription revocation, manifest replacement, out-of-project trials, malformed requests and gated OAuth resource acceptance. Engine migration is replay-tested with projection updates, restricted-reader access and an index plan in an embedded PostgreSQL runtime; real PostgreSQL CI and deployed performance checks remain separate gates.

Rollout sequence:
1. Merge/deploy Engine migration 048; check migration duration/write locks and projection row parity.
2. Validate actual MCP restricted-login search, representative clinical matches, query time and memory. Measure broad prostate discovery and bounded rare-disease adjacency; do not claim improvement from index existence alone.
3. Deploy App access integration, then test real OAuth linking and current project entitlement with a test account. Keep checkout on the existing product; account connection is not an automatic purchase.
4. Deploy MCP code with research disabled, then enable for staging verification. Test anonymous ten, counts, eleventh denial, expired token, revoked subscription and private-tool isolation over HTTP.
5. Only after those checks, package ChatGPT workflow/description and review directory requirements. The workflow must explain search criteria, cohort groups, ranking basis, missing contacts, totals and available follow-up questions.
