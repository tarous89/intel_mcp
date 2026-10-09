# Research MCP contract

Endpoint: `https://mcp.trialagents.com/research/mcp`. Use only the exposed tools; their current schemas take precedence over examples.

| Tool | Purpose | Access |
|---|---|---|
| search_research_trials(criteria) | Build a bounded selection; returns ID, cohort/groups and entity totals, not ranked rows | Anonymous |
| rank_research_entities(selection_id, offset=0, limit=10, project_id=null, include_cro_contacts=false) | Rank the whole cohort; CRO emails only when explicitly requested | Anonymous first ten; active paid account for pagination |
| get_research_entity_evidence(selection_id, entity_id, offset=0, project_id=null) | Supporting trials for one returned entity | Anonymous top-ten entities, bounded evidence; paid account for expanded access |
| list_research_projects() | Connect account and show account capabilities | OAuth |

Selections expire (normally 15 minutes). Search construction is concurrency-limited: make entity-category searches sequentially. Explicit save_research_project(selection_ids, title, include_cro_contacts=false) is an OAuth-protected write that saves private snapshots without analysis or payment. get_saved_research_project(project_id, section=0, offset=0, limit=10) reopens them with current owner/access checks. No arbitrary SQL, count-only catalogue, full-profile, outreach or checkout tool exists here.

## Criteria

Required: `base` (structured hard filters), `entity_type` (`cros`, `sites`, `pis`), `as_of` (current YYYY-MM-DD). Supply positive `base.therapeutic_areas` or `base_text`. Structured values must follow the live schema; don't guess enum codes.

`base_text`: `fields` from title/diseases/population/stages/settings/inclusion/exclusion, `terms` (1–20), `operator` any/all, optional `exclude_terms`. Terms are case-insensitive substrings across the selected fields. Different structured fields and base_text combine with AND.

`subgroups`: up to 12 ordered objects with id, label, bucket direct/related/broader, optional structured filters and text predicate. At least one explicit predicate is required. Do not combine subgroups with direct/related shorthand filters. First matching group owns the primary count; other matches are overlap tags. Public ranking always includes the whole base cohort; private selection tools retain their include_broader behavior.

`phase_title_fallback=true` belongs on a subgroup with a positive phase filter, not the base; it only fills missing structured phase from the title. It never overrides a known conflicting phase.

`entity_countries` means a CRO's registered country or a site's/PI's recorded affiliation country, not service coverage. Trial-country filters are separate. `cro_identity` is reviewed_group (default) or legal_entity; returned reviewed groups are curated aliases, not a claim of historical ownership on each trial date.

`function_code` applies only to cros: 1 monitoring; 2 investigator recruitment; 3 IRT; 4 laboratory; 5 project management; 6 data management; 7 EDC; 8 safety; 9 QA; 10 statistics; 11 medical writing; 12 regulatory; 13 medical expertise; 14 medicinal product management; 15 other. “CROs/providers” can include laboratories/vendors; do not claim all are full-service CROs.

## Example: exploratory mHSPC phase III landscape

Load `prostate-landscape.json` as an example, replace as_of with today's date and set entity_type to each requested category in turn. The base searches prostate disease/title mentions across phases. Its first group is explicitly *mHSPC terminology candidates*, not verified eligibility. A second phase-III prostate group offers related experience; the rest remain broader. Explain this choice first. If phase III is mandatory, add the base phase filter and disclose that missing structured phase will then be excluded before subgroup fallback.

The text engine cannot combine (hormone-sensitive OR hormone-naive) AND metastatic as separate narrative predicates in one group. Acronym/specific-phrase candidates are not proof of complete clinical inclusion. Explain this limitation; do not silently label broad hormone-sensitive mentions “metastatic.” Review returned trial evidence for candidates; this public surface does not expose raw profile sections.

## Discovery and coverage responses

Search returns `discovery_guidance`: target 200–500, actual trial count, below_target/within_target and the next step. A below-target initial exploratory selection requires a justified broader search or an explanation of why hard constraints/relevance prevent expansion. This guidance does not alter filters or authorize silent broadening.

The public cohort uses `coverage=complete_available_profile_selection` and `source_scope`. It covers the successful bounded selection of available profiles; it does not assert every CTIS study exists in the database. Over-limit/unsupported-profile reads fail rather than returning a sampled or partially ranked cohort. Individual missing fields and uncertain identities are separate limitations.

The HTTP input schema expands local references so criteria fields are visible to the host; runtime Pydantic validation and every supported filter remain unchanged. If an installed client still displays criteria as unknown, refresh its tool metadata. Do not guess undocumented field names.

## Access and output

Anonymous rank offset must remain zero, limit <=10. Evidence is limited to visible entities and ten-study pages; further evidence pages for those entities are allowed anonymously (this is not pagination of the entity list); free evidence omits discovery excerpts and operational narratives. Respect actual error codes/results. Never use repeated partitions to enumerate a paid list. A genuine user-requested narrower clinical question is a new selection and may yield different ten entities.

Ranked rows supply trial_counts, function_counts, countries/affiliations, contacts, identity_basis/legal_entities, sponsor co-occurrences, recency and evidence. Counts are distinct trials within this selection, not lifetime experience. Preserve source URLs/trial IDs and distinguish missing data from zero. Sponsor trial counts are descriptive, not a collaboration quality metric. There is no performance score.

Full access requires OAuth plus active paid account access, without project or cohort-coverage matching. Rank pages can be up to 100 when authorized. Authentication is not itself a subscription or a grant of paid access. Do not prescribe new pricing; TrialAgents owns subscription terms outside the plugin.

Both search and ranking return `access_info` with total_matching, returned, offset, anonymous_limit, has_more, requirements and message. Include the message once in each initial report, plus displayed/total counts per category. It explains existing paid-account access without a subscription CTA; do not add checkout or upgrade links. A result with six available entities must say six of six, not imply a hidden ten.


0.1.4: ranking accepts show_followups and show_access_notice (true by default). Set both false on earlier requested category charts and true on the last. Search returns capabilities with anonymous, existing_entitlement and not_exposed lists. Respect that inventory for next actions; private backend data is not automatically accessible from public tools.

0.1.5 historical behavior: the tools used a shared branded view. Current 0.2.2 behavior supersedes that: prepare/open workspace renders the four Intel tables; rank and evidence inspection are data-only. Supporting-trial lists require an explicit user request, even after a workspace error. Keep default chat to concise summary and insights; do not automatically fall back to trial or entity tables. Exactly three final data actions, no generic narrowing prompts. Saving is explicit and private; repeat saves reopen the same owner/snapshot/category/contact-mode project. Stored results are not auto-refreshed; current access is rechecked on reopen. No additional LLM job or purchase starts.


## Shared workspace tools (requires coordinated App/MCP rollout)

Use live schemas as authoritative. inspect_research_trials pages safe candidate metadata; refine_research_cohort validates source snapshot, selected trial IDs and rationale. prepare_research_workspace computes one read-only four-table preview from that selection; it writes no project. get_research_workspace reads one authorized page; open_research_workspace opens the view; revise_research_workspace appends a revision with expected_revision; claim_research_workspace saves a preview to an authenticated account. Writes must retain write annotations.

The extension prefers fullscreen (the supported host workspace), with no embedded sidebar or Reports. Dataset, Account and About dataset access use external App destinations. /share/research/{projectId} is the research variant of the existing shared-preview shell; preserve its #preview capability on anonymous links. Save after authentication preserves this ID. Existing /share/{token} links keep their existing behavior.

Unsaved previews expire with the source selection (expires_in_seconds). Legacy persisted anonymous projects expire after one week. Free accounts retain ten records per table; paid accounts use existing entitlements. User registration does not confer paid access. Show factual available/displayed counts; access information lives at /dataset-access and contains no purchase controls. Never direct a plugin user to a transactional subscription page.

Account handoff: create_research_account_handoff validates source access and returns a private 15-minute website login link. The selected website account receives the preserved project (or exact copy for an already-owned source); completion opens /projects. Never print the link token or require a second Connect step. This does not authorize the host OAuth session.

Initial workspace display is read-only: `prepare_research_workspace` computes an unsaved preview from the existing selection, including for signed-in users. Never claim it is saved or call a write tool merely to show results. Refine an unsaved preview with search/refine then prepare again. The explicit Connect account action passes the returned `draft` to `create_research_account_handoff`, which persists the exact snapshot and opens website login/signup. After login it appears in normal Projects. Expired previews must report expiry; never silently rerun and save different results. Existing saved project read/revise/claim paths remain supported.
