# Intel Agent dataset workspace and multiple-report workflow — implementation plan

Date: 2026-09-18
Status: agreed product scope; implementation plan only. This document does not establish implementation, testing, deployment or changed entitlements.
Primary implementation owner: tarous89/intel_agent_app.
Plan location: intel_mcp repository root, beside MAX_AGENT_REDESIGN_SCOPE.md, at the user's explicit request.
Source of decisions: the product-design discussion completed on 2026-09-18.

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

Restore and retain the established dark-themed, dark-green/sage branded report design. Reuse its existing visual system and mature chart/print components rather than generating an unrelated page or generic report.

Every report follows this order:

1. Short title and a simple results summary containing one meaningful sentence per included analysis.
2. Compact factual dataset context, without long completeness commentary.
3. For each analysis: headline → concise result statement → graph → meaningful subgroup findings or specific notes → very short method description.
4. Source references and only necessary supporting detail.

Avoid long essays, repetitive disclaimers, empty cards and summaries that claim omitted objectives were completed. A skipped explicitly requested objective may receive a short factual note; do not pad the report with processing diagnostics.

Keep at most ten displayed items per graph. Maintain readable labels, correct axes and percentages, adequate contrast, meaningful zeros and coherent colors. Smaller subgroup tables/notes should not create an unbounded series of extra graphs.

Use one versioned branded template and shared deterministic rendering for HTML and PDF. The agent supplies evidence-backed content and chart inputs. No separate design model is required by the agreed plan; any later change to that architecture should be justified by measured quality.

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

- Apply the established dark branded template and requested section order.
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

- [ ] Dark branded HTML/PDF matches the established visual reference.
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
