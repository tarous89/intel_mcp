---
name: analyze-trial-evidence
description: "Answer questions about an existing TrialAgents selection, including complete profiles, protocol text, eligibility, endpoints, timelines, sponsor co-occurrence, country coverage and recorded operational findings. Use for evidence questions and deeper follow-ups; route visual analyses and reusable structured outputs to the Custom tab."
---

# Analyze trial evidence

Read [answer standard](../../references/presentation-standard.md) and [access rules](../../references/access-and-evidence.md).

1. Resolve the current preview or owned project. Use read_project with kind/controls omitted for the latest saved view, or read_project_preview for a cached preview. Read data through these MCP tools, not by navigating workspace tables. Keep the current workspace visible while gathering evidence. Paid reads accept limit 1–100; prefer 100 for broad counts/comparisons and choose smaller pages for detailed records. Follow next_offset as needed; free access remains the authorized first ten. Inspect matching counts and scope, not just the first page.
2. When trial profiles or documents are needed, call prepare_project_custom_view to get the authorized trial scope and eligible IDs; table-only questions can use the analytical reads directly. Use only eligible IDs from this current context, carrying its matching project or preview reference. On TRIAL_NOT_IN_PREVIEW, refresh that context and choose eligible IDs before retrying. Keep the free fixed-ten boundary. For full-cohort claims, read all relevant authorized pages of the entity being counted. A site-country count needs Sites pages, not unrelated Trials pages. When coverage is partial, give useful findings with the analyzed scope instead of withholding the answer.
3. Call describe_trial_profile_schema before interpreting unfamiliar fields. Use read_trial_profiles for complete profiles (omit sections or use []) or exact one/multiple sections. Available sections: overview, population, trial_design, interventions, eligibility, objectives, endpoints, sponsor_and_organizations, contacts, countries, sites, documents, lifecycle, results. Preserve returned nesting and follow next_part for large profiles.
4. Use list_trial_documents for exact available filenames and read_trial_document for extracted text; follow next_part until null. Do not promise unavailable files. Retrieval dates can differ from frozen profile dates; mention this if material.
5. Calculate only from records actually read; show denominators/unknowns and separate overlapping groups. Trial-level operational findings may describe recorded delays or outcomes but do not prove responsibility or entity performance. Use the shared workspace for lists, and [create-custom-view](../create-custom-view/SKILL.md) for multi-part comparisons or visual analyses beyond it.
6. Present the answer using [the main routing skill](../answer-in-trialagents/SKILL.md).
