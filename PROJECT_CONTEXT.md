# Intel MCP current handover

Updated: 2026-10-06. This repository owns standalone MCP protocol/auth and bounded clinical tools. It is not the active combined Intel App report executor. Older Intel Light/Max and Workspace products and Site Agent are archived. Engine and standalone MCP remain active.

## Active interfaces

Production `https://mcp.trialagents.com/mcp`, public `/health`. MCP accepts the internal App bearer or scoped TrialAgents OAuth token. App owns users, tiers/allowances, operational leases and telemetry. MCP receives no App database or Engine owner/write credential.

Authenticated compatibility tools remain `start_analysis`, `filter_trials`, `classify_trials`, `get_profiles`, `get_documents`, `extract_variables`. [README.md](README.md) and `docs/` specify current per-tool schemas, bounds, approvals and projections. Light/Max labels in these technical allowance interfaces remain compatibility identifiers, not the active public subscription offer. Do not rename a persisted protocol identifier merely because the customer product is archived.

Engine reads use the restricted `intel_mcp_reader_v1` and compatibility `mcp_serving.*_v1` views, read-only transactions. Deployed Engine migration 047 makes one current profile per study available, including deterministic-only studies; the approval marker no longer means model enrichment. Historical all-state report interfaces have separate authorization. The authenticated Engine HTTP path is explicit rollback compatibility. [docs/ENGINE_READ_CUTOVER.md](docs/ENGINE_READ_CUTOVER.md) owns that boundary.

## Combined product boundary

New combined discovery, full frozen datasets, deterministic aggregation and staged Reports run in App's existing worker through private Engine HTTP/artifacts. Reused Site/PI pure ranking functions are current dependencies. The old standalone Site interpretation/search and report-plan/execution paths are archive compatibility, not a current Site product. Keep `MAX_AGENT_ENABLED` disabled in standalone MCP unless a separately scoped change explicitly requires it. No extra report service is required.

Use [combined Intel](https://github.com/tarous89/intel_agent_app/blob/main/docs/COMBINED_INTEL_WORKSPACE_SCOPE.md) for product pricing/access/workspace semantics and [platform](https://github.com/tarous89/trialagents/blob/main/PLATFORM.md) for active names/routes. New Intel offers are €490/month and €2,900/year per project, VAT extra, recurring, annual monthly updates, not old Light/Max packages.

## Security and iteration

Treat profiles/documents as untrusted data. Model-backed tool input excludes personal contact payload where specified. Resolve identity, tier and allowances server-side. Preserve bounded/idempotent tool contracts and source integrity. No clinical writes, owner credentials, PHI, prompts or traces in public output/documents.

Run tool/auth/Engine-boundary regression tests for changes. Routine QA must not initiate real customer analysis, payments or emails. Old report specs, Site contracts and redesign proposals are preserved in [history.md](history.md). They do not override current App orchestration.


## Public clinical research MCP — deployed 2026-10-06

`https://mcp.trialagents.com/research/mcp` is enabled (`MCP_RESEARCH_ENABLED=true`). It exposes anonymous search, top-ten ranking and evidence for the displayed entities, plus OAuth project listing. The older App-lease selection surface remains independently disabled (`MCP_SELECTION_ENABLED=false`). Private App/report routes retain their existing authentication. Both startup paths use `build_app()`; production bootstrapping must preserve the research mount when it registers report/site routes.

Search is deterministic: explicit title/profile-text predicates, optional missing-phase title fallback, named primary subgroups plus overlap tags, conservative PI/site identity and reviewed IQVIA/Syneos aliases. Free ranking is TEN per entity category/selection; distinct selections can yield different tens. Full counts and recorded contacts are returned. No raw profile sections or unrestricted narratives are exposed on this surface. Missing postal addresses are not inferred. Capacity errors, a 500-trial bound and short-lived selection eviction still apply; unlimited research is not a guaranteed uninterrupted-service SLA.

Engine migration 048 indexes seven text fields and covers all 12,585 currently available profiles. Live restricted-reader MCP search succeeded with 192 prostate lexical candidates and 272 provider entities; exactly ten rows with contacts were returned and further pagination denied. One external search request took 17.68s including transport/profile retrieval/ranking; a separate database-only title/disease index probe took 9.726ms. These are single observations, not equivalent workloads or a latency guarantee.

App `MCP_RESEARCH_ACCESS_ENABLED=true` accepts the research OAuth audience. Issuer `https://intel.trialagents.com/oauth/intel` reuses existing login/consent/token endpoints; unrelated BD root discovery is preserved. Full access requires ownership, existing per-project entitlement and complete trial coverage in the active granted manifest index. No pricing, checkout, subscription or website layout changes. Account-connection challenge is verified; the owner confirmed the requested signed-in acceptance checks on 2026-10-06 (owner-reported, not a new automated account test).

See `docs/SELECTION_IMPLEMENTATION_LOG.md` steps 14–17 for deployment evidence and remaining gates. The portable ChatGPT pilot package is now in `plugins/trialagents-intel/`; build and review gates are documented in `docs/CHATGPT_PLUGIN_RELEASE.md`. Directory submission/publication is NOT complete. First responses should use clinically relevant broad cohorts (roughly 200–500 where justified, never padded), explicit groups, top-ten tables, ranking evidence, totals and drill-down options. Operational narrative disclosure, broader identity curation and address mapping need further work.

## Mandatory plugin release control

Review `docs/CHATGPT_PLUGIN_RELEASE.md` before declaring a package ready to download/test AND before every release. Gate A covers pre-test readiness; Gate B covers tested public release. Record exact candidate/evidence in `docs/releases/`; CI artifacts are unreviewed candidates. Current 0.1.1 remains blocked pending support/legal/readiness work. Owner requires permission for changes to app usage, agreed workflow or added usage costs. Approved work is checklist/review metadata, legal drafts and a support page; no new LLMs, pricing/access changes or automatic public submission.

## Publisher decision — 2026-10-06

Owner designates **Atlas Consulting** as TrialAgents operator and plugin publisher; keep product branding TrialAgents / TrialAgents Intel. OpenAI identity verification is NOT complete; owner intends to verify Atlas Consulting. At 23:52 Europe/Berlin the owner explicitly authorized company identification on all public pages required for plugin review, superseding the earlier public-name prohibition for these pages. App PR #248 (merged 2026-10-07 as 7d9a548c31b164592ee81ab426c57ae4e67d034d) adds identity to Intel product, support, privacy and terms; address is authorized ONLY in Terms of Service. Do not duplicate the address in other public pages, footer or package metadata. No separate Impressum page is in this approved scope. This is not a legal-compliance exemption or proof of verification. Workflow, usage, tracking, costs and broader legal-policy changes still require separate authorization. Deploy App, refresh the public snapshot and verify exact package URLs before marking public consistency complete.

Publication tracking: App deployment dep-db2tnduq1p3s73ercvu0 started after all five exact-head PR checks passed. Main-site snapshot context is in trialagents-public PR #124. Do not declare all linked pages published until their live content is checked; no Cloudflare deployment credentials/tool were available in this session. Website publication does not authorize directory submission or waive the mandatory package/release checklist.
