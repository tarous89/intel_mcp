# Unified Intel project implementation contract

Approved direction: 2026-10-09. Existing projects are test data and are outside this refactor. No migration, recovery or deletion is required. Accounts, billing and source clinical data are not test data.

## Identity and research
Use public.projects plus combined_intel.projects as the only saved project identity for both entry points. Origin is metadata, not a second project type. Saved selections/datasets remain immutable revisions under that ID. Remove new writes to research_workspaces only when both creation paths and reads use the canonical service.

Keep search_research_trials, count/inspection, filtering, broadening/narrowing, subgroup rules, ranking and evidence exploration independent of the website wizard. Do not replace MCP base predicates with the website's full therapeutic-area union. An intermediate search is not a committed project revision. A committed refinement advances the same project, with expected-revision conflict detection and idempotent retries. Previously ready results remain readable until the next complete revision is published.

## Frozen input
MCP already holds the full captured trial profiles in SelectionDataset.records. A new private intel-prepared-selection-1 input freezes:
- exact criteria, including text rules, exclusions, countries, dates and subgroup definitions;
- selection snapshot and source rationale;
- complete selected trial membership;
- original profile/schema and direct/related/overlapping subgroup membership;
- byte-verified JSON records, with content hashes explicitly distinguished from Engine source revision IDs.

The serializer and validator feed the private cache intake and canonical prepared-source service. They must never be returned as model/widget output. Table results/recommendations must accompany the prepared selection and retain their exact ordering and evidence associations; do not rerank on connection.

Validate all four table cohorts against frozen membership before persisting anything. Retain existing 500-trial/16 MiB source bounds and 64 MiB total result bound. Store full profiles and result pages as bounded compressed objects, not giant JSONB parameters. Reserve the preview ID as a proposed project ID; resolving collisions/claims must remain owner-bound and transactional. A preview alone is not a saved project.

## Service integration order
1. Add canonical prepared-selection intake and durable bounded source storage. Define a real storage contract; do not fake Engine artifact URLs or readiness.
2. Add atomic owner-bound canonical create/revise with an idempotency key, request hash, expected revision and complete source pointer. Browser clients cannot submit arbitrary clinical source snapshots.
3. Publish valid immutable dataset artifacts using the App-owned worker. Native reports require full profile chains plus membership and manifest hashes. Reuse frozen profiles, with no fresh search, LLM or duplicate clinical extraction on account connection.
4. Give ready table pages a clearly defined lifecycle while report artifacts prepare. A dataset must not be advertised as report-ready until its actual manifest/profile chain passes validation.
5. Make website and MCP read the same dataset revision through the same access policy. Preserve approved account-wide MCP access; resolve project-bound website billing without silently granting access or changing subscriptions.
6. Route canonical projects through the normal website shell. Extract a transport-independent presentation used by both clients; only host controls and permitted banners differ.
7. Add explicit OAuth-protected create/update tools, canonical list/read, and account connection returning to Projects. Do not disguise writes as reads or assume website login grants MCP OAuth.
8. Preserve guest 24-hour preview caching. Attach frozen data after authentication without rebuilding it; expired previews must not silently substitute a new search.
9. Refresh latest revision on focus/navigation and bounded polling where needed. Do not pin all future requests to the original revision. Cancel stale requests and stop background polling when hidden.
10. Retire old project-type routing from the new journey, without migrating old projects.

## Verification and rollout
Required before deployment: same ID and exact rows/counts/evidence across both clients; refine/broaden/narrow and retry retain that ID; two-account isolation; stale-write conflict; no partial revision publication; entitlement expiry; export/report completeness; bounded memory/SQL payloads; 24-hour cache retention across restart; native/mobile/embedded UI checks.

Deploy App schema/service before dependent MCP/UI. Actual ChatGPT write acceptance must be checked separately from tool descriptors and unit tests. The previous historical host denial remains unproven; current permissions do not establish a blanket write prohibition.

## Current evidence
- Canonical prepared-source storage, owner-bound create/revise, idempotency and revision checks are implemented. New frozen previews attach directly to public.projects / combined_intel.projects; legacy projects are untouched.
- Website and MCP read canonical project IDs. The website keeps its normal shell and uses the shared tables. Cached rows are immediately readable while the existing worker publishes frozen profile/report artifacts, without Engine search or model calls.
- Explicit OAuth save_project, open_project, list_projects and durable read_project_preview are implemented. Legacy write tools are compatibility-only and hidden from model discovery.
- Search/inspect/refine/prepare remain independent of the website wizard. Preview cache lasts 24 hours; saved source is retained independently. Previous ready datasets remain visible during refinement.
- Local verification: 447 MCP tests passed (4 skipped); canonical database creation/refinement/isolation/expiry journey, shared table rendering and resumable prepared worker tests passed. The synthetic canonical connection took 28 ms; this is not a production latency guarantee.
- Repository CI, deployment and real-host rendering/OAuth write verification remain pending at this checkpoint. Historical host denial is not proven resolved by tests.
- No old projects were migrated, repaired or deleted. Deploy App schema/service before MCP/UI/package.
