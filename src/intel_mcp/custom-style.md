# Custom view rendering defaults

Use these defaults unless the user requests another visual style. Keep the HTML self-contained and readable in the app and extension.

- Typography: Inter/system sans; body, tables and controls 16px; h1 28px/600, h2 20px/600, h3 18px/600; chart labels, captions and helper text 14px. Chart labels stay below heading size. Do not scale an entire SVG up from a small viewBox: design its coordinates for its displayed width, keeping labels around 14–16 screen pixels. Canvas accounts for device pixel ratio.
- Layout: 16–24px gaps; responsive grids; one view frame and at most one frame per chart/component. Keep functional labels visible, focus clear and touch targets usable.
- Tables: use normal word wrapping and adequate column widths; no word-break:break-all or overflow-wrap:anywhere on ordinary text. Put wide tables in a horizontally scrolling container. Reserve emergency wrapping for URLs/IDs. Do not squeeze words into single-letter columns or shrink all text to fit.
- Surfaces: white/off-white, ink #183b2b, muted text #526359, border #dce9df. Green actions #2c7650. Avoid filling every component with green.
- Charts: choose ONE color family per graph and distinguish series through its shades. Different graphs/views may use different families. Green: #14532d / #25804b / #58a875 / #a4d4b4. Blue: #1e3a8a / #2563eb / #60a5fa / #bfdbfe. Orange: #9a3412 / #c65b13 / #ed9653 / #fbd5b5. Cyan: #155e75 / #0e849b / #46b6c9 / #b0e3ec. Use dark labels on light shades; neutral gray for unknowns. Add labels/patterns so meaning never depends on color alone. User-requested palettes or semantic color conventions can override the default.
- Content: analytical views default to a title, at most two summary sentences, then question headings and visual findings. Advice stays in chat. Forms/trackers/calculators use task-appropriate structure. Show units, denominators, scope and unknowns; never invent findings for a template.

Use static HTML/SVG or isolated interactive inline CSS/JS, without external assets/network, parent access or direct database writes. Use the documented state bridge and deliberate Save changes for editable state. Check narrow and desktop rendering when possible; report visual-check limitations honestly.
