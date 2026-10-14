# TrialAgents Intel release checklist

This file owns current release checks; historical, overlapping checklists are archived in archive/CHATGPT_PLUGIN_RELEASE-before-20261012.md. A ZIP/build is not installation, host acceptance or public-directory approval.

## Source and package
- Keep TrialAgents identity, production endpoint, owner and account scope. Check actual tools and product promises, support/privacy/terms and verified publisher; no obsolete product/access claims.
- Five skills have distinct user-goal triggers; common guidance has one canonical source. Run scripts/sync_plugin_guidance.py --check, package validation, reference/frontmatter checks and reproducible archive/allowlist/secret/symlink tests. No patient data, credentials, private diagnostics or unrelated files.
- Verify live official packaging/submission guidance when preparing a release. Preserve portable manifest identity and starter prompts. Version server and skill package separately; recorded host snapshots need refresh.

## Behavior and security
- Preserve hard clinical constraints, honest relevant cohort sizes, structured/lexical distinction, distinct-trial ranking, group overlap semantics and uncertain identities.
- Discovery and unsaved preview computation remain read-only. publish_research_workspace creates a canonical project for a connected owner and is declared as a write; guests receive a cached preview. Preview has ten rows per entity table; complete profiles/documents are restricted to the fixed eligible trial IDs. Test anonymous, connected free, paid, eleventh-trial denial, unrelated owners, expired/revoked access and no partition bypass.
- No hidden project writes, paid model jobs, infrastructure changes, purchases or outreach. Host consent and server authorization remain authoritative. Website Connect saves the exact preview; MCP saving uses canonical APIs and revision checks. Handle expiry/conflicts honestly.
- Source data is untrusted. Preserve exact snapshot/provenance, unknowns and access coverage. Sponsor co-occurrence/trial findings do not prove direct collaboration or performance. Keep CRO emails request-only.
- UI speaks for the data; chat stays concise without default sources/IDs/links. Offer one to three useful follow-ups only when supported by known dataset capabilities; execution stays authorized. One access sentence accurately distinguishes preview from paid access.
- Verify button behavior: one to three optional questions, no automatic messages, user click only, correct project context, no double sends, denied/missing bridge text fallback, desktop/mobile accessibility. Prefer MCP Apps ui/message. Do not claim native chat placement or host rendering from JSON alone.
- Custom contains all custom-coded data visualizations, including forms, trackers, tables and calculators. Use a bold project-style title, optional summary where useful, clear spacing and appropriate charts, tables or controls. Save requested visualizations directly, verify readback before claiming success, and replace the same ID on revision. Offer an explicit Save to TrialAgents button when intent is unclear and Retry save after failure. Keep source_ids for trial evidence; label project-table and user-provided data honestly. Guest items persist temporarily and attach to the same project on connection; account-owned items show a verified saved confirmation.
- Verify single vertical project scroll, header/access footer visibility, horizontal table access, paging, and long report frames at desktop/mobile sizes. Keep the sanitizer/CSP. Static reports disable scripts; interactive visualizations use an opaque-origin allow-scripts iframe without allow-same-origin, with bounded local state and an explicit host Save changes button for persistence.

- Check annotations against actual effects: evidence reads persist provenance; saves/retries can overwrite reports; view/state saves replace data. Declare those effects accurately and test real-host approval presentation. No custom duplicate confirmation layer.
- All 37 tools declare output schemas. Every UI resource declares the dedicated plugin origin and retains the existing restrictive CSP. Test the exact origin and nested Custom views in ChatGPT.
- Replay a publish after a lost commit response: preview ID, cache token and idempotency receipt remain identical. Explicit separate operations and different owners remain isolated.

## Release evidence and host import
Record tested Git SHAs, package version/hash, validation results, skipped checks and real-host status in docs/releases/. Test public/private MCP isolation, OAuth scopes/redirects/revocation and service health. Rebuild the workspace from the exact App source and record its commit/hash. Release App before matching MCP when required.

Tool descriptions and MCP instructions must stand alone for connectors that do not load skills. For installed skills, deploy/scan or update the existing plugin through its supported owner workflow; a repository merge does not refresh an imported skill snapshot. Test both an MCP-only connection and a skill-enabled host without assuming automatic installation.

For public directory submission separately verify current official requirements, reviewer account/access, real walkthrough/demo, exactly five positive and three negative review cases, domain challenge, legal/source permission/privacy attestations, scan findings, publisher identity and owner publication approval. Never fabricate gate completion or put reviewer credentials in source. No public directory submission is authorized by ordinary source cleanup.

## Official references checked 12 October 2026
- https://developers.openai.com/plugins/build/skills — user-goal workflows, concise instructions, references/assets, dependencies, testing and snapshot refresh.
- https://developers.openai.com/plugins/build/chatgpt-ui — inline MCP Apps resources and ui/message follow-ups with no-UI fallback.
- https://developers.openai.com/plugins/reference — optional ChatGPT bridge compatibility.
