
## 2026-10-09 — Website-first account connection
Connect uses openLink immediately; no tool call, project write, or project preparation wait in the embedded workspace. It carries the existing draft in the website URL fragment. After login/signup, the website imports the exact validated snapshot through service-authenticated /internal/research-snapshot and creates the project in the authenticated account. Import progress/retry lives at /projects/sync. The endpoint reads existing source only and never searches or writes projects. Existing source-cache expiry/eviction still applies; a missing source fails explicitly. Legacy model-invoked handoff tools remain for compatibility. Deploy the website support before this new UI.
## 2026-10-09 — Embedded tab recovery and UI resource versioning
A tab click on an unsaved preview reached the persisted-project reader and returned 404. The old resource URI was reused across incompatible client changes, allowing stale host UI caching. Workspace resource IDs now include the actual bundled HTML hash; the legacy URI remains a compatibility alias. Loaded preview tabs switch locally. Optional host context failures cannot fail navigation, and failed remote pages preserve current rows with a table retry action. Browser regression tests run in MCP CI. Website/shared table source is unchanged; this is an embedded client and resource registration fix.


## 2026-10-09 — Read-only initial workspace; save on account connection
Initial `prepare_research_workspace` now computes the embedded preview from the existing short-lived search snapshot without creating a database project, for both anonymous and signed-in users. It is truthfully read-only; host permissions remain authoritative. The UI retains the draft specification and snapshot hash. Explicit Connect account materializes those exact results idempotently, then uses the existing website handoff/login and normal Projects flow. Search expiry/eviction produces an error instead of silently recreating different results. Saved project tools remain compatible. Shared UI distinguishes unsaved search previews from legacy week-long anonymous projects; Dataset stays in the embedded workspace. This supersedes automatic project writes during initial viewing. Actual ChatGPT host acceptance requires a refreshed tool descriptor and host check.
# intel_mcp history

Updated: 2026-10-03. Historical decisions and trade-offs only. Current instructions live in PROJECT_CONTEXT.md or README.md and their linked owning contracts. Entries retain original dates/claims, which are not statements about current production.

## Decisions

- Standalone bounded MCP tools remain active. Managed/combined report execution moved to the App worker and private Engine HTTP/artifacts, preventing a second orchestration/data pipeline.
- Older Intel Light/Max/Workspace and Site products are archived. Their technical allowance names, old schemas and pure ranking functions remain compatibility/current dependencies.
- Dated redesign proposals below are historical, not instructions to reintroduce package run caps, old prices, a separate Site product or standalone managed report workers.

## Previous documents

## site-agent-context-md

Previous `SITE_AGENT_CONTEXT.md`: [original document at the audited revision](https://github.com/tarous89/intel_mcp/blob/862ef4aa6a4337510b86a8d419e4843a75a316f7/SITE_AGENT_CONTEXT.md). Its older offer, milestone or implementation narrative is historical. Use the current owning contract before making changes.

## max-agent-redesign-scope-md

Previous `MAX_AGENT_REDESIGN_SCOPE.md`: [original document at the audited revision](https://github.com/tarous89/intel_mcp/blob/862ef4aa6a4337510b86a8d419e4843a75a316f7/MAX_AGENT_REDESIGN_SCOPE.md). Its older offer, milestone or implementation narrative is historical. Use the current owning contract before making changes.

## intel-agent-workspace-redesign-plan-2026-09-18-md

Previous `INTEL_AGENT_WORKSPACE_REDESIGN_PLAN_2026-09-18.md`: [original document at the audited revision](https://github.com/tarous89/intel_mcp/blob/862ef4aa6a4337510b86a8d419e4843a75a316f7/INTEL_AGENT_WORKSPACE_REDESIGN_PLAN_2026-09-18.md). Its older offer, milestone or implementation narrative is historical. Use the current owning contract before making changes.

## report-execution-context-md

Previous `REPORT_EXECUTION_CONTEXT.md`: [original document at the audited revision](https://github.com/tarous89/intel_mcp/blob/862ef4aa6a4337510b86a8d419e4843a75a316f7/REPORT_EXECUTION_CONTEXT.md). Its older offer, milestone or implementation narrative is historical. Use the current owning contract before making changes.

## project-context-md

Previous `PROJECT_CONTEXT.md`: [original document at the audited revision](https://github.com/tarous89/intel_mcp/blob/862ef4aa6a4337510b86a8d419e4843a75a316f7/PROJECT_CONTEXT.md). Its older offer, milestone or implementation narrative is historical. Use the current owning contract before making changes.


## 2026-10-06: deterministic selection backend pilot

Owner requested an MCP-specific implementation log, validation and deterministic CRO/site/PI tools before ChatGPT packaging. Chose additive opt-in tools and existing approved-only access; preserved old entitlements. Complete bounded cohorts are ranked with direct/related/broader experience and recorded CRO function evidence. Source drift fails explicitly. Reused legacy authorization batching for the pilot, with partial-admission metering documented; a new atomic session/admission API is a rollout gate. No production settings or schema changes.


## 2026-10-09 coordinated account/project UX correction
Owner approved direct website login/signup from Connect, free account choice, automatic exact-result saving and one normal /projects list. Handoff capabilities are short-lived, hashed, same-origin and independent per browser tab; repeat completion is idempotent. Anonymous claim preserves project identity. Only an authorized source-owner handoff can copy an owned snapshot into another chosen account. Current web and MCP sessions remain separate. The normal catalog includes existing research workspaces and legacy snapshots, with canonical /projects routes; /research redirects to /projects. No search rerun, paid job or entitlement change. App migration0058 and endpoint must be deployed before the MCP producer/UI. Actual host acceptance must be recorded separately from automated tests.

## 2026-10-09 — Account connection button recovery
- Advertise standard app/model visibility and ChatGPT widget-access compatibility for workspace tools, including the handoff and saved-page readers.
- Show connection progress above every tab, bound stalled requests, honor open-link refusal, and retain the private handoff in memory for navigation-only retry.
- Guard repeated Account clicks; distinguish expired previews without leaking backend errors or capabilities. Preview generation remains read-only; connection still saves through an annotated write tool.
- Regression coverage: both buttons, Dataset visibility, duplicate clicks, timeout/late reply, host refusal, retry without a second save, and tool metadata.
- Real ChatGPT host acceptance remains required after refreshing cached connection metadata.
