# Intel Agent dataset workspace and multiple-report workflow — implementation plan

Date: 2026-09-18
Status: agreed product scope; implementation plan only. This document does not establish implementation, testing, deployment or changed entitlements.
Primary implementation owner: tarous89/intel_agent_app.
Plan location: intel_mcp repository root, beside MAX_AGENT_REDESIGN_SCOPE.md, at the user's explicit request.
Source of decisions: the product-design discussion completed on 2026-09-18.
Approved supplement: pre-agent presentation restoration and integrated delivery, documented on 2026-09-18; see section 20.

## 1. Product objective and authority

Change Intel Agent from a brief, analysis plan and single evolving report into a reusable trial dataset workspace with multiple independently saved reports.

The journey is:

Describe benchmark trials → discover groups and actual counts → approve groups → choose Light or Max → enter a message → receive a saved report → continue with another message.

A message may request new analysis, a revision, a different subgroup or a wording change. Each successfully fulfilled report-producing message is one run. Each run produces one new report containing up to four analyses/graphs. Every successful report, including revisions, remains independently available until deleted.

This scope supersedes conflicting earlier design decisions for the new workflow only. In particular:

- Do not require analysis objectives during initial trial discovery.
- Do not require a separate objective-plan approval before each run.
- Do not count individual graphs as paid/free usage units.
- Do not restrict adjacent groups to subsets of the first disease group.
- Do not retain the old one-free-Light-report-per-account restriction for new projects.
- Do not offer unlimited Max revision runs under the new purchase contract.
- Do not reuse an ever-growing conversation containing every report.
- Do not abort a useful report because an optional objective or editorial criterion is incomplete.
- Do not move managed execution back to the standalone MCP service.

Current production context remains authoritative about what is actually shipped. This plan describes the target, not current production behavior. Earlier contracts continue to apply to legacy purchases until an explicit migration policy is chosen.

## 2. Terminology

| Term | Meaning |
|---|---|
| Project / workspace | One trial-selection context, approved search groups, frozen dataset, package entitlement and collection of reports. |
| Discovery group | A short named comparison cohort defined by executable deterministic criteria. Groups may overlap and need not be nested. |
| Matched trials | Unique trials returned by the union of active discovery groups, before package sampling or pilot selection. |
| Dataset | Versioned, frozen trial profiles and group memberships selected for this workspace/tier. |
| Analysis | A question answered with supported findings, normally represented by one graph. |
| Run | One user analysis/revision message that produces a new report; not each model call or graph. |
| Report | The immutable published result of a successful run, containing at most four analyses/graphs and its own PDF. |
| Reference report | The report open when the user submits a message; it supplies context if the message refers to prior work. |
| Attempt | Internal execution/recovery work within a run; automatic attempts are not additional billable runs. |

Use consistent terminology in package copy, remaining-run counters, persisted state and operational metrics. Avoid calling 100 runs “100 analyses” where that would suggest 100 graphs.

## 3. Agreed packages and accounting

| Feature | Light | Max |
|---|---|---|
| Base price | Free | €450 per dataset workspace |
| Included runs | 5 per project | 100 per purchased workspace |
| Analyses/graphs per report | Up to 4 | Up to 4 |
| Potential total graphs | Up to 20 | Up to 400 |
| Trial selection | 5% of unique matches, rounded up; minimum 5, maximum 20, bounded by actual availability | Public allowance remains up to 1,000 analyzed trials |
| Initial runtime ceiling | At most 20 | Keep current private 100-trial testing ceiling |
| Reuse across messages | Same fixed Light sample | Same fixed Max dataset |
| Revisions | Included within 5 runs | Included within 100 runs |
| Individual PDF export | Yes | Yes |
| Source dataset XLSX download | No | Yes |
| New projects | Users may create additional Light projects | Separate purchase/grant for a different Max dataset workspace |
| Expiry | No new automatic expiry in this scope | No new automatic expiry in this scope |

The user explicitly accepts that 100 runs could generate 400 graphs and that €450 is the starting offer; monitor economics before later pricing changes. Do not introduce a subscription or a lifetime one-project restriction.

### 3.1 Light selection formula

Let N be the exact deduplicated match count across the final approved active groups, before the Max pilot ceiling is applied.

light_count = min(N, 20, max(5, ceil(0.05 × N)))

Examples:

| N | Light trials |
|---:|---:|
| 0 | 0; do not start analysis without evidence |
| 3 | 3 |
| 40 | 5 |
| 100 | 5 |
| 200 | 10 |
| 380 | 19 |
| 381 | 20 |
| 400 | 20 |
| 1,000 | 20 |

The five-trial minimum takes precedence over percentage limits for small cohorts. There is no separate hard 10% limit. Apply the formula to matched trials, not the 100-trial Max testing cap.

Freeze a representative, reproducible sample once. Preserve useful group diversity where sample size permits; never promise representation of every subgroup in a five-trial sample. Avoid sampling anew for each question, cherry-picking after seeing results, or always taking the first/newest database page.

### 3.2 Run accounting

- Reserve one run atomically when accepting an analysis/revision submission.
- Commit exactly one usage unit when a valid report is durably published.
- New questions, analytical revisions and successful one-word edits all cost one run.
- A successful partial report costs one run; it need not contain four graphs.
- Automatic retry, worker restart, replayed callback or duplicate browser submission must not consume an additional run.
- A technical failure with no published report releases the reservation after bounded recovery.
- A clarification-only response produces no report and consumes no completed run.
- Viewing, downloading, renaming or deleting reports consumes no run.
- Deleting a report does not refund its completed run.
- Trial discovery and pre-approval group refinements belong to setup, not the report-run allowance. Apply operational rate controls without silently changing the agreed project allowance.
- App-owned database accounting is authoritative. Logs are diagnostics, not the source of remaining allowance.
- Reservation recovery must be fenced against late publication so an expired attempt cannot both refund and publish.

## 4. Initial workspace UX

Keep the existing branded page design and the upper trial-description field. Remove the separate initial “what analysis do you want?” field.

Suggested placeholder:

“Describe your planned trial, or the disease, therapeutic area or types of trials you want to benchmark.”

The field accepts a planned trial description or a general benchmark interest. It must not force a disease when the user is interested in modality, trial design, phase, stage, operations or another supported dimension.

On submit:

1. Show the existing progress-bar treatment for understanding the description.
2. Generate structured search groups in one quick, bounded model call.
3. Execute deterministic database searches and show progress for each named group.
4. Show real group counts and the unique total.
5. Offer “Continue” / approval and “Refine groups”.
6. Keep the refinement text field collapsed until the refinement button is clicked.
7. After approval, show Light and Max with actual selected-trial expectations and 5/100 runs.
8. Once the tier is selected/activated, prepare the frozen dataset and show the single analysis composer.

Do not reintroduce a compulsory analytical plan between the user's analysis message and execution. A genuinely unclear analysis reference may trigger a short clarification, but sparse search results should normally use the agreed fallback strategy first.

## 5. Structured discovery contract

### 5.1 Model responsibility

Use a compact structured-output call to translate the description into executable search expressions. Supply the model with the actual supported field catalogue and controlled values from the database-backed interface, including therapeutic areas and modalities; do not let it invent category labels.

The model returns:

- A concise workspace title and interpreted trial description.
- A primary broad group, normally the named disease without unnecessary phase/stage/biomarker restrictions.
- A target of three to five additional meaningful narrower or adjacent groups.
- Fewer groups where justified; aim for at least two meaningful groups, but do not invent or duplicate groups to satisfy a hard count.
- Stable group keys, short human-readable names and explanatory selection labels.
- Structured criteria and a nested AND/OR expression for each group.
- Clinically appropriate disease names, aliases and abbreviations.
- A small ordered set of broader fallback groups in the same response.
- Explicit supported dimensions such as therapeutic area, modality, phase, stage and country as relevant, with any unknown mapping identified internally.

Disease is not mandatory. Where absent, a combination of therapeutic area, modality, phase, stage or operational/design attributes may define the first group, subject to actual searchable fields.

Adjacent groups may lie outside the primary disease. Examples include a similar modality in another indication or a comparable operational/design setting. Do not relabel these as disease subgroups or force them into the primary disease's denominator.

### 5.2 Deterministic backend responsibility

- Validate structured output against an allowlisted expression schema.
- Resolve category values against the current controlled catalogue.
- Execute parameterized conditions, not model-generated SQL.
- Support nested AND/OR with explicit parentheses and bounded expression depth, leaf counts and term lengths.
- Implement categorical filters and case-insensitive text matching over titles, disease/condition fields and relevant profile narrative fields supported by the Engine.
- Use defined token/phrase matching for short abbreviations to reduce accidental substring matches. Do not assume every vaguely similar acronym is a disease synonym.
- Keep missing fields distinct from negative evidence.
- Paginate fully for counts and eligible IDs; distinguish zero results from query/transport failure.
- Deduplicate by canonical trial identity within each group and across all groups.
- Preserve overlapping memberships and distinguish group totals from unique workspace totals.
- Record normalized criteria, query version, profile/source version and timestamps.
- Treat profile approval states equally in this authorized workflow; do not filter, weight or rank by approval metadata.
- Keep public MCP/Site permissions unchanged; use the authorized App–Engine boundary for the new Light and Max workspace behavior.

Illustrative expression shape, not a database column specification:

~~~json
{
  "id": "lung_trials",
  "name": "Lung cancer trials",
  "expression": {
    "any": [
      {
        "all": [
          {"field": "therapeutic_area", "op": "in", "values": ["<database oncology value>"]},
          {"field": "clinical_text", "op": "contains_any", "values": ["lung cancer", "NSCLC", "non-small cell lung cancer"]}
        ]
      },
      {
        "all": [
          {"field": "therapeutic_area", "op": "in", "values": ["<database respiratory value>"]},
          {"field": "clinical_text", "op": "contains_any", "values": ["lung carcinoma", "small cell lung cancer"]}
        ]
      }
    ]
  }
}
~~~

Map logical fields to verified Engine fields during implementation. Unsupported filters cannot simply be ignored if doing so changes the intended query. Repair the expression or choose an explicitly broader, accurately named supported group.

### 5.3 Scope of search evidence

The initial discovery pass uses database categories and searchable profile text. Do not make initial counts depend on new OCR, full-document extraction or an autonomous research loop. Reuse already available search projections.

Analytical tool access can use the existing authorized retrieval surface, but this scope does not assume that every source-document capability is currently enabled. Confirm enabled document access and bounds during implementation; any allowed evidence must belong to a frozen workspace trial and be captured before use.

## 6. Fallback groups and sparse results

The model prepares fallback expressions in the initial call. They are not initially shown and need not be executed unless the primary/ordinary group union contains fewer than 100 unique trials.

Recommended deterministic policy for implementation:

1. Search the ordinary groups and calculate their deduplicated union.
2. If the union is at least 100, do not activate fallback groups.
3. Otherwise, execute fallback candidates in model-provided order from more relevant/specific to broader.
4. Activate the first useful candidate that supplies sufficient breadth; retain the original groups.
5. If necessary, consider the next bounded candidate. Deduplicate additions and stop when the target is reached or candidates are exhausted.
6. Every activated fallback becomes a visible named group with its actual count before user approval.
7. Keep unused fallback candidates out of the visible group list.
8. If all candidates remain below 100, show the real smaller result and allow a supported analysis. One hundred is a breadth target, not a mandatory success gate.
9. If no trials exist, retain the brief and offer refinement; do not invent a dataset or consume an analysis run.

Examples of useful fallback combinations: phase III oncology; oncology antibody trials; phase III antibody trials. Prefer constrained combinations to all oncology or phase alone. Broader does not mean indiscriminate.

The fallback broadening is intentional and does not require an additional warning/approval detour before showing results. The normal group approval/refinement step lets users correct an overly broad result.

The user chose automatic broader results over repeatedly asking them to make their description more precise. However, matched counts must stay factual and labels must make the broadened cohort clear.

## 7. Dataset preparation and stable evidence

After group approval and tier selection, freeze the authorized dataset once and reuse it for all subsequent runs.

Store:

- Approved description, groups, normalized queries and active fallback provenance.
- Unique matched count and per-group matched counts.
- Selected trial IDs, full profile versions/hashes and retrieval timestamps.
- Selected group memberships, separate from total discovered memberships.
- Sampling/selection rule, deterministic seed where applicable and package/pilot limits.
- Dataset manifest, schema version and immutable evidence references.
- Derived fields/results with their definitions and source references, versioned separately from raw evidence.

Keep raw trial evidence and large artifacts in Engine-owned storage; App stores ownership, workflow metadata and references.

For Max, select up to 100 during testing while preserving relevant group diversity. Keep the public ceiling at 1,000. Raising to 500 or 1,000 is a later measured rollout decision; this plan does not authorize that increase.

Search counts are not analyzed counts. The report must describe the trials actually analyzed and must never claim all matches were processed when a selection ceiling was applied. Private rollout labels stay out of marketing.

Changing questions or graph presentation does not refresh the dataset. Requests to change the underlying trial universe should lead to a new dataset/project, not silently replace evidence underneath existing reports.

For later Light-to-Max upgrade support, prefer a separately versioned Max snapshot based on the approved search snapshot, retaining the Light evidence/report versions. Detailed grant transition behavior is an implementation default to verify, not an authorization to rewrite historic purchases.

## 8. Single composer and agent context

Use one text input for new analysis and revision. Do not add a mandatory “new versus revise” selector or deterministic keyword classifier.

Each submission captures, server-side:

- User message.
- Workspace/dataset identity and authorized trial manifest.
- The currently open report ID/version, if any.
- The compact structured content of that report: titles, text, chart data, methods, subgroup results and source/calculation references.
- Current versioned analysis/design instructions and scoped tool access.
- The pending run identity, budgets and idempotency key.

The same analyst call interprets intent. A separate intent-classification LLM call is unnecessary.

| User message | Expected interpretation |
|---|---|
| “Change this to percentages.” | Revise the referenced report; preserve the underlying evidence and recompute dependent text where needed. |
| “Now compare recruitment across countries.” | New analytical question against the same dataset. |
| “Repeat this for Germany.” | Reuse the reference report's analytical approach with a German subset. |
| “Shorten the introduction.” | Presentation revision, still a full run if it publishes a report. |
| “Add trials registered this week.” | Dataset change request; do not silently alter the frozen dataset. |
| Ambiguous reference with no identifiable report | Ask one concise clarification without consuming a completed report run. |

Start a fresh logical execution context for each run. Send only the open/reference report, not the full project history, all past PDFs or an accumulating conversation. Provide referenced calculation artifacts on demand. Bounded within-run recovery may resume the same execution from durable checkpoints.

Capture the reference at submission; clicking another sidebar card while the run executes must not change its input. Opening an older report makes that report the reference for the next message.

The agent determines whether previous analytical content is relevant. A new question must not be forced into the previous report's objectives merely because that report was open.

## 9. Analysis behavior

On submission, begin immediately and show progress. Within the same run, the agent:

1. Interprets the question and its relationship to the reference report.
2. Identifies the main analysis and a small number of useful adjacent analyses.
3. Limits the report to at most four analyses/graphs.
4. Retrieves or reads relevant frozen profiles and source-backed derived fields.
5. Executes reproducible calculations and stores supports.
6. Produces concise findings and meaningful subgroup comparisons.
7. Applies targeted corrections and publishes every independently valid supported section.

Four is a maximum, not a target that requires padding. The agent should broaden analytical perspective where useful, not generate repetitive cards or irrelevant objectives.

Retain existing useful analytical rules:

- Answer clinical, trial-development and operational questions; do not fill reports with database completeness metrics.
- Deduplicate supporting trials and use correct contributing denominators.
- Overlapping groups cannot be summed as disjoint populations.
- Do not turn participation into unsupported enrollment/performance estimates.
- Unknown membership is not proven nonmembership.
- Omit empty/unsupported sections and n=0 frequency results; preserve legitimate zero-valued measurements.
- Use descriptive small-sample findings when justified without implying unsupported precision.
- Rank against complete relevant results before limiting graph display to ten items.
- Preserve complete rankings in Max data exports.
- Broad context comes first when it meaningfully answers the question; follow with relevant subgroup differences.
- Since groups may now be nonnested, choose the appropriate named comparison population for each graph rather than forcing every graph to use the original disease group.
- Do not force a misleading graph for a genuinely qualitative question. A useful supported table or brief qualitative section is acceptable; never invent numeric evidence to fill the graph allowance.

Do not automatically call every trial profile into every prompt. Use the frozen evidence bundle, deterministic summaries, bounded retrieval and calculation artifacts. Preserve the user's intent to analyze the authorized dataset without pretending that a prompt containing a few examples constitutes whole-dataset analysis.

## 10. Report design and PDFs

Restore and retain the actual pre-agent report presentation pinned in section 20, including the dark background, green/blue/amber analysis palettes, typography, spacing, chart components and PDF branding/pagination. Recover and reuse the source components and styles; a prompt requesting a similar design is insufficient. The analyst supplies structured content and chart inputs; the application-owned renderer controls presentation. Build this restoration and the new workflow together, with no separate production rollback.

Every report follows this order:

1. Short title and a simple results summary containing one meaningful sentence per included analysis.
2. Compact factual dataset context, without long completeness commentary.
3. For each analysis: headline → concise result statement → graph → meaningful subgroup findings or specific notes → very short method description.
4. Source references and only necessary supporting detail.

Avoid long essays, repetitive disclaimers, empty cards and summaries that claim omitted objectives were completed. A skipped explicitly requested objective may receive a short factual note; do not pad the report with processing diagnostics.

Keep at most ten displayed items per graph. Maintain readable labels, correct axes and percentages, adequate contrast, meaningful zeros and coherent colors. Smaller subgroup tables/notes should not create an unbounded series of extra graphs.

Use one versioned branded template and shared deterministic rendering for HTML and PDF, extracted from the pinned pre-agent implementation. The agent supplies evidence-backed content and chart inputs, never unrestricted layout/CSS that replaces the approved presentation. No separate design model is required by the agreed plan; any later change to that architecture should be justified by measured quality. Section 20 defines the exact recovered design, writing and PDF contract and its intentional adaptations.

Each successful run has its own downloadable PDF. Online content and PDF must agree. Preserve dark backgrounds/contrast in print, readable type, wrapped labels and reliable multi-page flow. Do not shrink a report to unreadable text to fit pages.

Combined PDF export of selected reports is in the first-release scope. It assembles existing report artifacts in selected order, identifies each report and adds no model work or usage charge.

PDF rendering failure must not erase valid published HTML. Retry the derivative export independently and attach it to the same immutable report; do not create a new run or charge again.

## 11. Right sidebar and workspace navigation

- Use a right sidebar on desktop and a collapsible equivalent on narrow screens.
- Show one named entry for every successful run, including revisions.
- Each card includes a small report-page preview/snippet, title and useful date/order information.
- Provide open, rename, delete and individual PDF actions.
- Include Max dataset XLSX download in the sidebar.
- Show remaining runs clearly without exposing internal model/tool details.
- Auto-save reports; do not require a Save button.
- Opening a report establishes the next message's reference.
- Keep prior reports visible while a new run is queued, executing or retrying.
- Failed attempts do not create empty successful report cards; expose retry/status separately.
- Use lazy preview loading and compact metadata so a 100-report sidebar does not load 100 full HTML reports or PDFs.
- Store report lineage privately for tracing revisions, while presenting every result as a peer entry.
- A user deletion hides/removes that report from normal browsing but must not break retained child reports, dataset integrity or usage accounting. Define safe artifact retention/reference cleanup.

No shareable analysis links are required in this release.

## 12. Reliability and partial completion

The user explicitly prefers a useful report over repeated failure because a nonessential criterion is unmet.

Use bounded recovery and objective-level isolation:

| Condition | Intended handling |
|---|---|
| Optional field missing | Continue with supported fields. |
| One objective unsupported | Omit it; publish valid siblings and adjust the summary. |
| One subgroup empty | Omit that subgroup result; do not fail the report. |
| Minor prose/length/design preference missed | Normalize or keep readable valid output. |
| Malformed optional section | Salvage valid constituent findings. |
| Synthesis failure | Compose a concise summary from validated findings. |
| Transient provider/network error | Retry with backoff and checkpoint reuse. |
| Analyst interruption | Reconcile durable state before resuming; avoid duplicate paid work. |
| PDF failure after valid HTML | Retry export independently. |
| No valid supported finding survives | Preserve dataset and previous reports, explain briefly, release allowance; do not charge for an empty shell. |
| Invalid authorization, cross-user access or unsafe executable output | Enforce the boundary; never relax it to improve completion rate. |
| Unsupported arithmetic or fabricated evidence | Repair or remove the finding, never publish it as established fact. |
| Artifact persistence unavailable | Retry; do not claim an unsaved report is published. |

Differentiate hard protections from advisory quality checks. Keep ownership, evidence identity, numerical validity, HTML isolation and immutable publication requirements strict. Do not keep the old “all planned objectives must pass or the entire report fails” gate.

If fewer than four analyses remain, publish them. A correction should target the failed unit, not rerun all valid work. Persist progress/results independently of model-session lifetime. Use bounded attempts and explicit terminal states; “minimize no report” does not mean unlimited retries.

## 13. Architecture and ownership

| Repository/service | Responsibility |
|---|---|
| tarous89/intel_agent_app | Primary implementation: discovery orchestration and UX, projects, package/checkout, usage ledger, jobs, analyst orchestration, report records, sidebar, progress and exports. |
| Existing App Render service and Python worker | Execute the new workflow using the existing supervised worker; no new worker service is part of this plan. |
| tarous89/intel-agent | Clinical search/categories, all-state authorized reads, source profiles, frozen evidence and large artifact persistence through versioned HTTP interfaces. |
| tarous89/intel_mcp | Holds this plan beside the earlier scope. Standalone MCP remains isolated; no new managed-workflow routing through it is required. Preserve legacy/public/Site behavior. |
| tarous89/trialagents-public | Update affected public package copy/landing content when the new commercial flow actually launches. Do not edit archived App public report/CTIS sources. |
| tarous89/trialagents | Shared brand/product rules only if a shared rule actually changes. |

Reuse the App-owned restricted evidence surface. If MCP-compatible tool calls are used, that does not require the standalone MCP service to own execution.

Keep clinical retrieval limited to authorized filter/profile/document capabilities. No agent access to ingestion, classification/extraction worker starts, admin, billing, database credentials or writes. Validate trial identity against the workspace manifest on every analytical read; the analyst cannot expand the dataset through a new filter call.

Documents, profiles and user-supplied trial descriptions are data, not permission to execute embedded instructions.

Exact Engine interface changes must be verified against its current context/source during implementation. Do not duplicate clinical SQL in App or widen unrelated public read scopes.

## 14. Proposed persistence and API contracts

These are engineering proposals, not claims that these tables/routes already exist. Prefer extending current compatible records over introducing parallel systems.

### 14.1 Records

| Record | Essential fields |
|---|---|
| Workspace | Owner, title, brief, flow version, state, approved search version, active dataset/tier grant references. |
| Search version | Catalogue/schema versions, normalized groups/expressions, fallback candidates/activation, exact counts, result manifest, timestamps. |
| Dataset version | Trial/source manifest, content hash, matched/selected counts, package/pilot limits, memberships, selection trace, storage reference. |
| Package grant | Workspace/user, Light/Max, frozen price/discount/payment source, run allowance, grant version. |
| Run | Message, reference report ID/version, dataset ID, idempotency key, reservation, job/attempt state, progress, provider execution IDs, timestamps. |
| Report | Run ID, optional parent/reference report, name, supported section metadata, immutable HTML/PDF/preview references, calculation/support manifest, published timestamp, deletion marker. |
| Usage ledger | Grant/run, reserve/commit/release transitions, idempotency and audit references. |
| Export job | Exact report IDs/versions or dataset artifact version, state, checksum and output reference. |

Persist raw evidence/large artifacts on the Engine side and ownership/workflow references on the App side. Frozen raw profiles must not be recopied for every run; save run-specific derived artifacts and immutable references.

### 14.2 API capabilities

Provide authenticated operations for:

- Creating a workspace and submitting/refining trial discovery.
- Polling/resuming discovery progress and obtaining named counts.
- Approving a particular search version.
- Activating Light or verifying/granting Max.
- Preparing/resuming the dataset snapshot.
- Submitting a message with an explicit reference report and idempotency key.
- Reading authoritative run progress and remaining allowance.
- Listing/opening/renaming/deleting report entries.
- Streaming individual PDFs and Max XLSX exports.
- Requesting combined PDF export of exact selected report versions.

Enforce owner checks server-side on every read/write/download. Capture approved search and dataset versions in checkout/run requests so concurrent tabs cannot switch the paid dataset.

Serialize conflicting dataset preparation and resource-heavy work through existing durable jobs. Support either a short per-workspace run queue or one active run at a time with explicit UI state; do not permit concurrent submissions to overspend the final allowance.

### 14.3 State transitions

Workspace: draft → discovering → groups_ready → package_selection → dataset_preparing → ready.

Run: accepted/reserved → queued → interpreting → analyzing → preparing_report → published.

A run can transition into retrying, needs_clarification or failed/released as appropriate. Published report state is independent of PDF-derivative state.

Progress uses completed-stage counts where factual. Active model work is indeterminate; do not manufacture percentages. Report preparation becomes active immediately after analytical work, including while saving and exporting.

## 15. Current implementation touchpoints

Paths verified in the App repository tree during planning include:

- app/app/page.tsx and app/app/projects/page.tsx.
- app/components/ReportPlanOverview.tsx.
- app/components/ReportPackageDialog.tsx.
- app/components/LightReportProgress.tsx.
- app/components/MaxAgentReport.tsx and max-agent-report.module.css.
- app/lib/report-package-copy.ts.
- app/lib/max-agent-jobs.ts.
- app/lib/report-pdf-pagination.ts.
- app/api/analysis-plan/route.ts.
- app/api/internal/max-agent/route.ts.
- app/api/max-agent/evidence/[runId]/route.ts.
- report_worker/max_report_worker/plan.py.
- report_worker/max_report_worker/max_agent_execution.py.
- report_worker/max_report_worker/max_agent_session.py.
- report_worker/max_report_worker/max_agent_evidence.py.
- report_worker/max_report_worker/max_agent_tools.py.
- report_worker/max_report_worker/max_agent_instructions.py.
- report_worker/max_report_worker/max_agent_output.py.
- report_worker/max_report_worker/max_agent_exports.py.
- report_worker/max_report_worker/max_agent_pdf.py.
- report_worker/max_report_worker/report_dataset.py and report_artifacts.py.

Inspect current source before assigning exact edits. Add migrations using the next available sequence at implementation time. Do not blindly retrofit the legacy MCP executor or reuse its obsolete ownership instructions.

## 16. Delivery sequence

The approved approach is one integrated build and release: recover the presentation foundation first, verify it against the pinned pre-agent version, connect the new workspace flow to it, then validate and deploy together. Do not restore the old production application as an intermediate deployment.

### Phase 0 — recover and verify the presentation foundation

- Pin the App and analyst-source baselines listed in section 20.
- Extract the actual legacy report renderer, styles, chart palettes, progress components and PDF rules into reusable App-owned presentation components.
- Preserve the current durable worker, jobs, evidence interfaces and security boundaries.
- Define a versioned structured report contract and adapter so agent output uses the restored renderer.
- Render the original and recovered foundation with identical synthetic content; compare desktop, mobile and PDF before connecting new workflow behavior.
- Apply only the explicit adaptations listed in section 20: four analyses per run, ten graph items, concise opening and method, independent report history and the newly agreed package/group rules.
- Capture checked reference fixtures and a source/behavior mapping in the implementation repository. This planning update itself creates no implementation or deployment.

Exit: the recovered foundation demonstrably matches the old visual system and PDF behavior apart from documented, intentional adaptations. “Looks roughly dark green” is not acceptance.

### Phase 1 — contracts, state and feature boundary

- Define versioned discovery expressions, workspace/dataset/run/report contracts and package terms.
- Add additive schema/ledger changes and a server-side new-workflow flag.
- Preserve legacy routes/renderers and entitlements.
- Establish immutable publication, idempotent usage and artifact ownership invariants.
- Inventory enabled retrieval/document capabilities and verify Engine contract gaps.

Exit: synthetic state transitions, cross-user checks, concurrency and allowance recovery pass.

### Phase 2 — trial discovery and fallback

- Implement controlled catalogue input and the quick structured planner.
- Implement validated nested AND/OR search through Engine interfaces.
- Add paginated exact counts, deduplication, fallback execution and group refinement.
- Deliver the single-field initial UX and factual progress bars.
- Include disease-free queries and nonnested adjacent cohorts.

Exit: deterministic fixtures demonstrate correct expressions, overlap counts, fallback thresholds and visible group names.

### Phase 3 — packages and frozen datasets

- Implement Light formula and stable representative selection.
- Implement Max private 100-trial pilot selection with the public 1,000 allowance unchanged.
- Freeze profile snapshots/checkpoints before analyst work.
- Wire €450 workspace grants and 5/100-run accounting.
- Remove the account-wide single-Light-project limit only for the new flow.
- Retain existing verified checkout, discounts and replay protections.

Exit: same dataset survives repeated runs/restarts; sampling and entitlement boundaries are correct.

### Phase 4 — unified run execution

- Route both tiers through the durable App-owned orchestration for the new workflow.
- Implement one composer, explicit reference capture and fresh bounded run context.
- Identify up to four analyses internally without a second plan screen.
- Add objective-level correction/salvage and persist independent findings.
- Publish one immutable report per successful message.
- Verify all-state equality and dataset-scoped tools.

Exit: new question, revision, older-report reference and partial-success cases work without full-history loading or duplicate usage.

### Phase 5 — presentation, sidebar and exports

- Connect the new run/report records to the already recovered and verified Phase 0 renderer; do not introduce a second presentation redesign at this phase.
- Add right sidebar previews, open/rename/delete, responsive layout and run counter.
- Add individual PDFs for both tiers, selected-report combined PDF and Max-only XLSX.
- Make HTML usable during a derivative PDF retry.
- Render and inspect desktop, mobile and multi-page PDF fixtures.

Exit: online/PDF consistency, reliable page flow and 100-entry navigation are verified.

### Phase 6 — migration, pilot and release

- Keep stored reports and existing purchases available through their original contracts.
- Decide explicitly whether/how prior paid customers receive new grants; do not silently reduce unlimited legacy revisions to 100.
- Launch to controlled new projects behind the flag.
- Keep the 100-trial testing ceiling.
- Run non-model verification first. Existing user direction reserves the first real managed-report test for the user; planning does not authorize background paid report runs.
- Measure real quality, runtime, memory, per-run cost, partial completion and export success during the authorized pilot.
- Coordinate launch copy across App and canonical public owners.
- Update owning current contexts only when behavior is actually implemented or interfaces change.
- Roll back new-workflow creation independently of preserving access to completed reports/jobs.

Exit: release gates below pass and user acceptance is recorded. Expansion to 500/1,000 trials requires separate measured readiness.

## 17. Acceptance checklist

### Discovery and cohort integrity

- [ ] Initial UI has one concise description field; no analysis objective field.
- [ ] Controlled categories correspond to actual database values.
- [ ] Disease synonyms search supported title/condition/profile text with correct AND/OR precedence.
- [ ] Adjacent disease, modality and design groups can be outside the primary disease.
- [ ] Ordinary group counts and unique union are exact and deduplicated.
- [ ] At 100 unique initial matches, fallback is not activated; at 99 it can be.
- [ ] Unused fallback groups remain hidden; activated ones are named and counted visibly.
- [ ] Query failure is not shown as zero matches.
- [ ] Fewer than 100 results can proceed; zero does not create a fake dataset.
- [ ] Group refinement input appears only after its button is clicked.
- [ ] Approval states have equal eligibility.

### Dataset and commercial behavior

- [ ] Light formula passes N = 0, 3, 40, 100, 200, 380, 381, 400 and 1,000.
- [ ] Light uses the matched union count, not the Max pilot-selected count.
- [ ] Light sample does not change between messages or after reopening.
- [ ] Multiple Light projects are allowed, with five runs in each.
- [ ] Max base purchase is €450 for 100 runs in one dataset workspace.
- [ ] A 100% authorized account discount still works without a fake payment.
- [ ] Both revisions and new analyses consume one run when a report publishes.
- [ ] Duplicate submit, retry and callback consume at most one run.
- [ ] Concurrent requests cannot overspend the last available run.
- [ ] Failed/no-report and clarification-only outcomes do not consume completed allowance.
- [ ] Deletion does not refund allowance.
- [ ] No Light dataset download route can be bypassed through report artifacts.
- [ ] Match count, selected count and actual contributing counts are not conflated.

### Agent and history behavior

- [ ] Same composer supports new questions, formatting edits and analytical revisions.
- [ ] Every successful run creates a separate report; reference report remains unchanged.
- [ ] Opening an older report correctly changes the next submitted reference.
- [ ] Changing the open report after submission does not change an active run.
- [ ] Only the referenced report enters context, not all prior reports.
- [ ] Up to four analyses/graphs; fewer are permitted without failure.
- [ ] Fresh execution can reproduce reference calculations from saved artifacts.
- [ ] Analyst tools cannot expand beyond the authorized dataset or access other workspaces.
- [ ] One unsupported objective does not cancel valid siblings.
- [ ] Hard evidence/authorization/sanitization protections remain enforced.
- [ ] If no valid result survives, prior reports/dataset remain available and allowance is released.

### Design, exports and operations

- [ ] Phase 0 source recovery and the detailed section 20 visual/PDF acceptance matrix pass.
- [ ] Dark branded HTML/PDF matches the pinned pre-agent visual reference, with only documented new-workflow adaptations.
- [ ] Summary is short; each analysis follows headline/result/graph/subgroups/method order.
- [ ] Ten-item graphs, long labels, negative values, zero values and small subgroups render correctly.
- [ ] Right sidebar cards have useful previews and work with 100 saved reports.
- [ ] Every report has an independently downloadable PDF.
- [ ] Combined export includes exact selected report versions in requested order.
- [ ] PDF retry leaves valid HTML and usage unchanged.
- [ ] Max XLSX includes frozen profiles, group definitions/memberships, derived data, full rankings and source support with lossless long-text handling.
- [ ] Exports reuse persisted evidence/results and do not start LLM runs.
- [ ] Restart after reservation, evidence freeze, calculation or publication does not lose state or duplicate charges.
- [ ] Progress survives reload and reports true stages without invented percentages.
- [ ] Existing Light/Max reports, purchases, Site Agent and public MCP remain usable.
- [ ] No new Render service, compute upgrade, DNS change or standalone MCP dependency is introduced.

## 18. Risks, defaults and deferred decisions

### Agreed guardrails

- Keep the current 100-trial Max testing ceiling until measured expansion.
- Use the existing App worker; do not add a paid service.
- Keep independent work units and bounded retrieval/export memory.
- Do not equate incomplete optional content with report failure.
- Do not relax numerical truth or access controls to improve completion metrics.
- Keep pricing at €450/100 runs initially and observe cost rather than silently changing the offer.

### Engineering defaults to verify during implementation

These are proposed implementations of the agreed behavior, not separately negotiated product promises:

- Ordered fallback selection and a bounded maximum number of fallback queries.
- Stable, group-aware sampling and selection tie-breaks.
- Exact query-expression complexity limits and text-search projections.
- Exact schema/route names, retry budgets and provider/session adapters.
- One active run per workspace or a short durable queue.
- Safe deletion/tombstone and shared-artifact cleanup mechanics.
- Frozen-source handling for Light-to-Max upgrade.
- Versioned derived-data attachments in the Max workbook while keeping the raw dataset fixed.
- No new expiry unless a later product decision explicitly introduces one.

### Deferred product/release decisions

- Automatic conversion or additional grants for historic Max purchases.
- Any paid top-up/subscription after the included 100 runs.
- Changes to €450 pricing or the allowance based on measured economics.
- Raising runtime trial limits to 500 or 1,000.
- Shareable analysis links.
- Any new source-document retrieval/extraction capability beyond the existing authorized surface.

None of these deferred items blocks writing this plan or implementing the new-project flow. Do not invent a migration entitlement or expand source access in the meantime.

## 19. Documentation and release handoff

This dated plan is intentionally saved beside the earlier MAX_AGENT_REDESIGN_SCOPE.md. That earlier document remains available as historical design context; its old persistent-session, mandatory plan, nested-group and MCP-worker ownership choices do not override this scope or current owner contexts.

At implementation start, read only the owning repository's current PROJECT_CONTEXT.md and one relevant subsystem MD. Open Engine or public repositories only for their documented interface/copy changes.

At completion:

- Update App PROJECT_CONTEXT.md and REPORT_EXECUTION_CONTEXT.md with shipped state.
- Update Engine context/subsystem documentation if its API contract changes.
- Update canonical public copy at release, not archived App/CTIS editorial sources.
- Link the implementation work to this plan.
- Record concrete acceptance evidence and outstanding release gates separately from product promises.
- Never store secrets, mutable production counts or chronological debug logs in current contexts.

References:

- [Previous agent redesign scope](MAX_AGENT_REDESIGN_SCOPE.md)
- [Current App context](https://github.com/tarous89/intel_agent_app/blob/main/PROJECT_CONTEXT.md)
- [App report execution context](https://github.com/tarous89/intel_agent_app/blob/main/REPORT_EXECUTION_CONTEXT.md)
- [Current MCP context](PROJECT_CONTEXT.md)


## 20. Approved pre-agent presentation restoration contract

Approval: the user approved recovering the previous presentation as the foundation of the new build and adding the complete restoration scope to this plan on 2026-09-18.

This section is an implementation requirement, not an optional design suggestion. It supplements sections 9–12 and 16–17 and resolves the meaning of “restore the old design.” Do not treat the September 18 cosmetic restoration or a newly generated dark-themed template as an exact substitute for the pre-agent reference.

### 20.1 Recovery baseline and evidence

The last App commit before the managed-agent UI integration is:

- Repository: tarous89/intel_agent_app.
- Commit: bf77b4f6eb375fb8b4763aa1bfba839acca09d3f.
- Date: 2026-09-15.
- It is the direct parent of the September 17 agent UI integration commit 0118da79c0e4e8883043fc2822ac8196de94cfb3, PR #144.

The relevant pre-agent analyst/presentation-instruction baseline is:

- Repository: tarous89/intel_mcp.
- Commit: c80286d795d35c0af5eb3306fc820b605494c060.
- Date: 2026-09-15.
- It precedes managed-agent implementation commit 10c526c4f1bed5337ab8fad69be6864550a37cf4, PR #73.

The inspected September 17 App diff routes completed max_agent_html_v1 output away from CompletedReport into a newly added MaxAgentReport wrapper. The wrapper initially uses basic controls and a white-background iframe. The same change routes active managed jobs away from ProgressCard into an ordered status list. Therefore the old CSS and renderer are recoverable, but were bypassed by the new path.

App PR #152, commit 62737f05b0d1b7304b3dfa1870a8cc281f952eba on September 18, attempts to restore branding/progress and strengthen report coverage. It is useful current implementation context, but not the approved historical visual baseline. Its report-fatal coverage rules must not override this plan's partial-success policy.

These findings come from repository source/diffs and pinned instructions. They do not establish that a particular customer's historical report has been visually re-rendered or that current production matches the old version.

### 20.2 Source inventory to recover

| Pinned source | Recover and preserve |
|---|---|
| [App report and progress renderer](https://github.com/tarous89/intel_agent_app/blob/bf77b4f6eb375fb8b4763aa1bfba839acca09d3f/app/components/LightReportProgress.tsx) | CompletedReport, analysis/visual composition, palettes, cohort strip, export controls, ProgressCard/StepBar, PDF cover/branding/export behavior. |
| [App report stylesheet](https://github.com/tarous89/intel_agent_app/blob/bf77b4f6eb375fb8b4763aa1bfba839acca09d3f/app/components/light-report-progress.module.css) | Exact report colors, spacing, typography, backgrounds, borders, responsive behavior and print-layout styles. |
| [PDF pagination helper](https://github.com/tarous89/intel_agent_app/blob/bf77b4f6eb375fb8b4763aa1bfba839acca09d3f/app/lib/report-pdf-pagination.ts) | Block-aware continuation, complete text/inline markup, indivisible graphics, oversized-content handling and no font shrinking. |
| [Application styles](https://github.com/tarous89/intel_agent_app/blob/bf77b4f6eb375fb8b4763aa1bfba839acca09d3f/app/globals.css) | Light workspace, dark navigation, branded inputs, controls and layout rhythm; reuse relevant selectors, not a whole-file rollback. |
| [Package chooser styles](https://github.com/tarous89/intel_agent_app/blob/bf77b4f6eb375fb8b4763aa1bfba839acca09d3f/app/components/report-package-dialog.module.css) | Light card and restrained dark-green/sage Max card, selected/hover states and readable contrast. |
| [Historical execution context](https://github.com/tarous89/intel_agent_app/blob/bf77b4f6eb375fb8b4763aa1bfba839acca09d3f/REPORT_EXECUTION_CONTEXT.md) | Established report, progress and PDF behavior, interpreted with the explicit supersessions below. |
| [Shared concise-writing and editorial recovery rules](https://github.com/tarous89/intel_mcp/blob/c80286d795d35c0af5eb3306fc820b605494c060/src/intel_mcp/report_output.py) | Takeaway-first writing, short interpretation, safe shortening and retention of valid original content. |
| [Max analytical instructions](https://github.com/tarous89/intel_mcp/blob/c80286d795d35c0af5eb3306fc820b605494c060/src/intel_mcp/max_report.py) | Decision relevance, broad/contextual findings, meaningful subgroup comparisons, provenance and clinical qualifications. |
| [Group-result ordering](https://github.com/tarous89/intel_mcp/blob/c80286d795d35c0af5eb3306fc820b605494c060/src/intel_mcp/max_group_analysis.py) | Broad-to-specific ordering without changing metric values, labels, support or within-group rankings. |
| [Report presentation regression fixtures](https://github.com/tarous89/intel_agent_app/blob/bf77b4f6eb375fb8b4763aa1bfba839acca09d3f/tests/report-quality.test.mjs) | Signed/zero bars, omission of internal evidence panels and empty sections, clinical cohort strip and retained-finding display. |
| [PDF visual stress fixture](https://github.com/tarous89/intel_agent_app/blob/bf77b4f6eb375fb8b4763aa1bfba839acca09d3f/tests/report-pdf-isolated-fixture.mjs) | Concise and oversized text, full graphic preservation, overflow checks and visual page inspection. |

The source location of old prompts does not assign execution ownership to MCP. Adapt those instructions into the App-owned analyst contract. Reuse only relevant presentation behavior from historical files; preserve current runtime interfaces and unrelated improvements.

### 20.3 Integrated build, not a preliminary rollback

The agreed order is:

1. Recover the old report renderer and design as a fixed, reusable presentation foundation in the implementation branch.
2. Verify this foundation against the pinned baseline using identical content.
3. Connect the new discovery, dataset, runs, right sidebar and message composer to that foundation.
4. Verify the complete experience and deploy the integrated release.

Do not first deploy the entire old application, revert the agent rollout wholesale, restore the legacy multi-call executor, return execution to standalone MCP, restore retired storage or alter current purchases.

The restoration and new workflow are one build/release. The foundation is completed early enough to prevent the new workflow from growing around the wrong report renderer.

### 20.4 Fixed presentation ownership and report contract

The agent produces analysis; the application controls its presentation.

- Extract actual legacy rendering/styles into shared, versioned components usable by the new workflow. Retaining the old source file unchanged while continuing to bypass it is not restoration.
- Provide a structured adapter for report title, summary takeaways, analyzed cohort, analyses, result sentences, graph specifications, subgroup observations, brief methods, decision implications and private source/calculation references.
- Let validated graph data drive tested stat/bar/donut components and appropriate compact tables.
- Keep outer layout, fonts, color tokens, section hierarchy, spacing, axes, pagination and branding deterministic.
- Do not rely on unrestricted agent-authored HTML/CSS, prompt compliance, or a separate model to reproduce the brand.
- Where isolated static HTML remains the artifact format, generate it from the same restored components/style contract. An iframe may remain an isolation mechanism but must not impose a white report, generic controls or a different template.
- Sanitize generated text/markup and preserve current HTML isolation and access protections.
- Version the report content schema, template/style bundle and renderer. Save those versions with each immutable artifact.
- Both browser display and PDF consume the same published report data. Do not make a separate model call to rewrite the PDF.
- Previews are derivatives of that report, not a newly designed representation.
- A renderer adapter must not silently discard supported fields because they do not fit the old schema. Extend the structured contract for the new method/summary fields while preserving the visual foundation.
- Reopening an old report must not silently regenerate it with a new template or overwrite its artifact. Revisions create new saved reports as already agreed.

These requirements apply to new Light and Max reports; tier differences govern data/usage, not a lower-quality or unrelated Light design.

### 20.5 Exact visual foundation

Recover the following values and relationships from the pinned stylesheet. Use the original font token and its application definition rather than substituting a browser default.

| Element | Baseline |
|---|---|
| Report background | #0b0f0d. |
| Main report text | #f7faf8. |
| Hero | Dark gradient #0d1410 → #102319 with a restrained green radial glow. |
| Primary brand accent | #69d296. |
| Supporting hero text | #c8d1cc. |
| Main interpretation text | #d0d7d3. |
| Secondary explanation text | #abb6b0. |
| Graph card | Gradient #151d18 → #101612; subtle white border at 10% opacity; 14px radius. |
| Chart track | #222b26. |
| Desktop report frame | Maximum width 1120px, 20px corner radius, subtle shadow; adapt available width for the new sidebar without breaking proportions. |
| Desktop content spacing | Original 64px horizontal report padding and generous section rhythm as the starting reference. |
| Heading hierarchy | Hero 36–58px responsive, analysis heading 32px, subheading 22px in the original screen design. |
| Reading text | Interpretation around 16px with 1.7 line height; retain the readable original hierarchy. |
| Mobile behavior | At the original 760px breakpoint, 22px horizontal content padding, smaller headings, stacked cohort/legend layout and wrapped labels. |

Original objective palette families:

| Family | Shades |
|---|---|
| Green | #a9e8c2, #8be0ad, #69d296, #4eb47b, #347e57 |
| Blue | #c5d4f7, #a8bdf1, #7b9ee8, #6687cd, #4c68ad |
| Amber | #f9d7b4, #f6c18e, #f0a25a, #d98945, #a96732 |

Preserve coordinated colors for headings and their charts. For four analyses, reuse the established palette cycle or consistent shade assignment; do not invent an unrelated fourth brand color. Extending to ten chart items must maintain distinguishability and readability; do not turn every graph into an overfilled ten-slice donut.

The graph is the only boxed element inside a standard analysis. Interpretation, ranked-item explanations, subgroup details and methods remain clean text or compact tables beneath it, separated with whitespace and subtle rules. Avoid nested cards, repeated shaded panels and an “everything in boxes” redesign.

The original product was not dark everywhere: it used a light workspace and header, dark navigation and a dark report. Preserve that distinction. Style the new right report-history sidebar and composer to belong to this application rather than arbitrarily making the entire app black.

### 20.6 Section composition and wording

The agreed new-report order is authoritative:

1. Branded report title.
2. A short summary: one meaningful result sentence per included analysis.
3. A compact trials-analyzed strip with actual selected counts, relevant named groups and “Groups may overlap” where applicable.
4. Up to four analysis sections.
5. Each section: headline → result sentence → graph → useful subgroup findings/specific notes → brief method.
6. A concise decision implication or closing statement only when it contributes a distinct useful point.

Use the original heading scale, accent relationship, spacing and unboxed interpretation treatment. A small analysis label may replace the old “Objective” label; do not restore a mandatory objective-planning layer.

Recovered writing targets:

| Content | Editorial target |
|---|---|
| Main takeaway | One clear, short sentence. |
| Interpretation | Two or three short sentences, approximately 60 words, when needed. |
| Ranked-item explanation | One sentence for each useful named item. |
| Decision implication | One or two sentences; concrete and supported. |
| Units | Brief: %, trials, months, etc. |
| Denominator / essential qualification | One concise chart note, not repeated through the prose. |
| Method | Brief factual description of what was compared/calculated. |
| Opening | Use the newly agreed one-sentence-per-analysis summary rather than automatically restoring the older three-to-four-sentence introduction. |

The old editorial code used word thresholds to request bounded shortening, not as hard publication ceilings. Preserve that distinction. Do not omit a useful distinct finding, clinical exception, named entity, number, denominator or uncertainty just to hit a target. Never truncate text to fit the page.

A wording-only edit must preserve facts, metrics, labels, chart order and evidence. Scientific negation and qualifications must survive shortening; “not established” cannot become “established.” If optional editorial correction is unsafe or fails, retain valid original wording.

No repetition of all plotted numbers, generic disease background, filler interpretations, empty headings, boilerplate caveats or lengthy closing recap. Do not repeat an introduction under every graph.

Public text excludes internal source aliases, profile approval status, extraction variable names, code, model workflow, documentation rates and processing/identity explanations. Required provenance remains attached to results and available through the intended evidence/export contract. Scientific qualifications needed to interpret a result remain visible.

A short explanation for an explicitly requested objective that could not be supported is compatible with the partial-success policy. It should not become an empty objective card or a lengthy data-completeness section.

### 20.7 Recovered analytical focus and graph behavior

Restore the substance of the earlier instructions along with appearance:

- Assess which frozen trials actually contribute to each question; do not assume the full workspace total is every graph's denominator.
- Inspect relevant broader, narrower and adjacent groups; publish only useful supported findings.
- Start with useful broad context, then show what relevant subgroups change, agree with or contradict.
- Separate phase, disease, design and endpoint strata where pooling would mislead.
- Preserve meaningful minority precedents, eligibility exceptions and conditional alternatives.
- Missing structured fields do not prove absence of a fact present in source text.
- Do not infer causality, patient eligibility counts or recruitment improvement from trial-feature frequencies.
- Activity/experience does not establish investigator quality or site capacity.
- Recommendations need actual decision relevance and supporting trials.
- Keep overlapping memberships non-additive and deduplicate trial identities.
- Do not inflate N to the report-wide total or add unrelated trials to fill the pilot cap.
- Omit empty/unsupported findings and n=0 categories; preserve valid zero-valued continuous measurements or differences.
- Sparse direct precedents may be described when useful, without presenting unsupported percentages or inferential certainty.
- Supporting facts/calculations remain traceable even when internal support machinery is absent from public prose.
- The report must retain every approved, independently valid included section in both HTML and PDF; no hidden UI slice may discard one after generation.

New groups need not be nested. Therefore the old “first disease group always leads every objective” instruction becomes “use the appropriate supported broad comparison for the question.” If only a subgroup supports a meaningful answer, present it directly without filler.

Graph requirements:

- At most ten displayed items, replacing the old five-item UI/prompt cap.
- At most four analyses/graphs per run; do not restore eight findings per objective as a new visible capacity.
- Rank using the complete relevant data before selecting displayed items.
- Keep labels and values aligned; do not silently slice labels independently from data.
- Preserve full useful rankings in the Max dataset.
- Use correct common-zero behavior for signed bars and zero width for a zero bar.
- Keep brief units beside values; show long definitions once below the chart.
- Wrap long labels instead of ellipsis or clipping.
- Prefer bars for many categories. Composition graphs must preserve their true denominator, including an explicit remainder where necessary, within the display limit.
- A relevant table or brief qualitative result is allowed when graphing would mislead.

### 20.8 PDF design and pagination contract

Restore the PDF as a deliberately designed document, not a browser screenshot with accidental page cuts or a plain white text export.

Required visual behavior:

- A4 portrait, 210 × 297 mm.
- Near-black green background on every page, with the established dark cover treatment.
- Designed cover with centered title, concise results summary and the trial-count/group panel.
- TrialAgents logo/name and “Autonomous agents for clinical trials” branding in the header.
- Website, logo and page numbering in the footer, with the original subtle separator rules.
- Main analyses begin on a fresh page; the cover remains a cover.
- Maintain the original readable hierarchy and generous space.
- Preserve contrast and chart colors in the generated file.
- Exclude application controls, composer and right sidebar from report PDFs.

Reference export geometry in the old implementation is a 760px layout width mapped to an A4 content area with 18mm top, 10mm right, 17mm bottom and 10mm left margins. These are the parity starting point, not permission to clip content when a renderer measures fonts differently.

Pagination invariants:

- Keep headings with their first meaningful result/graphic where possible.
- Keep an ordinary graph and its labels intact; do not split SVG paths or raster chart content across pages.
- Move ordinary blocks to the next page when they do not fit.
- Split oversized text/content safely at text/DOM boundaries and continue it without omission.
- Preserve inline formatting, names, numbers, non-ASCII text and scientific notation.
- Long units appear once, not repeated or lost in continuation.
- Do not shrink fonts, delete words or rewrite findings to meet a page budget.
- Avoid unintended blank trailing pages and repeated continuation borders/spacing.
- Perform export from a clone or immutable report representation; do not mutate the stored report or its visible data.
- Clean up temporary export resources on failure.
- Confirm page/footer numbering after final pagination.

The historical implementation used browser rendering and block-aware pagination. Reusing its behavior does not require reinstating the same raster/PDF library or request-process execution. A server-side exporter may use the restored HTML/CSS and equivalent tested pagination, provided it matches the design and lossless-content requirements within the existing worker constraints.

Each new or revised report keeps its own immutable PDF. Combined export preserves the chosen report order and report boundaries; assembling a bundle does not rewrite analyses or consume runs. A derivative PDF failure retries independently while valid HTML remains accessible.

### 20.9 Application controls and progress

Recover the original visual control system:

- Styled export buttons with icons, consistent sizing, borders and hover/loading/error states.
- Max dataset download remains available through its authorized action; Light has no dataset download.
- Restrained dark-green/sage Max package card and readable Light card, updated to the newly agreed package text.
- Overall progress track and individual named stage tracks.
- Waiting, in-progress and completed states.
- Active indeterminate motion when work has no truthful percentage.
- Real completed/total units where available.
- Reduced-motion behavior and saved-progress messaging.
- Reload/revisit restores server-authoritative status.
- Final report preparation remains visibly active during persistence/export.

Reuse the old component language while replacing obsolete stages such as the rigid SAP/per-trial extraction chain with actual new-workflow steps. Never claim the old five/20-trial quantities if the new selection contains a different number.

The report-history sidebar needs previews, names, date/order, opening, deletion and export while retaining the approved application spacing/typography. A 100-entry history should load compact cards and previews lazily. The reference report stays visible during a new run. The single composer must use branded controls, not unstyled browser defaults.

### 20.10 Explicit conflict resolution

| Historical behavior or later regression | Approved treatment in this build |
|---|---|
| Exact old visual/CSS foundation | Recover and reuse it. |
| Old five displayed graph items | Increase to ten with layout tests. |
| Many objectives/eight findings per objective | Replace with up to four analyses/graphs in each saved run. |
| Three-to-four-sentence general introduction | Use one meaningful sentence per included analysis. |
| Missing explicit brief-method field | Add the agreed short method in the existing text hierarchy. |
| “Objective” planning layer | Do not restore it; new questions execute directly. |
| Every group nested inside the named disease | Do not restore; adjacent/non-disease groups remain allowed. |
| Universal broad-disease-first graph | Use meaningful question-specific broad context; do not force inappropriate pooling. |
| One free Light report per account | Do not restore; multiple projects with five runs each. |
| Unlimited revisions / old marketing messages | Replace with current 5/100-run contract for new workspaces; protect legacy entitlements. |
| Light upgrade banners | If retained, preserve their original styling and use accurate new terms; no obsolete “unlimited revisions” claim. |
| Growing persistent report/session history | Use fresh run context with only the selected reference report and frozen dataset. |
| Plain managed progress list/basic controls | Replace with the recovered branded components. |
| Whole-report failure on missing optional coverage | Omit/repair the affected unit and publish useful valid work. |
| Quality checks that erase independent valid findings | Preserve valid siblings; corrections are bounded and targeted. |
| A dataset-only shell represented as a successful analysis | Do not charge a completed run if no supported result survives. |
| Standalone MCP worker / old execution chain | Do not restore; App continues to own managed execution. |
| Already-published immutable artifacts | Keep intact; new revisions receive the restored renderer. |

Release visual checks and runtime report validity are different. A visual regression should block release of a broken renderer; a minor optional wording deviation in one real report should not fail an otherwise useful report.

### 20.11 Visual and behavioral acceptance matrix

Use the same synthetic content for the pinned original and recovered renderer so differences are attributable to presentation, not a new model's output. Save the implementation's reference images/artifacts and verify them visually. Clearly label fixtures as synthetic; do not describe reconstructed fixtures as historical customer reports.

| Fixture | Required evidence |
|---|---|
| Standard completed report | Matching dark hero, colors, heading scale, spacing, graph cards and unboxed findings. |
| Four analyses | Stable green/blue/amber family behavior, correct hierarchy and four-section cap. |
| Ten long category names | No clipped/ellipsized labels, complete values, readable PDF. |
| Signed and zero measures | Correct shared zero axis, negative direction and zero-width bars. |
| Long units/denominators | Concise inline unit or one full note; no repetition or lost text. |
| Adjacent/non-nested cohorts | Accurate labels/denominators and no false subset or additive claim. |
| Sparse/partially unsupported request | Useful remaining report, adjusted summary, no empty cards or whole-run cosmetic failure. |
| Long interpretation, table or ranked explanations | Lossless continuation; no font shrinking or clipped bottom lines. |
| Very long unbroken/non-ASCII text | Safe wrapping/continuation without losing characters. |
| Cover and multi-page PDF | Dark cover, branding, margins, page numbers and new-page analysis starts. |
| Mobile report | Responsive typography, stacked legend/cohort content and usable controls. |
| Active discovery/analysis/export | Original bar treatment with truthful status, reload continuity and reduced-motion behavior. |
| New/revised report in 100-entry sidebar | Correct reference capture, distinct saved entry, useful preview and bounded loading. |
| PDF failure and retry | Published HTML/usage unchanged; PDF attaches to the exact same report. |
| Light and Max | Same presentation quality with correct controls and current package terms. |
| Combined PDF | Exact chosen reports/order, preserved boundaries and no LLM rewrite. |

Acceptance is not satisfied by tests merely finding a dark CSS color or a chart element. Inspect actual desktop/mobile renders and exported PDF pages, including stress cases. Compare report text and chart data across HTML/PDF to detect omitted sections or altered values.

During implementation, document intentional deviations required by the approved new workflow. Do not introduce unreviewed aesthetic changes and call them restoration.

### 20.12 Definition of done and maintenance

This restoration is complete only when:

- The source-to-component mapping identifies the recovered pinned files and the new shared renderer.
- The new workflow actually invokes that renderer for both tiers.
- Versioned agent instructions preserve the recovered analytical/editorial rules and explicit new limits.
- The acceptance matrix has concrete rendered evidence, not only prompt assertions.
- Individual and combined PDFs preserve the approved look and all supported content.
- Existing report access, current worker ownership and durable jobs remain intact.
- No separate old-version deployment occurred as a prerequisite.
- No new service, plan increase or paid inference was introduced merely to recover the design.
- The new workflow and restored presentation are released together after their implementation gates.
- Future agent/backend changes must run the same presentation/PDF regression checks rather than replacing the design again.

At implementation handoff, update App PROJECT_CONTEXT.md and its report subsystem context to link this approved contract and describe only verified shipped behavior. This documentation-only approval is not authorization to claim that restoration has already been implemented or deployed.
