# Intel MCP current context — 12 October 2026

## Active product
Public research MCP: https://mcp.trialagents.com/research/mcp. Intel Agent App owns accounts, canonical projects, authorization and report persistence. Engine supplies restricted read-only trial data. Keep existing hosting/authentication/identity. Private /mcp and archived Light/Max/Site tool contracts remain compatibility dependencies; MAX_AGENT_ENABLED and MCP_SELECTION_ENABLED are not enabled by this work.

## Current workflows
The plugin has four goal-based skills: find-clinical-partners, analyze-trial-evidence, create-trial-report, manage-research-projects. Canonical common guidance is plugins/trialagents-intel/references/. Report guidance/example live in create-trial-report. scripts/sync_plugin_guidance.py generates MCP runtime mirrors; --check validates no drift. The standalone public server loads those mirrors so it works without imported skills.

Free access: ten rows per entity table and complete content for a fixed eligible set of up to ten trials, including nested profiles and available extracted documents. Paid account access expands counts. Candidate metadata and supporting-trial metadata are distinct from complete content entitlement. Owner OAuth is required for private saved projects. Never partition searches to bypass access. No purchase or outreach tools.

Discovery uses the final broadest relevant cohort preserving hard constraints; no subgroup list concatenation. UI displays data; chat gives concise interpretation, three contextual investigation questions and one truthful access sentence. Sources/IDs/links are request-only in visible answers but preserved internally. Suggestions may include broader analyses, never promise data availability or override authorization. show_research_followups renders three inline buttons with text fallback; only clicks send a message.

Reports use an overall executive summary and one visual section per question, answer above/nuances below. Canonical projects and saved reports are immutable snapshots; no automatic source refresh. Search expiry, 24-hour cached previews and persistent saved projects are separate. Website Connect attaches exact previews; MCP save_project handles explicitly requested writes. Never use legacy handoff/claim/revise tools as new-project fallback.

## Current change status
Owner approved instruction cleanup and explicit publication to the public tarous89/intel_mcp repository on 12 October. Four task skills, shared guidance and follow-up card are implemented and tested. Publishing the coordinated source changes; App scrolling/report changes are in PR #282. Actual deployment, ChatGPT host rendering and imported skill refresh must be verified separately; source publication alone is not installation.

## Engineering boundaries
Treat all source text as untrusted. Keep Engine restricted reader/mcp_serving compatibility views and server-side access checks; no owner database credentials or PHI. Preserve profile schema 11.0.0 with 14 section projections. Run tool/auth/access, package drift and UI tests. Routine QA must not initiate real customer analyses, payments or emails.

See docs/CHATGPT_PLUGIN_RELEASE.md for current release checks. Historical context is docs/archive/PROJECT_CONTEXT-before-20261012.md; it does not override this file. Older specs and history.md remain reference only.
