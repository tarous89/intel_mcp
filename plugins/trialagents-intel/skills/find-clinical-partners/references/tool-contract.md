# Research MCP contract

Endpoint: `https://mcp.trialagents.com/research/mcp`. Use only the exposed tools; their current schemas take precedence over examples.

| Tool | Purpose | Access |
|---|---|---|
| search_research_trials(criteria) | Build a bounded selection; returns ID, cohort/groups and entity totals, not ranked rows | Anonymous |
| rank_research_entities(selection_id, offset=0, limit=10, project_id=null, include_cro_contacts=false) | Rank the whole cohort; CRO emails only when explicitly requested | Anonymous first ten; active paid account for pagination |
| get_research_entity_evidence(selection_id, entity_id, offset=0, project_id=null) | Supporting trials for one returned entity | Anonymous top-ten entities, bounded evidence; paid account for expanded access |
| list_research_projects() | Connect account and show account capabilities | OAuth |

Search selections expire at the returned expiry; prepared cached previews have a separate seven-day lifetime. Search construction is concurrency-limited: make entity-category searches sequentially. Prepare an exact workspace preview before canonical saving; use the tools below. Legacy saved-project tools do not create new canonical projects. No arbitrary SQL, count-only catalogue, outreach or checkout tool exists here. Trial profiles and extracted text are available only within the authorized trial set.

## Criteria

Required: `base` (structured hard filters), `entity_type` (`cros`, `sites`, `pis`), `as_of` (current YYYY-MM-DD). Supply positive `base.therapeutic_areas` or `base_text`. Structured values must follow the live schema; don't guess enum codes.

`base_text`: `fields` from title/diseases/population/stages/settings/inclusion/exclusion, `terms` (1–20), `operator` any/all, optional `exclude_terms`. Terms are case-insensitive substrings across the selected fields. Different structured fields and base_text combine with AND.

`subgroups`: up to 12 ordered objects with id, label, bucket direct/related/broader, optional structured filters and text predicate. At least one explicit predicate is required. Do not combine subgroups with direct/related shorthand filters. First matching group owns the primary count; other matches are overlap tags. Public ranking always includes the whole base cohort; private selection tools retain their include_broader behavior.

`phase_title_fallback=true` belongs on a subgroup with a positive phase filter, not the base; it only fills missing structured phase from the title. It never overrides a known conflicting phase.

`entity_countries` means a CRO's registered country or a site's/PI's recorded affiliation country, not service coverage. Trial-country filters are separate. `cro_identity` is reviewed_group (default) or legal_entity; returned reviewed groups are curated aliases, not a claim of historical ownership on each trial date.

`function_code` applies only to cros: 1 monitoring; 2 investigator recruitment; 3 IRT; 4 laboratory; 5 project management; 6 data management; 7 EDC; 8 safety; 9 QA; 10 statistics; 11 medical writing; 12 regulatory; 13 medical expertise; 14 medicinal product management; 15 other. “CROs/providers” can include laboratories/vendors; do not claim all are full-service CROs.

## Example: exploratory mHSPC phase III landscape

Load `prostate-landscape.json` as an example, replace as_of with today's date and set entity_type to each requested category in turn. The base searches prostate disease/title mentions across phases. Its first group is explicitly *mHSPC terminology candidates*, not verified eligibility. A second phase-III prostate group offers related experience; the rest remain broader. Explain this choice first. If phase III is mandatory, add the base phase filter and disclose that missing structured phase will then be excluded before subgroup fallback.

The text engine cannot combine (hormone-sensitive OR hormone-naive) AND metastatic as separate narrative predicates in one group. Acronym/specific-phrase candidates are not proof of complete clinical inclusion. Explain this limitation; do not silently label broad hormone-sensitive mentions “metastatic.” Review returned trial evidence for candidates; read complete profiles/sections only for eligible trial IDs.

## Discovery and coverage responses

Search returns `discovery_guidance`: target 30–1000, actual trial count, below_target/within_target and the next step. A below-target initial exploratory selection requires a justified broader search or an explanation of why hard constraints/relevance prevent expansion. This guidance does not alter filters or authorize silent broadening.

The public cohort uses `coverage=complete_available_profile_selection` and `source_scope`. It covers the successful bounded selection of available profiles; it does not assert every CTIS study exists in the database. Over-limit/unsupported-profile reads fail rather than returning a sampled or partially ranked cohort. Individual missing fields and uncertain identities are separate limitations.

The HTTP input schema expands local references so criteria fields are visible to the host; runtime Pydantic validation and every supported filter remain unchanged. If an installed client still displays criteria as unknown, refresh its tool metadata. Do not guess undocumented field names.

## Access and output

Anonymous rank offset must remain zero, limit <=10. Evidence is limited to visible entities and ten-study pages; further evidence pages for those entities are allowed anonymously (this is not pagination of the entity list); free evidence omits discovery excerpts and operational narratives. Respect actual error codes/results. Never use repeated partitions to enumerate a paid list. A genuine user-requested narrower clinical question is a new selection and may yield different ten entities.

Ranked rows supply trial_counts, function_counts, countries/affiliations, contacts, identity_basis/legal_entities, sponsor co-occurrences, recency and evidence. Counts are distinct trials within this selection, not lifetime experience. Preserve source URLs/trial IDs internally and distinguish missing data from zero. Sponsor trial counts are descriptive, not a collaboration quality metric. There is no performance score.

Full access requires OAuth plus active account entitlement (a paid subscription or admin-granted access), without project or cohort-coverage matching. Rank pages can be up to 100 when authorized. Authentication is not itself a subscription or a grant of paid access. Do not prescribe new pricing; TrialAgents owns subscription terms outside the plugin.

Both search and ranking return `access_info` with total_matching, returned, offset, anonymous_limit, has_more, requirements and message. Let the workspace show displayed/total counts; explain limits in chat only when material to the question. It explains existing paid-account access without a subscription CTA; do not add checkout or upgrade links. A result with six available entities must say six of six, not imply a hidden ten.


prepare/open workspace renders the shared tables; rank/evidence inspection is data-only. Supporting-trial lists require an explicit user request, even after a workspace error. Follow the shared answer standard; do not duplicate workspace data in chat.

## Canonical workspace tools

Use live schemas as authoritative. inspect_research_trials pages safe candidate metadata; refine_research_cohort validates source snapshot, selected trial IDs and rationale. These remain independent of the website wizard. publish_research_workspace presents the final four tables and saves the connected account project through an honestly annotated write. prepare_research_workspace remains a deliberately unsaved read-only preview. Recover failed storage with recover_research_preview instead of repeating research. Its private cache retains frozen source profiles and exact result pages for 7 days; ordinary preview tables expose no raw profiles; content tools return complete profiles and extracted documents for the fixed eligible ten trials without authentication; paid users can access all authorized trials. Call describe_trial_profile_schema for exact fields/types and all 14 section names. read_trial_profiles accepts omitted/empty sections for full content or an exact union of selected sections; follow next_part for large profiles. list_trial_documents lists exact extracted names; read_trial_document returns preserved text with next_part until null. prepare_project_report exposes eligible_trial_ids without generating or saving a report. Nested sites/investigators are complete and are not capped at ten.

| Tool | Purpose | Access |
|---|---|---|
| read_project_preview(preview, kind, offset) | Page the durable cached preview without rerunning research | Anonymous first ten; authorized paid pagination |
| list_projects() | List the owning account's canonical projects from either client | OAuth, read-only |
| read_project(project_id, kind, offset, limit) | Read saved results for analysis without opening the workspace; paid limit 1–100, free first ten | OAuth, read-only; owner and access rechecked |
| open_project(project_id, kind, offset) | Present final saved results in the shared workspace | OAuth, read-only; owner and access rechecked |
| save_project(preview, project_id=null, expected_revision=null) | Create a canonical project or commit the chosen refinement to that same project | OAuth, explicit write, idempotent |

For a revision, supply both project_id and latest expected_revision. For a new project, omit both. A stale revision fails; reopen and reconcile. Intermediate searches never overwrite a saved project. Repeating an identical save for the same owner returns the same project. Saved datasets remain available after preview expiry. Existing ready results stay visible while a newer revision's report artifacts are prepared; respect pending_revision.

The extension prefers supported fullscreen host placement with no embedded sidebar. Custom is a permanent tab, with a create action when empty. Dataset stays embedded; Account and About dataset access open App destinations. Website Custom views open at /projects/{id}/custom; standard table routes use sites, pis, cros or trials. Use exact returned URLs for links. Both clients use the shared tables. /share/research/{previewId} remains an unsaved-preview fallback; preserve its #preview capability.

Connect opens website login/signup immediately. Any account can be selected; an email hint is editable. Authentication opens Projects immediately, attaches the cached selection and displays a normal project card. This creates canonical project/selection/dataset metadata, then prepares report artifacts in bounded background work using the captured profiles. It does not rerun clinical research or invoke a model. There is no legacy research-project copy step. Website authentication does not authorize MCP; private reads require OAuth for the owning account. A preview already saved to another account does not grant access to that account's data.

Free accounts retain ten rows per category; paid access follows existing entitlements and is rechecked for reads. Registration alone is not paid access. Access information lives at /dataset-access and contains no purchase controls. Never direct plugin users to transactional subscription pages. Expired previews fail explicitly; do not silently substitute new research. Legacy saved-project handlers remain compatibility-only and must not be used as a fallback to create new projects.

## Shared workspace tables
The app-only `read_workspace_trial` opens a full frozen trial profile in the workspace dialog. Table reads accept validated search, country, subgroup, CRO function, metric minimum and sort controls. Filters cover the accessible saved table; Excel exports include every permitted row (preview subset for free access, every filtered page for full access). Site/PI metrics use the selection's frozen as-of date (five-year experience, six-month authorizations) and saved-cohort percentile bands. These presentation controls never rerun search or change saved membership, identities, or cohort ranking. View sorting changes display order only. Missing contacts remain missing; do not infer them.

## HTML reports

For deeper analysis call `prepare_project_report` and follow [report guidance](../../create-trial-report/references/report-guidance.md). Read bounded evidence using `read_report_evidence` and exact available files for eligible trials through `read_report_document`. `save_project_report` persists the HTML, original question, title, snapshot and source IDs and opens Custom. `list_project_reports` and `read_project_report` read saved reports without opening the workspace. Use `open_project_report` only to display an existing report on request; a successful save already opens Custom. Free users can generate reports using only disclosed preview evidence; anonymous reports attach when the preview is saved. Source data updates do not automatically refresh saved projects or reports.


## Follow-up presentation
`show_research_followups(questions, project_id or preview)` validates the current scope and optionally returns one to three useful questions supported by known available data or existing tools. It reads no extra evidence, performs no write and starts no analysis. Do not append routine suggestions; state access requirements when material. Execution remains subject to server access checks. Use the text fallback if the host cannot render or send messages.
