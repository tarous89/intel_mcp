# Research MCP contract

Endpoint: `https://mcp.trialagents.com/research/mcp`. Use only the exposed tools; their current schemas take precedence over examples.

| Tool | Purpose | Access |
|---|---|---|
| search_research_trials(criteria) | Build a bounded selection; returns ID, cohort/groups and entity totals, not ranked rows | Anonymous |
| rank_research_entities(selection_id, offset=0, limit=10, project_id=null, include_cro_contacts=false) | Rank the whole cohort; CRO emails only when explicitly requested | Anonymous first ten; entitled project for pagination |
| get_research_entity_evidence(selection_id, entity_id, offset=0, project_id=null) | Supporting trials for one returned entity | Anonymous top-ten entities, bounded evidence; project for expanded access |
| list_research_projects() | Connect account and list owned projects/access | OAuth |

Selections expire (normally 15 minutes). Search construction is concurrency-limited: make entity-category searches sequentially. No arbitrary SQL, count-only catalogue, full-profile, outreach, saved report or checkout tool exists here.

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

Full access requires OAuth plus an owned entitled project whose granted trial manifest covers the complete selected cohort. Rank pages can be up to 100 when authorized. Authentication is not itself a subscription or a guarantee of coverage. Do not prescribe new pricing; TrialAgents owns subscription terms outside the plugin.

Both search and ranking return `access_info` with total_matching, returned, offset, anonymous_limit, has_more, requirements and message. Include the message once in each initial report, plus displayed/total counts per category. It explains existing-account/project access without a subscription CTA; do not add checkout or upgrade links. A result with six available entities must say six of six, not imply a hidden ten.


0.1.4: ranking accepts show_followups and show_access_notice (true by default). Set both false on earlier requested category charts and true on the last. Search returns capabilities with anonymous, existing_entitlement and not_exposed lists. Respect that inventory for next actions; private backend data is not automatically accessible from public tools.
