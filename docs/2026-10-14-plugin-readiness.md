# Plugin readiness — 2026-10-14

**Status: scope and plan only. No implementation, deployment, account change, or public submission authorized.**

Date: 14 October 2026, Europe/Berlin. Owner request: scope the publication-readiness edits, group them into a few steps, save this dated document in the repository, and identify every proposed change that could affect performance, workflows, or user experience.

Saving this document is the only change authorized by this request. Checkboxes below are future work, not implementation permission. This plan must not be treated as approval for earlier deferred proposals.

## Baseline and evidence

- Package: `plugins/trialagents-intel`, version **0.7.4**; five installed skills; 37 live MCP tools.
- MCP source inspected: `tarous89/intel_mcp` at `bd22ae9b7ed6a37f30a8b849aa1904a42d535073`.
- Relevant application source inspected: `tarous89/intel_agent_app` at `71c2ac9ab7787eb2fb9d5e25289583abb84d127d`.
- Live workspace bundle SHA-256: `eb3756cbfc8e42656d23b2adf1569de682dc013a2311789e8f9e3cb63744f2b0`, matching the MCP build. Its source provenance identifies App commit `e472f0e6243462c20f5ca37c3a8712a8854115f5`; distinguish the embedded bundle from newer App source.
- Inspected the release ZIP, installed skills, relevant source, live initialization/tool/resource metadata, authentication discovery, public pages, CI results and synthetic desktop/mobile screenshots.
- Current MCP/package CI passed. This environment could not execute local browser tests because browser/dependencies were unavailable. CI screenshots do not prove real ChatGPT-host behavior.
- Current publishing-Portal configuration, verified publisher status, reviewer credentials, and authenticated save/update flows were not verified. The audit did not write customer data.
- Public privacy/terms content was available through web retrieval; direct requests to the main website received an access denial. Verify unauthenticated reviewer/browser access before release rather than treating the website as either fully accessible or definitely down.
- Recheck the latest repository and deployed versions before implementation; this is a dated baseline.

## Scope boundaries

Preserve the current product unless a specific change below is later approved:

- Keep existing plugin/App identities, endpoint, hosting, ownership and authentication boundaries.
- Preserve the owner-approved public name **EU Trial Intelligence**, compact name **EU Trial Intel**, and TrialAgents platform branding. Reconcile usage and remove test-only labels for public release; do not invent a new rebrand.
- Keep frozen cohorts, hard research constraints, ranking, four research tables, full profiles/documents within the fixed free trial set, and account-wide entitlements.
- Preserve canonical project identity, account attachment, Custom views, explicit interactive-state saving, same-item report revisions, retained retries, and truthful saved/temporary/failed status.
- Preserve current pending-approval guidance: while host approval is pending, do not send unrelated links or navigate the user away; do not introduce a second approval system.
- Preserve the existing visual-report defaults and user-requested alternative formats.
- Preserve current prices, subscriptions, discounts and payment implementation. Correct descriptions of existing behavior; do not change billing.
- Do not create patient-data workflows, outreach tools, automatic source refresh, automatic form persistence, or a new project-deletion feature.
- Read `AGENTS.md`, `PROJECT_CONTEXT.md`, and [OPTIMIZATION_PERMISSION_REQUIRED.md](OPTIMIZATION_PERMISSION_REQUIRED.md) before future work. Progressive categories/details, durable background stages, additional cache offloading/retention/eviction changes, cross-request result reuse, and new scheduling/polling remain separately restricted. This plan does not authorize them or undo already approved optimizations.

## Step 1 — Correct the MCP and extension contract

**Required fixes; implementation remains pending owner approval.**

### R1. Dedicated widget origin

Evidence: the deployed UI resource declares CSP/display metadata, but neither `_meta.ui.domain` nor `openai/widgetDomain`. Current OpenAI reference requires a unique component origin for UI submission.

Scope:
- Choose/configure the required unique origin through the supported host setup; do not guess a domain or create unapproved infrastructure.
- Return consistent resource metadata, including the compatibility alias if needed.
- Revalidate redirects, account handoff, initialization and component isolation under that origin.
- Review every shipped UI resource, not just the primary workspace.

Likely files: `src/intel_mcp/research_workspace.py`, `src/intel_mcp/research_server.py`, `src/intel_mcp/followups.py`, resource registration and associated tests.

Acceptance: deployed resource metadata contains the correct origin; workspace and follow-up resources initialize in the intended host without origin/CSP failures.

Impact: host loading, isolation, origin-scoped state and account navigation may be affected. No intended ranking or database change.

### R2. Accurate tool annotations and persistence descriptions

Evidence:
- `read_trial_profiles`, `read_report_evidence`, `read_report_document` and `read_trial_document` reach App source-registration writes despite read-only annotations.
- `save_project_report`, visualization-state saving and view replacement/reset can overwrite stored user data while using non-destructive write annotations.
- Some tools share a single annotation object despite differing effects.
- Repeated document reads create source records with a fresh retrieval timestamp; audit their idempotency claims too.
- Internal prepared-preview caching needs an explicit classification based on actual behavior; do not assume every internal cache write is a user artifact.

Scope:
- Produce a per-tool matrix for all 37 tools: side effects, read-only/destructive/open-world/idempotent values, authentication, data scope and retry behavior.
- Give overwrite-capable operations truthful destructive annotations, including tools that support both create and update modes.
- Make descriptions disclose persistence and account attachment.
- Keep server authorization and revision checks independent of host hints.
- Synchronize runtime guidance, packaged skills, review notes and affected tests.

**Workflow decision before implementation:** retaining evidence registration during reads and marking those tools as writes is the smallest behavioral change, but may add host approval prompts during reading. Moving registration to an explicit save operation could preserve read-only retrieval, but changes evidence provenance, storage timing and the report-save path. The required outcome is truthful behavior/metadata; the second design is not automatically included.

Likely files: `research_server.py`, `research_workspace.py`, `project_reports.py`; App `app/lib/project-chat-reports.ts`; canonical plugin references and generated mirrors.

Acceptance: annotations match actual effects; overwrite approval, refusal/cancellation and read/save flows are tested. No hidden writes, scope expansion, lost evidence, or approval bypass.

### R3. Stable publish retries

Evidence: `publish_research_workspace` calls preparation without an existing preview ID; preparation creates a UUID; `save_project` derives its request identity from that UUID. A retry of identical publish arguments can create a second canonical project despite `idempotentHint: true`.

Scope:
- Add or propagate a stable operation identity from the original publication attempt through preview preparation, canonical commit and retry.
- Distinguish a retry from an intentional new project and from a revision.
- Preserve owner scoping, expected revision checks, exact source snapshot and recovery after an ambiguous response.
- Do not implement broad result caching, deduplicate unrelated research, or delete existing projects.
- Correct retry descriptions/hints until their guarantees are supported.

Likely files: `research_workspace.py`; App `app/lib/combined-prepared-projects.ts`; relevant UI recovery code if propagation requires it.

Acceptance: sequential and concurrent repeats, including a lost success response, resolve to one canonical project for the same operation. Deliberately new operations remain possible; different users never share ownership.

Impact: project creation/recovery workflow; possible additional lookup or lock cost. Measure changed paths without promising a speed improvement.

### R4. Custom-view embedding compatibility

Evidence: static and interactive Custom views use nested `srcDoc` frames; no frame allowlist is declared. Official host guidance disables subframes by default. Actual host failure was not reproduced.

Scope:
- First verify both renderers inside real ChatGPT under R1's origin.
- If needed, configure only the supported minimum frame policy and supply the required review justification.
- If the host does not support the current arrangement, scope a supported rendering adjustment for owner approval before changing the architecture.
- Preserve static sanitization, opaque-origin interactive isolation, message-source/token checks, explicit Save changes, and network restrictions. No broad CSP weakening.

Acceptance: reports, charts, forms/trackers, resizing, scrolling, state-save and cancellation work on desktop/mobile; crafted content cannot call privileged host actions or persist data by itself.

Impact: rendering, interactive behavior and potentially load/resize performance. A renderer rewrite is conditional, not a confirmed required fix.

## Step 2 — Align policies, access language and permissions

### R5. Final public policy and support content

Evidence: published terms/privacy retain draft-production wording; terms include the retired Max Report offering; support describes cohort/project-specific entitlement while current inspected access is account-wide.

Scope:
- Finalize terms for the actual service and remove obsolete/draft claims.
- Describe actual collected data, purposes, recipients/processors, retention timelines and deletion controls for research inputs, projects, reports, evidence records, interactive state, temporary previews, authentication and operational records.
- Confirm source-data reuse rights and the treatment of recorded professional contact details. This is a verification requirement, not a finding that rights are absent.
- Align support and product pages with fixed free limits, account-wide access, current report availability and actual update behavior.
- Verify public accessibility and working support contact routes.
- Use Atlas Consulting consistently where publisher/legal identification is required; do not add it to unrelated main-app presentation.

Likely ownership: App support/access pages; the repository that owns the published TrialAgents legal/product pages (verify the current source before editing).

**Boundary:** accurate disclosures are required. New retention periods, purge jobs, storage migrations, project deletion, or changed access rules require a separately reviewed design and explicit approval. Do not write policies promising capabilities that do not exist.

Acceptance: approved factual policy text is published, accessible, and consistent with the product and actual storage lifecycle.

### R6. Clear account connection and permission copy

Scope:
- Explain account connection and existing entitlement separately; connection alone must not imply full paid access.
- Describe private-project/report create/update permissions accurately in consent and access text.
- Retain distinct guest temporary-save, connected-save, expired-access and failure states.
- Verify account/manage-account destinations and return journeys.
- Keep informational access pages informational; no subscription promotion, upgrade initiation or checkout controls inside the plugin.
- Do not change OAuth scopes/token behavior merely to rewrite wording. If a scope change proves necessary, scope reconnection and migration effects separately.

Acceptance: guest, connected-free and connected-full-access users receive accurate messages, and cancellation does not falsely imply persistence.

Impact: user decisions, consent and connection journeys; copy-only changes should have no material runtime cost.

## Step 3 — Finish listing, documentation and bounded UX polish

### R7. Listing and identity consistency

Scope:
- Reconcile public/package/App-owned metadata using the already approved EU Trial Intelligence naming; retain stable internal IDs.
- Describe intended research users, supported tasks, European coverage, evidence limitations and account requirements clearly.
- Diversify up to three starter prompts beyond prostate cancer, using only supported tasks.
- Verify listing URLs, publisher identity and icon legibility on light/dark surfaces.
- Current public submission docs accept square SVG icons with appropriate dimensions. Existing SVG format is not a blocker; PNG conversion, dark assets and screenshots are optional polish.
- Existing paid-account support is not itself prohibited; preserve the product's business model and avoid promotional pricing copy in the listing.

Impact: discoverability, expectations and example-driven tool routing; no intended entitlement/ranking change. New branding or capability claims require owner agreement.

### R8. Canonical instructions and reviewer cases

Scope:
- Update `docs/CHATGPT_REVIEW_NOTES.md` and `docs/CHATGPT_PLUGIN_RELEASE.md`: 37 mixed-effect tools, five skills, current account access, current save behavior and conditional follow-ups.
- Remove contradictions with newer entries in `PROJECT_CONTEXT.md` without erasing decision history.
- Align expected tool sequences with conditional inspection/refinement; make the contact case exercise actual contact retrieval.
- Keep hard-constraint handling, unavailable-data honesty, no invented capability/contact claims, source-text distrust, no patient-specific treatment decisions, and pending-approval focus.
- Change behavior-governing skills only where a concrete inconsistency is identified; editorial review documentation is otherwise sufficient.
- Maintain one canonical guidance source and validate generated mirrors with `scripts/sync_plugin_guidance.py --check`.

Impact: documentation-only changes have no runtime effect. Changes to skills/tool descriptions can alter routing, follow-ups, approval handling and tool-call volume; review those as behavior changes.

### R9. Mobile layout and export parity decision

Scope:
- Check full workspace-title access, horizontal-scroll discoverability, reachable final columns/actions, fixed header/footer spacing, focus/keyboard behavior and small-screen Custom views.
- Apply only approved targeted layout fixes shared across App/extension where the same component is used.
- Review deliberately hidden extension Export/Dataset controls against actual advertised functionality and current host rules.
- **Do not automatically restore controls or remove App features.** If required, choose a supported permissioned export path with a separately scoped UX/data-handling change, or accurately limit the public claim.

Acceptance: no blocked content/actions on supported viewport sizes; advertised actions are available; exports, if later added, obey the same access limits.

Impact: layout/navigation; an export addition could add serialization cost, memory use, downloads and a new user flow. Layout fixes are polish; export changes are conditional on the parity review.

## Step 4 — Prove the candidate in the real host

Validation only at this stage; findings do not authorize unscoped code or infrastructure changes.

- Run all five positive and three negative review cases independently against the exact candidate. Add targeted engineering checks without substituting them for the required review cases.
- Cover anonymous, connected-free, full-access, expired/revoked and unrelated-owner states.
- Cover search with strict constraints, sparse/zero results, unsupported/out-of-database requests, optional contacts and evidence/document boundaries.
- Cover host approval pending/approve/deny/cancel; no link or navigation that hides a pending approval.
- Cover project/report/state creation and revision, duplicate/lost-response retries, revision conflicts, cache expiry, retained failed saves, account attachment and reconnect.
- Cover Custom-view isolation, untrusted-source/prompt-injection cases, supported desktop/mobile rendering and account destinations.
- Use isolated synthetic fixtures and a dedicated reviewer/test account. Future write tests must be explicitly within the approved implementation/testing scope; do not use customer projects, send messages or make payments.
- Measure initial search/workspace time, tab/detail interaction, peak process memory, payload size, save/retry latency, concurrent requests, busy responses and selection eviction.
- Existing shared locks and bounded cache warrant measurement; they are not proof of unacceptable production capacity. Record results and agree acceptable limits. Any capacity or cache redesign remains subject to the optimization hold.
- Verify exact-candidate CI, package contents, manifest/schema/reference checks, no secret inclusion, bundle/source provenance and deployed UI metadata. Extend release checks for demonstrated gaps such as missing UI origin and annotation drift; avoid brittle checks that merely repeat implementation.

Acceptance: evidence demonstrates supported journeys and honest failures; unresolved host, authorization, data-loss, duplicate-write or submission-contract defects block readiness. Record untested cases explicitly.

Impact: planned tests have no product behavior change. Live concurrency tests can consume shared resources and affect other users; prefer an isolated environment or approve a bounded production test separately.

## Step 5 — Assemble the review packet and hand off for publication approval

Scope:
- Confirm the verified Atlas Consulting publisher identity and authorized publishing account in the actual Portal.
- Confirm stable plugin/App identity, domains, availability countries and supported clients.
- Provide a dedicated reviewer account with sample data and appropriate existing access throughout review; no reliance on the owner's inbox/OTP. Store credentials only in secure reviewer fields, never in this repository.
- Record a real accessible walkthrough of the tested build; include search, evidence, Custom views, connection/saving and access boundaries. `demo_recording_url` is absent from the inspected ZIP; first check whether it already exists in the Portal.
- Supply corrected five-positive/three-negative cases, iframe justification if applicable, factual data/source/privacy attestations and release notes.
- Verify metadata/skills/tool scans and resolve or accurately appeal findings with evidence.
- Prepare one coherent release candidate, including the matching App source and rebuilt MCP bundle, then verify installed skill/package state separately from repository state.
- Future implementation release order: App changes/migrations if any, compatible MCP/extension, then installed package/skills; validate each dependency before proceeding.
- Obtain explicit owner authorization for deployment/public submission at the appropriate later stage. This document authorizes neither.

Acceptance: a concrete, reproducible, fully reviewable candidate and complete reviewer packet exist; all confirmed blockers are closed and any conditional issues have documented outcomes.

## Impact register for owner review

| ID / proposed edit | App/plugin performance | Workflow or user-experience effect | Scope status |
| --- | --- | --- | --- |
| R1 widget origin | Normally small; host/storage behavior must be checked | Could affect extension initialization, origin state and account navigation | Required contract fix |
| R2 safety annotations/descriptions | Little direct compute cost; changed model routing may affect calls | Host may request approval more often, including evidence reads and updates | Required; approval UX must be reviewed |
| R2 alternative evidence-registration timing | Changes DB write timing, source lookup and save latency | Could preserve read-only research but changes source registration and report-save flow | Design option only; not implicitly selected |
| R3 stable publish identity | May add lookup/locking; prevents duplicate write work | Retries return the same project; intentional new projects need a distinct operation | Required defect fix |
| R4 CSP/frames/renderer | Could affect loading, resizing and script behavior | May affect all static/interactive Custom views and state saving | Host verification required; renderer changes conditional |
| R5 policy/support copy | No material runtime effect | Changes expectations about retention, data and access | Required content correction |
| R5 retention/deletion implementation, if gaps are found | Could affect storage, cleanup load and available history | Could remove evidence, reports or saved data | Separately scoped and approved only |
| R6 consent/access text | No material runtime effect if copy-only | Changes account-connection decisions and understanding of save/full-access states | Required clarity; no auth redesign selected |
| R7 metadata/starter prompts | No direct backend cost; may change triggered research/call volume | Listing expectations, onboarding and routing may change | Required consistency; cosmetic additions optional |
| R8 skills/tool guidance | May alter tool-call count and perceived latency | Can change approvals, follow-ups, evidence and save routing | Only concrete inconsistencies; behavior review required |
| R9 mobile/shared component layout | Usually small; measure if rendering changes | Titles, table navigation, footer spacing, focus and Custom layout can change on both surfaces | Targeted polish after approval |
| R9 permissioned export, if required | Serialization/memory/download cost | Adds a user action and moves authorized data to a file | Conditional; no automatic restoration |
| Step 4 load/host tests | Can consume live capacity if run in production | Potential temporary slowdown during testing | Isolate or obtain bounded production-test approval |
| Step 5 candidate rollout | Restart/migration/compatibility risk depends on approved fixes | Users may need updated skills/package or reconnection if auth actually changes | Later approval; not part of this documentation task |

Documentation, reviewer video, test-case corrections and Portal preparation alone do not require a runtime redesign. Do not infer that all conditional options in this register must be implemented.

## Completion checklist

- [ ] Owner approves specific implementation scope and resolves R2/R4/R9 choices where needed.
- [ ] Step 1 contract and retry issues resolved with targeted evidence.
- [ ] Step 2 public policies/access text match confirmed practices.
- [ ] Step 3 listing/docs and approved UX corrections complete.
- [ ] Step 4 actual-host and concurrency evidence recorded; unresolved risks explicit.
- [ ] Step 5 reviewer packet and Portal gates verified.
- [ ] Separate deployment/publication authorization recorded before release actions.

## Source references

Official requirements checked during the audit; revalidate at implementation/submission:
- https://developers.openai.com/plugins/plugin-guidelines
- https://developers.openai.com/plugins/reference
- https://developers.openai.com/plugins/deploy/submission

Repository evidence:
- `src/intel_mcp/research_workspace.py`
- `src/intel_mcp/project_reports.py`
- `src/intel_mcp/research_server.py`
- `plugins/trialagents-intel/plugin.json` and its five skills/references
- `ui/research/workspace.tsx`, `workspace-source.json`, and shipped bundle
- `docs/CHATGPT_REVIEW_NOTES.md`, `docs/CHATGPT_PLUGIN_RELEASE.md`
- App `app/lib/project-chat-reports.ts`, `combined-prepared-projects.ts`, `project-report-html.ts`, `mcp-research-access.ts`
- App `app/research/InteractiveVisualization.tsx`, `WorkspaceTables.tsx`, `ProjectReports.tsx`
- Public support, access, terms, privacy and product pages referenced by the package

All work above is scoped future work. Only this dated planning document was added.
