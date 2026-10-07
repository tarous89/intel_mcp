# Owner-approved research iteration — 2026-10-07

Latest requirement: target 200–500 relevant trials; 500 remains the hard ceiling. Broaden through clinically relevant therapeutic area, phase or modality. Preserve explicit mandatory constraints, explain expansions and honest shortfalls; do not pad or silently sample.

Public ranking now uses distinct trials across the whole selected cohort, then stable name/ID ties. Private App ranking is unchanged. Public evidence eligibility uses the same ordering. CRO emails are suppressed by default, including connected results, and returned only on explicit contact requests with a regulatory/source-contact caveat. Initial display omits direct/related/broader breakdown unless requested, shows inventory and experience, includes access disclosure and offers 2–3 data-supported follow-ups.

Inline MCP Apps bars/table use the already-authorized ranking result with no added DB or LLM calls. Text/table fallback remains available. Browser SDK versions: ext-apps 1.7.5, OpenAI extensions 0.1.0; rebuild with npm ci && npm run build under ui/research. No CDN dependencies. UI resource version changes when bundle changes.

Auth companion: intel_agent_app PR249 fixes the ignored OAuth return path, explains consent/account access, adds account switching and safe expiry/replay recovery. Exact cause of the earlier owner expiry incident is not established. No state/PKCE/user-binding/TTL relaxation. No pricing, checkout, billing, new model calls or infrastructure purchase.

## Mandatory pre-test handoff and every-release checks
- [x] Public/private ranking isolation and public evidence eligibility tests.
- [x] Default CRO email suppression and explicit-contact caveat tests.
- [x] Full-list pagination and entitlement enforcement regression tests.
- [x] Inline resource registration and MIME contract tests.
- [ ] Actual ChatGPT inline rendering and plain-table fallback acceptance.
- [ ] Actual ChatGPT 200–500 broadening, scope disclosure and follow-up acceptance.
- [ ] Fresh logged-out login/signup and signed-in account-linking acceptance.
- [ ] Expired/consumed/account-change recovery acceptance in host.

Review the package branch docs/CHATGPT_PLUGIN_RELEASE.md before any package download/test handoff and before every release. Local tests do not establish host acceptance or OpenAI approval.
