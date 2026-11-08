# Search criteria

Endpoint: `https://mcp.trialagents.com/claude/mcp`. The live tool schemas take precedence over this summary and the examples.

## Criteria

Required: `base` (structured hard filters), `entity_type` (`cros`, `sites`, `pis`), `as_of` (current YYYY-MM-DD). Supply positive `base.therapeutic_areas` or `base_text`. Structured values must follow the live schema; don't guess enum codes.

`base_text`: `fields` from title/diseases/population/stages/settings/inclusion/exclusion, `terms` (1–20), `operator` any/all, optional `exclude_terms`. Terms are case-insensitive substrings across the selected fields. Different structured fields and base_text combine with AND.

`subgroups`: up to 12 ordered objects with id, label, bucket direct/related/broader, optional structured filters and text predicate. At least one explicit predicate is required. Do not combine subgroups with direct/related shorthand filters. First matching group owns the primary count; other matches are overlap tags. Public ranking always includes the whole base cohort; private selection tools retain their include_broader behavior.

`phase_title_fallback=true` belongs on a subgroup with a positive phase filter, not the base; it only fills missing structured phase from the title. It never overrides a known conflicting phase.

`entity_countries` means a CRO's registered country or a site's/PI's recorded affiliation country, not service coverage. Trial-country filters are separate. `cro_identity` is reviewed_group (default) or legal_entity; returned reviewed groups are curated aliases, not a claim of historical ownership on each trial date.

`function_code` applies only to cros: 1 monitoring; 2 investigator recruitment; 3 IRT; 4 laboratory; 5 project management; 6 data management; 7 EDC; 8 safety; 9 QA; 10 statistics; 11 medical writing; 12 regulatory; 13 medical expertise; 14 medicinal product management; 15 other. “CROs/providers” can include laboratories/vendors; do not claim all are full-service CROs.

`max_recent_trials` (1–800) keeps the newest matching trials by latest country submission or approval date (undated last, ties by EU trial number). Leave it unset for the default behaviour: complete selection up to 800 trials, otherwise the latest 800 with `recent_cap` in the result. Set it when the user asks for a specific number of latest trials.

## Example: exploratory mHSPC phase III landscape

Load `prostate-landscape.json` as an example, replace as_of with today's date and set entity_type to each requested category in turn. The base searches prostate disease/title mentions across phases. Its first group is explicitly *mHSPC terminology candidates*, not verified eligibility. A second phase-III prostate group offers related experience; the rest remain broader. Explain this choice first. If phase III is mandatory, add the base phase filter and disclose that missing structured phase will then be excluded before subgroup fallback.

The text engine cannot combine (hormone-sensitive OR hormone-naive) AND metastatic as separate narrative predicates in one group. Acronym/specific-phrase candidates are not proof of complete clinical inclusion. Explain this limitation; do not silently label broad hormone-sensitive mentions “metastatic.” Review returned trial evidence for candidates; read complete profiles/sections only for eligible trial IDs.

## Search results

- `discovery_guidance` reports the trial count and whether it is within the exploratory range.
- `recent_cap` appears when more than 800 trials matched: `max_recent_trials` (800), `matching_trials` (null when more than 1,000) and `matching_trials_label`. The cohort limitations also state the newest-first cap.
- `cohort.coverage=complete_available_profile_selection` describes the matching available TrialAgents profiles; it is not a census of every CTIS study.
- `access_info` gives total matching, returned and the access message. A result with six available entities is six of six, not a hidden ten.
- Search construction is concurrency-limited: run entity categories one after another. Selections expire after `expires_in_seconds`.
