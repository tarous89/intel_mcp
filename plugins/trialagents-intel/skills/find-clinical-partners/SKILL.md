---
name: find-clinical-partners
description: Discover and shortlist CROs, sites, principal investigators or trials for a clinical study, and refine the research cohort. Use for new partner searches and clinically justified changes to selection criteria, not for reading an already selected protocol or saving a report.
---

# Find clinical partners

Read [answer standard](../../references/presentation-standard.md) and [access rules](../../references/access-and-evidence.md). Read [tool contract](references/tool-contract.md) before constructing criteria; use [the prostate example](references/prostate-landscape.json) only when helpful, adapting its date and criteria.

1. Extract disease, population, phase, modality, geography, requested entity types and CRO function. Ask only when missing information prevents useful research. Distinguish trial countries from entity affiliation countries. Run category searches sequentially.
2. Preserve explicit must/only constraints. For exploratory searches target 200–500 relevant disease-family trials, placing preferences in named subgroups. Below 200, broaden only when clinically defensible and disclosed; otherwise report the honest shortfall. Over 500 requires explicit narrowing, never silent sampling or padding.
3. Inspect candidate metadata and page before claiming complete review. Lexical matches, exclusion mentions and broad hormone-sensitive terminology do not prove clinical eligibility. Primary subgroups use first-match precedence; overlaps cannot be added. Phase-title fallback cannot override conflicting structured phase.
4. Finish discovery/broadening before showing results. Use one final broadest relevant cohort preserving hard constraints; never concatenate subgroup top-ten lists. Refine only for user-requested narrowing or mandatory exclusions, with rationale. Use the same criteria/date across requested categories without adding duplicate cohort counts.
5. Call prepare_research_workspace to open the read-only preview. Rank by distinct trials across the final cohort; distinguish model recommendations from deterministic counts. Let the workspace present Sites, PIs, CROs and Trials. Keep chat to a concise summary and useful interpretation.
6. Finish with three contextual investigations and the one-sentence access notice using show_research_followups. Follow [answer standard](../../references/presentation-standard.md) for the text fallback.

For profile/protocol/operational follow-ups use [analyze-trial-evidence](../analyze-trial-evidence/SKILL.md). For a visual saved analysis use [create-trial-report](../create-trial-report/SKILL.md). For opening, paging, saving or revising projects use [manage-research-projects](../manage-research-projects/SKILL.md). Do not call legacy save/claim/revise tools to create new projects.
