# Reviewer preparation notes — 2026-10-14

Internal maintainer reference, not a review approval or a completed test report. No credentials belong here. Keep the existing plugin/App identity, five skills and 37 tools.

## Actual tool effects

All tools are confined to the TrialAgents catalogue and authorized account/preview scope (openWorldHint=false). Server-side ownership and access checks remain authoritative.

| Operations | Read-only | Destructive | Reason |
| --- | --- | --- | --- |
| Discovery, ranking, schema/inventory, current account/project/report reads, follow-up choices | true | false | Retrieval/computation; no saved user artifact is changed. |
| prepare_research_workspace / recover_research_preview | true | false | Internal bounded query-preview caching, separate from a saved project. The existing 24-hour preview capability is not a promise of backend erasure. |
| read_trial_profiles / read_report_evidence | false | false | Register frozen evidence sources used for report provenance. Additive and content-addressed. |
| read_report_document / read_trial_document | false | false | Persist dated extracted-document source records. Repeated retrieval can add a record, so idempotentHint=false. |
| publish_research_workspace | false | false | Creates/attaches an owner's project; guests receive a cached preview. Stable operation identity makes retries reuse the original project. |
| save_project / revise_research_workspace | false | true | Can replace the active project selection/title. Historical data or conflict checks do not justify a non-destructive declaration. |
| save_project_view | false | true | Replaces stored table controls. |
| save_project_report / retry_project_report | false | true | Create or overwrite a Custom view. An overwrite replaces its current HTML/content; a version counter is not an archive of old HTML. |
| save_visualization_state | false | true | Replaces deliberately saved form/tracker state under a version check. |
| Legacy save/claim/handoff | false | false | Explicit account attachment, additive project save or connection handoff. Existing server authorization remains in place. |

Preserving the evidence registration path avoids a new evidence cache, larger tool payloads or additional retrieval during save. Moving that persistence into the save operation would require a separate source-reference design and compatibility work. The current correction therefore describes the existing behavior honestly. ChatGPT controls approval presentation; actual prompts remain a host acceptance gate. Do not hide a pending approval behind another link or add a second custom confirmation dialog.

All 37 tools declare object output schemas, including the three legacy tools whose explicit CallToolResult responses are preserved. UI resources declare https://mcp.trialagents.com as the plugin's dedicated origin, using both standard and compatibility metadata. Confirm host acceptance/uniqueness in the actual submission; declaration is not Portal verification. Existing nested srcDoc report rendering is unchanged and needs real-host verification and an iframe justification.

## Retry semantics

For connected accounts, the same owner, selection, title, contact mode, recommendations and optional operation_id identify a publication. Anonymous calls retain independent random preview capabilities: a shared cached public search must never share private guest reports. Replays keep the preview UUID and server-keyed secret cache capability stable, matching the App receipt's token hash. A table-tab change does not create another project. Use a distinct operation_id for an intentionally separate project from the same cached selection; retain that value on retries. No result cache, new background job or database lookup was added. A 32-byte server-only key prevents deriving a private preview capability from shared search inputs or an account ID. Expired selections still fail honestly; this is not durable search recovery.

## Reviewer setup and cases

Use a dedicated reviewer account with durable sample data and account-wide full access throughout review. Connecting alone does not grant full access. Verify a fresh login without dependence on an owner's OTP/MFA, successful pagination, expired/revoked access and another owner's denial. Keep credentials in secure Portal fields only.

Execute five positive and three negative cases independently against the exact candidate. Cohort sizes and ordering are data-dependent; do not hardcode live IDs/counts. For requested CRO contacts pass include_cro_contacts=true to publication/ranking and read contacts from CRO results; get_research_entity_evidence supplies supporting trials, not contacts. Read document parts only when an authorized inventory contains them. Reports, state changes and revisions must respect host approval and server access checks.

## Publisher and public pages

Publisher name: Atlas Consulting. Postal contact is displayed in Terms only, using the owner-confirmed address supplied on 14 October. Support: intel@trialagents.com. Product name remains EU Trial Intelligence (compact EU Trial Intel); TrialAgents remains the platform brand. Public text must not claim verified or approved status.

- https://trialagents.com/intel-agent — product and publisher disclosure.
- https://trialagents.com/privacy-policy — controller, plugin data practices and retention.
- https://trialagents.com/terms-of-service — provider, exact postal address and current access terms.
- https://intel.trialagents.com/support/intel — account-wide access and support.

The first three pages are served by the public snapshot: App source deployment alone does not update them. Deploy App source, run the existing trialagents-public exact-head predeploy/snapshot process, then inspect all four live URLs. Owner confirmation of actual retention practices and source/contact rights remains necessary; factual copy is not a legal attestation.

## Submission evidence still required

Record exact source/package/bundle versions, passed tests, actual ChatGPT desktop/mobile results, accessible demo, reviewer login, publisher/domain verification and current Portal scans. The official guidelines and submission-error reference differ on written annotation justifications; follow the actual Portal fields and use the factual explanations above. Do not label an unrun case, inaccessible link or missing Portal check as passed.
