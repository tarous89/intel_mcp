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
2. Selection-specific PI matching uses full name plus recorded site identity, or full name plus a valid email. Missing therapeutic area no longer prevents same-site consolidation. A first name or surname plus shared email is i…365 tokens truncated…bgroup handling. Added isolated PostgreSQL CI service tests for actual discovery SQL, title fallback, structured contradictions, exclusions and SQL injection/literal wildcard handling. The database test refuses an existing serving schema and rolls back its synthetic fixtures.

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

CI follow-up: MCP CI passed all 411 tests (including actual PostgreSQL discovery SQL); Engine CTIS Validation passed all 505 tests (including migration 048). App entitlement tests and whole-project TypeScript checks passed after changing the throwing validation helper to a function declaration so TypeScript retains validated input narrowing. The existing local workbook byte-equality test failed once and passed on isolated rerun; workbook code was unchanged and MCP CI passed it. Published changes: Engine PR #250, App PR #246 and MCP PR #79. Both new feature flags remain disabled, and these PRs are not yet merged/deployed. The public research endpoint requires `MCP_ENGINE_SOURCE=database` with the existing restricted reader credentials; unsupported HTTP-only configuration fails explicitly.


## 16. Deployment validation and production startup correction — 2026-10-06

Merged Engine #250, App #246 and MCP #79. Engine migration 048 completed; all 12,585 available profiles have search projections and the restricted role retains SELECT access. A database-only title/disease prostate index probe returned 192 candidates in 9.726 ms; this is not full profile retrieval or end-to-end MCP latency. App research OAuth metadata is live and the pre-existing BD root metadata is preserved.

The production `intel-mcp` entrypoint uses `bootstrap.py`, which registers report/site routes and rebuilt only the legacy HTTP server. The first live research check therefore returned 404 despite the research flag. Corrected both entrypoints to call the same HTTP composition factory after route registration; changed the regression to load the actual production bootstrap. Existing private App routes retain their service-token boundary. Public access still requires live end-to-end validation after this correction.

## 17. Live rollout verification — 2026-10-06

Engine #250 and App #246 are live; MCP #79 plus production-bootstrap correction #80 are live. Research and App research-account flags are enabled. Existing private selection flag is unchanged. Main website and Intel login respond successfully; new internal entitlement route rejects unauthenticated HTTP requests; research issuer metadata returns 200 and old BD root metadata is unchanged. A research-resource authorization request passes parameter validation and correctly rejects an unregistered test client; no customer account, payment or email was created.

Live anonymous MCP tests used the deployed restricted database connection: title/disease lexical `prostate` yielded 192 profiles and 272 recorded provider entities, ten visible rows with contacts, and denied offset ten. The account tool returned the OAuth connection challenge. These are operational smoke-test candidates, not a reviewed mHSPC cohort or a claim that every provider is a full-service CRO. One external search call took 17.68s; tools/list and cached ranking calls were around 10s through this execution transport, so these are not isolated server benchmarks. The separate 9.726ms database probe measures only indexed text lookup.

Remaining user check: complete real ChatGPT account connection with an existing entitled project and verify full-list access versus an unentitled/out-of-project selection. Automated entitlement tests cover ownership, revocation and trial scope, but do not replace this signed-in journey. Workflow packaging/directory submission and postal-address mapping remain unfinished. No main-site/App UI, pricing or checkout changes were made by this rollout.


## Step 18 — Package the ChatGPT discovery workflow (2026-10-06)

- Input: owner confirmed the requested acceptance checks and authorized the next step. Record this as owner-reported signed-in verification.
- Decision: portable Agent Plugins package in `plugins/trialagents-intel`, with a workflow skill and one remote research MCP. Anonymous ten-per-category access and existing per-project OAuth entitlement stay server-owned. No runtime, app layout, signup, checkout, price or database change.
- Implementation: manifest/listing, existing brand icon, three starters, five positive and three negative review cases, workflow and concrete prostate criteria, explicit-file reproducible ZIP builder and CI artifact. Consolidated the stale top-five/private workflow document to current behavior.
- Learnings: the current official submission format supports skills plus mcp.json; upload is separate from review/publication. The public API cannot return arbitrary raw sections or a complete trial-list export. Lexical mHSPC groups are candidates, not verified population eligibility. Hard phase filters exclude missing structured phases before subgroup fallback. Entity-country and trial-country are different constraints. Anonymous evidence pagination for displayed entities differs from blocked entity-list pagination.
- Validation: skill quick-validator passed; both package boundary tests passed (reproducibility/secret-file exclusion and symlink rejection). Bundled example validates against the implementation model. Independent read-only workflow forward-test covered broad mHSPC, hard phase/Germany and attempted access bypass; incorporated its clarifications. Full local regression: 411 passed, 2 database-integration tests skipped without the PostgreSQL fixture. These are local checks, not a claim of OpenAI approval or ChatGPT installation. Release PR: https://github.com/tarous89/intel_mcp/pull/81.
- Remaining release gates: actual packaged ChatGPT pilot, verified developer/domain challenge, reviewer account, walkthrough video, support/legal adequacy and current live annotation requirements. See CHATGPT_PLUGIN_RELEASE.md. No invented review credentials or challenge token and no public directory submission.

## Step 19 — Mandatory release gates and submission hardening (2026-10-06)

- Owner required research learnings and consistency checks to be documented BEFORE proceeding, with review mandatory before download/test readiness and every release. Committed the checklist and blocked readiness record first.
- Guide now distinguishes Gate A (owner-test handoff) from Gate B (public release), records item evidence/owners and explicitly says CI artifacts do not establish readiness. It covers naming, service/source consistency, access parity, provenance, privacy, metadata, legal/support, deterministic behavior, auth, cost authorization, review scans and lifecycle.
- Decisions: preserve agreed tool/skill behavior and ten-result/project model. No additional LLM calls or service-cost changes. Legal changes remain drafts pending retention/controller facts; support is a static page in a separate App PR. No deployment or public submission in this step.
- Package 0.1.1 uses independent fresh-chat evidence/account cases, production-focused release wording, and proposed support URL. Annotation explanations and field-minimization concerns are documented without changing live annotations or outputs. Source review found conflicting official justification requirements; portal evidence must resolve this per release.
- Gate A remains blocked until the support URL is live and the remaining legal/source/data/readiness checks are evidenced. Gate B additionally requires packaged ChatGPT testing, reviewer access, verification/scans, video, attestations and approval/publication.

- Delivery: App support/legal-draft PR https://github.com/tarous89/intel_agent_app/pull/247; package/checklist remains PR #81. Local validation retry encountered missing project/pytest dependencies in the refreshed workspace; use current GitHub CI results, not a claimed local pass.

## Step 20 — Pre-test verification and support deployment (2026-10-06)

- Confirmed current package build/MCP CI and all three App PR checks succeeded. Expanded readiness into individual checklist outcomes with source/code/CI evidence and explicit factual blockers.
- Merged approved support/legal-draft PR #247 as c5a06ad0c903c1e19a6032732febe30a6be37216; Render auto-deploy dep-db2g923l550s73cf1aug started on the existing App service. No service plan/env/billing/LLM change. Legal draft remains internal, not a new published policy.
- Fresh MCP health and both research OAuth discovery endpoints returned 200 with correct audience/issuer. Support initially returned 404 during the build; final status is recorded in the readiness record.
- Reviewed owned-project output fields, complete-manifest authorization, ephemeral cache semantics and source-version identifiers. Verified expiry must not be described as guaranteed physical deletion. Render workspace retention cannot be inferred from instance pricing tier.
- Gate A remains blocked on actual legal/controller, source reuse and retention facts plus final publication/verification. No download/test-ready or public approval claim. Owner factual requests are specific in docs/releases/0.1.1-readiness.md.

- Deployment verified live. Found main-host support URL 404 versus Intel App support URL 200; corrected only plugin supportURL to https://intel.trialagents.com/support/intel. Live tool scan returned all four expected tools/auth declarations. New CI artifact required after this metadata correction.

## Step 21 — Atlas Consulting publisher identity (2026-10-06)

- Owner chose Atlas Consulting as TrialAgents' operating company and plugin publisher. Updated only package author.name/developerName plus repository context/readiness notes; preserved product name, workflows, access and costs.
- Explicit restriction: do not add Atlas Consulting or an address to any public TrialAgents page without asking for permission first. No App source, privacy/terms/support page or deployment changed in this step.
- Verification status is unconfirmed. Official business verification guidance requests the current registered/operating address privately; published plugin manifest requirements do not include a postal-address field. Public website identification/disclosure remains a separate approval-dependent check, not waived.
- Sources checked: https://help.openai.com/en/articles/10910291-api-organization-verification and https://developers.openai.com/plugins/deploy/submission .

## Step 22 — Authorized public publisher identification (2026-10-06)

- Owner confirmed Germany, supplied an address for Terms only, and then explicitly authorized Atlas Consulting identification on all plugin-review public pages. Earlier blanket public-name restriction is superseded within this scope; postal-address placement remains Terms only.
- App PR https://github.com/tarous89/intel_agent_app/pull/248 adds operator/publisher identification to the Intel product footer, support, privacy and terms. No verified/approved claim, new Impressum route, app-usage/workflow/tracking change or new LLM call.
- Learning: trialagents.com is served by the separate trialagents-public snapshot. App source merge/deploy alone is not proof that all four package URLs have updated.
- Decisions: owner will complete Atlas Consulting verification. Keep Gate A/B factual blockers open; existing privacy/retention/source-rights and stale legal wording are not resolved by this identity-only patch. Deployment/live evidence must be recorded before closing the public-identity check.

## Step 23 — Publish authorized disclosures and retain handover (2026-10-07)

- Owner explicitly requested publication and durable MD context. All five App #248 checks passed on 70cf1928d3618d15410e2b388bb920d6bac99822 (test, verify, report-dataset, max-agent, app-worker). Merged as 7d9a548c31b164592ee81ab426c57ae4e67d034d; existing Render service started dep-db2tnduq1p3s73ercvu0 automatically.
- Preserved decisions: Atlas Consulting operator/publisher; postal address in Terms only; no verified/approved claim; OpenAI verification to be completed by owner. No separate Impressum, workflow, entitlement, tracking, pricing or LLM change.
- Main-site publishing is separate: trialagents-public PR #124 records source/deployment ordering and live checks. This session has GitHub/Render access but no connected Cloudflare publishing tool or authenticated Wrangler. Do not infer Cloudflare publication from App merge or documentation updates.
- Current live evidence and remaining publication work are tracked in docs/releases/0.1.1-readiness.md. All existing source-rights, privacy/retention and package readiness gates remain mandatory.

- Deployment follow-up: Render became live at 05:45:28 UTC; all four source pages returned HTTP 200 with Atlas Consulting and address only in Terms. GitHub revealed the existing Cloudflare Workers Builds integration; this resolves the earlier assumed credential blocker via the existing GitHub publishing path. Public #124 predeploy layout checks are still required before merge.

- Final closeout: public #124 merged after successful exact-head predeploy validation. Production commit 0d3409f510b6e47d407ec1bfd8338ab9b1ba25a5 triggered successful Cloudflare build 37f0a6ab-cef7-4feb-af67-920f41f21a80, version ac76303d-4cbd-4b42-8973-82a62cd27ef8. The exact plugin-linked URLs (trialagents.com/intel-agent, /privacy-policy, /terms-of-service; intel.trialagents.com/support/intel) all returned 200 and contain Atlas Consulting. Only Terms contains the postal address. This supersedes the earlier pending/credential-blocker notes in Step 23. App and public context/history are merged; MCP package/context remain on PR #81. No directory submission/publication or verification claim.

## Step 24 — ChatGPT research OAuth discovery repair (2026-10-07)

- Owner's first ChatGPT test unexpectedly requested connection; screenshot reached private BD `/api/mcp/bd/oauth/authorize` and failed with `Invalid OAuth resource` before sign-in. Do not interpret this as a subscription/account denial.
- Reproduced missing RFC 9728 research-specific metadata path (404); root fallback advertises legacy MCP/root App issuer, which discovers BD authorization. Existing mounted research metadata and both `/oauth/intel` issuer discovery variants were correct. Root-fallback explanation is consistent with screenshot; exact client settings/cache were not available.
- Fix PR #82 adds `/.well-known/oauth-protected-resource/research/mcp` ahead of the legacy mount, with regression assertions for research issuer/resource and private isolation. Tests passed; merged b89a076a05fd4ad0980243f6dd5edd6310871850, Render dep-db2uckp5efls73bo6b10 live 06:28:36 UTC.
- Live verification: new metadata path 200 with correct `/research/mcp` audience and `/oauth/intel` issuer; anonymous research tools/list 200; private `/mcp` remains 401. No access/workflow/pricing changes or backend LLM calls. Details in main-branch docs/RESEARCH_OAUTH_DISCOVERY_INCIDENT.md.
- Owner retest: refresh/recreate only the custom TrialAgents Intel Test connection using the exact research URL; cached BD client registration may need replacement. OAuth must use `/oauth/authorize`, not the BD path. End-to-end ChatGPT behavior and initial anonymous-search prompting still need owner confirmation; a passing discovery probe is not OAuth acceptance.


## Step 25 — Preserve anonymous-first tool authentication metadata (2026-10-07)

- Owner reported first use still requested connection. New screenshot reached clinical /oauth/authorize and showed Approval expired. Previous discovery repair fixed routing only; it did not verify anonymous-first ChatGPT behavior.
- Confirmed deployed tools/list omitted top-level securitySchemes, with declarations only under _meta. OpenAI documents that omission inherits server defaults. SDK 2.x drops unknown Tool fields and filters them again during protocol serialization.
- Decision: research-only response middleware mirrors existing securitySchemes after SDK serialization. Search/rank/evidence remain noauth plus optional OAuth; project listing stays OAuth-only. No change to agreed workflow, ten-result enforcement, app usage, subscriptions, token validation or LLM costs.
- Iteration: initial result serializer failed the new HTTP-wire regression because the later SDK protocol filter dropped the extension. Response middleware fixed that; all five focused tests and full CI passed.
- PR #83 merged as 862e6087e8573fe7ad0a6184b8d0074738befd8c. Render dep-db2uqsp5efls73bokr60 live 06:58:39 UTC.
- Live checks without credentials: three research descriptors include top-level noauth and matching compatibility metadata; prostate CRO search reported 272 entities, ranking returned ten, evidence succeeded, offset ten was denied, private /mcp remained 401. These counts describe this validation selection, not global coverage.
- Required owner/client retest: refresh test app metadata and start a fresh conversation without connecting a TrialAgents account. First research must return results without external login. Optional full-access linking is a separate test. Installed-client settings/cache are not verified by server probes.
- Keep anonymous-first behavior, HTTP-wire auth declarations and voluntary upgrade tests on the mandatory pre-test/pre-release checklist in docs/RESEARCH_OAUTH_DISCOVERY_INCIDENT.md. Broader publication blockers remain; do not mark the package submission-ready from this repair alone.


## Step 26 — Owner host-test findings and proposed workflow correction (2026-10-07)

Status: investigation and planning only; obtain owner approval before changing the agreed workflow. No runtime/app usage, pricing or LLM-cost change in this entry.

Evidence:
- Owner screenshots show validation retries, a final six-trial cohort, omitted access explanation, and generic incomplete-coverage/identity caveats.
- Installed ChatGPT search tool is exposed as criteria: unknown. The server uses a nested SelectionCriteria schema; test host rendering explicitly rather than assuming a valid server schema is sufficient. Exact importer cause remains unverified.
- Successful installed-tool call with the existing bundled broad prostate example (date 2026-10-07) returned 192 trials: 18 phase III mHSPC terminology candidates, 49 other phase III prostate candidates, 125 unmatched broader prostate trials, and 272 CRO/provider entities with ten visible. These are lexical candidate groups, not validated exact eligibility; broader does not mean every trial is equally relevant.
- Main selection.py still emits a static migration-047-pending coverage warning and complete_approved_base label. Earlier deployment entries record migration 047 applied and available-profile parity checked. This warning is not a live measurement of missing studies.
- Identity alias limits remain a separate real limitation; do not delete them merely to improve appearances.
- Bundled skill already instructs broader landscape discovery, but says explain the access limit only when relevant. It is not confirmed that the installed custom MCP test includes/loads this bundled skill. Server instructions alone do not contain the full broad-first procedure.

Proposed acceptance checklist; review before package download/testing readiness and every release:
- [ ] Expose explicit usable search requirements in the ChatGPT tool schema, with a validated minimal example in tool help. Validate a fresh first invocation without exploratory validation failures. Investigate inlining local schema references or a simpler typed public contract; retain server-side validation.
- [ ] Ensure broad-first instructions are delivered in the actual tested installation, not only the unmerged ZIP source. Make first exploratory output a relevant 100–500-trial landscape when available; direct/related/broader groups must be explicit and disjoint.
- [ ] If a first narrow query returns below 100, run the disclosed relevant broader landscape before finalizing. Never fabricate counts, sample silently, or relax explicit mandatory constraints. If relevant data remains below 100, explain the actual scope and counts.
- [ ] Preserve direct-experience ranking priority; do not let broad counts imply exact clinical expertise.
- [ ] Always show displayed/total entity counts and a neutral access footer on initial results: free use shows up to ten per category; connect or create a TrialAgents account for full-access options; full lists require an eligible entitled project covering the cohort. No forced login for the free result, no claim that login alone unlocks paid access.
- [ ] Include structured access information in search/ranking responses and clear presentation instructions. Verify against current OpenAI guidance before adding external subscription CTA/link wording.
- [ ] Replace historical migration warning and approval-era naming with verified serving-coverage semantics; check live coverage before claiming completeness. Distinguish database scope, missing individual fields, identity uncertainty and actual retrieval truncation/failure.
- [ ] Keep real material caveats concise and tied to the returned evidence. Do not assert missing/unserved profiles from a static historical warning.
- [ ] Repeat the owner's exact prompt in the installed ChatGPT plugin: no required login, no schema-guessing errors, broad subgroup counts, top ten per requested category, recorded contacts, access footer, source-based ranking explanation.
- [ ] Record server deployment and installed workflow version separately; successful API calls alone do not establish host workflow compliance.

Permission boundary: requested corrections are concrete above. Await owner approval for workflow/response-contract edits. No backend LLM is proposed; deterministic selection remains unchanged.


## Step 27 — Implement approved host-test corrections (2026-10-07)

Owner approved the four Step 26 corrections. Used public MCP presentation changes rather than changing App behavior, ranking, database reads/permissions, auth, entitlements or pricing. No backend LLM calls added.

- Schema: inline local references in research HTTP input schemas after SDK serialization; retain all filters and Pydantic validation. Add explicit required fields, a valid minimal example and broad-first steps to search help. Descriptor size increases to roughly 94 KB; host metadata refresh/import is a separate gate.
- Workflow: target 100–500 relevant trials; below-target exploratory output explicitly asks for justified broadening before finalizing, with hard-constraint/relevance exceptions. No automatic filter relaxation, fabricated minimum or silent sampling.
- Access: search and rank always return access_info with actual total/displayed counts, cap and neutral existing-account/project entitlement explanation. The workflow requires it in the first report. OpenAI guideline check permits neutral access information but prohibits digital-subscription promotion; therefore no create-account-and-subscribe CTA, checkout link or pricing.
- Coverage: public output uses complete_available_profile_selection and source_scope. Historical pending-migration wording is removed; genuine identity/missing-field limitations remain. Private selection labels and consumers are untouched.
- Package: bump source to 0.1.2; update skill, contract, release checklist and context. Merge main's OAuth/discovery/host fixes into the package branch to prevent a later release restoring old metadata.
- Validation: 421 local tests passed, two PostgreSQL checks skipped locally; required GitHub CI passed including database integration. Package boundary tests passed. HTTP descriptor exposes object properties and no unresolved refs; optional auth remains correct.
- Runtime PR #84 merged as 3aa676ffdb7c7969d4bd2ef00e4e8dd16e549cbf. Render dep-db30htjrjlhs73fukn30 live 08:56:14 UTC.
- Live installed-tool validation: same exploratory prostate rules gave 192 trials (18 phase III mHSPC terminology candidates, 49 other phase III candidates, 125 broader). Inventory: 272 CRO/providers, 1,002 sites, 1,918 PIs. Ranking returned ten with access notice; evidence succeeded; offset ten denied. Static migration warning absent. These are candidate/cohort counts, not confirmed eligibility or a market census.
- Actual current conversation still advertises cached old search help/criteria: unknown, while tool responses reach the new backend. Refresh installed metadata and retest first-call schema comprehension plus full initial-report behavior. Do not claim this host presentation gate has passed.
- Main validation checklist: docs/RESEARCH_HOST_WORKFLOW.md. Package Gate A/B remain subject to docs/CHATGPT_PLUGIN_RELEASE.md; this correction is not OpenAI approval or a public package release.


## Step 28 — Second owner host test: next issues and OAuth investigation (2026-10-07)

Investigation/planning only; no production behavior changed in this step.

Owner requests:
- Hide CRO/provider emails from initial results; return recorded contacts only on explicit request and label source/purpose without claiming business-development suitability. This does not remove CROs from the shortlist.
- Default top ten should rank distinct-trial experience across the whole relevant cohort. Hide direct/related/broader/A-B-C breakdown unless requested. This supersedes direct-first default ranking for the public experience view; requires a deterministic ranking change, not just hiding columns.
- Seek at least 100 relevant trials where available and raise the proposed ceiling to 1,000. Do not fabricate trials or silently relax mandatory constraints. Current cap remains 500; test memory/bytes/latency before increasing it and keep the 16 MB response/snapshot guard in view.
- Concise initial output: cohort size, total inventory, top-ten experience counts and functions/affiliations; two or three contextual follow-ups.
- Recommend horizontal bars for categorical trial-count comparison, with a compact table fallback. Optional MCP Apps HTML component can render inline; model/tier/host universal availability is not established. Use a reusable deterministic component, not per-response generated HTML or new LLM jobs.
- Explain exactly which follow-up needs connection/entitlement before invoking auth. Country/function research and evidence for visible entities already work anonymously and must not be falsely paywalled. Full entity lists are access-gated. Trial-results/operational-narrative analysis is not presently exposed by this public tool surface; do not advertise it as unlocking merely through login.
- Consent journey needs purpose/benefits, clear identity, cancel, and correct logged-out login/create-account navigation; already-signed-in users should see their account and continue/change-account options, not redundant signup.
- Investigate repeated Approval expired.

Confirmed code findings in intel_agent_app main:
1. app/oauth/authorize/route.ts GET redirects logged-out users to /auth?mode=login&return_to=<original authorization path/query>.
2. app/auth/page.tsx login/signup success ignores return_to; destination is selected from unrelated workspace/combined/share/legacy landing routes. This is a definite broken continuation for logged-out OAuth. It is not proof of the reported expired-approval cause.
3. Already signed-in GET creates a user-bound approval request with ten-minute TTL. POST returns Approval expired whenever the request is absent, expired or mismatched to the current user; a successful/denied request is deleted. A repeated submit can therefore hit the same generic message.
4. Consent text still describes approved clinical-trial analyses / analysis allowances instead of current project-based research access.
5. Render OAuth-filtered logs for the reported recent window returned no entries; the exact failing request/cause is not established. Do not claim a ten-minute wait, double-click or user switch as fact.
6. No safe restart/action UI is offered on the error page. Do not fix this by disabling expiry, user binding, state or PKCE.

Priority order:
- [ ] Repair and regression-test OAuth continuation through login/signup with a validated same-origin authorization return path; preserve unrelated app destinations.
- [ ] Distinguish expiry/consumed/account-mismatch conditions with safe user-facing recovery and non-secret diagnostic reasons. Prevent accidental double submission; do not blindly reuse authorization codes or auto-approve.
- [ ] Make consent purpose explicit and verify user-facing benefits match actual entitlements/tool scope. Keep authentication separate from purchase/entitlement.
- [ ] Implement public overall-cohort ranking and explicit-request CRO contacts; retain audit breakdown for requested drill-downs and stable sorting.
- [ ] Validate the 1,000-trial ceiling without new LLM usage or infrastructure purchases.
- [ ] Add three honest, question-specific follow-ups with free/connected-access classification.
- [ ] Build optional inline bar-chart component with text/table fallback only after host support/scoping is confirmed.
- [ ] Review mandatory pre-test/pre-release guide, then repeat logged-out, already-signed-in, expired, duplicate-submit and denied-entitlement tests.

Sources reviewed: https://developers.openai.com/plugins/build/auth (tool-level OAuth challenges can include error_description; native host banner wording is not documented as fully customizable); https://developers.openai.com/plugins/build/chatgpt-ui (inline MCP Apps components and non-UI fallback). Existing digital-subscription commerce restrictions continue to apply.


## Step 29 — Approved owner iteration (2026-10-07)
Latest decision supersedes Step 28's proposed 1,000 ceiling: target **200–500** relevant trials, hard cap500. Broaden through relevant therapeutic area, phase or modality without dropping mandatory constraints; report a shortfall when the available evidence cannot meet200. No padding or silent sampling.

Implementation scope: public whole-cohort distinct-trial ranking (private ranking unchanged), matching evidence eligibility, explicit-request CRO emails with source-purpose caveat, concise inventory/experience presentation without default match tiers, contextual free versus account-required follow-ups, OAuth return allowlist/login continuation, consent benefits/account choice, safe expiry/replay recovery and optional deterministic inline bars/table.

Confirmed learning: prior login ignored return_to. The prior generic Approval expired message conflated missing/consumed, expired and account-changed requests. Exact cause of owner's earlier incident remains unproven. Preserve expiry, state, PKCE, user binding and one-use codes; record only bounded failure reason, never secrets.

No new LLM calls, pricing/billing changes, paid jobs or infrastructure purchases. Broader discovery can require additional bounded database searches. Check docs/CHATGPT_PLUGIN_RELEASE.md before package download/test handoff and every release. Host rendering and full authenticated journey require actual ChatGPT acceptance after deployment; do not mark those checks passed from local tests alone.


Step29 validation/deployment: MCP PR85 merged as9de8987b14485c3c6d4462a65b9625c782dee205 and Render dep-db31tth5efls73bs4beg is live. App PR249 merged as0f8dbd3a472e16cd89e37ea86f1fcabfaf2bdf80; check deployment status before host handoff. Local MCP423 passed/2 DB checks skipped; GitHub required CI passed including database checks. OAuth mocked-route lifecycle test and app CI/TypeScript passed. DOM checks verified visible counts, bar scaling and escaping. Package0.1.3 build/tests and package CI passed. No runtime differences between package branch and deployed main.

Live bounded verification: broad title/disease lexical search prostate OR bladder OR urothelial across phases returned339 trials and453 providers; ten results sorted by total_trials_desc/name_asc/id_asc, zero CRO emails by default, offset10 denied. This is not339 exact mHSPC phaseIII studies. Do not equate this backend test with automatic host broadening or final-report acceptance. Refresh installed metadata: current host cached the pre-change contact schema/help. Host visual and authenticated end-to-end tests remain open; no claim of OpenAI approval.


## Step30 — Frozen approval, report structure and access clarity (2026-10-07)

Owner authorized signup/login clarification, branded consent, report reordering and readable chart typography. Recovered first screenshot via uploaded file ID; second screenshot unavailable.

Root cause reproduced in isolated Chromium: form POST succeeds but self-only form-action blocks external OAuth callback; submit guard leaves controls disabled. Corrected consent CSP adds only the origin of the exact registered/validated callback, with no wildcard. Browser test then reaches callback. Preserve PKCE/state/expiry/user binding/one-use code. App PR250 includes route/CSP regressions, signup-first OAuth entry, one primary branded connection action and secondary account/cancel links.

Report decision supersedes earlier default hide-all-breakdowns: executive answer2–3 sentences, criteria and primary trial breakdown ONCE, requested categories only with heading/two-sentence summary/chart, final2–3 supported next actions. Public ranking and200–500 cap unchanged. Optional widget uses host-sized text; final-only controls prevent repeated access/actions. Capabilities list distinguishes available filters/evidence/contacts from unexposed protocols/patient documents/full EU history. Existing entitled evidence can contain trial-level operational findings; never infer entity fault.

Payment decision: requested automatic signup→payment/free-versus-paid choice was NOT implemented. Official plugin guidelines rechecked2026-10-07 prohibit digital subscription upsell/checkout initiation, including indirect funnels. Existing paid-account access and neutral entitlement information are allowed. New/unentitled accounts return to free research, not checkout. Source https://developers.openai.com/plugins/plugin-guidelines. Existing pricing/billing untouched; no new backend LLM or paid analysis.

Validation: MCP423 local tests passed/2 DB checks skipped; focused new tests passed. DOM checks validated requested-category display, text escaping, follow-up message and final-only controls. App route lifecycle/CSP tests passed; real Chromium local fixtures reproduced old block and verified corrected navigation. Actual ChatGPT signup/token exchange and UI acceptance still required after deployment. Review release checklist before test handoff/every release.


## Step31 — Seven-field discovery timeout — 2026-10-07

Owner screenshots at 13:59 UTC showed ENGINE_UNAVAILABLE. Correlated database logs showed statement_timeout during FETCH FORWARD 10 FROM selection_profiles, not a database outage. Reproduced: three prostate terms across all seven text fields failed; the same three terms across title/diseases/population succeeded (180 records at investigation time).

Read-only EXPLAIN ANALYZE identified a sequential eligibility-text scan: approximately 18.1 seconds. Splitting the positive cross-field OR into per-field UNION branches used existing trigram indexes: approximately 4.9 seconds. Materializing bounded candidate IDs/match flags before indexed profile retrieval measured approximately 5.1 seconds for the 501-row overflow probe. These are database measurements, not end-to-end ChatGPT benchmarks. The seven-field search matched 828 records including exclusion-text mentions; this is lexical discovery, not 828 clinically relevant prostate trials.

Decision: preserve any/all-term and exclusion semantics, bound candidates to 501 for overflow detection, fetch payloads in batches of ten from one statement snapshot, and keep the hard 500 cap with no partial ranking. Keep existing restricted reader, 15-second timeout and infrastructure plan. Report query/pool timeout as ENGINE_TIMEOUT (504), retaining ENGINE_UNAVAILABLE (503) for database failures. No LLM, billing, OAuth, main App UI or entitlement changes.

Mandatory checks before package download/test handoff and every release:
- [ ] Run PostgreSQL regression for all seven fields, any/all terms across different fields, exclusions, wildcard escaping and duplicate prevention.
- [ ] Confirm query timeout, pool timeout and connection failure have distinct safe error responses without database details.
- [ ] Replay the seven-field production failure: obtain explicit COHORT_TOO_LARGE rather than timeout/outage, with no partial result.
- [ ] Verify a bounded relevant cohort can be searched and ranked anonymously, with no more than ten entities returned.
- [ ] Carry these checks/results into the package branch release guide; do not mark unobserved checks passed.


Validation after deployment: MCP PR87 merged as 5d0e1da44d406fb49c370d92b6cd16db0f192676; Render dep-db358uk9v7es73ccngi0 live at 2026-10-07T14:18:37Z. All 428 CI tests passed, including PostgreSQL. First replay reached draining old instance 8whwl and reproduced its timeout; logs confirm shutdown14:19:36Z. Subsequent replay returned COHORT_TOO_LARGE without partial results. Live broadened title/disease/population search for prostate/bladder/urothelial returned342 trials and462 recorded provider entities; anonymous ranking returned10. This is an operational discovery probe, not a clinical validation of every match; the copied phase3 subgroup label was prostate-specific despite the broader base, so do not reuse it as a reviewed report. No package reinstall or account reconnection is required for this server-side fix. Remaining real ChatGPT UI/OAuth acceptance checks stay open.


## Step32 — Full-list access wording — 2026-10-07

Owner requested a single Access full list button instead of Check my access. Implement that label for all categories; avoid Access full dataset because public tools do not provide dataset exports. Keep counts and the requirement for an existing eligible project covering the cohort visible before connection; signing in alone does not unlock access. On missing entitlement, explain the restriction and retain free research.

Reviewed official https://developers.openai.com/plugins/plugin-guidelines (Commerce and monetization) on 2026-10-07. Existing paid-account access and neutral missing-entitlement explanations are allowed. Informational entitlement links are allowed, but direct/indirect subscription promotion, checkout and pages initiating an upgrade/subscription/purchase are not. Therefore no payment funnel on the hosted connection page or signup redirect. This is implementation guidance, not a guarantee of OpenAI approval.

Reviewed current intel_agent_app app/oauth/authorize/route.ts: existing-project benefits, no purchase on connection/signup, and free fallback are already stated; retain the explicit Connect TrialAgents consent action. No main App, billing or authentication behavior changed. Widget continues to request the host-supported flow and cannot bypass native authorization.

Before every release and package test handoff, verify: one Access full list action only when more results exist; accurate counts/entitlement disclosure; no purchase/upgrade links or signup-to-checkout redirects; unsupported-host text fallback; connected/unentitled accounts retain free use. Recheck current OpenAI guidelines for any later commerce change.


## Account-wide research and saved projects — approved 2026-10-07

Owner approved one branded table for every data response (including evidence/account details), in-row green experience bars, expandable detail in the same table, no duplicate Markdown table when UI renders, and three contextual data actions at the end. Plain Markdown is a single fallback only when host UI is unavailable. Stars are not performance ratings; trial findings must not be attributed to providers without evidence.

Owner superseded project-bound public MCP entitlement: active paid account access grants full lists across selections without matching a licensed project's trial population. Existing live, unrevoked subscriptions with future paid_through and live paid combined_premium purchases qualify; pending/test/refunded/expired payments do not. Existing billing amounts (€490/month and €2,900/year) and Stripe behavior are unchanged in this release. The requested €500/month offer is a separate pending billing rollout; do not claim it is live or change existing contracts automatically. The 500-trial-per-selection ceiling remains technical, not a research-usage quota.

Explicit Save/Open in Intel Agent creates a private, owner-bound snapshot at /research/projects/{id}; /research lists saved snapshots. Save reuses existing deterministic rankings and records criteria, trial IDs, snapshot and requested categories. Identical owner/snapshot/category/contact-mode retries reopen the same project. No automatic saving of every query, public sharing, checkout, extraction, analysis job or LLM call. Contacts respect explicit-request CRO-email policy. App returns only top-ten/redacted evidence to free users; paid full pagination rechecks account access, including after expiry/revocation. Saved research can be reopened through the MCP using its project ID. Stored snapshots do not auto-refresh with new source data. Database payload bound12MiB, maximum3 category selections,500 trials per selection; latest100 project titles listed on website.

Hosted signup/consent now explains account-level access and keeps native OAuth checks; saved-project login return uses an exact same-origin UUID allowlist. Existing OAuth takes precedence. No email is inferred from ChatGPT. Sign in with ChatGPT integration and the new product overview remain separate future work. No digital-subscription funnel is added: existing-account access and neutral entitlement information only, per current OpenAI plugin guidelines.

Mandatory before package test handoff and every release:
- [ ] Real PostgreSQL/PGlite checks: owner isolation, repeat-save idempotency, completeness/size rejection, free ten, paid next page, expiry/revocation and payment states.
- [ ] Tool metadata: saving is an explicit OAuth-protected write; account/evidence/read tools are read-only; anonymous research stays available.
- [ ] One branded table with complete requested details, escaped source text, host-size typography and exactly three supported actions on the final result.
- [ ] Apply additive migration0055 and deploy App before MCP; no LLM/checkout jobs start on save or open.
- [ ] Real ChatGPT new metadata import: anonymous research, evidence widget, account summary, explicit save, private website reopen and MCP revisit. Do not mark host acceptance from unit tests.


## Resume verification — 2026-10-08

Recovered uncommitted account-wide access, private saved-project and branded-table changes. Compared against App main df6b19ac42a97ee95470e390f64c80fb7ca3e7e9 and MCP main db1c63db73c1cef58e988e0e58fdbd5a45061685. Exclude stale local combined-premium.ts, workspace-contract.ts and support/intel/page.tsx from App publication. Preserve current remote code outside the approved file set.

App PGlite account/ownership/idempotency/expiry checks and OAuth lifecycle tests pass. MCP selection and research checks: 38 passed. DOM verification passes for a single branded table, three actions, escaped source content, count-derived bars and host follow-up messages. New widget bundle rebuilt. Whole-repository TypeScript/CI and actual ChatGPT rendering/save/reopen remain release gates.

Publication BLOCKED: automatic approval review rejected GitHub create_tree to tarous89/intel_agent_app, requiring explicit authorization to upload local source to that destination. Do not retry via another tool or route. No PR, merge, production migration or deployment was performed. Ask owner to approve publication and deployment to tarous89/intel_agent_app and tarous89/intel_mcp. Deploy App/migration 0055 before MCP. Existing prices and payment processing remain unchanged; EUR500 billing rollout is separate.

Owner explicitly approved publication and deployment to both repositories on 2026-10-08. The preceding approval block is resolved; App-first rollout and remaining CI/host gates still apply.


## Approved next direction — 2026-10-08

See [ChatGPT workspace direction](CHATGPT_WORKSPACE_DIRECTION.md) for the owner-approved architecture and ordered implementation/acceptance steps. ChatGPT drives cohort selection and recommendations; the backend validates, normalizes and persists evidence. One project feeds the actual Intel Agent CRO/PI/site/trial tables in a preview/extension with an external fallback. Same account access applies to the model and UI; no embedded or directed subscription funnel. This is staged work, not yet the live workflow. Existing explicit save and renderer remain until replacement is verified.

First build increment: paginated candidate inspection, validated source-ID cohort refinement, saved model-attributed selection provenance and exact canonical CRO-name grouping. See the direction document for tests and remaining milestones. Current deployment is unchanged.

Shared-workspace build continued locally on 2026-10-08: four actual App tables, versioned projects/recommendations, expiring preview/claim and MCP extension bridge. See CHATGPT_WORKSPACE_DIRECTION.md for test evidence and exact upload block. GitHub create_tree to tarous89/intel_agent_app was rejected by automatic approval review; no workaround or production rollout is authorized by that rejection.


Approval resolution — 2026-10-08: the owner explicitly approved uploading these changes to tarous89/intel_agent_app and tarous89/intel_mcp, updating the PRs and continuing verification. The preceding source-upload block is resolved. Production migration/deployment and real-host acceptance remain pending.
