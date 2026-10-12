---
name: analyze-trial-evidence
description: Answer questions about an existing TrialAgents selection, including complete profiles, protocol text, eligibility, endpoints, timelines, sponsor co-occurrence, country coverage and recorded operational findings. Use for evidence questions and deeper follow-ups; use the report skill when an HTML report is needed.
---

# Analyze trial evidence

Read [answer standard](../../references/presentation-standard.md) and [access rules](../../references/access-and-evidence.md).

1. Resolve the current preview or owned project. For questions about current filters, call open_project again with kind/controls omitted to obtain the latest saved view; do not rely on stale UI context. Inspect matching counts and scope, not just the first visible page.
2. Call prepare_project_report to get the authorized trial scope and eligible IDs; this prepares context only and does not require creating a report. Keep the free fixed-ten boundary. On paid projects enumerate the authorized Trials pages before full-cohort claims.
3. Call describe_trial_profile_schema before interpreting unfamiliar fields. Use read_trial_profiles for complete profiles (omit sections or use []) or exact one/multiple sections. Available sections: overview, population, trial_design, interventions, eligibility, objectives, endpoints, sponsor_and_organizations, contacts, countries, sites, documents, lifecycle, results. Preserve returned nesting and follow next_part for large profiles.
4. Use list_trial_documents for exact available filenames and read_trial_document for extracted text; follow next_part until null. Do not promise unavailable files. Retrieval dates can differ from frozen profile dates; mention this if material.
5. Calculate only from records actually read; show denominators/unknowns and separate overlapping groups. Trial-level operational findings may describe recorded delays or outcomes but do not prove responsibility or entity performance. Use the shared workspace for lists, and [create-trial-report](../create-trial-report/SKILL.md) for multi-part comparisons or visual analyses beyond it.
6. Give a concise answer without unsolicited source IDs/links. End with three new questions and the access notice using show_research_followups. Suggest useful broader investigations even if they would need additional authorized records; do not claim those records have been analyzed.
