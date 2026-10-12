# Visual report workflow

Use ordinary tables for lists/filtering/rankings. For deeper evidence-backed analysis:
1. Call prepare_project_report for the current project/preview. Read dataset ID, revision, authorized trial count and access_scope. For current-filter questions read the latest applied view and distinguish it from the entire cohort.
2. Read authorized profiles with read_report_evidence in batches of at most five IDs, preserving source_ids. For sections use describe_trial_profile_schema and read_trial_profiles. Free access includes complete content for the fixed eligible ten; paid reads cover authorized trials. Enumerate/read the relevant population before any full-population conclusion.
3. Read available extracted documents with read_report_document using exact inventory names. Follow next_part for complete text. Keep provenance and retrieval dates internally; disclose a material mismatch with snapshot dates. No new extraction/OCR, external report worker or billing.
4. Calculate supported comparisons with units, denominators, unknowns and explicit overlapping-group membership. Separate facts from interpretation; participation is not performance or causation.
5. Generate the report using the structure below and the supplied HTML example. Call save_project_report with title, original query, short summary, html, dataset_id, revision, internal source_ids and stable request_key. Identical retries reuse the key; changed reports are new versions. Honor host write approval; do not claim saved on failure.
6. Let the returned workspace open Reports. Anonymous reports stay in the 24-hour preview until Connect attaches them. End the brief chat answer with show_research_followups: three contextual questions and one accurate access sentence. Do not repeat the report, its source IDs or the card in prose.

## Structure and visual design
- Report name in the report or host header, then an overall executive summary.
- One section per requested question: descriptive headline; a one-sentence answer ABOVE the graph (two only when necessary); a labeled visualization; nuances, subgroup differences and additional findings BELOW it.
- Every quantitative comparison needs a graph, including numeric comparisons in additional findings. Use real units, counts/denominators and unknowns. A numeric table alone is insufficient. Use meaningful matrices, process diagrams, timelines or structured cards for qualitative content; an evidence-gap matrix is appropriate when records are missing. Do not fabricate scores or frequencies.
- Add concise scope/missingness limitations. No default sources appendix or unsolicited trial IDs/links; store them in source_ids and provide them when requested. Do not manufacture a fixed number of analyses.
- Use the existing Inter/system sans typography, dark green text, restrained green accents and white/off-white panels with generous spacing.

## Renderer contract
Use semantic main/section, h1–h3, p, figure/figcaption, table, lists, and summary/limitations classes. Graphs use self-contained inline SVG with viewBox, accessible title/description and readable labels/units. No JavaScript, external assets, stylesheets, custom CSS, inline style attributes, iframes, forms, tracking, SVG foreignObject or remote graph libraries. The server sanitizes HTML and supplies the app style. Keep HTML below 800 KB. The host also stores/displays query, scope and version.
