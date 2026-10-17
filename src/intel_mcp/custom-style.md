# Custom view defaults

Use these defaults unless the user requests another style. Select useful sections and customize them to the actual question and authorized data; never reproduce the entire example gallery by default.

- Start immediately with the title, then an optional concise summary. Omit decorative mastheads, category eyebrows and badges. Keep meaningful scope and source notes.
- Center the view in a maximum 1,104px container with 32px outer padding and a white 12px-radius frame. Use 40px inner padding on desktop and 20px on phones; 28px section gaps, 24px panel padding (18px on phones), and 16px metric gaps. Avoid duplicating a frame if the host already supplies it.
- Typography: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif. Use 28px/600 title (25px mobile), 20px/600 headings, 16px body, 14px chart/table labels and 12px secondary notes. The sandbox cannot fetch fonts; retain a system fallback rather than promising Inter will always render.
- Surfaces: canvas hsl(60 6% 97%), white panels, ink #20272b, muted #59656b, borders #e2e7e5, green actions #3d9e69 with dark green text #286543. Chart tracks are light neutral backgrounds. Keep one frame per component.
- Use one coherent color family within each chart and vary families between charts: green #347f55/#55a776/#91bfa1; blue #234b83/#3975b8/#80a9d5/#c5d9ed; purple #65458d/#8762b1/#b49bce/#e0d4ed; orange #925220/#c77938/#e8ba87/#fcf5ed. Use dark text on pale fills, visible labels and exact legend matches. Gray #b0bab4 represents unknowns, not zero. Respect semantic status colors and explicit user palettes.
- Label values, units, denominators and missing data. Use shared scales across comparable rows. Do not use an attrition funnel for unrelated populations. Distinguish user plans from observed evidence.
- Use full-width semantic tables inside a horizontal scroll container. Keep timelines scrollable at narrow widths; stack metric cards and chart labels on phones rather than shrinking all text. Keep page-level overflow absent.
- For inline CSS/JS use the existing interactive renderer and self-contained HTML. Static rendering uses server-provided CSS and supported semantic classes only; the static shell remains a fallback. Never request network assets, alter sandbox policy or change MCP tools for styling.
- Trackers use the existing state bridge and deliberate host Save changes action. Restore fields before calculating derived summaries; programmatic updates must update draft state. Never imply automatic persistence.

Read the create-trial-report design patterns for chart selection, source rules and pre-save checks. The branded gallery demonstrates horizontal bars, a blue attrition funnel, a purple planning timeline and an editable tracker; the other SVG examples remain available for different questions.
