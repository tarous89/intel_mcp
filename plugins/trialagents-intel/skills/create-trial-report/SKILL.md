---
name: create-trial-report
description: Create, save, revise and present any custom-coded data or analysis visualization in TrialAgents, including reports, dashboards, charts, cards, tables, forms, trackers, calculators and custom interactive views. Use regardless of whether the user calls the result a report. Also use when saving an existing visualization or editing one already saved.
---

# Create and save a project visualization

Read [answer standard](../../references/presentation-standard.md), [access rules](../../references/access-and-evidence.md), and [visualization workflow](references/report-guidance.md). Use [the HTML example](assets/report-example.html) for layout only; replace synthetic findings with authorized evidence.

Any requested data/analysis visualization requiring custom code belongs in the shared Reports workspace. Create it, call save_project_report and present its returned workspace in the same turn. Do not stop at an inline chat artifact, save_project, or a promise to save. No additional save request is needed; honor the host's write approval. If saving intent is genuinely unclear, keep the candidate visible in chat and call offer_visualization_save for a real Save to TrialAgents button. Never invent a clickable button in prose.

For revisions, list/read the existing item and pass its report_id and expected_version to save_project_report. Replace that item in place. Create a separate copy only when explicitly requested. Use the same request_key for identical retries and a new one for edits. Confirm saved only when report_saved=true. On failure retain the chat visualization, explain the actual error, and show Retry save.

Guests receive temporary database storage and see Connect Account to keep the same project and all its visualizations. Connected owners receive verified account-save confirmation and can access the item in both plugin and app. Never describe temporary storage as permanent account storage.

Prefer useful visualizations with coordinated colors and dark backgrounds when contrast helps. Tables, lists and short summaries are welcome when useful. Use a bold larger title matching project-name typography; summaries/question headings are optional for simple charts, forms or trackers. Check consistent spacing and prevent overlap or clipping at desktop/mobile widths. Keep one report frame and one frame per chart. Source provenance and permissions remain authoritative.
