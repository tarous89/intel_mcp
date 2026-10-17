> Superseded: the current upper limit is 1,000 trials (owner-approved October 17); the prior release details below are historical.

# Approved fixes — 17 October 2026

Scope and incident evidence: ../2026-10-17-surgical-review.md.

Tested source: App f2aa38c26371efdcb5c5b368f747f5c3c41d5571 (PR #309); MCP 79aa376372a2d12a85ba48450e74be9f459bd106 (PR #139). This record changes documentation only. The embedded workspace manifest pins that exact App commit.

Local validation: 497 Python tests passed, four PostgreSQL integration tests skipped locally and exercised by CI; seven workspace browser/navigation/bundle checks passed; App TypeScript and focused OAuth/subscription checks passed. MCP CI includes PostgreSQL, memory benchmark, connection/follow-up and browser checks. App CI includes persistence, production build and workspace browser gates. The Public site check required retry after registry throttling before tests began.

Repository package version: 0.7.11. Prepared installed skill overlay version: 1.0.9. SHA-256 of its seven-file ZIP: b71301fe9b8973005cd987371ef6054103da8c6290d0e8f7be89b58209da6ec8. Existing App-bound identity, MCP binding, presentation and omitted files are preserved. The overlay updates discovery to the existing runtime cap of 800 and new minimum of 30, and changes report failure/reopen guidance.

Release sequence: complete candidate CI; merge and verify App auto-deployment; merge and verify MCP auto-deployment; install the guarded skill overlay. Deployment/installation outcomes are recorded in PR release notes. Rollback targets before release: App e227adfb3d7674de30980b89c98d61eec508e5b4; MCP 8aa716f4d16e1d3d421d91aca7209942d8885a84; installed plugin 1.0.8.

Real ChatGPT host walkthrough and warning reproduction were not run. Synthetic browser tests do not establish host acceptance. No customer searches, billing changes, data migrations or public Directory submission are part of this release.
