---
name: create-custom-view
description: "Create, save, open or revise Custom views in TrialAgents, including reports, charts, dashboards, comparisons, visualizations, tables, reusable forms, trackers, checklists and calculators. Use for requests to show research differently or save a visualization. These terms all route to Custom views."
---

# Create a custom view

Follow [the save procedure and renderer contract](references/custom-view-guidance.md). For generation, load [rendering defaults](../../references/custom-style.md) and reuse the relevant sections of [the HTML shell](assets/custom-view-shell.html). For other formats, reuse the relevant [SVG examples](assets/visual-examples.html). The templates illustrate layout; populate them from the requested data. Read [access rules](../../references/access-and-evidence.md) when gathering evidence.

For polished charts, dashboards, journeys and trackers, read [design patterns and checks](references/design-patterns.md) and adapt the relevant sections of [the branded interactive gallery](assets/custom-view-examples.html). Start with the user's title; choose only sections that answer the request. Use the gallery's inline CSS with renderer=interactive. Treat all example content as synthetic; replace it with authorized data or explicit user inputs. Keep the existing save and recovery procedure below unchanged.

For an explicit request to create or revise a Custom view, proceed through preparation and saving without asking for an additional conversational confirmation. Respect actual host approvals and explicit chat-only requests.

Apply the [main answering skill’s pending-approval rule](../answer-in-trialagents/SKILL.md#pending-approval) when a host approval is pending.

1. Prepare the current project/preview context. Retrieve additional evidence only where needed for the request.
2. Create the requested view, or revise the existing view using its ID and version. Select renderer=interactive for any custom CSS, including styled cards and CSS-based charts without controls or JavaScript. Use renderer=static only with the supported semantic HTML/SVG shell.
3. Save with save_project_custom_view when the view is ready; its completed result opens Custom views. Do not add a redundant open call. If custom_view_saved=true but presentation_status=unavailable, use the returned presentation_recovery to open the saved view without saving again. Use custom_view_saved to distinguish verified storage from a retained draft.
4. On failure, use the returned recovery information and the single retry control beside the unchanged workspace. Reconcile changed context or Custom view versions before a corrected save.

The HTML and generated content are stored. Existing interactive views may use the documented deliberate Save changes bridge; automatic input persistence is outside this workflow. ChatGPT can revise and save tracker content through the normal versioned save operation.
