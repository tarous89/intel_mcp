# Browser table and login correction — 2026-11-06

Shared App source: 744e322e23a5660da295e9e06464f61618b78ece.

Removed narrow-screen table-to-card rules. Sites and PIs retain their column geometry, headers and table-local horizontal scrolling; CROs and Trials retain their existing shared row layout. Sticky name cells and corresponding headers preserve identity when scrolling. OAuth authorization now redirects signed-out users to mode=login, retaining the exact validated continuation; signup remains available.

Rebuilt MCP workspace from the recorded App source. Retained the previous resource URI as a compatibility alias so existing installed tool snapshots can read the updated UI.

Validation: OAuth journey regression passed (login redirect, continuation, account binding, expiry, denial and single-use approval). Thirteen bundle/browser/connection checks passed; layout covers all four categories at 1280, 900, 760 and 420 px. Explicit disclosure and navigation regressions passed separately. Plugin guidance sync check passed. Browser screenshots use synthetic data. Actual ChatGPT installation and a fresh account OAuth round trip remain owner acceptance checks.

Owner-supplied browser package v0.7.26 is the distribution source for v0.7.27, preserving .app.json, its app ID, all five skills and existing assets. Only plugin version and release notes change. The older portable MCP package in this repository is not substituted for that working browser package. Public review submission is not performed by this release.

