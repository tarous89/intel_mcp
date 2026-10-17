---
name: create-trial-report
description: Create, save, open or revise Custom views in TrialAgents: charts, alternative visualizations, comparison cards, tables, dashboards, reusable forms, trackers, checklists and calculators. Use for requests such as show this differently or save this visualization, whether or not called a report.
---

# Create a custom view

Follow [the save procedure and renderer contract](references/report-guidance.md). For generation, load [rendering defaults](../../references/custom-style.md) and reuse the relevant sections of [the HTML shell](assets/report-example.html). For other formats, reuse the relevant [SVG examples](assets/visual-examples.html). The templates illustrate layout; populate them from the requested data. Read [access rules](../../references/access-and-evidence.md) when gathering evidence.

For polished charts, dashboards, journeys and trackers, read [design patterns and checks](references/design-patterns.md) and adapt the relevant sections of [the branded interactive gallery](assets/custom-view-examples.html). Start with the user's title; choose only sections that answer the request. Use the gallery's inline CSS with renderer=interactive. Treat all example content as synthetic; replace it with authorized data or explicit user inputs. Keep the existing save and recovery procedure below unchanged.

Apply the [main answering skill’s pending-approval rule](../answer-in-trialagents/SKILL.md#pending-approval) when a host approval is pending.

1. Prepare the current project/preview context. Retrieve additional evidence only where needed for the request.
2. Create the requested view, or revise the existing view using its ID and version.
3. Save with save_project_report when the view is ready; its completed result opens Custom views. Do not add a redundant open call. If report_saved=true but presentation_status=unavailable, use the returned presentation_recovery to open the saved view without saving again. Use report_saved to distinguish verified storage from a retained draft.
4. On failure, use the returned recovery information and the single retry control beside the unchanged workspace. Reconcile changed context or report versions before a corrected save.

The HTML and generated content are stored. Existing interactive views may use the documented deliberate Save changes bridge; automatic input persistence is outside this workflow. ChatGPT can revise and save tracker content through the normal versioned save operation.
