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
