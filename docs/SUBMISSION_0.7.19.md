# Submission 0.7.19

Owner approved the two navigation fixes, publication to the existing App/MCP repositories and an updated submission package on 18 October 2026.

- The App redirects valid bare `/projects/{uuid}` links on the Intel host to `/projects/{uuid}/sites`, the existing default tab. The temporary 307 preserves query parameters. Explicit tabs, Site Agent routes, legacy query behavior and destination authentication/ownership checks are unchanged.
- Saved canonical Custom view workspaces return `/custom` in both `url` and `custom_url`, including preview references that resolve to an owned project. Tools and packaged/runtime guidance require exact-link reuse; a temporary preview ID does not authorize an account-project link.
- The package carries forward 0.7.18's naming, five skills, listing, three starter prompts, four PNG assets, demo, commerce, targeting, contrast/recovery guidance and review cases. P5 additionally checks returned Custom view links.

No tool names, annotations, storage, recovery, access, renderer, UI bundle or data migration changed. Deferred optimizations and the separate preview read-only / legacy claim destructive annotation concerns remain outside this release.

## Reproduction and release checks

Run `python scripts/sync_plugin_guidance.py --check` and `python scripts/build_chatgpt_plugin.py`. The explicit 28-file allowlist produces `dist/trialagents-intel-0.7.19.zip` without app bindings, credentials, dependencies or unrelated source. Test Custom view save/open URL consistency for owned projects and resolved previews, absent account URLs for temporary previews, and the App redirect across trailing slashes, tracking parameters, explicit tabs and other hosts. CI and production verification are required before release completion.

The existing demo and listing URLs were verified during the same-day 0.7.17 audit and are retained. The dedicated reviewer-account five-positive/three-negative end-to-end cases and submission portal scan have not been rerun for this release. Earlier public-page naming and reviewer/portal requirements remain. This release does not submit the plugin, replace an installed skill snapshot, or guarantee approval.

## Local validation

- Four App routing tests passed, covering default-tab redirects, query retention, explicit tabs, legacy links and host isolation.
- 34 targeted MCP tests passed across Custom view save/open/recovery, canonical projects, package validation and annotations.
- Modified skill validation, guidance mirror checks and whitespace checks passed.
