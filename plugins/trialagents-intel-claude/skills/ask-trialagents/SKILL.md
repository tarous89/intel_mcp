---
name: ask-trialagents
description: "Ask TrialAgents about European clinical trials: find and compare clinical sites, principal investigators (PIs) and CROs for a study, explore trial landscapes, read protocols, eligibility and endpoints, build charts, reports, comparisons or trackers from the results, and open or save TrialAgents research projects. Use for any TrialAgents, CTIS, site selection, investigator search or CRO selection request."
---

# Ask TrialAgents

TrialAgents Intel searches European clinical-trial records (EU CTIS) through the TrialAgents MCP tools and shows results in an interactive workspace inside the conversation, with Sites, PIs, CROs, Trials and Custom tabs. This skill is the single entry point; load the reference that matches the request.

| Request | Reference |
| --- | --- |
| New search: sites, PIs, CROs or trials for a study, landscape, shortlist | [Find partners](references/find-partners.md) and [search criteria](references/criteria.md) |
| Filter, sort, page, reopen or save existing results; list saved projects; connect an account | [Projects](references/projects.md) |
| Question about protocols, eligibility, endpoints, timelines, sponsors or countries of the selected trials | [Trial evidence](references/evidence.md) |
| Chart, dashboard, comparison cards, report, custom table, form, tracker, checklist or calculator | [Custom views](references/custom-views.md) |
| Ordinary explanation or simple text answer | Concise chat |

Every request also follows [access and evidence rules](references/access-and-evidence.md).

## How results reach the user

- Show results in the workspace, not as a bare link. publish_research_workspace, prepare_research_workspace, open_project, open_research_workspace, save_project_custom_view and open_project_custom_view display the workspace, which opens full screen when it is ready.
- Open the workspace with every answer about TrialAgents research, so the interface appears after each query. A successful publish or Custom view save already displays it. Otherwise, after answering (for example an evidence question or a chat-only summary), display the current results once at the end of the turn: open_project for a saved project or open_research_workspace for a preview, with the table kind the answer is about. Skip this only when there are no results yet (clarifying question, empty search, failure) or the user asks for chat only.
- Keep chat short: scope, cohort size, whether the newest-first cap applied, total and visible entities, the access note when material, and two or three useful observations. Do not repeat workspace tables in chat.

## End every answer with the same footer

After each answer that has results, end the message with these lines, in this order:

1. **Website link.** For a saved project, the url returned by the latest tool result, copied exactly, for example `[Open in TrialAgents](https://intel.trialagents.com/projects/…/sites)`; for a Custom view, its custom_url. Never build a link from an ID. For an unsaved guest preview, do not show its returned url, because it carries the private preview capability; write instead: "Connect your TrialAgents account to save this project and get a link."
2. **Reopen.** "Say \"show the workspace\" to reopen it here." When the user says this, call open_project or open_research_workspace for the current results; both are read-only.
3. **Full screen.** "The workspace opens full screen when ready. Use the X in its header to return to the chat; if Claude asks for an approval while it is open, close it to see the approval."

Keep the footer to these three short lines and do not repeat them elsewhere in the message.

## Always come back with a list

- Do not stop to ask the user to narrow a search because of its size. When 800 or more trials match, the search keeps the latest 800 by latest country submission or approval date (600, 400 or 250 when 800 trial records are too large for one selection) and reports recent_cap. Publish that selection and say in one sentence that it covers the latest recent_cap.max_recent_trials of the matching trials (at least that many match), adding that narrower criteria give a complete selection.
- For a request that names a size ("latest 500 trials"), set criteria.max_recent_trials to that number (1–800).
- Ask a clarifying question only when the clinical question itself is missing, not when the cohort is large.
- Preserve explicit must and only constraints from the user. Report small or empty results honestly.

## Failures

Explain a failed or stopped operation briefly in chat with the next step. Tables already shown stay the last successful result. Storage tools retry transient failures twice inside the call; after automatic_retry_complete=true, use the returned recovery tool on the user's request instead of repeating research.
