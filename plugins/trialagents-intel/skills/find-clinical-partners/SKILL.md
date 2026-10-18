---
name: find-clinical-partners
description: "Discover and shortlist CROs, sites, principal investigators or trials for a clinical study, and refine the research cohort. Use for new partner searches and clinically justified changes to selection criteria, not for reading an already selected protocol or saving a report."
---

# Find clinical partners

Read [answer standard](../../references/presentation-standard.md) and [access rules](../../references/access-and-evidence.md). Read [tool contract](references/tool-contract.md) before constructing criteria; use [the prostate example](references/prostate-landscape.json) only when helpful, adapting its date and criteria.

1. Extract disease, population, phase, modality, geography, requested entity types and CRO function. Ask only when missing information prevents useful research. Distinguish trial countries from entity affiliation countries. Run category searches sequentially.
2. Preserve explicit must/only constraints. For exploratory searches target 30–1000 relevant disease-family trials, placing preferences in named subgroups. Below 30, broaden only when clinically defensible and disclosed; otherwise report the honest shortfall. Over 1000 requires explicit narrowing, never silent sampling or padding.
3. Inspect candidate metadata and page before claiming complete review. Lexical matches, exclusion mentions and broad hormone-sensitive terminology do not prove clinical eligibility. Primary subgroups use first-match precedence; overlaps cannot be added. Phase-title fallback cannot override conflicting structured phase.
4. Finish discovery/broadening before showing results. Use one final broadest relevant cohort preserving hard constraints; never concatenate subgroup top-ten lists. Refine only for user-requested narrowing or mandatory exclusions, with rationale. Use the same criteria/date across requested categories without adding duplicate cohort counts.
5. Call publish_research_workspace to present the final results and save the connected account project, respecting host write approval. Guests receive a cached preview. Rank by distinct trials across the final cohort; distinguish model recommendations from deterministic counts. Let the workspace present Sites, PIs, CROs and Trials. Keep chat to a concise summary and useful interpretation.
6. Follow the shared [answer standard](../../references/presentation-standard.md).

Use [the main answering skill](../answer-in-trialagents/SKILL.md) for subsequent requests.
