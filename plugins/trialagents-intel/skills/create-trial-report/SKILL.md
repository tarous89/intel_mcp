---
name: create-trial-report
description: Create and save a visual HTML report answering one or more questions about a TrialAgents trial selection, including protocol comparisons, operational patterns and subgroup analyses. Use for deeper analysis requiring charts or a saved report; ordinary partner lists stay in workspace tables.
---

# Create a visual trial report

Read [answer standard](../../references/presentation-standard.md), [access rules](../../references/access-and-evidence.md), and [report workflow](references/report-guidance.md). Use [the HTML example](assets/report-example.html) for layout only; replace every synthetic finding with authorized evidence.

Prepare scope, inspect evidence, then default to: bold, larger h1 report title using the same sans-serif family as the project name → executive summary (one or two sentences total) → question headings and graphs only. Interpretation, advice and narrative belong in chat. Graph labels carry units, denominators, missingness and scope. Use one report frame and one frame per graph, no nested panels or boxed summary. Follow another format only if the user explicitly requests it. Never invent data.

Every report-generation request includes versioned storage: always call save_project_report before presenting the finished report, without waiting for a separate save request. Preserve previous versions and use a new request key for changed content. Save with source IDs in internal metadata, preserving the snapshot and host write approval. Show it in the shared Reports tab. Keep chat concise and finish with three useful follow-up questions via show_research_followups and one access sentence. Do not repeat the report or display citations unless requested.
