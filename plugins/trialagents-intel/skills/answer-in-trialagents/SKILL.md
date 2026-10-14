---
name: answer-in-trialagents
description: Start here for TrialAgents questions. Route discovery, table operations, requested or alternative visualizations, reusable forms and trackers, revisions, and account actions to the appropriate specialist and workspace destination.
---

# Answer in TrialAgents

New searches, query revisions, ranking, sorting, filtering, paging, and record details must use the standard Sites, PIs, CROs, and Trials tables. Visual analyses, alternative presentations, and reusable coded outputs—including comparisons, charts, forms, and trackers—must be saved and opened in Custom views. Visual analyses must include the actual visualizations in the saved Custom view; chat provides a concise summary. Choose a format suited to the question and data. Ordinary explanations use concise chat. Explicit user format preferences take precedence.

Start new research with public search. For guests, publish results as a preview; request connection when the user chooses account storage or account-only access. For a supported database search, invoke search_research_trials once the criteria are clear; its workspace provides early loading feedback. Keep unsupported questions and clarification in chat. Distinguish an empty search from unavailable data or a failed operation. Explain failed or stopped operations briefly in chat, with the appropriate next step; retained tables remain the last successful results. Continue the existing research and final-workspace publication procedure.

## Pending approval

While an operation is actually awaiting user approval in ChatGPT, keep the response focused on that approval. Do not add navigation links, unrelated action buttons, or alternative calls to action until the user approves, declines, or cancels. Explain the pending operation briefly if clarification is needed. Authentication or account-connection actions required to proceed remain available. Apply this rule to an existing approval request; it does not introduce an additional confirmation step.

Use this routing table for the current request and project state. Load the relevant specialist.

| Request | Destination and skill |
| --- | --- |
| Initial discovery or a new selection | Standard tables → [find clinical partners](../find-clinical-partners/SKILL.md) |
| Filter, sort, page, inspect or reopen results | Existing tables → [manage projects](../manage-research-projects/SKILL.md) |
| Evidence question needing profiles or documents | [Analyze evidence](../analyze-trial-evidence/SKILL.md); present according to the requested format |
| Chart, distribution, comparison cards, custom table, dashboard, or “show this differently” | Custom views → [create a custom view](../create-trial-report/SKILL.md) |
| Reusable coded output, form, tracker, checklist, calculator, or editable content | Custom views → [create a custom view](../create-trial-report/SKILL.md) |
| Revise an existing custom view | Update that view → [create a custom view](../create-trial-report/SKILL.md) |
| Account or project management | [Manage projects](../manage-research-projects/SKILL.md) |
| Ordinary explanation or simple text/list answer | Concise chat |

Creating a custom view includes saving and opening it in Custom views in the same turn, using the returned save status. Guests have temporary storage; connected owners have account storage. The specialist covers saving and recovery. Read the [answer standard](../../references/presentation-standard.md) for interpretation and useful next steps.
