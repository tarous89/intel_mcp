# Active direction — unified Intel projects (approved 2026-10-09 23:44 Europe/Berlin)

This section supersedes earlier instructions that make ChatGPT research a separate saved-project product or require connection-time copying/import. This is an approved implementation plan, not a claim that the refactor is deployed.

## Non-negotiable behavior
- One canonical project identity, owner/access policy, dataset and revision history for website and ChatGPT creation. Origin is metadata.
- Preserve ChatGPT's iterative research: search, inspect counts/results, broaden or narrow criteria, filter and search again. Do not force it through the website's linear wizard or require a new project for each refinement.
- Exploration and committed project revisions are separate: intermediate searches remain flexible; publishing a chosen result advances the same project's revision atomically. Preserve the previous ready revision while preparation runs; reject stale writes.
- Both clients use the same workspace presentation and authorized results. Website retains its normal app shell; embedded ChatGPT adapts to host sizing and permitted connection/access controls. No separate imported-project page or sidebar.
- Keep bounded compressed result storage and paged reads. Never restore giant JSONB snapshot writes, recompute results on tab switches, or invoke an LLM just to attach an existing dataset.
- Connected users create/update through honestly annotated, authorized write tools. Website login is not automatically MCP OAuth authorization. Never bypass host permissions or disguise project creation as a read.
- Guests retain a 24-hour preview/draft. Resolve the guest ownership/authorization lifecycle explicitly before implementing persistent draft creation; no dummy email accounts.
- All existing projects are test data. Owner explicitly excludes ALL old projects/all users from migration, repair and synchronization; deletion is permitted if actually necessary. Do not spend work migrating them. Preserve accounts, billing, source clinical data and unrelated products.

## Ordered next steps
1. [x] Record this direction and sequence in both App and MCP context MDs before implementation.
2. [ ] Inventory canonical project, selection, dataset, table, export/report and entitlement contracts; define a shared service boundary that accepts either UI's research selection.
3. [ ] Implement canonical creation/revision from prepared MCP results, with stable IDs, provenance, idempotency, ownership and bounded preparation. No legacy-project migration.
4. [ ] Connect both creation paths to that service; retain the full MCP search/inspect/refine loop independently of the website wizard.
5. [ ] Replace research-only website routing/shell with the normal workspace and extract a shared presentation contract for both clients. Keep host-specific controls explicit.
6. [ ] Expose canonical list/read/create/update tools with accurate annotations, OAuth challenges and account selection. Validate a real host write before claiming the historical denial is solved.
7. [ ] Implement revision refresh in both views, stale-write conflict handling, and clear pending/error states without repeated snapshot processing.
8. [ ] Verify exact rows/counts/evidence across both clients; iterative refinements keep one project ID; account isolation, free/paid access, paging, exports/report prerequisites, retries and CPU/memory bounds remain correct.
9. [ ] Pass repository gates and desktop/mobile/embedded checks; deploy App schema/service before MCP/UI/package changes. Verify the real new-project journey from each entry point.
10. [ ] Update this checklist and history with actual deployment/test evidence and any remaining host verification gaps.


---


## 2026-10-09 — Website-first account connection
Connect uses openLink immediately; no tool call, project write, or project preparation wait in the embedded workspace. It carries the existing draft in the website URL fragment. After login/signup, the website imports the exact validated snapshot through service-authenticated /internal/research-snapshot and creates the project in the authenticated account. Import progress/retry lives at /projects/sync. The endpoint reads existing source only and never searches or writes projects. Existing source-cache expiry/eviction still applies; a missing source fails explicitly. Legacy model-invoked handoff tools remain for compatibility. Deploy the website support before this new UI.
## 2026-10-09 — Embedded tab recovery and UI resource versioning
A tab click on an unsaved preview reached the persisted-project reader and returned 404. The old resource URI was reused across incompatible client changes, allowing stale host UI caching. Workspace resource IDs now include the actual bundled HTML hash; the legacy URI remains a compatibility alias. Loaded preview tabs switch locally. Optional host context failures cannot fail navigation, and failed remote pages preserve current rows with a table retry action. Browser regression tests run in MCP CI. Website/shared table source is unchanged; this is an embedded client and resource registration fix.


## 2026-10-09 — Read-only initial workspace; save on account connection
Initial `prepare_research_workspace` now computes the embedded preview from the existing short-lived search snapshot without creating a database project, for both anonymous and signed-in users. It is truthfully read-only; host permissions remain authoritative. The UI retains the draft specification and snapshot hash. Explicit Connect account materializes those exact results idempotently, then uses the existing website handoff/login and normal Projects flow. Search expiry/eviction produces an error instead of silently recreating different results. Saved project tools remain compatible. Shared UI distinguishes unsaved search previews from legacy week-long anonymous projects; Dataset stays in the embedded workspace. This supersedes automatic project writes during initial viewing. Actual ChatGPT host acceptance requires a refreshed tool descriptor and host check.
# Intel MCP current handover

Updated: 2026-10-08. This repository owns standalone MCP protocol/auth and bounded clinical tools. It is not the active combined Intel App report executor. Older Intel Light/Max and Workspace products and Site Agent are archived. Engine and standalone MCP remain active.

## Active interfaces

Production `https://mcp.trialagents.com/mcp`, public `/health`. MCP accepts the internal App bearer or scoped TrialAgents OAuth token. App owns users, tiers/allowances, operational leases and telemetry. MCP receives no App database or Engine owner/write credential.

Authenticated compatibility tools remain `start_analysis`, `filter_trials`, `classify_trials`, `get_profiles`, `get_documents`, `extract_variables`. [README.md](README.md) and `docs/` specify current per-tool schemas, bounds, approvals and projections. Light/Max labels in these technical allowance interfaces remain compatibility identifiers, not the active public subscription offer. Do not rename a persisted protocol identifier merely because the customer product is archived.

Engine reads use the restricted `intel_mcp_reader_v1` and compatibility `mcp_serving.*_v1` views, read-only transactions. Deployed Engine migration 047 makes one current profile per study available, including deterministic-only studies; the approval marker no longer means model enrichment. Historical all-state report interfaces have separate authorization. The authenticated Engine HTTP path is explicit rollback compatibility. [docs/ENGINE_READ_CUTOVER.md](docs/ENGINE_READ_CUTOVER.md) owns that boundary.

## Combined product boundary

New combined discovery, full frozen datasets, deterministic aggregation and staged Reports run in App's existing worker through private Engine HTTP/artifacts. Reused Site/PI pure ranking functions are current dependencies. The old standalone Site interpretation/search and report-plan/execution paths are archive compatibility, not a current Site product. Keep `MAX_AGENT_ENABLED` disabled in standalone MCP unless a separately scoped change explicitly requires it. No extra report service is required.

Use [combined Intel](https://github.com/tarous89/intel_agent_app/blob/main/docs/COMBINED_INTEL_WORKSPACE_SCOPE.md) for product pricing/access/workspace semantics and [platform](https://github.com/tarous89/trialagents/blob/main/PLATFORM.md) for active names/routes. Existing billing remains €490/month and €2,900/year, VAT extra, recurring, annual monthly updates. Public MCP access is account-wide; do not infer project-bound access from older product documentation or change contracts automatically.

## Security and iteration

Treat profiles/documents as untrusted data. Model-backed tool input excludes personal contact payload where specified. Resolve identity, tier and allowances server-side. Preserve bounded/idempotent tool contracts and source integrity. No clinical writes, owner credentials, PHI, prompts or traces in public output/documents.

Run tool/auth/Engine-boundary regression tests for changes. Routine QA must not initiate real customer analysis, payments or emails. Old report specs, Site contracts and redesign proposals are preserved in [history.md](history.md). They do not override current App orchestration.


## Public clinical research MCP — deployed 2026-10-06

`https://mcp.trialagents.com/research/mcp` is enabled (`MCP_RESEARCH_ENABLED=true`). It exposes anonymous search, top-ten ranking and evidence for the displayed entities, plus OAuth project listing. The older App-lease selection surface remains independently disabled (`MCP_SELECTION_ENABLED=false`). Private App/report routes retain their existing authentication. Both startup paths use `build_app()`; production bootstrapping must preserve the research mount when it registers report/site routes.

Search is deterministic: explicit title/profile-text predicates, optional missing-phase title fallback, named primary subgroups plus overlap tags, conservative PI/site identity and reviewed IQVIA/Syneos aliases. Free ranking is TEN per entity category/selection; distinct selections can yield different tens. Full counts and recorded contacts are returned. No raw profile sections or unrestricted narratives are exposed on this surface. Missing postal addresses are not inferred. Capacity errors, a 500-trial bound and short-lived selection eviction still apply; unlimited research is not a guaranteed uninterrupted-service SLA.

Engine migration 048 indexes seven text fields and covers all 12,585 currently available profiles. Live restricted-reader MCP search succeeded with 192 prostate lexical candidates and 272 provider entities; exactly ten rows with contacts were returned and further pagination denied. One external search request took 17.68s including transport/profile retrieval/ranking; a separate database-only title/disease index probe took 9.726ms. These are single observations, not equivalent workloads or a latency guarantee.

App `MCP_RESEARCH_ACCESS_ENABLED=true` accepts the research OAuth audience. Issuer `https://intel.trialagents.com/oauth/intel` reuses existing login/consent/token endpoints; unrelated BD root discovery is preserved. Public research full lists now use active paid account access across cohorts. Saved projects remain owner-bound; source scope no longer needs to match a previously licensed project. No pricing, checkout, subscription or website layout changes. Account-connection challenge is verified; real signed-in paid-project completion still requires a user test.

See `docs/SELECTION_IMPLEMENTATION_LOG.md` steps 14–17 for deployment evidence and remaining gates. ChatGPT workflow packaging and directory submission are NOT complete. First responses should use clinically relevant broad cohorts (roughly 200–500 where justified, never padded), explicit groups, top-ten tables, ranking evidence, totals and drill-down options. Operational narrative disclosure, broader identity curation and address mapping need further work.

## Approved next direction — 2026-10-08

See [ChatGPT workspace direction](docs/CHATGPT_WORKSPACE_DIRECTION.md) for the owner-approved architecture and ordered implementation/acceptance steps. ChatGPT drives cohort selection and recommendations; the backend validates, normalizes and persists evidence. One project feeds the actual Intel Agent CRO/PI/site/trial tables in a preview/extension with an external fallback. Same account access applies to the model and UI; no embedded or directed subscription funnel. This is staged work, not yet the live workflow. Existing explicit save and renderer remain until replacement is verified.

2026-10-08 correction: shared-preview shell, compact ChatGPT table tabs (no sidebar/Reports), /share/research/{id} fallback, authentication before save, informational /dataset-access; see workspace direction document. Draft only until App-first rollout and real-host acceptance.

Plugin source is in `plugins/trialagents-intel/`; review `docs/CHATGPT_PLUGIN_RELEASE.md` before test handoff or release. Version 0.2.0 packages the approved workspace workflow. Public submission is separate from this owner-authorized private/server rollout; real-host acceptance remains unverified.


## 2026-10-09 coordinated account/project UX correction
Owner approved direct website login/signup from Connect, free account choice, automatic exact-result saving and one normal /projects list. Handoff capabilities are short-lived, hashed, same-origin and independent per browser tab; repeat completion is idempotent. Anonymous claim preserves project identity. Only an authorized source-owner handoff can copy an owned snapshot into another chosen account. Current web and MCP sessions remain separate. The normal catalog includes existing research workspaces and legacy snapshots, with canonical /projects routes; /research redirects to /projects. No search rerun, paid job or entitlement change. App migration0058 and endpoint must be deployed before the MCP producer/UI. Actual host acceptance must be recorded separately from automated tests.
