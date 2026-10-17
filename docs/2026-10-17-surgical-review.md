# October 17 scoped implementation and source review

Owner request: implement 1, 2, 3 and 7; inspect and recommend 4, 5 and 6 only. No deployment or Directory submission is performed by this change.

## Implemented source changes

App: compact app-hosted OAuth consent and login benefit sentence: “Save your search results, projects and custom views for later use in TrialAgents.” Existing active ChatGPT tokens select the connected state; pending requests/codes do not. Approval, account switching, cancellation, PKCE and redirects remain unchanged.

Subscription display: the previous overview awaited live Stripe (25-second timeout) and study-count retrieval (10-second timeout), even though billing_display was already stored. Return account-owned stored display metadata first; refresh Stripe independently of study counts. Preserve verified snapshots on refresh failure, label stale display, disable cancellation until refresh finishes successfully, and invalidate older UI responses after cancellation. No new cache, migration, entitlement or payment changes.

Review metadata: positive case 2 now requests CRO regulatory-submission experience in phase 2 pediatric trials and requires direct evidence rather than inference from participation. Replace negative access-circumvention case with the Greece patient-information-sheet prompt. Five positive and three negative cases remain. These are candidate metadata changes, not completed live review cases or an installed-plugin update.

## 4 — Cardiovascular search latency (recommendation only)

Confirmed source findings: research_server.py search_research_trials targets 100–800 trials and instructs further broadening below 100. research_presentation.py discovery_guidance(trial_count) has no query-intent or explicit-constraint input. Runtime/package guidance has historically used other target sizes. A specific phase/country/ongoing trial-list request can therefore receive broadening advice despite its constrained intent. Search also ranks the selected entity category before publication; publication prepares the full workspace, so broadening is not the only potential latency source.

Smallest recommended correction: make broadening guidance conditional on exploratory partner discovery; explicit trial lists should report the actual matching count and preserve phase, country and status filters without a target minimum. Keep the existing full-workspace preparation architecture. Add bounded timing around existing search/preparation/publication boundaries only if existing logs cannot attribute latency. Change SQL/indexes only if query plans show that they are the bottleneck.

Do not claim the October 17 latency root cause is proven. Production logs were not inspected: Render returned no selected workspace and requires user workspace confirmation. No customer queries or records were used for testing. Deferred progressive loading, new caches and background work remain prohibited without separate approval.

## 5 — Suspicious-instruction warning (recommendation only)

No original warning transcript was available in this workspace. A source audit cannot prove what triggered the host warning.

Candidates for surgical wording changes: research_workspace.py publication docstring says “with no account preflight”; legacy claim guidance directs completing OAuth and retrying the claim. project_reports.py save docstring includes a long argument about study-level data not being personal patient information. Discovery outputs contain imperative presentation/broadening text. These are candidates, not proof of malicious behavior or a rejection.

Recommended scope: describe verified credential behavior, storage effects, parameters and returned status as facts; remove host-directed authentication/classification instructions and move discretionary research procedure into the existing skills. Keep accurate write annotations and permissions. Do not remove factual data-scope descriptions or try to suppress host review. Existing publication already chooses guest/owner storage deterministically, with account-bound stable publication identity; App already enforces ownership, source scope, idempotency and version checks. Preserve that implementation rather than rewriting it.

Acceptance: descriptor diff limited to wording, existing auth/persistence regressions pass, and the original scenario is retested after tool refresh. No promise of warning-free behavior or OpenAI approval.

## 6 — Intermediate Custom views / save conflict (recommendation only)

Confirmed: project_reports.py save_project_report and retry_project_report both have workspace UI metadata. On save failure they return active_tab=custom plus pending_custom_view.html. App CustomViewRecovery.tsx deliberately renders that unsaved HTML. This explains how an intermediate artifact can be visible while persisted report count is zero; zero is correct if nothing has been saved.

Backend saveChatReport already has transaction locks, write receipts keyed by scope/request_key, content conflict detection and expectedVersion checks. Adding a second draft database or new persistence architecture is not justified by current evidence.

Recommended first change: retain the failed payload server-side and show a compact save-status/retry control while preserving the last confirmed workspace; do not render pending draft HTML or force Custom on failure. Keep deliberate user-requested revisions. If host remounting still occurs because of UI metadata, only then split non-displaying save from final display; that is a larger second step.

For the conflict, distinguish project revision, report version and request-key conflicts. Prepare_project_report supplies dataset_id/revision; report read supplies report_id/version. Exact retries reuse content and request key; deliberate changed content gets a new key and current expected report version. Do not auto-overwrite another edit after reading a newer version. Existing retry only corrects a narrow fixed-preview revision mismatch; preserve that safety boundary.

The save verification currently checks only the returned report ID. Tighten it to verify the committed version/content identity before claiming success. Do not report a successful write as a failed save merely because subsequent workspace presentation fails; track storage confirmation separately from presentation failure. Log bounded error codes and stage timing, not source HTML or access capabilities.

The incident's specific version/conflict code remains unconfirmed without its tool trace or logs. No changes to items 4–6 are included in this candidate.

## Validation

App focused billing, delayed-loading, grant, cancellation, OAuth continuation and disconnection checks: 15 passed. Added active-only/pending authorization assertions also pass separately. MCP package tests: 3 passed. No live ChatGPT review case, production billing operation, deployment or Directory submission performed. Whole-app checks are recorded in the companion App PR.
