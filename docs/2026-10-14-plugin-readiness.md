# Plugin readiness — 2026-10-14

**Status: planning only. Current UX is a release requirement. No implementation or deployment authorized by this document.**

Updated 14 October 2026, Europe/Berlin, after the owner clarified: publish the existing experience and preserve the weeks of UX optimization already completed.

This revision supersedes the earlier broad five-stage scope. That version mixed publication requirements, verification tasks and optional polish. Its audit evidence remains available in Git history, but its optional changes are not part of the publication plan.

## Non-negotiable baseline

Preserve the current tables, navigation, controls, visual/report defaults, Custom views, connection and save journeys, loading feedback, ranking, account access rules and normal interaction speed.

Retain the approved EU Trial Intelligence / EU Trial Intel names and TrialAgents brand. Keep current plugin/App IDs, hosting and endpoints. Preserve deliberate state saves, report revisions, exact-preview attachment and the pending-host-approval focus rule.

A change is eligible only when it addresses an explicit submission requirement or a reproducible defect that threatens the submitted journey. Prefer a metadata, documentation or internal correction that leaves the successful user journey intact. A hypothetical risk is a verification task, not permission to redesign.

The default scope excludes layout polish, new buttons, exports, starter-prompt changes, rebranding, broad skill rewrites, new retention/deletion behavior, billing changes and architecture optimization. If a concrete review or test result establishes an actual blocker in one of these areas, document the requirement, smallest remedy and exact user impact for the owner before proceeding.

Read AGENTS.md and [OPTIMIZATION_PERMISSION_REQUIRED.md](OPTIMIZATION_PERMISSION_REQUIRED.md). The previous restriction on progressive loading, background stages, additional cache offloading/reuse/retention changes and scheduling remains in force. This plan does not reverse approved fixes or authorize deferred proposals.

## Stage 1 — Complete submission material around the existing product

These tasks should not change the app's interactive behavior.

- Correct the published terms/privacy/support content: remove draft-production wording and retired product claims; describe actual account-wide access, existing data practices and storage lifecycle accurately.
- Verify source-data/professional-contact permissions and public access to legal/support pages. Do not invent new retention promises or build deletion features as part of copy cleanup.
- Keep the chosen branding, current icons and current starter prompts. Adjust listing facts only where inaccurate or incomplete for submission; no positioning redesign.
- Correct stale reviewer/release documentation to match the present five skills, tool effects, saving behavior and access model. Do not change working skill routing merely to make documentation easier to write.
- Prepare/verify publisher identity, Portal eligibility and availability settings, secure dedicated reviewer access, sample data, an accessible real walkthrough, and the required five positive/three negative cases.
- Inspect actual Portal fields before declaring missing materials: the ZIP has no demo-recording URL, but the Portal was not audited.
- Keep reviewer credentials outside the repository.

Acceptance: reviewers can access the current product and understand its real capabilities, permissions and data handling. No product redesign is required to finish these materials.

## Stage 2 — Make only essential technical corrections

Implementation is not authorized yet. Each correction must preserve the existing successful user journey.

### A. Declare the dedicated UI origin

Confirmed gap: the live component resource lacks the required dedicated origin.

Configure and return the correct unique origin through the supported host setup. Verify initialization, account navigation and existing Custom views. This is intended as a configuration correction, not a visual change.

Nested frames require a real-host check and the relevant review explanation. Keep the current renderer if it works under the supported policy. Do not infer a need to rewrite it merely because it uses srcDoc frames. Any unavoidable renderer change must be separately justified.

### B. Correct retry identity without changing the save journey

Confirmed source risk: publish_research_workspace generates a fresh preview identity, which can become a different canonical project on a repeated publish attempt.

Preserve a stable identity for the same operation through save/retry; preserve intentional new projects and explicit revisions. Keep the existing buttons, automatic account attachment behavior, approval mechanism and visible save states. Do not delete duplicates or alter existing customer data during this fix.

Acceptance: retry after a lost response returns the same project; distinct operations/users remain separate. The normal successful flow behaves as before. Measure any added lookup/locking cost.

### C. Make tool metadata truthful while minimizing approval friction

Confirmed issues: evidence readers register persisted source records; overwrite-capable operations use non-destructive annotations. These cannot be solved by declaring actual writes to be read-only.

The UX-preserving design target is:
- Genuine discovery and evidence retrieval remain read-only.
- Any required source/artifact registration occurs within the existing save operation where feasible, with no extra user-facing step.
- Actual saves and overwrites receive accurate annotations, with the host remaining responsible for consent.
- No custom confirmation modal or duplicate approval layer is added.

Before choosing an implementation, trace which source records are required to preserve frozen evidence, existing saved reports and retries. Determine whether a small internal separation can keep retrieval read-only without increasing report payloads, repeating expensive retrieval or changing source provenance. This is a design to validate, not an implemented or guaranteed solution. It is not permission for a general cache/storage refactor.

If that separation would require a broad rewrite, stop and present the narrower alternatives and their real-host approval impact. Do not broadly mark every read as a write just to avoid the design question.

**Unavoidable uncertainty:** ChatGPT controls approval presentation. Accurate overwrite/write annotations can affect its prompts. We cannot guarantee an identical number of host approvals or remove required consent. Test the actual effect before deciding that the UX must change.

Likely technical owners: MCP research_workspace.py / project_reports.py / resource registration; App project-chat-reports.ts and combined-prepared-projects.ts only where necessary. Public tool contracts and existing saved evidence need compatibility checks if their implementation changes.

## Stage 3 — Validate the existing experience and prepare submission

- Capture the current desktop/mobile screens and successful research-to-save journeys as the reference.
- Verify the candidate against that reference: visual appearance, navigation, loading feedback, report structure, access states, connection, save/retry and approval focus.
- Execute the review cases plus focused checks for ambiguous retries, overwrites/conflicts, guest/account attachment, expired access and another user's data.
- Confirm unsupported/out-of-database requests remain honest, source text cannot redirect the workflow, and unauthorized evidence stays inaccessible.
- Test the existing embedded views inside real ChatGPT before proposing any frame/rendering change.
- Measure only paths affected by technical edits. Use isolated synthetic data. Treat existing concurrency/cache concerns as checks, not authorization for optimization. Production load tests need a separately approved bounded scope.
- Keep the existing interface unless a reproducible functional defect or explicit review requirement demands a change. Visual preference is not a release blocker.
- Verify exact-candidate CI, package contents, live resource metadata, source/bundle correspondence, installed skill state and Portal scans. Repository updates alone do not prove installed-state updates.
- Assemble a concrete candidate and reviewer packet. Any implementation, deployment or public submission requires the owner's subsequent authorization; none is performed by this planning revision.

Acceptance: mandatory contract gaps are resolved, required review materials are complete, the existing supported journeys still work, and measured changes show no material regression. Define an acceptable performance tolerance from the actual baseline before implementation; do not invent a speed guarantee.

## Disposition of the earlier audit items

| Earlier item | Narrow publication scope |
| --- | --- |
| Missing widget origin | Required configuration correction; preserve UI |
| Tool annotations/source registration | Required accuracy; investigate smallest internal solution preserving read-only research |
| Publish retry duplication | Required reliability fix; preserve normal save flow |
| Nested frames | Validate and explain current implementation first; no automatic renderer rewrite |
| Terms/privacy/support | Correct factual public documents; no new product retention/deletion system |
| Account/consent copy | Change only inaccurate permission/access claims; preserve existing destinations and controls |
| Branding/icons/starter prompts | Keep current approved assets and behavior; no optional refresh |
| Stale reviewer docs | Correct docs to match product; no general skills rewrite |
| Mobile layout/export parity | Verify current behavior and claims; no new controls or cosmetic changes without a demonstrated blocker |
| Concurrency/memory | Validate as needed; previously restricted optimizations remain excluded |

## Remaining possible impact to disclose before implementation

1. **UI origin/frame policy:** can affect host loading and navigation even without a visual change; verify current screens and account journeys.
2. **Retry identity:** can add database lookup/locking; desired visible effect is only elimination of duplicate projects after retries.
3. **Evidence registration separation, if selected:** can change DB-write timing and save latency; preserve frozen evidence, existing reports and the same user actions.
4. **Accurate write/overwrite annotations:** may change host approval prompts. This is the main unresolved UX-sensitive requirement.
5. **Necessary permission/access wording:** can change what users read, but should not add steps or alter entitlements.
6. **Future rollout/testing:** can consume resources or restart services; keep isolated testing and the existing coordinated release process.

No runtime, UX or workflow edit has been made. The only edit in this revision is this plan.

## Audit baseline and references

- Package 0.7.4; five installed skills; 37 tools observed live.
- MCP inspected: bd22ae9b7ed6a37f30a8b849aa1904a42d535073.
- Relevant App source: 71c2ac9ab7787eb2fb9d5e25289583abb84d127d.
- Live bundle matched SHA-256 eb3756cbfc8e42656d23b2adf1569de682dc013a2311789e8f9e3cb63744f2b0; embedded source provenance points to App e472f0e6243462c20f5ca37c3a8712a8854115f5.
- Current CI passed; inspected screenshots used synthetic fixtures. Local browser execution was unavailable. Authenticated write journeys and Portal status were not verified.
- Current official docs accept SVG icons and access through existing paid accounts; neither is itself a publication blocker.
- Main-site direct access was denied to the audit client while public content was retrievable via web search; verify ordinary reviewer access rather than assuming an outage.
- Recheck source/deployed versions and requirements before implementation.

Official references:
- https://developers.openai.com/plugins/plugin-guidelines
- https://developers.openai.com/plugins/reference
- https://developers.openai.com/plugins/deploy/submission
- https://developers.openai.com/plugins/deploy/app-review

The earlier detailed audit plan is retained in Git history at acc8bc94d013d743b67e3e7477926341afa1d100. Its optional work is superseded by the scope above.
