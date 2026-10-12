---
name: create-trial-report
description: Create and save a visual HTML report answering one or more questions about a TrialAgents trial selection, including protocol comparisons, operational patterns and subgroup analyses. Use for deeper analysis requiring charts or a saved report; ordinary partner lists stay in workspace tables.
---

# Create a visual trial report

Read [answer standard](../../references/presentation-standard.md), [access rules](../../references/access-and-evidence.md), and [report workflow](references/report-guidance.md). Use [the HTML example](assets/report-example.html) for layout only; replace every synthetic finding with authorized evidence.

Prepare scope, inspect the evidence, then produce: report title → overall executive summary → one section per question, each with a short answer ABOVE a visualization and nuances BELOW. Every quantitative comparison needs a labeled graph; use a matrix/diagram/cards for qualitative evidence. Never invent data or extra sections.

Every report-generation request includes versioned storage: always call save_project_report before presenting the finished report, without waiting for a separate save request. Preserve previous versions and use a new request key for changed content. Save with source IDs in internal metadata, preserving the snapshot and host write approval. Show it in the shared Reports tab. Keep chat concise and finish with three useful follow-up questions via show_research_followups and one access sentence. Do not repeat the report or display citations unless requested.
