# ChatGPT instruction audit — 12 October 2026

Status: cleanup approved and implemented on 12 October. Active contradictions removed, old context/release prose archived, four goal-based skills introduced. Owner explicitly approved publication to the public tarous89/intel_mcp repository. Source publication is in progress; deployment and installation remain separately verifiable. The table below records the approved changes, not outstanding approval requests.

## Approved additions
- Source/ID/link display is request-only in answers and reports; preserve source metadata and material limitations.
- Executive summary, one section per question, one sentence (at most two) above a visualization, nuances below. Quantitative comparisons need graphs; qualitative questions need a matrix/diagram/cards, without fabricated values.
- Matching semantic HTML/SVG example uses the existing App report renderer style. Returned by prepare_project_report as well as bundled with the skill; plain MCP connections therefore also receive it.
- One canonical shared answer/access standard replaces the temporary precedence workaround; report structure is owned by the report skill.

## Approved cleanup implemented

| Item | Evidence and location | Proposed action |
|---|---|---|
| Visible citations required by default | skill SKILL.md “cite accessible entity/trial IDs”; report-guidance.md graph source references and final traceable sources; project_reports.py read_report_evidence docstring | Remove visible-citation requirements; retain internal source_ids and on-request references. |
| Prose-only qualitative analyses and artificial section quotas | report-guidance.md “Two to four distinct useful analyses” and “table or prose” | Replace with one section per question and a qualitative visualization. Keep tables when they form meaningful comparison matrices. |
| Anonymous raw-profile denial and paid-only documents | references/tool-contract.md text predicate paragraph says raw sections are not exposed; final report paragraph says documents require paid access | Remove obsolete restrictions. Exact ten eligible trials have full content; other trials remain restricted. Compact entity-evidence responses still omit some narratives, which is a separate real contract. |
| Old connect/save/paging flow in active MCP instructions | research_presentation.py RESEARCH_WORKFLOW instructs create_research_account_handoff, claim_research_workspace, revise_research_workspace and prepare again for paging | Replace model workflow with website Connect, read_project_preview, save_project and open_project. Keep compatibility tool implementations and persisted identifiers. |
| Conflicting expiry instructions | RESEARCH_WORKFLOW equates prepared previews with selection expiry; SKILL.md says rerun original search and later says request a new selection | Distinguish short-lived search selections from 24-hour cached previews and persistent saved projects; no silent replacement of an expired snapshot. |
| Stale plugin review expectations | plugin.json cases still say “no … Reports,” use legacy rank-first workflows, and deny raw profiles | Update review cases to current workspace, Reports and full eligible-trial content; keep negative access-bypass/security cases. |
| Historical instructions accumulating as current guidance | PROJECT_CONTEXT.md includes incompatible dated blocks; CHATGPT_PLUGIN_RELEASE.md appends repeated releases, “covered project” access and unsupported-profile claims | Keep a concise current reference and move obsolete prose to an explicitly historical archive after approval. Preserve compatibility contracts, change history and evidence. |
| Duplicate operational rules and report guidance copies | repeated counts, access, error, save, and report directions across workflow, skill and references; two manually maintained report-guidance.md copies | Consolidate authoritative text and generate/validate mirrors; keep standalone tool guidance sufficient when a host does not load skills. |

## Safeguards included or recorded for release
- Add a drift check that fails when runtime and packaged presentation/report files differ (included for the new assets in this draft).
- Acceptance cases cover: multi-question report; qualitative-only question; absent evidence; requested sources; no requested sources; long mobile report.
- Mark legacy/private worker prompts separately from active public research instructions. The private server.py start_analysis workflow is not the public research MCP and must not be deleted merely because the public flow changed.
- Reconcile ambiguous capability wording: paid-only *compact entity evidence* versus complete findings inside an eligible free trial profile. Do not expand trial access accidentally.

## Review scope and exclusions
Reviewed packaged skill, tool contract, example criteria, plugin manifest/review cases, active research server/workflow/capability declarations, workspace/report tool descriptions, App report context, HTML sanitizer/style and report viewer; checked legacy server and report worker boundaries and repository release/context documents. App table chat is a bounded deterministic interpreter, not a ChatGPT prompt. Historical/private worker contracts remain intact. Installed plugin configuration and actual ChatGPT cached metadata are not proven updated by local source edits.

## Scrolling follow-through
Shared App/extension project shell uses a single vertical content scroll area, stable header and pinned access footer. Tables expand within it; horizontal scrolling stays available. Canonical tables page at ten, legacy table selector allows ten or twenty. The sanitized report frame resizes to content while scripts remain prohibited. Verify desktop/mobile, long reports and permissions before release.

## Local verification
TypeScript passed. Fifteen focused MCP/report/package tests passed; runtime/package presentation assets are identical. The real App sanitizer preserves the HTML/SVG example; its styled desktop render was visually checked. Sixteen App desktop/mobile route checks passed. Embedded Chromium checks with ten-row tables and a long report passed at widths 1280, 760 and 420: fixed header/footer, main vertical scroll, no nested table/report vertical scroll, horizontal columns reachable. Real ChatGPT host and production release remain pending.

## Skill organization and follow-up implementation
OpenAI official skill guidance (https://developers.openai.com/plugins/build/skills, checked 12 October 2026) recommends skills with different user-goal triggers/inputs/outputs and concise bodies with references/assets. Implemented four: partner discovery, trial evidence analysis, visual reports, and project management. MCP access is common infrastructure, not a separate end-user task skill. Canonical files are shared through references and deterministic wheel mirrors checked in CI.

The inline follow-up card uses the documented MCP Apps ui/message bridge (https://developers.openai.com/plugins/build/chatgpt-ui). Exactly three full questions are model-selected per context, independent of tier; the tool checks scope without reading extra evidence or saving. It verifies owner/preview context before rendering. Clicking updates the original research context then sends the selected question. No automatic send, execution or purchase. The bridge failure path retains visible text for manual use; successful sends disable repeat submission. Actual placement is host-controlled.

Free disclosure: “Preview: up to 10 trials; connect your account to use existing full access.” Smaller/empty/connected-free/full scopes receive accurate variants. The ten-row entity-table limit remains separate. Source IDs stay internal, and reports/analysis cannot bypass the fixed eligible trial set.

Verification: all four skill validators and package reference checks passed; 465 Python tests passed with four database-dependent skips. The inline card passed six desktop/mobile bridge cases (success, rejected message, missing context support), including no automatic messages, exact clicked question, original context, no repeat send and text fallback. Installed skill snapshots and real ChatGPT placement remain unverified until release/import.
