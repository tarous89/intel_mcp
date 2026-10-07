# Research OAuth discovery incident — 2026-10-07

Owner ChatGPT test opened `/api/mcp/bd/oauth/authorize` and displayed `Invalid OAuth resource` before login. This is an OAuth routing failure, not evidence of missing subscription or invalid account credentials.

Live investigation: research tools/list succeeds anonymously and advertises mixed noauth/OAuth for search/rank/evidence. `/research/.well-known/oauth-protected-resource` advertises the correct research resource and `/oauth/intel` issuer; both issuer discovery variants work. The RFC 9728 path `/.well-known/oauth-protected-resource/research/mcp` returned 404. Root resource metadata instead describes legacy `/mcp` with the root App issuer, whose authorization metadata points to BD. That fallback is a plausible explanation of the screenshot; client configuration/cached discovery has not been inspected.

Fix: add the research-specific well-known route before the legacy root mount. Preserve root metadata and all existing auth/entitlement boundaries. Regression checks require matching research resource/issuer via both discovery routes and retain private `/mcp` rejection. No app usage, workflow, price, tracking or LLM-cost change.

After deployment: verify the new route live, refresh or recreate only the TrialAgents Intel Test custom connection using `https://mcp.trialagents.com/research/mcp`, and retest anonymous research before account connection. If OAuth is requested, it must open `/oauth/authorize`, never `/api/mcp/bd/oauth/authorize`. A renewed client registration may be needed because the old client was registered with BD. Do not change URL parameters or weaken resource validation to reuse it. Successful discovery is not an end-to-end OAuth test; owner must confirm the ChatGPT flow.

Reference: https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization .
