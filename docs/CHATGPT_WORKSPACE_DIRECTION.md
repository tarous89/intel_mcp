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

## Shared workspace increment — local candidate, 2026-10-08

Implemented App migration0056 and versioned four-table workspaces, one-hour hashed-capability previews, explicit atomic account claim, optimistic updates and history, recommendations tied to accessible entity evidence, and exact same-cohort validation. All pages and old revisions recheck account access; anonymous capability stops working after claim. Browser API can read/claim only; source snapshot writes are internal-service-only. The same project ID survives account connection. Owned workspaces appear in the research list.

The actual App CombinedEntityTable/SiteResultsTable components now feed both the external project page and the compiled MCP inline/fullscreen view. No second table design or payment controls. CRO insights preserve legal names/contacts, cohort metrics use selected-trial labels, and recommendations are distinct from measured experience order. MCP prepare/get/open/revise/claim tools support the flow; the read tool does not generate duplicate views. Display expansion detects host support and falls back to the external project on user click. Model-context updates contain only displayed authorized rows.

Verification: 46 targeted MCP tests; four App Node tests covering real PGlite persistence/access, existing OAuth, and shared-component DOM controls. Targeted TypeScript passes with real component/Postgres types and framework/db/auth stubs; full repository CI still required. Shared bundle built; source hashes are in ui/research/workspace-source.json. Browser visual testing is blocked by missing executable/invalid browser download; DOM checks do not establish visual or real-ChatGPT acceptance.

Publication blocked: automatic approval review rejected create_tree for tarous89/intel_agent_app, stating that uploading substantial local source/documentation needs trusted user authorization naming the repository. Do not retry via another transport. The empty App branch codex/chatgpt-research-workspace exists at its original main commit; no implementation was uploaded. MCP PR91 still contains only the prior cohort increment. Request explicit approval to upload these changes to tarous89/intel_agent_app and tarous89/intel_mcp. No production migration/deployment occurred.

Next authorized steps once publication is unblocked: upload candidate App and dependent MCP branches, run full CI/typecheck, refresh the packaged workflow on the existing package branch, deploy App/migration and enable MCP_RESEARCH_WORKSPACE_ENABLED before MCP, then complete the documented real-host acceptance/release gates. Do not call the candidate a completed release or directory-ready package.


Approval resolution — 2026-10-08: the owner explicitly approved uploading these changes to tarous89/intel_agent_app and tarous89/intel_mcp, updating the PRs and continuing verification. The preceding source-upload block is resolved. Production migration/deployment and real-host acceptance remain pending.


## Agreed correction — 2026-10-08

The previous draft reused row components but introduced a separate research-page design. The owner rejected that presentation. Reuse the existing public preview shell through SharedProjectFrame (also used by /share/[token]/SharedProject) and the actual Intel tables. Inside ChatGPT remove the sidebar and Reports; use Sites, PIs, CROs, Trials, Dataset, Account and a factual access notice with totals. Prefer fullscreen host workspace; host placement still requires real-host acceptance. Keep recommendations/insights in chat.

The research variant now opens at /share/research/{projectId}; old /research/workspaces URLs remain compatible. This shares visual components with the existing preview while preserving the validated MCP cohort/revision storage. It is not an existing combined-intel dataset and must not be passed to those dataset APIs. Dataset opens this project's metadata/counts, not a purchase/export endpoint. Existing ordinary /share/{token} purchase flows are unchanged.

Anonymous viewing is allowed for one hour. Explicit save requires authentication; a per-tab pending-save marker resumes claiming after sign-in/registration, preserving the project ID. No admin ownership is used. Free account creation retains preview limits. Existing active paid access is rechecked server-side. Once claimed, anonymous token-only access is denied; ChatGPT must connect the same account to continue.

About dataset access opens /dataset-access, an informational page explaining preview limits, full access and monthly/yearly options without prices, purchase buttons or transactional links. No plugin link initiates an upgrade. Approved basis: https://developers.openai.com/plugins/plugin-guidelines (commerce section, checked 2026-10-08).

Regression coverage: four-table compact navigation, no sidebar/Reports/checkout, external link callbacks, source escaping, anonymous view and authenticated pending-save continuation with unchanged free entitlement. App PGlite and OAuth checks pass; targeted MCP tests pass. Draft publication and CI follow; no production migration or live-host verification is implied.


## 2026-10-09 initial-results correction
The initial answer must use ONE final broadest clinically relevant cohort (within the existing cap and explicit hard constraints). Complete broadening before showing entities; earlier narrower cohorts and subgroups must not generate additional top-ten lists. Keep one top-ten list per requested category. Search/refinement tool descriptions and returned presentation guidance now route to prepare/revise workspace, not legacy rank. The ranking tool remains read-only and data-only; its competing inline resource binding is removed. The workspace resource advertises fullscreen correctly, verified through resources/read; real ChatGPT rendering still requires host acceptance. A server deployment does not prove the installed packaged skill was updated.
