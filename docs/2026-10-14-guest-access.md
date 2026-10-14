# Guest entry and seven-day previews — 2026-10-14

Owner approved implementation and publication. Plugin activation should use mixed authentication without mandatory account login; explicit workspace Connect/logo actions retain the existing OAuth-first flow and website fallback. Invalid credentials may access only allowlisted guest calls with no account identity and no project ID; private actions still require valid OAuth. Never convert an account operation into a guest write.

Guest previews and unsaved Custom views use a seven-day database lifetime. No new workspace footnote. Search-selection and in-memory cache limits are unchanged. New default applies to newly stored previews; existing records keep their recorded expiry and expired previews are not bulk revived. Existing stream retry expiry behaviour is retained with the new duration.

App migration 0069 changes preview retention and makes report receipt deletion cascade. Existing periodic maintenance runs regardless of import queue activity and removes expired previews/reports with their receipts, preserving saved-project references. Publish App/migration before MCP. Shared UI bundle is unchanged; account Connect remains click-triggered.

Expected impact: at steady traffic guest-preview disk storage can approach seven times the previous one-day amount. No additional research/model calls or polling. Expired-token fallback buffers at most 2 MiB to inspect public JSON-RPC requests; private, malformed, oversized and batch requests still require valid auth. Database cleanup can briefly delay an import during the hourly maintenance pass. No background/staged-loading optimizations were added.

Validation: MCP suite 487 passed, 4 PostgreSQL integration checks skipped locally. App synthetic import/retention/cleanup test passed, including report receipt cascade and preservation of claimed projects. 53 MB synthetic ingestion passed under the 160 MiB heap limit. Registered ChatGPT app auth mode and actual host install/decline/reconnect acceptance are not verified by these tests.

Release gates: exact-commit CI; App-first rollout; main-site privacy snapshot refresh; configure the registered app for mixed auth and refresh its imported metadata/skills; verify fresh install, declined reconnect, guest Custom views and explicit account claim in the real host. Portable mcp.json alone does not prove the existing app registration changed.
