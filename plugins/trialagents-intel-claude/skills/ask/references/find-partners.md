# Find clinical partners

Use for a new search for sites, principal investigators, CROs or trials, and for clinically justified changes to the selection criteria. Build criteria with [search criteria](criteria.md); the [prostate example](prostate-landscape.json) shows a complete exploratory search (replace its date and adapt its criteria).

1. Extract disease, population, phase, modality, geography, requested entity types and CRO function. Distinguish trial countries (base.countries) from entity affiliation countries (entity_countries). Ask only when the clinical question is missing.
2. Preserve explicit must and only constraints in base. Put preferences such as an exact population or phase in named subgroups, with include_broader=true, so the ranking covers the whole relevant cohort.
3. Size: the search returns the complete selection up to 800 matching trials. Above 800 it returns the latest 800 with recent_cap; use that selection without asking the user to narrow. Use criteria.max_recent_trials when the user asks for a specific number of latest trials. Below 30 trials, broaden only when clinically defensible (a wider therapeutic area, phase or modality, keeping the request as a subgroup) and say so; otherwise report the honest count.
4. Run requested entity categories sequentially with the same criteria and date. Inspect candidates with inspect_research_trials before claiming a complete review. Lexical matches and exclusion mentions do not prove clinical eligibility. Refine with refine_research_cohort only for user-requested narrowing or mandatory exclusions, with a rationale.
5. Finish broadening and refinement first, then call publish_research_workspace once with the final selection_id and the requested kind. It displays the workspace inline and saves the project for a connected account; guests receive a seven-day private preview. Do not publish intermediate cohorts or combine subgroup top-ten lists.
6. In chat give the scope, cohort size, the cap sentence when recent_cap is present, total and visible entities, and a few observations. Rankings count distinct trials in the selection; distinguish model recommendations from deterministic counts.

Follow-up requests go through the routing table in [SKILL.md](../SKILL.md).
