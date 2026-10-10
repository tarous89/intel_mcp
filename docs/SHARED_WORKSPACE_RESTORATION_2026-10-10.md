# Shared Intel workspace restoration scope — 2026-10-10

Status: investigation and implementation scope; no runtime changes in this patch.
Owner confirmed the released canonical save/sync flow works well in the actual ChatGPT session. Preserve it.

## Findings and where parity was lost

Audited App main afe6e4207d0aa0135d1465e1bdd1a9c044db7f4f and MCP main 49265e28acca27293f67bca272e1110f078bde34. App changes after PR270 only affect public footers.

1. The richer implementation remains in App CombinedTablesView.tsx, SiteResultsTable.tsx, CombinedTrialProfile.tsx and combined_site_ranking.py. It was not deleted.
2. WorkspaceTables.tsx had hard-coded one experience field, empty ranking criteria, no table toolbar, and inline trial evidence from its initial shared-workspace commit c9710aaf5aabd67f2c95520edecce7b50af30885. Canonical commit 53d6eb95e47515db5ba5b5f15e9285bffc06db91 routed prepared ChatGPT projects into that reduced presentation. Thus shared row markup was achieved without full feature parity.
3. App research-table-rows.ts maps only total selected trials and sponsors into Site/PI metrics. It labels that total therapeuticAreaTrials, although the original metric has a five-year authorization window. Trial adaptation fills most detail fields with null/zero/empty arrays. Missing data must not be represented as measured zero.
4. MCP selection.py explicitly emits contacts=[] for sites; PI email collection remains. The App adapter cannot recover missing contacts and replaces a contact name with “Recorded contact” when an email exists.
5. publish_prepared preserves these sparse rows and builds rankingCriteria with empty disease terms and no phase/modality criteria. Original clinical profiles are frozen and published, but their rich fields are not connected to the workspace profile UI.
6. The shared view has no filter, field, sorting or export controller. These remain implemented in CombinedTablesView and server table/index/export services.
7. Project-list routing chooses selection when active_dataset_id is absent, although prepared table snapshots already exist. Import cards separately route completed imports to CROs. This explains inconsistent first views; all new entry paths should use Sites once a canonical project exists.
8. Sync currently mixes import-job readiness, prepared table availability and report-artifact readiness. Import polling backs off to 15 seconds; hidden-tab refresh waits for its timer. Discovery polling is two seconds while preparing. These can delay displayed completion. The exact reported session timing is not proven without its project ID/runtime trace; do not claim a specific stuck server job.
9. Existing documentation COMBINED_INTEL_WORKSPACE_SCOPE.md explicitly retains deterministic metrics, ordinary filters/sorts/subgroups and detailed rows. Removal of conversational filter/rank analysis from the website did not authorize removal of table controls.

## Non-negotiable continuity

- One canonical project ID and immutable selected dataset revision; identical accessible rows, counts, evidence and feature behavior on website and ChatGPT.
- Preserve ChatGPT search, inspect, filter, broaden/narrow and iterative refinement independently of the website wizard.
- No fresh search, model calls, extraction, or silent reranking during account connection/save.
- Compute derived metrics once from frozen profiles/criteria and store them; never recompute on tab opening.
- Keep source cohort and saved default order unchanged. Explicit user sort/filter changes the view, not the research membership.
- Preserve access policies, explicit OAuth writes, idempotency, stale-write conflicts and prior-ready data during refresh.
- Previously excluded legacy testing projects remain outside migration. Projects created since the successful release must not be treated as disposable tests; support non-destructive enrichment from their frozen profiles if needed.

## Ordered implementation

### 1. Sites-first readiness and progress
Use one readiness contract separating account import/save, table availability, and report/export preparation. Navigate newly connected/saved project entry and project-card entry to /projects/{id}/sites as soon as the ID exists; show ready tables immediately. Do not reset a tab the user intentionally selected during refresh.

Replace captured-profile/table-count text with the existing new-project progress-bar styling and a continuously moving indeterminate segment while that operation is active. No fabricated completion percentage is necessary. Respect reduced-motion preferences. A report-preparation indicator must say what is preparing and must not imply already-visible tables are still syncing.

Refresh status immediately on visibility/focus restoration; use bounded active polling, cancel stale responses, stop on ready/failed, and remove progress on the first terminal response. Failure shows a clear retry state rather than endless animation. Verify no import, table, or report status can hold an unrelated spinner open.

### 2. Restore site contacts and metric payload
Reuse the established identity-aware contact selection: site-associated recorded investigators, prefer relevant matched PI with a valid email, otherwise the existing deterministic recorded-contact fallback. Retain real name, role, email, affiliation and evidence provenance; reject masked/invalid emails and never invent contacts or attach unrelated people.

Restore Site and PI metrics from combined_site_ranking.py:
| Metric | Existing definition |
| --- | --- |
| Therapeutic-area expertise | Distinct qualifying trial participations in the five-year authorization window |
| Indication expertise | Five-year trials matching recorded disease terms |
| Phase expertise | Five-year trials matching requested phase(s) |
| Modality expertise | Five-year trials matching requested modality |
| Paediatric expertise | Five-year paediatric trials when relevant; otherwise not applicable |
| Recent activity | Distinct participations with positive CTIS authorization in the last six months |

Also retain sponsor experience, matched disease/subgroup counts, relevant PI/site affiliations and evidence. Preserve frozen as-of dates, country-aware authorization rules, deduplication and unknown/not-applicable handling.

Existing percentile formula is 100 * (count(lower) + 0.5 * count(equal)) / count(eligible values); >=90 is Leading 10%, >=75 Upper 25%, <25 Bottom 25%, otherwise Typical; existing zero handling is Bottom 25%. Compute over the full relevant entity population, not a page or top-ten preview. Label the comparison population and evidence coverage; these are experience bands, not performance/recruitment claims.

Carry actual research criteria through prepare/cache/read/publish. For flexible ChatGPT predicates, preserve original membership and subgroup semantics: do not expand to a therapeutic-area-wide search merely to reproduce website defaults. Keep selected-cohort total separate from five-year expertise. Missing metric eligibility must not become zero.

Enrich at preview preparation before freezing/saving. For already-saved release projects, derive only from retained profiles using a versioned, atomic enrichment path; preserve IDs, memberships, order and the old readable artifact until complete. Do not silently mutate immutable artifacts or require rerunning research.

### 3. Full trial profile
Extract/reuse the existing rich profile content and modal behavior rather than replacing it with another summary.
- Website: centered, prominent dialog with close, Escape, focus containment/return and independent scrolling.
- Embedded workspace: full-panel overlay/detail view with a visible Back/Close control and preserved table position; use dialog only if supported well by the host.
- Content: overview, phase/status/dates, population/disease/stage/setting/biomarkers, eligibility/design, products/modality/mechanism/targets, objectives/endpoints, sponsors/organizations/contacts, country/site/PI directory, lifecycle, results and operational findings where recorded.
- Read exact frozen profile by project + dataset revision + trial ID. Loading, missing data and entitlement states must be explicit; do not expose raw internal profile storage to the model.
- Introduce an authorized, bounded read transport for embedded profile details; website fetch and MCP host calls use the same service and access checks. Existing App profile endpoint relies on ready/indexed datasets and must be reconciled with early-ready prepared tables and account access.

### 4. One shared table controller and toolbar
Extract reusable behavior from CombinedTablesView/SiteTableOptions; both clients consume it through transport adapters.
Restore search/filter, Rank by, field selection and download across all four tables. Include supported metric sorting, country/affiliation filters, relevant subgroups, CRO service/function filter, reset and clear active-filter state. Rank by remains ordinary deterministic sorting.

Carry validated controls into canonical native and prepared reads. Current canonical reads accept only kind/offset/limit, so merely displaying controls is insufficient. Full-access controls operate across the complete saved dataset, with stable pagination and revision-bound cursors. Preview controls remain honestly scoped to accessible rows.

Provide genuine .xlsx downloads, preserving visible filter/sort scope and offering explicit page versus full eligible results where supported. Existing per-table preview export is CSV; full category export already has a separate implementation. Never relabel CSV as Excel or silently export only ten rows as the full table. Reuse authorization, frozen-source export jobs, bounded storage and spreadsheet formula protection. Embedded download uses a permitted host-accessible delivery path.

### 5. Verification and release
- Same fixture through website and ChatGPT yields the same fields, metrics, contacts, ordering, filters and trial profile.
- Contact extraction covers multiple sites, matching PI preference, fallback, dedupe, masked emails and missing contacts.
- Metrics cover authorization boundaries, frozen as-of, duplicate participations, no matching phase/modality, percentile ties, null versus zero and full-population denominators.
- Sync covers immediate cached readiness, delayed report artifacts, hidden/focus resume, terminal failure, stale responses and user-selected tabs.
- Profile opens visibly from all evidence links; keyboard/back behavior and return-to-table position work.
- Filter/sort/page/export over more than one page reconcile; XLSX contents match the chosen scope and entitlement.
- Preserve exact-save/idempotency/revision and two-account isolation tests; no new search or paid model calls on save.
- Verify desktop/mobile website and actual ChatGPT host. Owner's successful core-sync acceptance does not imply these restored features are already verified.
- Deploy App/service changes first, then rebuild/version the shared MCP bundle against the released App source. Keep existing service/plugin identities.

Definition of done: no feature reduction based on project origin; restored data and controls work identically in both clients, and progress reflects the relevant current operation.
