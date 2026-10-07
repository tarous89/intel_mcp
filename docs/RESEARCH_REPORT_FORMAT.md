# Research report format and capabilities — owner decision2026-10-07

Supersedes earlier hide-all-initial-breakdowns presentation: show ONE compact primary trial-group breakdown in the overview, never repeat it in each entity section. Preserve whole-cohort ranking and200–500 relevant trial target/500 ceiling.

1. Executive summary:2–3 sentences answering the specific question.
2. Criteria and trials: search scope/filters/expansions, total and primary trial-group counts once; overlapping groups are not additive. No invented exact-match interpretation.
3. Only requested entity categories: heading, two short factual summary sentences, then graph/table. CRO-only questions must not trigger site/PI retrieval. Charts summarize counts; ChatGPT supplies contextual executive text without a backend LLM call.
4. One final access explanation and2–3 capability-supported suggestions. Set show_followups/show_access_notice false for earlier category widgets and true for the last. Buttons submit a user message through the SDK; if unavailable, show text to ask in chat. Never auto-link accounts or auto-run follow-up queries.

Use host font family and body-size token, minimum1rem; no miniature chart labels/footer. Optional host UI falls back to a normal Markdown table. Do not duplicate the same table in text after a chart.

Capabilities exposed today: bounded lexical/structured cohort discovery; country/phase/modality/therapeutic-area refinements; whole-cohort top-ten CRO/provider/site/PI ranking; roles/functions, source trial links, affiliations, sponsor co-occurrence; explicit-request CRO contacts and recorded PI contacts. Eligible existing project access supports full lists and recorded trial-level operational findings where present. Not exposed: protocol documents, patient information documents/patient data, complete EU lifecycle history, full results tables, outreach. Backend availability is not proof that a public tool exposes it. These require separate access/tool design before being advertised.

Newly connected users without eligible projects remain on free research. No checkout redirect or subscription-choice screen: OpenAI plugin guidelines currently prohibit digital subscription upsell/initiation. Link/authentication is not payment. App companion fixes callback CSP and redesigns consent.

Mandatory before test handoff/every release: review docs/CHATGPT_PLUGIN_RELEASE.md; verify CRO-only/multi-category structure, single breakdown, font sizes, button-to-message behavior and plain-text fallback; test logged-out signup and return to ChatGPT. Host acceptance is not established by unit/DOM tests.
