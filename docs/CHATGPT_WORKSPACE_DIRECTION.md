# ChatGPT-driven Intel Agent workspace

Decision approved by owner: 2026-10-08. Implementation in progress; not a claim of deployment or host acceptance.

## Product direction

ChatGPT owns conversational interpretation, trial selection/refinement and evidence-based recommendations. MCP provides bounded retrieval; the backend validates IDs, access and source evidence, normalizes identities, persists projects and serves deterministic data. Do not add backend LLM calls. Existing search predicates remain retrieval primitives, not a mandatory filtering wizard. Retain explicit user constraints and disclose incomplete/paginated searches. The 500-trial bound remains until separately engineered; never silently sample or pad a cohort.

Use one project/cohort for CROs, PIs, sites and trials. Submit source trial IDs plus selection rationale, not model-reconstructed records. Persist selection and recommendation revisions with provenance and optimistic concurrency. Keep measured trial experience separate from ChatGPT's recommendation; do not infer performance from participation. Support revising the same project without mutating unrelated projects or losing previous evidence.

Reuse Intel Agent's actual workspace table components/data contract for an inline preview and expanded workspace. ChatGPT supplies a concise summary and insights, without duplicating rendered tables. Where supported, open the project in a conversation panel/fullscreen extension; otherwise offer a user-clicked external project preview. Feature-detect capabilities, accept host-controlled placement, and never promise automatic opening everywhere. Preserve project identity across account connection.

The model and UI receive the same account-authorized data. Anonymous/free entity access remains ten per category/selection; paid access is account-wide. Broad trial discovery metadata is separate from provider/contact access and must not expose unrestricted profiles or enumerate hidden entities. Do not harvest narrow cohorts to bypass entity caps. Recheck access server-side, including expiry and revocation.

CRO normalization is central and versioned: group only reviewed aliases/legal entities under a canonical identity, preserve original names/countries/roles/source attribution, and count distinct trial IDs. Do not merge companies through fuzzy similarity or assume acquisition-era ownership. Unknown/ambiguous mappings remain separate for review.

No digital-subscription upsell, price banner, checkout or upgrade-starting link in the extension or its directed fallback. Existing-account connection can restore existing access; connection alone does not grant paid access. External fallback must be a useful project view, not a disguised checkout funnel. Existing independent billing is unchanged.

## Required next steps and acceptance

1. Add bounded candidate-trial inspection and validated cohort refinement through MCP. Return pagination/completeness, immutable source snapshot and selection rationale. Refined cohorts reuse trusted source records and existing deterministic aggregation; reject invented IDs and preserve the parent snapshot. Keep public projections free of hidden provider/contact data.
2. Strengthen reviewed CRO identity matching, including canonical group names, conflict rejection and distinct-trial regression tests. Broader alias expansion requires source-backed curation; do not guess legal suffix/country mappings.
3. Extend App's saved-research contract to one four-table project with revision history, saved recommendations and provenance. Add an expiring anonymous preview and atomic account claim; never create publicly enumerable projects. Validate ownership, retry idempotency, stale updates, limits and revocation. Existing explicit-save path stays until replacement is ready.
4. Extract/reuse the active Intel Agent table components, not the interim branded MCP renderer. Add the trial table and extension-safe route without purchase banners. Register the preview/workspace resources and supported display modes; preserve external preview fallback and current plugin identity/OAuth/server hosting.
5. Wire conversational changes to project revisions and model context containing authorized rows only. Test free/paid parity, source-text escaping, keyboard/mobile layout, unsupported-host fallback, sign-in return and existing-access restoration.
6. Deploy App migration/contracts before dependent MCP changes; refresh the existing plugin metadata. Run the release checklist and real ChatGPT preview/open/refine/save/reopen acceptance. No directory submission is implied.

## Superseded decisions and rollout boundary

This replaces the long-term separate MCP-table design, fixed deterministic recommendation order and explicit-save-only product direction. During the staged build, current live tools retain their compatible behavior. Search-time project preview, four shared tables, persisted model recommendations and automatic/open-on-click extension behavior must not be advertised until implemented and verified. Deterministic experience order remains factual; model recommendation order is a separately labeled layer.

Official references reviewed 2026-10-08: [Extensions](https://developers.openai.com/plugins/build/extensions), [UI reference](https://developers.openai.com/plugins/reference), [plugin guidelines](https://developers.openai.com/plugins/plugin-guidelines). Capability availability and commerce policy require rechecking before release.

## First implementation increment — 2026-10-08

Implemented in the development candidate:
- `inspect_research_trials(selection_id, offset, limit)` returns paginated trial ID/title/disease/phase/modality metadata with completeness indicators. No raw profiles, hidden providers or contacts.
- `refine_research_cohort(selection_id, refinement)` validates source snapshot and selected trial IDs, reuses trusted records, records model-attributed rationale and returns a derived expiring selection. It cannot broaden a source cohort or overwrite a project. Retries reuse the cached selection. The existing save tool persists its IDs and provenance.
- Derived cohort coverage is explicitly labeled `model_selected_source_subset`; original retrieval criteria are not presented as proof of completeness after model selection.
- Exact IQVIA/Syneos canonical labels join their already-reviewed country aliases. Unknown legal entities and conflicting names stay separate; original legal names and distinct-trial evidence remain available. Broader company curation remains pending.

Validation: 44 targeted Python tests pass, covering MCP HTTP schemas/auth declarations, source integrity, projection redaction, free pagination denial, expiry/idempotency, saved provenance and distinct-trial grouping. No production data, paid model call or payment was used. This increment is backend groundwork only; it does not yet implement the extension/shared tables, anonymous persistent previews or same-project revisions. No package readiness or real-host acceptance is claimed.
