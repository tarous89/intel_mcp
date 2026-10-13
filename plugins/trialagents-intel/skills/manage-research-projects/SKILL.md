---
name: manage-research-projects
description: Open, page, filter, save or revise TrialAgents research projects, or connect an account to an existing preview. Use for project persistence and current-view actions, not new clinical cohort discovery or report content analysis.
---

# Manage research projects

Read [answer standard](../../references/presentation-standard.md) and [access rules](../../references/access-and-evidence.md).

- Use list_projects and open_project for canonical projects from either client. Omit kind/controls to read the latest saved view. Explicit controls are read-only overrides; {} means unfiltered. Honor ownership.
- Page cached previews with read_project_preview, never re-search or recompute on tab changes. Use publish_research_workspace for final new results and save_project with expected_revision for project revisions. Deliberately unsaved prepare_research_workspace remains read-only. Recover failed preview storage with recover_research_preview, retaining its identity.
- Website Connect opens login/signup directly and attaches the exact cached preview and reports to the chosen account under /projects. Use the embedded button, not a pre-login save tool. An email hint is editable. Website login and MCP OAuth are distinct sessions; private MCP reads require the same owner account.
- For connected users, persist the final chosen workspace with the explicit write save_project(preview), honoring host approval; do not save intermediate searches. For an authorized cohort revision, prepare a new exact preview then save_project(preview, project_id, expected_revision). On conflict, reopen and reconcile; never silently overwrite or duplicate the project. Save presentation changes with save_project_view using the returned view.version and revision; this does not change cohort membership.
- Preserve the previous ready dataset while a revision prepares. Do not claim saved before success. Explain 24-hour anonymous report/preview persistence when relevant; a connected free account may save without buying access.

Use [the main answering skill](../answer-in-trialagents/SKILL.md) for the next request and the shared answer standard for presentation.
