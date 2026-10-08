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
