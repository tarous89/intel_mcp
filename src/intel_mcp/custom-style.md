# Custom view defaults

Reuse the relevant sections of the custom-view HTML shell. These are defaults; explicit user styling takes precedence.

- Typography: Inter/system sans, body/table/controls 16px; h1 28px/600, h2 20px/600, h3 18px/600; captions and chart labels 14px. Keep chart labels at 14–16 rendered pixels. The shell’s HTML bar layout keeps labels independent of chart scaling.
- Layout: title, up to two executive-summary sentences, then relevant sections with a heading, optional one-sentence interpretation, and a chart/table/tool. Use 16–24px gaps and one frame per component. Forms and trackers follow their task structure.
- Surfaces: white/off-white backgrounds, ink #243238, muted #5b6870, borders #dce2e5; green #2c7650 for primary actions. Table headers and chart tracks use neutral gray.
- Charts: select one color family per chart, using its shades for series. Vary families across charts/views. Blue #1e3a8a / #2563eb / #60a5fa / #bfdbfe; orange #9a3412 / #c65b13 / #ed9653 / #fbd5b5; cyan #155e75 / #0e849b / #46b6c9 / #b0e3ec; green #14532d / #25804b / #58a875 / #a4d4b4. Include labels/units and readable contrast. User palettes and semantic colors can override this default.
- Tables: full-width semantic table inside .table-scroll; normal word wrapping, adequate columns, horizontal overflow for wide data. Reserve emergency wrapping for long URLs/IDs.
- Rendering: static semantic HTML uses the server’s supported classes. Interactive HTML can supply inline CSS/JS through the isolated renderer. Keep source scope, denominators and unknowns accurate. Use placeholders or empty data for templates.

Check the final rendered view at narrow and desktop widths for wrapping, chart text, table width and spacing.
