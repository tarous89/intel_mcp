# Branded Custom views

Use these patterns with assets/custom-view-examples.html. The gallery is an example library, not a required four-section report. Preserve the existing MCP save procedure and tool names.

## Choose and adapt

- Answer the user's actual question first. Choose only useful sections; a single chart is sufficient for a single breakdown. Do not invent a tracker, journey, insight, cohort, status or date merely to fill the layout.
- Start immediately with a specific title, followed by a concise summary when useful. Omit decorative brand mastheads, eyebrows and category badges. Put evidence scope, provenance and limitations near the relevant result or at the bottom.
- Replace every example number, label, row and interpretation with authorized data. Example studies and counts are synthetic and must never become clinical claims. If demonstrating a template, label its data as illustrative in a note.
- Reports, charts, dashboards, comparisons, visualizations and Custom views are request vocabulary for this workflow; retain precise artifact_kind values and the existing tool identifiers.

## Pattern selection

| User need | Pattern | Data requirements |
| --- | --- | --- |
| Compare endpoint families or categories | Horizontal bars, green shades | Shared zero baseline, exact counts, units and denominator; explicit unknowns. Define a co-primary/multiple-category counting rule. |
| Show sequential screening or shortlist attrition | Blue staged funnel | The same population and nested stages. Widths proportional to counts, equal band heights, exact labels. Loss percentages use the preceding stage; retained shares use the initial population. Do not imply availability from participation. |
| Plan work or show recorded milestones | Purple timeline | Equal-width time intervals; actual dates or clearly user-provided/planned durations. Distinguish a plan from observed trial timings. |
| Assign owners and track actions | Editable table, orange progress | User-provided project tasks, stable field names and explicit statuses. No patient records. Completion derives from current rows. |

Use other suitable charts from visual-examples.html when the question warrants them. Apply the same typography and surfaces; do not force unrelated data into these four patterns. Use tables when exact comparisons are clearer than graphs.

## Rendering and persistence

The polished gallery contains inline CSS and controls: save it with renderer=interactive, even if a selected section is visually static. Keep a full HTML document with a closing </head> for the existing host bridge. For renderer=static, use only the existing semantic shell and supported classes; custom CSS will not survive that renderer. Do not change server rendering or security policy.

Use the app's Inter/system font stack. The isolated view cannot fetch fonts, images, libraries or other network resources. Inter is used only if available or legally embedded; the fallback is expected. Do not promise identical font metrics across devices or invent a logo.

Give form controls stable unique IDs or names. Initialize on DOMContentLoaded after the host has restored saved form values; then derive progress, status colors and summaries. The host tracks ordinary input edits as draft state. Programmatic changes such as reset must also call the existing window.TrialAgents.setState bridge, preserving unrelated state and form keys. A deliberate host Save changes action persists the draft. Never claim autosave or implement a fake in-frame save button. A standalone example must clearly say that edits are temporary.

## Before saving

- Check arithmetic, denominators, units, legends, scale geometry, source scope and missing data. Retain precise source references; never invent citations.
- Check desktop and narrow layouts: centered content, consistent padding, readable 14px chart labels, no page overflow, and horizontally scrollable wide tables/timelines. Do not shrink a whole chart until labels are unreadable.
- Use textual labels as well as colors; check contrast, keyboard focus, form labels and empty states. Recalculate geometry when data changes, including zero or missing totals.
- Remove unused example sections, placeholder rows, demo reset buttons and design-specification notes from real outputs unless explicitly useful to the user.
- Verify save through custom_view_saved and the existing recovery procedure. A polished preview alone is not a saved Custom view.
