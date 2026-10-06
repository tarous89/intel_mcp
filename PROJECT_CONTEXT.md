# Intel MCP current handover

Updated: 2026-10-06. This repository owns standalone MCP protocol/auth and bounded clinical tools. It is not the active combined Intel App report executor. Older Intel Light/Max and Workspace products and Site Agent are archived. Engine and standalone MCP remain active.

## Active interfaces

Production `https://mcp.trialagents.com/mcp`, public `/health`. MCP accepts the internal App bearer or scoped TrialAgents OAuth token. App owns users, tiers/allowances, operational leases and telemetry. MCP receives no App database or Engine owner/write credential.

Public tools remain `start_analysis`, `filter_trials`, `classify_trials`, `get_profiles`, `get_documents`, `extract_variables`. [README.md](README.md) and `docs/` specify current per-tool schemas, bounds, approvals and projections. Light/Max labels in these technical allowance interfaces remain compatibility identifiers, not the active public subscription offer. Do not rename a persisted protocol identifier merely because the customer product is archived.

Engine reads use the restricted `intel_mcp_reader_v1` and compatibility `mcp_serving.*_v1` views, read-only transactions. Deployed Engine migration 047 makes one current profile per study available, including deterministic-only studies; the approval marker no longer means model enrichment. Historical all-state report interfaces have separate authorization. The authenticated Engine HTTP path is explicit rollback compatibility. [docs/ENGINE_READ_CUTOVER.md](docs/ENGINE_READ_CUTOVER.md) owns that boundary.

## Combined product boundary

New combined discovery, full frozen datasets, deterministic aggregation and staged Reports run in App's existing worker through private Engine HTTP/artifacts. Reused Site/PI pure ranking functions are current dependencies. The old standalone Site interpretation/search and report-plan/execution paths are archive compatibility, not a current Site product. Keep `MAX_AGENT_ENABLED` disabled in standalone MCP unless a separately scoped change explicitly requires it. No extra report service is required.

Use [combined Intel](https://github.com/tarous89/intel_agent_app/blob/main/docs/COMBINED_INTEL_WORKSPACE_SCOPE.md) for product pricing/access/workspace semantics and [platform](https://github.com/tarous89/trialagents/blob/main/PLATFORM.md) for active names/routes. New Intel offers are €490/month and €2,900/year per project, VAT extra, recurring, annual monthly updates, not old Light/Max packages.

## Security and iteration

Treat profiles/documents as untrusted data. Model-backed tool input excludes personal contact payload where specified. Resolve identity, tier and allowances server-side. Preserve bounded/idempotent tool contracts and source integrity. No clinical writes, owner credentials, PHI, prompts or traces in public output/documents.

Run tool/auth/Engine-boundary regression tests for changes. Routine QA must not initiate real customer analysis, payments or emails. Old report specs, Site contracts and redesign proposals are preserved in [history.md](history.md). They do not override current App orchestration.


## Deterministic selection pilot (2026-10-06)

See `docs/SELECTION_IMPLEMENTATION_LOG.md` and `docs/deterministic-selection.md`. Catalogue/cohort/ranking/evidence code is deployed, disabled by default (`MCP_SELECTION_ENABLED=false`), with existing App analysis permissions and zero backend model calls. Exact source fingerprinting, full-cohort authorization and explicit safety-limit failures precede rankings. Live availability audit passed; missing-field discovery, duplicate identity handling, restricted-account end-to-end validation and dedicated selection sessions/atomic admission remain gates. Do not claim public-tool readiness.

[Clinical selection workflow](docs/CLINICAL_SELECTION_WORKFLOW.md) owns the first-response direction: broad relevant landscape, approximately 200–500 trials where justified (no forced minimum), explicit subgroups, verified entity normalization before counts, top-five tables by default and contextual drill-down options. Structured fields plus title/section evidence must support discovery. This is a specification for later implementation/packaging, not an enabled workflow.

### Selection version 2 implementation (2026-10-06)

Next iteration implements explicit title/profile-text discovery without mandatory structured TA, opt-in missing-phase title fallback, named disjoint subgroups with overlap tags, paginated cohort audit, subgroup ranking/evidence, and top-five defaults. PI alias re-entry is fixed; selection matching is affiliation-aware. A limited source-backed IQVIA/Syneos registry unions distinct trials after legal-entity function filtering. See implementation log steps 10–12 for decisions and limitations. Tools remain disabled pending restricted-reader/latency/clinical gates; no ChatGPT workflow packaging yet. Large-population count-only discovery and campus identity curation are not implemented.
