# TrialAgents Intel ChatGPT plugin release

## Mandatory release checklist — review before test handoff AND every release

This guide is the source of truth for release readiness. **Review every item before declaring any ZIP ready to download and test, and again before every release, including updates.** A successful build or CI artifact is an unreviewed engineering candidate, not permission to distribute or publish. Never carry a previous release's sign-off forward automatically.

Two gates avoid circular requirements:
- **Gate A — ready for owner testing:** complete all A items, review every B item and record its owner/blocker. B-only activities such as recording the tested walkthrough can remain pending. Do not call the package ready for testing while an A item is unresolved.
- **Gate B — ready for public release:** repeat A against the exact candidate, complete all applicable B items, and record evidence. Approval by OpenAI and the owner's publish decision are separate final requirements.

Use a dated release record under `docs/releases/` containing version, Git SHA, ZIP SHA-256, reviewer, item-by-item PASS/BLOCKED/NOT APPLICABLE with evidence/reason, remaining owners and both gate decisions. Do not mark unobserved behavior passed. Changes to package, endpoint, public pages or entitlements after sign-off invalidate affected checks. Never put credentials, private reviewer data or patient data in these public records.

### A — product, naming, sources and access consistency

- [ ] A01 Compare product UI, website, support/legal pages, README/context, skill, tool descriptions, examples and listing: same active product and service, no archived Max/Site Agent functionality presented as current.
- [ ] A02 Use TrialAgents Intel for the plugin and explain its relationship to Intel Agent/TrialAgents; verified developer identity must match the actual verified publisher, not an assumed brand/legal name. Domains, logos, contacts and source links must identify the same service.
- [ ] A03 Compare every advertised capability with exposed tools and accessible output. Do not promise raw profiles, operational narratives to anonymous users, outreach, saved lists, trial-list exports, performance or recruitment capacity where unsupported.
- [ ] A04 Confirm source provenance and permission to use/distribute underlying CTIS-derived data and professional contacts. Do not present the plugin as an official CTIS/EMA connector or endorsement. Separate record-derived facts, lexical matches and interpretations; never assert worldwide completeness.
- [ ] A05 Check cohort rules: explicit hard constraints, justified broadening, candidate labels, missing/contradictory phase handling, distinct primary groups versus overlaps, conservative identity normalization, true counts and deterministic ranking. Target a relevant 100–500-trial exploratory landscape; if below 100, verify justified broadening or a documented constraint/relevance exception. Never pad counts or guarantee ten when fewer exist.
- [ ] A06 Verify that every initial report shows displayed/total entity counts and the neutral access_info.message, including existing-account connection and required entitlement. Describe ten per category per selection, not ten lifetime results or ten trials. Legitimate new queries may return different tens; do not harvest partitions to bypass restrictions. Evidence pagination for visible entities is distinct from entity-list pagination.
- [ ] A07 Anonymous use collects no account email by virtue of being anonymous. OAuth connection alone does not grant full access; ownership, entitlement and complete cohort coverage are required. Missing/expired/revoked/uncovered access must remain denied server-side.
- [ ] A08 Confirm website/plugin access and service claims are consistent; same entitlement must not receive an intentionally inferior ChatGPT service or ChatGPT-only surcharge. Compare actual included features; explain the plugin's narrower supported surface rather than claim complete app parity.
- [ ] A09 Keep neutral access explanations and existing-account connection distinct from digital upsells. No checkout links, upgrade initiation, subscription promotion or price advertisements in listing/workflow. Review all account redirects, not only tool names. Do not change the agreed access model without owner permission.
- [ ] A10 Obtain explicit permission before changing app usage, agreed plugin workflow or anything adding usage cost (including LLM calls). Record approved scope. No backend LLM addition, infrastructure purchase or paid reviewer subscription merely to satisfy this checklist.

### A — public information, privacy and security

- [ ] A11 Verify live support/privacy/terms URLs are accessible without login, accurate and production wording. Remove obsolete Max Report/€450 language and unfinished legal placeholders only after factual review. Correct documentation, not commercial terms by accident.
- [ ] A12 Reconcile privacy text with actual collected AND returned fields: user requests, public PI/contact/affiliation data, project/account metadata, processors/recipients, retention timelines and user controls. Verify hosting/security logs separately from the 15-minute selection cache; do not invent deletion guarantees.
- [ ] A13 Provide a working support contact and useful support page covering connection, access, expired selections, missing data and correction/privacy requests; do not ask users to email secrets or patient information.
- [ ] A14 Inventory nested outputs for unnecessary identifiers, hashes, telemetry or personal information. Justify necessary selection/entity/project IDs used by tool calls; identify unnecessary fields for an owner-approved change rather than silently altering contracts.
- [ ] A15 Validate source-content injection boundaries and least-privilege database/account access. No arbitrary SQL, chat-history collection, patient-level data requests, tokens or secrets in model output/ZIP/log evidence. Scope public professional contact disclosure to relevant results.

### A — package and deterministic verification

- [ ] A16 Check current official package/submission rules and record check date. Include plugin.json, mcp.json, skill/references and owned icon at correct paths; meet current name/description/prompt/image limits. Do not label an unfinished demo production-ready.
- [ ] A17 Ensure descriptions accurately state when each tool is used, limitations, input/output scope and side effects, with no manipulative selection language, hidden operations or exaggerated superiority claims.
- [ ] A18 Inspect actual advertised readOnlyHint/destructiveHint/openWorldHint booleans per tool. Explain temporary cache versus persistent state; externally hosted does not automatically mean open-world. Keep a rationale ready and resolve portal findings. Official sources currently conflict on whether justifications are mandatory; verify portal behavior each release.
- [ ] A19 Provide exactly five positive and three negative review cases; each must work from a fresh chat or explicitly state complete setup. Use observable assertions, not brittle entity IDs/counts or expiry-sensitive saved selections. Cover anonymous, evidence, hard constraints, OAuth/full coverage and access bypass.
- [ ] A20 Run package validation, contract/regression checks appropriate to changes, reproducible ZIP build, allowlist/secret/symlink checks and inspect archive contents. Record skipped tests and artifact hash. CI alone cannot establish OpenAI approval.
- [ ] A21 Check production endpoint health, OAuth discovery/scopes/redirects and intended public/private route isolation. No paid analyses, purchases or emails in routine QA. Use synthetic/local fixtures where adequate.
- [ ] A22 If no custom UI, do not invent widgets, screenshots or CSP work. For a future approved UI: accessibility, desktop/mobile layout, exact CSP origins, no unnecessary third-party iframes, and current screenshot dimensions/count must all be reviewed.

### B — tested candidate and submission

- [ ] B01 Run the exact packaged workflow in supported ChatGPT desktop/mobile and other targeted surfaces. Test all submitted prompts, absent data, ambiguous criteria, empty/oversize cohorts, timeout/busy errors, expiry and retries. Record actual evidence; owner confirmation of an earlier app journey is not this package test.
- [ ] B02 Provide a dedicated preconfigured reviewer account/project with enough authorized sample data and entitlement. No inaccessible email/MFA, new signup, payment or additional setup required. Do not weaken production auth globally. Store credentials only in secure dashboard fields.
- [ ] B03 Check verified developer identity, permissions and eligible OpenAI project. Current MCP guidance excludes EU-residency submission projects; verify current rule. This does not authorize moving TrialAgents data or changing database hosting.
- [ ] B04 Host the exact dashboard-issued domain challenge without overwriting another integration's challenge. Connect the production universal MCP URL and complete a fresh tool scan; verify the scanned snapshot matches the candidate.
- [ ] B05 Wait for required metadata/skill/security scans and resolve required errors. Upload acceptance is not final submission acceptance. Explain every remaining finding or fix it; do not ignore findings as alternative rejection choices.
- [ ] B06 Supply a reviewer-accessible walkthrough video showing real core cases and account access; validate URL access. Review legal attestations, country targeting, publisher/support links and any UI-specific materials. Video can follow testing, not final submission.
- [ ] B07 Freeze and record candidate package/server versions and review case ID. Only one review is active per plugin; cancel/revise the existing draft when necessary rather than creating duplicates. Keep reviewer access valid for the review window.
- [ ] B08 On rejection, address each applicable finding or appeal with evidence in the original review email thread and case ID. If replies fail, use support with the case ID. Community reports include platform glitches and multiweek queues; no approval-time guarantee or expedited-review promise.
- [ ] B09 Verify OpenAI approval, then obtain/confirm the owner's publish authorization and explicitly publish. Approved is not published; published is not featured. Check exact-name/direct-link discovery after publication.
- [ ] B10 Before every subsequent release, repeat this checklist: ZIP/skill changes require version review; live MCP updates must preserve compatibility during scans. Maintain rollback, support ownership and a record of changes. Do not treat previous approval as permission for new capabilities.

## Research learnings and sources (checked 2026-10-06)

Official requirements take precedence over forum anecdotes. These sources do not provide rejection rates or an exhaustive taxonomy. Reduce avoidable rework; do not promise a fast queue.

| Finding | Evidence | Release response |
|---|---|---|
| OAuth/test credentials fail reviewer access | [June OAuth rejection report](https://community.openai.com/t/platform-openai-app-submission-glitch/1382472) | B02: preconfigured independent access |
| Branding differs from verified publisher; annotations mismatch | [May repeated rejection discussion](https://community.openai.com/t/understanding-the-rejecting-conditions-on-a-chatgpt-app-clarification-needed-on-rejection-feedback/1380927) | A02/A18; prefer current annotation rules over older forum network-only advice |
| Incorrect expected outputs, CSP findings, stale validation and resubmission bugs | [Submission improvements and developer reports](https://community.openai.com/t/app-submission-flow-improvements-roundup/1379047) | A19/B01/B04: exact reproducible cases and current scans |
| Privacy, returned data, commerce, manipulative metadata and safeguards can all be flagged together | [Multiple rejection reasons](https://community.openai.com/t/multiple-rejection-reasons-are-these-and-or-or/1377982) | Audit every applicable finding, not just one |
| Queue delays can persist despite fixes | [Six-week queue reports and support response](https://community.openai.com/t/chatgpt-app-review-pending-for-6-weeks-is-this-normal/1388077) | B07/B08; retain case ID and avoid guaranteed dates |
| Upload checks differ from final review; no custom UI required | [Submission errors](https://developers.openai.com/plugins/deploy/submission-errors), [MCP review](https://developers.openai.com/plugins/deploy/app-review) | Separate gates and no unnecessary UI scope |
| Existing paid-account access differs from selling digital subscriptions | [Plugin guidelines](https://developers.openai.com/plugins/plugin-guidelines) | A09; neutral entitlement explanation, no transactional funnel |
| Current annotation guidance conflicts across official pages | [Guidelines](https://developers.openai.com/plugins/plugin-guidelines), [submission errors](https://developers.openai.com/plugins/deploy/submission-errors) | Prepare rationale; verify portal; no blind annotation change |
| ZIP, dashboard and server have different responsibilities | [Submission flow](https://developers.openai.com/plugins/deploy/submission), [package format](https://developers.openai.com/plugins/build/plugins) | See responsibility table below |

| Material | Location |
|---|---|
| Manifest, MCP reference, workflow, icon, starters, review cases/release notes | ZIP |
| Support/privacy/terms | Live website; URLs in ZIP |
| Live tool metadata and OAuth discovery | MCP/App deployment; dashboard scan |
| Publisher verification, permissions, review credentials, attestations/countries | Dashboard; never package secrets |
| Domain challenge | Exact host/path and token from dashboard |
| Walkthrough | Accessible hosted video; URL in review metadata/dashboard |

## Status and decisions — 2026-10-06

Owner reported all requested signed-in acceptance checks confirmed and asked to proceed. This records user confirmation, not a new automated paid-account test.

Package source: `plugins/trialagents-intel/`, version 0.1.1. Uses the portable Agent Plugins format: root plugin.json, root mcp.json, workflow skill and assets. Remote MCP: https://mcp.trialagents.com/research/mcp. No legacy ai-plugin.json, duplicated custom GPT Actions API or static token. Anonymous and OAuth modes remain server-owned.

The package implements broad relevant discovery, explicit subgroup counts, top-ten tables, professional contacts, ranking explanations and evidence follow-ups. The MCP still performs deterministic selection; no added backend LLM calls. Existing website, auth, project entitlements, checkout and subscription prices are unchanged. Connecting an account does not itself unlock uncovered cohorts.

## Reproducible build and pilot

From repository root, install the project/dev dependencies, then run:

```sh
python scripts/build_chatgpt_plugin.py
python -m pytest -q tests/test_chatgpt_plugin.py
```

Output: `dist/trialagents-intel-0.1.1.zip`. Only seven explicitly allowlisted public package files are included; no repository, environment files, source credentials or reviewer credentials. ZIP paths start at plugin.json, not a containing directory. The builder validates local constraints and the bundled criteria against the actual SelectionCriteria model; this is not OpenAI certification or full remote schema validation.

The GitHub `ChatGPT plugin package` workflow builds and uploads the ZIP as an Actions artifact. Treat that artifact as an unreviewed engineering candidate until Gate A is signed off. After Gate A, download it and use the supported plugin upload/testing flow. Exercise the five positive and three negative cases in plugin.json before submission, particularly sparse cohorts, ten-result enforcement and full-project coverage. Evidence/account review cases now include fresh-chat research setup. Use a dedicated non-customer review project.

## Public directory gates

1. Select the verified developer identity and appropriate category in the OpenAI Plugins dashboard; upload the ZIP and inspect scan/import results. Adjust to any current schema errors before submitting.
2. Complete the dashboard-generated MCP domain verification. Publish its exact challenge under the specified well-known path. No token has been fabricated or deployed by this packaging change.
3. Test the package in actual ChatGPT: anonymous three-category discovery, contacts/evidence, expired selections, account connection, covered project expansion and denied uncovered project. Prior owner acceptance covers the app journey, not this newly packaged plugin.
4. Provide a reviewer-accessible walkthrough video and dedicated reviewer credentials through the secure dashboard. Neither is included in the ZIP. Reviewer access must not require private email/MFA approval from the owner. Do not weaken production authentication globally to create review access.
5. Confirm listing support/privacy/terms accurately describe this MCP data flow and contact handling. The supportURL is `https://intel.trialagents.com/support/intel`, deployed by App PR #247 and verified anonymously. The main `trialagents.com` host is separate and does not serve this new route; do not substitute that hostname without deployment and verification. Recheck the legal pages and public support contact in the dashboard.
6. Review the live tools' read-only/open-world annotations and any required justification fields against current submission checks. This package does not alter live tool metadata. Complete reviewer access, country targeting, legal declarations and final submission as the verified owner. After approval, explicitly publish; upload/PR merge is not public listing.

No public submission or publication has been performed by the package builder. Do not claim approval or automatic installation.

## Assets and sources

The icon reuses intel_agent_app/public/favicon.svg at commit d88bb67e7bcb6f5e38e60786488a0f5a008cb54c; only intrinsic dimensions change from 24 to 96 pixels to satisfy packaging size requirements, with paths/viewBox preserved. No new logo or license grant is introduced.

Official guidance checked 2026-10-06:
- https://developers.openai.com/plugins/build/plugins
- https://developers.openai.com/plugins/deploy/submission

Submission metadata includes five positive and three negative cases. The skill makes no raw-profile, performance, patient-treatment, email-sending or payment-tool claims. Operational narratives are not disclosed by free evidence; do not advertise their availability as an anonymous feature.


## Required regression checks after the 2026-10-07 owner test

Review these checks before any package download/test handoff and every release.
- [ ] The installed host sees explicit nested criteria fields and succeeds on its first valid search; HTTP schema validation alone is insufficient proof of host import.
- [ ] The owner's exploratory phase III mHSPC prompt produces a broad relevant prostate landscape with disjoint direct/related/broader counts, rather than stopping at a tiny exact group.
- [ ] A below-100 exploratory search triggers relevant broadening or a clear exception. An explicit "phase III only, Germany only" request preserves both constraints even if sparse.
- [ ] The report includes ten-result/access disclosure without forced login, subscription promotion or a promise that authentication alone unlocks results.
- [ ] Source-scope and missing-field caveats reflect actual evidence; no stale migration-pending warnings, worldwide completeness claim, or hidden real identity uncertainty.
- [ ] Record deployed server SHA and installed workflow version separately. A custom MCP connector may not load the ZIP skill; live tool descriptions and response guidance must stand alone.
- [ ] Recheck anonymous search/rank/evidence, offset denial, private-MCP isolation, and entitled/revoked project access.

OpenAI guidance rechecked 2026-10-07: https://developers.openai.com/plugins/plugin-guidelines
permits neutral entitlement explanations and existing paid-account use; it prohibits subscription
promotion and checkout/upgrade initiation. The initial notice therefore explains connection and
existing entitlement, not "create an account and subscribe." No pricing or auth flow change.
