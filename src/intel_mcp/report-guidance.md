# Visual report workflow

Use ordinary tables for lists/filtering/rankings. For deeper evidence-backed analysis:
1. Call prepare_project_report for the current project/preview. Read dataset ID, revision, authorized trial count and access_scope. For current-filter questions read the latest applied view and distinguish it from the entire cohort.
2. Read authorized profiles with read_report_evidence in batches of at most five IDs, preserving source_ids. For sections use describe_trial_profile_schema and read_trial_profiles. Free access includes complete content for the fixed eligible ten; paid reads cover authorized trials. Enumerate/read the relevant population before any full-population conclusion.
3. Read available extracted documents with read_report_document using exact inventory names. Follow next_part for complete text. Keep provenance and retrieval dates internally; disclose a material mismatch with snapshot dates. No new extraction/OCR, external report worker or billing.
4. Calculate supported comparisons with units, denominators, unknowns and explicit overlapping-group membership. Separate facts from interpretation; participation is not performance or causation.
5. Generate the report using the structure below and the supplied HTML example. Always call save_project_report as part of generation, without a separate save request, with title, original query, short summary, html, dataset_id, revision, internal source_ids and stable request_key. Identical retries reuse the key; changed reports are new versions and never overwrite older ones. Users can delete individual versions in the app. Honor host write approval; do not claim saved on failure.
6. For a connected owner, saving automatically attaches the exact preview to a durable app project and returns its canonical Reports view. Show that returned view and use its project_id for subsequent reads. Let the returned workspace open Reports. Anonymous reports stay in the 24-hour preview until Connect attaches them. End the brief chat answer with show_research_followups: three contextual questions and one accurate access sentence. Do not repeat the report, its source IDs or the card in prose.

## Default structure and visual design
Unless the user explicitly requests another format, every report has exactly:
1. A report title.
2. An executive summary of one or two sentences total (not one per question).
3. Question headings and graphs only.

Put interpretation, advice, recommendations, methods prose and additional narrative in chat, not the report. Do not put answer paragraphs above graphs or nuances/implications below them. Graph labels may include concise units, n/denominators, unknowns, scope and snapshot date so the data remains interpretable. Do not use prose-heavy cards or text tables as substitutes for graphs. If evidence cannot support a graph, explain that in chat; never invent data.

Use modern self-contained SVG charts, direct labels, restrained green accents, subtle axes and generous whitespace. Show real units and denominators, distinguish missing from zero, and disclose overlapping groups in graph labels. Use a single outer report frame (provided by the host), and exactly one figure frame per graph. No nested cards, section frames, inner chart boxes or boxed executive summary. Keep the SVG canvas borderless; sections and main are plain layout containers. Use Inter/system sans typography, dark green text and white/off-white backgrounds. Sources remain in metadata unless requested. Do not manufacture a fixed number of analyses.

## Renderer contract
Use semantic main/section, h1–h3, p, figure/figcaption, table, lists, and summary/limitations classes. Graphs use self-contained inline SVG with viewBox, accessible title/description and readable labels/units. No JavaScript, external assets, stylesheets, custom CSS, inline style attributes, iframes, forms, tracking, SVG foreignObject or remote graph libraries. The server sanitizes HTML and supplies the app style. Keep HTML below 800 KB. The host also stores/displays query, scope and version.
