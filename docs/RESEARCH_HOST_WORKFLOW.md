# Public research host workflow — 2026-10-07

Owner approved four corrections after the first installed ChatGPT test: visible search requirements,
initial access disclosure, accurate coverage language, and a relevant broader first landscape.

## Implementation decisions

- Inline local input-schema references only on the public research tools/list response, after SDK
  protocol serialization. Preserve the complete filter inventory, constraints, runtime validation and
  optional-auth metadata. The descriptor becomes larger (about 94 KB for criteria); no new model call,
  database query, price or infrastructure change is introduced. Actual ChatGPT import must be retested.
- Put the broad-first workflow in MCP instructions AND search tool help. Return discovery_guidance
  with actual counts and a 100–500 target. Below-target exploratory queries should broaden explicitly;
  hard constraints and clinical relevance outrank the target. No automatic filter relaxation or sampling.
- Return access_info on every search and ranking with displayed/total counts, ten-result cap and neutral
  existing-account/project access explanation. No signup/paywall promotion or checkout link.
- Public cohort coverage means a complete successful selection of current available profiles, not all
  global/CTIS studies. Remove the historical migration-047-pending warning from public output and retain
  actual missing-field/identity caveats. The deployment history records migration 047 applied.
- Leave the shared private selection contract, app usage, auth, entitlement checks and ranking unchanged.
- Package source 0.1.2 carries matching instructions. A custom MCP installation is not proof that a ZIP
  skill is installed; track server and installed workflow separately.

## Validation and release checklist

Review before any package download/test-ready handoff AND every release. These checks supplement
the package branch's docs/CHATGPT_PLUGIN_RELEASE.md; they do not waive its broader publication gates.

- [x] Runtime model and inlined JSON Schema accept a valid example and reject invalid fields/enums.
- [x] HTTP response exposes explicit criteria properties without $ref/$defs and preserves auth schemes.
- [x] Synthetic anonymous search/rank disclose counts and access; entitlement revocation remains denied.
- [x] Sparse-cohort guidance preserves hard constraints and actual counts; no fabricated minimum.
- [x] Public coverage translation leaves the private contract untouched and keeps identity limitations.
- [x] Local regression suite: 421 passed, 2 PostgreSQL integration checks skipped without fixture.
- [x] Required GitHub CI including PostgreSQL integration (PR #84).
- [x] Live server metadata and installed-tool landscape/access/coverage validation after deployment.
- [ ] Refresh the installed test connector and verify first-call schema comprehension in ChatGPT.
- [ ] Repeat exploratory mHSPC and hard-constraint sparse prompts in the intended host.
- [ ] Initial report shows actual subgroup counts, top-ten rows, recorded contacts and access notice.
- [ ] Verify the intended skill/package version is installed; complete the broader publication checklist.

Reference: https://developers.openai.com/plugins/plugin-guidelines (checked 2026-10-07):
neutral entitlement explanation and existing account access are allowed; subscription promotion and
checkout/upgrade initiation are not. No claim of OpenAI review approval or host acceptance.

Deployment: PR #84, main 3aa676ffdb7c7969d4bd2ef00e4e8dd16e549cbf; Render dep-db30htjrjlhs73fukn30 live 08:56:14 UTC. Live test: 192 trials (18/49/125), 272 providers, 1,002 sites, 1,918 PIs; ten ranked rows, evidence success and offset-ten denial. Metadata is explicit on the server but the current installed host still caches the old descriptor. Refresh/import and final-report checks remain open.
