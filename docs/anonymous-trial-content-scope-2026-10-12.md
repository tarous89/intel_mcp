# Anonymous trial content access — scope, 2026-10-12

Status: implemented and locally verified; release pending. Added describe_trial_profile_schema, read_trial_profiles, list_trial_documents and read_trial_document. App authorization now serves complete content for eligible trials. Local verification: 462 MCP tests passed (4 database-dependent tests deferred to CI), TypeScript passed, 17 App access/subscription/journey tests passed. User requested complete content within the trial-count limit and explicit model-facing profile/schema discovery.

## Verified baseline

Checked live `/research/mcp` tools/list and current main sources: MCP 5ba3db395c7052883225c0da96c944fae0423fc2; App 65dce3d5afc1404b26ff8e3a00e9d9ebb789a341.

- Anonymous search, cohort refinement, candidate metadata, top-ten entity tables and supporting trial links are available. inspect_research_trials can paginate metadata across the bounded cohort (up to 500), so ten is currently a table disclosure limit, not a universal count of IDs exposed.
- read_custom_view_evidence is model-visible, but App researchTrialProfile returns an accessible preview trial summary, `profile: {}`, and `limited: true` for free access.
- read_workspace_trial is app-only and uses the same restriction; a profile popup does not imply complete model access.
- read_custom_view_document is model-visible, but reportDocumentPermission rejects preview access with DOCUMENT_NOT_IN_PREVIEW. Protocols and other extracted text require full account access today.
- Free entity evidence strips discovery_evidence and operational_findings. Backend presence of full data is not permission to expose it.
- Legacy authenticated get_profiles already implements exact full/section projection, including combinations; get_documents already preserves extracted text across parts. Those are not anonymous research tools and their legacy lease quotas must not be carried into this change.

## Target policy

One content entitlement decision, by trial ID within the authorized research snapshot: anonymous and signed-in free users receive complete approved stored content for the same ten accessible trials; paid users receive complete content for all authorized trials. No additional section, profile-detail, document-count or document-text paywall within those trials. Repeated reads, alternate sections and subsequent text parts do not consume extra trial allowance.

Use the stable, unfiltered preview Trials IDs already used by profile authorization as the initial eligible set (up to ten). Filters, pagination, report calls and direct trial-ID reads must not silently rotate that set. Scope is per research snapshot/project, not an impossible anonymous lifetime quota. Genuine new research remains supported; preserve the existing instruction against partitioning cohorts to harvest hidden results.

Candidate metadata may remain available across the broader cohort for refinement; distinguish metadata discovery from entitlement to detailed trial content. Supporting links outside the eligible ten do not automatically authorize their profiles/documents. Expose eligible_trial_ids and count explicitly. If the product instead wants all trial metadata capped at ten, that is a separate change to current discovery flexibility.

Complete means complete stored approved profile, including nested organizations, sites, investigators, contacts and operational findings. Such nested records may exceed ten: do not truncate them to enforce entity-table limits. This intentionally changes the existing anti-enumeration rationale. Entity table limits remain separate; nested trial content must retain its real relationships. Continue treating source contact information as recorded public trial data, not verified outreach contacts.

Complete text means all successfully extracted text available from the serving source; do not promise unavailable/unextracted files, OCR recovery, non-public files or patient-level records. Distinguish missing documents from access denial. No automatic source regeneration, search refresh or model job.

## Model-visible contract

1. Add an anonymous-readable profile-schema/capabilities tool (and versioned resource if useful). Return authoritative schema version, top-level objects, section names/descriptions, exact JSON paths, types, arrays/nesting, enum values, units/date formats, null/missing semantics and realistic examples. Derive from the Engine-owned authoritative schema; the current schema.py version constant and hand-maintained section map alone are insufficient. Pin/validate schema artifacts and flag drift rather than inventing field definitions.
2. Expose a general profile read usable for ordinary questions, without requiring report creation. Accept a preview capability or owned project/revision, 1–10 exact eligible trial IDs, and optional sections. Reuse the existing ProfileSection enum/projection. Omitted or empty sections means full profile; one means one section; several means their exact union with original nesting. No summarization or silent truncation. Include schema/profile version, approval/source timestamp, snapshot/revision, returned sections and completeness. Bound large responses with explicit continuation if needed; transport bounds are not a content paywall.
3. Expose an explicit document inventory for eligible trials, also available through the documents profile section. Preserve exact accepted document names/types, availability and source identity. Current extracted inventory types: protocol, recruitment_arrangements, patient_information_and_informed_consent, assessments_and_forms, clinical_study_report, results_summary. Do not describe this extracted-only inventory as a complete CTIS file catalogue; determine whether broader metadata is served before promising it.
4. Expose a general document text read and reuse it in read_custom_view_document. Authorize the trial first, then exact inventory membership, then read existing text. Preserve page markers and all text; return next_part until null. Existing 200,000-character part size is a transport maximum to verify against actual host payload limits, not a total-text cap. No separate document quota for eligible trials. Return provenance/retrieval date; if source documents are not frozen with profiles, identify that fact and preserve retrieved report evidence.
5. Update report readers and the app-only profile dialog to share the same trial-level decision. Free reports can use complete content from eligible trials, but must still disclose ten-trial scope and avoid full-cohort conclusions. Private saved projects continue to require owner authentication. Preview capability expiry/revocation remains enforced; recheck authorization before releasing/storing data.
6. Update tool descriptions, RESEARCH_WORKFLOW, RESEARCH_CAPABILITIES, report guidance, plugin skill references and user-facing access wording together. Tool metadata must list the section enum and full/combined retrieval behavior, and point directly to the schema tool. Documentation alone is not discoverability. Replace paid-only content language with trial-count-based language.

## Existing section vocabulary to expose

| Section | Content |
|---|---|
| overview | Title/acronym, diseases, therapeutic areas, phase and key trial flags |
| population | Sex, population summary, stage/severity, treatment setting, characteristics, biomarkers |
| trial_design | Sample size, allocation, masking, intervention model, comparator types |
| interventions | Modalities, routes, targets, mechanisms, investigational and other products |
| eligibility | Inclusion and exclusion criteria |
| objectives | Primary and secondary objectives |
| endpoints | Structured endpoints |
| sponsor_and_organizations | Sponsor, legal representative and third parties |
| contacts | Trial management, scientific, recruitment and public CTIS contacts |
| countries | Country codes/counts and structured country records |
| sites | Site count, complete sites and nested investigators |
| documents | Available extracted document inventory |
| lifecycle | Complete CTIS lifecycle and dated overall/country updates |
| results | Participant flow, enrollment, endpoint/safety results and operational findings |

Stored profile schema version is currently 11.0.0, with filtering_variables, classification_variables, ctis_lifecycle and results roots. Requested absent data must remain distinguishable from an empty observed result. Validate section coverage against the authoritative schema: requesting all sections must not silently omit stored fields included in a full-profile response.

## Implementation order

1. Update both repository context checkpoints with this policy before runtime edits.
2. Introduce shared trial-content authorization in App, eligible IDs/count metadata and complete frozen profile retrieval; reuse it for dialogs/reports. Preserve owner, snapshot, expiry and paid-access checks.
3. Add section-aware model reads and the versioned schema discovery contract, reusing existing exact projection code.
4. Enable inventory-authorized text reads for eligible free trials, with complete pagination and provenance; retain post-read authorization checks.
5. Align all guidance and report scope/source metadata; remove contradictory content restrictions only inside eligible trials.
6. Validate anonymous/free/paid boundaries, actual model-visible tools, app dialog parity, report sources and schema discovery. Release App before MCP, then verify a no-auth end-to-end live read.

## Acceptance checks

- Without OAuth: obtain eligible ten, read one full profile, one section, several sections, document inventory and every part of a protocol; identical stored content to paid reads for the same frozen trial.
- Eleventh ineligible trial denied through profile, document, report and UI routes, including direct IDs, filters, offset tricks, unrelated preview capabilities and cross-project attempts.
- Repeated sections/documents/parts consume no additional trial units. Authenticated free behaves like anonymous; paid access covers its authorized full cohort.
- Profiles with >10 nested sites/investigators remain complete; entity table pagination still respects its own access limit.
- Protocol text reassembles without omissions/duplication; unknown names and unavailable/unextracted content have accurate errors. Continuation and response completeness are explicit.
- Schema tool and tools/list expose all 14 sections, exact fields/types and full/union semantics; schema/projection drift fails validation.
- Reports cite actual source IDs, preserve revision/provenance, include full eligible-trial evidence and accurately label their limited trial coverage.
- Expired preview and changed/revoked ownership/access cannot disclose new content; no unwanted project save, billing action, extraction or model job.
