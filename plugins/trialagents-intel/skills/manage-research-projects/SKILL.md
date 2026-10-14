---
name: manage-research-projects
description: Open, page, filter, save or revise TrialAgents research projects, or connect an account to an existing preview. Use for project persistence and current-view actions, not new clinical cohort discovery or report content analysis.
---

# Manage research projects

Read [answer standard](../../references/presentation-standard.md) and [access rules](../../references/access-and-evidence.md).

- Use list_projects and open_project for canonical projects from either client. Omit kind/controls to read the latest saved view. Explicit controls are read-only overrides; {} means unfiltered. Honor ownership.
- Page cached previews with read_project_preview, never re-search or recompute on tab changes. Use publish_research_workspace for final new results and save_project with expected_revision for project revisions. Deliberately unsaved prepare_research_workspace remains read-only. Recover failed preview storage with recover_research_preview, retaining its identity.
- The extension Connect action requests OAuth and saves the exact retained preview with save_project; its server attaches existing Custom views. If the user chooses “Continue connection in ChatGPT”, use that preview's retained draft with save_project and present the returned workspace. Honor host consent; cancellation leaves the preview available. Website-only import remains a fallback and does not establish MCP OAuth. Preview IDs identify context; cache tokens remain tool arguments, never chat text.
- Successful publish_research_workspace already saves the connected account project. Use save_project for a failed-save recovery with the retained draft, or for an authorized cohort revision with project_id and expected_revision. On REVISION_CONFLICT, reopen the latest project and reconcile before revising; retrying unchanged stale arguments cannot resolve it. Save presentation changes with save_project_view using the returned view.version and revision; this does not change cohort membership.
- Preserve the previous ready dataset while a revision prepares. Do not claim saved before success. Do not add guest-retention footnotes or routine expiry notices to the workspace or chat; explain seven-day expiry only when asked or needed to resolve an expired preview; a connected free account may save without buying access.

Use [the main answering skill](../answer-in-trialagents/SKILL.md) for the next request and the shared answer standard for presentation.
