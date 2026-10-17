# October 17 approved scope

The owner approved items 1–7, with item 4 limited to lowering the discovery threshold from 100 to 30 trials, and approved release.

1. Compact app-hosted OAuth connection copy reuses: “Save your search results, projects and custom views for later use in TrialAgents.” Existing authorization controls and account identity remain.
2. Show stored subscription details first; refresh billing independently from study counts. Preserve verified snapshots on failure and disable cancellation until live refresh succeeds.
3. Positive review case 2 requests CRO regulatory-submission experience from phase 2 pediatric trials, requiring direct evidence. Five positive cases remain.
4. Discovery guidance now uses 30–800 trials. The 100-row page size, 800 cap, explicit filters and workspace preparation architecture remain unchanged.
5. Tool descriptions state verified credential and storage behavior factually. Remove host-directed authentication/classification prose without changing authorization or write annotations. The original warning transcript was unavailable, so warning-free behavior cannot be guaranteed.
6. Keep failed Custom view content server-side; show compact retry status without rendering unsaved HTML or changing the selected table. Verify the committed report ID, version and HTML. Distinguish confirmed storage from later presentation failure; reopen a saved report instead of repeating its write. Preserve narrow revision recovery and conflict protection.
7. Negative review case now requests a patient information sheet for a clinical trial in Greece. Three negative cases remain.

## Evidence and limits

Production logs on October 17 include report_save REVISION_CHANGED (409) at 14:25:31 UTC, and workspace preparations of approximately 36 and 21 seconds. These establish a revision conflict and slow preparations, but do not identify the specific cardiovascular query or prove its root cause. No progressive-loading, background-work, caching or database redesign is included.

Review-case metadata changes are source changes, not completed live ChatGPT review runs or a public Directory submission. Updated runtime guidance and installed skills must ship together. Regression and deployment results are recorded in the associated PR and release report.
