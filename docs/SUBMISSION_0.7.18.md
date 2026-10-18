# Submission 0.7.18

Owner approved repository publication and the updated submission package on 18 October 2026. This release resolves the three routing/idempotence findings discussed after the 0.7.17 audit.

- Final new results use `publish_research_workspace`. `prepare_research_workspace` remains available for deliberately unsaved exploration.
- Cached-preview Connect descriptions match host-authorized `save_project`, explicit chat continuation and retained website import. Older previews retain their website path; website login does not establish MCP OAuth.
- Only `publish_research_workspace` changes its annotation to `idempotentHint=false`. Connected-account deduplication remains intact, and guest calls retain independent private preview capabilities. Recovery instructions reuse an available retained draft.

No storage, caching, recovery, authorization or UI implementation changed. Other tool annotations remain unchanged. No deferred optimization or guest retry redesign is included.

## Reproducible package

The repository manifest is now 0.7.18, based on the delivered 0.7.17 metadata. It preserves the original listing, three starter prompts, four owner-supplied PNG brand assets, demo link, commerce declaration and worldwide targeting. It also retains 0.7.17's corrected recruitment-status and Custom view review expectations. Five current skills, supporting references and HTML examples are shipped.

Run `python scripts/build_chatgpt_plugin.py` after installing this repository's dependencies. The explicit allowlist produces `dist/trialagents-intel-0.7.18.zip` with 28 files. The public ZIP includes no registered-app binding, reviewer credentials, dependencies or unrelated repository files. The builder validates the PNG assets and the distinct positive/negative review-case field shapes. Guidance mirrors are checked with `python scripts/sync_plugin_guidance.py --check`.

## Validation and review status

- 41 targeted tests passed locally across package, publication retry/guest isolation, workspace, restoration, canonical project, Custom view contract and project report coverage.
- The modified project-management skill passed frontmatter validation; guidance mirrors and whitespace checks passed.
- Candidate tool metadata retains 38 tools. Compared with the live contract captured during the 0.7.17 audit, only publication's idempotence annotation and the three intended tool descriptions changed.
- The public demo and listing URLs were checked during the same-day 0.7.17 audit and are preserved. The dedicated reviewer-account end-to-end cases and submission portal scan have not been run for this release.

The separate concerns about preview persistence being annotated read-only and legacy claiming being annotated non-destructive remain unresolved by this narrowly approved release. Existing public-page naming inconsistencies and reviewer/portal checks also remain. This package is not a guarantee of approval; refresh the portal's live tool scan after deployment before submitting it. The ZIP alone does not deploy MCP metadata or replace an installed skill snapshot. No public submission is performed by this release.
