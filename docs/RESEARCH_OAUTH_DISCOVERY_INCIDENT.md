# Research OAuth discovery incident — 2026-10-07

Owner ChatGPT test opened `/api/mcp/bd/oauth/authorize` and displayed `Invalid OAuth resource` before login. This is an OAuth routing failure, not evidence of missing subscription or invalid account credentials.

Live investigation: research tools/list succeeds anonymously and advertises mixed noauth/OAuth for search/rank/evidence. `/research/.well-known/oauth-protected-resource` advertises the correct research resource and `/oauth/intel` issuer; both issuer discovery variants work. The RFC 9728 path `/.well-known/oauth-protected-resource/research/mcp` returned 404. Root resource metadata instead describes legacy `/mcp` with the root App issuer, whose authorization metadata points to BD. That fallback is a plausible explanation of the screenshot; client configuration/cached discovery has not been inspected.

Fix: add the research-specific well-known route before the legacy root mount. Preserve root metadata and all existing auth/entitlement boundaries. Regression checks require matching research resource/issuer via both discovery routes and retain private `/mcp` rejection. No app usage, workflow, price, tracking or LLM-cost change.

After deployment: verify the new route live, refresh or recreate only the TrialAgents Intel Test custom connection using `https://mcp.trialagents.com/research/mcp`, and retest anonymous research before account connection. If OAuth is requested, it must open `/oauth/authorize`, never `/api/mcp/bd/oauth/authorize`. A renewed client registration may be needed because the old client was registered with BD. Do not change URL parameters or weaken resource validation to reuse it. Successful discovery is not an end-to-end OAuth test; owner must confirm the ChatGPT flow.

Reference: https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization .

## Follow-up: anonymous tools prompted for account connection

The next owner screenshot reached the clinical `/oauth/authorize` route but showed
“Approval expired”. Correcting discovery did not establish an anonymous-first
ChatGPT experience. Do not treat a successful tools/list HTTP status as that proof.

Investigation found that SDK 2.x emitted security schemes only under `_meta`;
the top-level `securitySchemes` field was absent. OpenAI's auth guide specifies
the top-level declaration and says an omitted array inherits server defaults.
This is a concrete metadata defect and a likely cause of premature linking;
the installed client's configuration/cache still needs an end-to-end retest.

Decision: preserve both declarations in serialized tools/list responses.
Search, ranking and evidence declare noauth plus optional OAuth. Project listing
remains OAuth-only. Implement a research-scoped list-result serializer because
the Python SDK Tool model drops extension fields. Do not change the legacy MCP,
app login, token validation, entitlements, pricing, ten-result cap, or LLM usage.

Release/retest checklist (required before download/testing readiness and every release):
- [ ] Run regression tests for HTTP-wire securitySchemes and compatibility mirror.
- [ ] Verify deployed anonymous tools/list includes noauth for all three research tools.
- [ ] Confirm anonymous search, ranking and evidence work with the ten-result boundary.
- [ ] Confirm private MCP and paid-project access still require authorization.
- [ ] Refresh the test app's tool metadata and test a fresh ChatGPT conversation without a TrialAgents login.
- [ ] First research must not redirect to TrialAgents or require account connection.
- [ ] Test voluntary account connection separately; an expired approval is not evidence the free tier needs login.
- [ ] Review the broader plugin publication checklist; this repair alone does not make the package submission-ready.

Reference: https://developers.openai.com/plugins/build/auth .
