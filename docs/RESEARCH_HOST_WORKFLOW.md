# Public research host workflow — 2026-10-07

Owner approved four corrections after the first installed ChatGPT test: visible search requirements,
initial access disclosure, accurate coverage language, and a relevant broader first landscape.

## Implementation decisions

- Inline local input-schema references only on the public research tools/list response, after SDK
  protocol serialization. Preserve the complete filter inventory, constraints, runtime validation and
  optional-auth metadata. The descriptor becomes larger (about 94 KB for criteria); no new model call,
  database query, price or infrastructure change is introduced. Actual ChatGPT import must be retested.
- Put the broad-first workflow in MCP instructions AND search tool help. Return discovery_guidance
  with actual counts and a 200–500 target. Below-target exploratory queries should broaden explicitly;
  hard constraints and clinical relevance outrank the target. No automatic filter relaxation or sampling.
- Return access_info on every search and ranking with displayed/total counts, ten-result cap and neutral
  existing-account/project access explanation. No signup/paywall promotion or checkout link.
- Public cohort coverage means a complete successful selection of current available profiles, not all
  global/CTIS studies. Remove the historical migration-047-pending warning from public output and retain
  actual missing-field/identity caveats. The deployment history records migration 047 applied.
- Preserve private selection ranking and entitlement checks. Public ranking now uses whole-cohort totals (PR85); OAuth continuation/consent/recovery is repaired in App PR249.
- Package source 0.1.3 carries matching instructions. A custom MCP installation is not proof that a ZIP
  skill is installed; track server and installed workflow separately.

## Validation and release checklist

Review before any package download/test-ready handoff AND every release. These checks supplement
the package branch's docs/CHATGPT_PLUGIN_RELEASE.md; they do not waive its broader publication gates.

- [x] Runtime model and inlined JSON Schema accept a valid example and reject invalid fields/enums.
- [x] HTTP response exposes explicit criteria properties without $ref/$defs and preserves auth schemes.
- [x] Synthetic anonymous search/rank disclose counts and access; entitlement revocation remains denied.
- [x] Sparse-cohort guidance preserves hard constraints and actual counts; no fabricated minimum.
- [x] Public coverage translation leaves the private contract untouched and keeps identity limitations.
- [x] Local regression suite: 423 passed, 2 PostgreSQL integration checks skipped without fixture.
- [x] Required GitHub CI including PostgreSQL integration (PR #84).
- [x] Live server metadata and installed-tool landscape/access/coverage validation after deployment.
- [ ] Refresh the installed test connector and verify first-call schema comprehension in ChatGPT.
- [ ] Repeat exploratory mHSPC and hard-constraint sparse prompts in the intended host.
- [ ] Initial report shows whole-cohort top-ten rows, CRO contacts only on request and access notice.
- [ ] Verify the intended skill/package version is installed; complete the broader publication checklist.

Reference: https://developers.openai.com/plugins/plugin-guidelines (checked 2026-10-07):
neutral entitlement explanation and existing account access are allowed; subscription promotion and
checkout/upgrade initiation are not. No claim of OpenAI review approval or host acceptance.

Deployment: PR #84, main 3aa676ffdb7c7969d4bd2ef00e4e8dd16e549cbf; Render dep-db30htjrjlhs73fukn30 live 08:56:14 UTC. Live test: 192 trials (18/49/125), 272 providers, 1,002 sites, 1,918 PIs; ten ranked rows, evidence success and offset-ten denial. Metadata is explicit on the server but the current installed host still caches the old descriptor. Refresh/import and final-report checks remain open.

## Superseding owner iteration
Target200–500; broader therapeutic area/phase/modality must be relevant and disclosed. The overview includes one primary trial-group breakdown; entity rows omit match tiers. Topten uses whole-cohort total trial counts. CRO emails require include_cro_contacts=true only on explicit contact request and carry a source-purpose caveat. Include two or three data-supported follow-ups; free evidence and refinements must not be falsely gated. Inline bars/table resource is optional and makes no additional model/database call. MCP PR85 is live; the installed host still needs metadata refresh to expose the new contact parameter and UI binding.

Live verification:339 prostate/bladder/urothelial title/disease lexical candidates;453 provider entities; ten returned, emails absent, rank order total_trials_desc/name_asc/id_asc, pagination pastten denied. This is not an exact mHSPC population count. Package0.1.3 has passing CI. Actual host visual and authenticated acceptance remain unchecked.


## Report structure — current owner decision

Start with a 2–3 sentence executive summary answering the question. Show criteria and a compact breakdown of primary trial groups ONCE, with the cohort total and disclosed expansions; overlaps are not additive. Then show ONLY the entity categories requested, each with its heading, two short evidence-grounded summary sentences and the inline graph/table. A CRO-only request must not trigger site or PI searches. Do not repeat a chart as a second text table. Keep entity rows focused on whole-cohort trial experience rather than match-tier columns.

End with 2–3 supported next actions once. Set rank_research_entities show_followups=false and show_access_notice=false on earlier category charts; true on the last. Use the host's body font size; no miniature labels. Buttons send user messages; when unavailable, offer the same actions as text.

Use the search response capabilities inventory. Public tools expose cohort filters, partner ranking, supporting trial links/roles, functions, affiliations, contacts and sponsor co-occurrence. Existing eligible project access allows full lists and recorded trial-level operational findings where present. Do NOT offer protocol downloads, patient information documents/patient-level data, complete EU trial history or full clinical-results tables: those are not exposed by this public MCP. Do not imply payment or login alone adds those tools.

After account linking, explain the returned project access outcome. No eligible project means free research remains available; signup does not charge or unlock full lists. No subscription/checkout routing from the plugin.
