# Mandatory custom-output style

Use the shared TrialAgents renderer shell: Inter/system sans-serif; body and controls 16px, title 28px/600, h2 20px/600, h3 18px/600, labels/captions at least 14px. Preserve these defaults; do not shrink the entire output. Long titles wrap.

Use workspace ink #183b2b, white/off-white surfaces, green actions #2c7650, border #dce9df. Charts may use coordinated teal, blue, purple and amber; unknowns use neutral gray. Dark chart panels need legible light labels. Never convey meaning by color alone.

Use consistent 16–24px gaps, responsive grids and scoped chart/table overflow. One host output frame and one frame per chart or functional component; no redundant nested cards. Inputs and buttons inherit typography, have visible labels/focus, and usable touch targets. SVG uses viewBox and readable text; canvas accounts for device pixel ratio. Prevent overlap/clipping at desktop and mobile widths.

Analytical reports default to a title, at most two executive-summary sentences, then question headings and visual findings. Advice belongs in chat. Simple tools/forms/trackers use only the structure needed; no forced report sections. Show units, denominators, scope and unknowns for evidence-based charts. Do not invent findings to populate templates.

Use self-contained HTML; choose static HTML/SVG or interactive inline CSS/JS. No external libraries/assets/network, parent access or direct database writes. Interactive controls use the documented TrialAgents state bridge and deliberate host Save changes. Inspect rendering when possible and state honestly when visual checks were unavailable.
