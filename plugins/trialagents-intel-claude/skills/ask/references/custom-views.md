# Custom views

A Custom view is a saved chart, dashboard, comparison, report, table, form, tracker, checklist or calculator built from the research and shown in the workspace Custom tab. Requests to "show this differently", "make a chart" or "compare these trials" are Custom view requests. A visualization shown only in chat is not a saved Custom view; respect an explicit chat-only request.

Follow [the save procedure and renderer contract](custom-view-guidance.md). For generation, load [rendering defaults](custom-style.md) and reuse relevant sections of [the HTML shell](../assets/custom-view-shell.html); for other formats reuse the relevant [SVG examples](../assets/visual-examples.html). For polished charts, dashboards, journeys and trackers, read [design patterns and checks](design-patterns.md) and adapt relevant sections of [the branded interactive gallery](../assets/custom-view-examples.html) with renderer=interactive. Example content is synthetic; replace it with authorised data or explicit user inputs. Start with the user's title and include only sections that answer the request.

Default to light backgrounds and explicitly contrasting text for headings, metrics, chart labels, tables and controls, following the [contrast rules](custom-style.md#text-and-background-contrast) before the first save.

An explicit request to create or revise a Custom view covers preparation and saving in the same turn without an extra confirmation; host approvals still apply.

1. Call prepare_project_custom_view for the current project or preview (include_template=true for the rendering contract). Read further evidence only where the request needs it, with read_custom_view_evidence, read_custom_view_document or read_project.
2. Build the view, or revise an existing one with its custom_view_id and expected_version. Use renderer=interactive for any custom CSS, including styled cards and CSS charts; renderer=static only with the supported semantic HTML/SVG shell.
3. Save with save_project_custom_view. A successful save displays the Custom tab; no extra open call. If custom_view_saved=true but presentation_status=unavailable, open the saved view with the returned presentation_recovery without saving again. Report storage from custom_view_saved.
4. Saves retry transient storage failures twice inside the call. After automatic_retry_complete=true, leave the manual save control in place; on the user's request retry with retry_project_custom_view and the returned retry_id. Reconcile changed context or versions before a corrected save.

When offering a website link, copy the returned custom_url (also url) exactly, including /custom. offer_visualization_save displays a Save to TrialAgents button for a candidate view; list_project_custom_views and open_project_custom_view list and reopen saved views.
