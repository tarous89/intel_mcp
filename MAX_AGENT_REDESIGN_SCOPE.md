# Max report agent redesign — implementation scope

Status: implementation drafted behind a disabled flag on 2026-09-17; no deployment.
See REPORT_EXECUTION_CONTEXT.md for verified local checks and remaining release gates.
Date: 2026-09-16.

Replace the rigid Max extraction/analyst/reducer chain with evidence preparation followed by one persistent analyst agent. Preserve the approved Brief → Plan → Report flow. The analyst performs calculations, interpretation, HTML production and subsequent revisions. This is two execution stages after plan approval, not necessarily two model requests.

## 1. Agreed product behavior

- Each graph contains at most 10 displayed items. This is a presentation limit, not an analytical limit. Complete rankings remain in the dataset. Prefer bars over a ten-category donut; if a composition chart omits categories, preserve its denominator with an explicit remainder within the ten-item limit.
- The main chart in each analysis uses the first approved group. When a disease is named, that group is the disease alone, without broadening to solid tumors or a therapeutic area. Other dimensions are fallbacks only when no disease is named.
- Keep 3–5 planned groups. Subsequent groups are relevant overlapping subsets of the first group and cover distinct query aspects.
- Examine every analysis across every relevant group, including broader, narrower and adjacent perspectives. Put concise, substantive subgroup findings directly below the broad result. Detail can include a small table when needed. Evaluate whole subgroup rankings, including entities absent from the broad top ten.
- Record why a group cannot contribute to an analysis internally. Never force a pooled estimate just to use more trials. Unknown membership is not false membership; overlapping groups cannot be added together.
- Omit n=0 results and empty cards. Preserve supported zero-valued measurements or differences when n>0. Relevant small samples may support clearly labeled descriptive precedents, without implying statistical certainty.
- Use the mCRC outreach report's broad-chart/subgroup structure, with substantially deeper, query-specific analysis. Do not create repetitive cards just to increase report length.
- Show actual approved-plan analysis counts in the package chooser. Keep factual denominators with findings, distinct from unsolicited database-completeness analyses.
- Revisions use one free-text input. No refresh-evidence button, separate refresh workflow, or mandatory new plan approval for ordinary report revisions.
- Max alone receives this new execution path. Existing Light, historical reports, pricing and entitlement terms are outside this redesign.

## 2. Stage A — retrieve and freeze evidence

Use the approved plan's discovery seeds and, where useful, a lightweight Responses API call to formulate broad search criteria. Backend code handles paginated retrieval, deduplication, complete profile loading and storage. A separate autonomous retrieval agent is unnecessary initially.

Filtering remains permissive. Preserve relevant context and uncertain candidates; do not require every trial to match the exact query or every objective. When candidates exceed the configured analyzed-trial allowance, retain useful group diversity and record the selection rule. Avoid silently using the first page or newest trials as a representative sample.

Save complete selected profiles immediately after retrieval and before semantic interpretation. Persist batches during retrieval so interruption does not require refetching completed batches. The raw snapshot includes unique IDs, source/approval metadata, retrieval timestamps, profile content hashes, brief, approved plan, criteria and selection trace. Existing Max freezes its main dataset only after semantic population; that checkpoint is too late for the new workflow.

Retain the current 100-trial internal pilot ceiling initially. Trial and document limits become explicit configuration rather than constraints embedded in prompts. Supporting the existing larger public allowance requires separate scale validation within this rollout; this scope does not change public marketing limits.

## 3. Stage B — one analyst session

Start a managed agent session with a code environment, the frozen profiles, user query, approved analyses/groups, versioned analysis instructions, report template and calculation helpers. Choose the model using a quality/cost comparison during the pilot; do not assume the existing Responses models or Flex settings map unchanged to the agent environment.

The same agent:

1. Creates an analysis × group checklist and a source-backed working dataset.
2. Extracts needed facts from complete profiles and, selectively, existing document text.
3. Runs code for counts, percentages, rankings, summaries and comparisons, saving inputs and results.
4. Interprets results against the user's actual questions, with concrete trial precedents and source references.
5. Writes the report in the approved HTML template and inspects its rendered output.
6. Addresses targeted mathematical, coverage and layout feedback before completing the version.

Replace the mandatory SAP → per-trial extraction → isolated analyst calls → reducer sequence for the new path. Retain useful deterministic normalization and validation helpers. Do not port the old 20-semantic-variable, five-chart-item or eight-finding constraints as content bottlenecks. Resource budgets remain explicit and bounded.

Long plans are processed in manageable internal work units with saved tables and checklist state. There is one analyst session, no separate design model, and no delegated specialist-agent architecture in the initial scope. Completion must be assessed against the requested analyses, not inferred from a polished conclusion.

## 4. MCP access — exactly three retrieval tools

Expose only `filter_trials` (the existing name for “filter”), `get_profiles`, and `get_documents` to this agent. No classification, extraction, worker, start-analysis, admin, billing or write tools. Local code/file operations remain available for analysis and rendering; those are not clinical MCP worker tools.

Implement a Max-scoped MCP endpoint or equivalent authenticated tool surface. Its tool listing and invocation dispatcher must both enforce the allowlist. A prompt restriction or client-side tool filter alone is insufficient. Backend code creates the report-bound analysis lease before the session starts and issues scoped access; the agent never needs `start_analysis`. Backend renews/reissues permitted leases for revisions while enforcing ownership and allowances.

Important existing differences to resolve:

- Current Max document allowances are zero. Add bounded document-read allowances without enabling the extraction worker.
- Existing public `get_profiles`/`get_documents` target approved profiles; Max currently reads current profiles across approval states. Preserve authorized Max coverage through the restricted endpoint and compatible Engine readers rather than silently switching to the smaller public pool. Do not widen public/Light permissions.
- `get_documents` returns already-extracted document text in numbered parts, not PDFs or newly performed OCR. Retain exact document names, part markers and source page markers when present. Missing source text is not permission to launch ingestion/extraction workers.
- Return cached snapshot content for already-captured trial/profile requests by default. Persist new tool evidence before using it in published findings, with source and version metadata. Freeze all used document parts in the report evidence package.
- Validate report ownership, allowed trial/document identities and resource limits server-side. No database credentials enter the agent environment.

## 5. HTML, charts and PDF

Create a versioned Max template from the mCRC report pattern: short executive findings, evidence context, detailed query-aligned analysis sections, broad chart followed by relevant subgroup comparisons, practical interpretation and traceable references.

Use shared deterministic chart/table components and print CSS. The agent controls supported content and section composition, while tested components control fonts, spacing, axes, pagination and chart sizing. Charts must use saved calculation results, with labels, values and denominators kept aligned.

Introduce an explicit new report artifact/schema version or format discriminator. Keep the legacy version-2 renderer available for Light and stored reports; do not pretend arbitrary HTML is valid legacy section JSON. Store artifact references plus compact searchable metadata in App; clinical evidence and large artifacts remain in Engine-owned storage.

Serve generated HTML through an isolated, sanitized report surface with restrictive content policy. Use static SVG/images and no agent-authored executable JavaScript, remote assets or embedded credentials. Produce PDF from the same sanitized HTML and print styles, preferably with an isolated headless-browser renderer. Preserve all content and readable font sizes; allow large tables/blocks to flow across pages. The online report can remain available if PDF rendering needs a retry.

Render and inspect representative PDFs, including ten long chart labels, long tables, references, sparse subgroups and multi-page sections. Prompt compliance alone is not layout verification. Keep PDF generation away from the App's limited-memory request process.

## 6. Revisions and persisted state

One report revision composer accepts questions, requests for deeper analysis, presentation edits or changed subgroup comparisons. Reuse the current snapshot, derived data, scripts, analysis results and analyst session. Recompute affected results and all dependent summaries/charts; purely presentational edits must not silently change calculations.

A question can receive a conversational answer without rewriting the report when no report change is requested. A requested edit creates a new report version. Show a short description of what changed and preserve earlier versions.

No separate refresh mode: if the text explicitly requests new/current trials or needs evidence outside the snapshot, the same agent may use its permitted retrieval tools within entitlement limits. Save additions as a new evidence version and identify changed scope/date in the resulting report. Ordinary edits perform no live refresh or silent cohort replacement.

Persist report ID, revision ID, parent version, revision text, approved-plan version, session/turn IDs, dataset manifest/hash, code/results/template versions, artifact references and run state. Use an additive App migration; keep large evidence outside App DB. Serialize competing edits per report or attach them to explicit base versions so two revisions cannot overwrite each other.

The latest completed report remains visible throughout revision. Publish the new version atomically after artifact persistence. A failed revision preserves the prior report and does not consume a second initial-report purchase. Existing entitlement rules authorize included revisions.

Persist work independently of session lifetime. If a session/environment cannot continue, create a replacement with saved artifacts and instructions. New snapshots can support older Max reports where full evidence was saved; do not claim to reconstruct missing historical evidence for reports without snapshots.

The downloadable XLSX remains deterministic and version-matched: full profiles, derived variables, definitions, group membership, complete rankings, analysis results, source/document references and internal assessments. Long text must retain the existing lossless continuation behavior. Export needs no model call.

## 7. Reliability and corrections

Track managed session/turn IDs durably and reconcile progress via authenticated, idempotent callbacks/events or polling. Recover tracking after an App/MCP restart without starting duplicate paid sessions. Retrieval and artifact persistence also need durable jobs/checkpoints; a managed analyst session does not automatically make those application operations durable.

Use live stage activity: preparing evidence, analyzing named topics, and preparing report. Avoid “for your study” labels and fabricated percentages. Report preparation becomes active immediately when preceding analysis finishes, including artifact saving and rendering. Replace the current blind stale-run timeout with reconciliation against actual job/session activity for this new path.

Quality checks request bounded targeted corrections; they never abort the entire report over an editorial preference, sparse group, missing optional field or imperfect section. Retain valid content; omit or qualify unresolved unsupported findings. If no finding survives, preserve the evidence package and state the absence of supported conclusions honestly.

Authorization and HTML execution protections remain enforced. Infrastructure failures, quota exhaustion and unavailable storage cannot be promised away or marked as successful. Retry transient failures with backoff and checkpoints; do not loop on exhausted billing. An optional PDF failure must not erase completed HTML. Save enough intermediate work to continue after a recoverable interruption.

Log stage timings, model/tool usage, retries, artifact sizes and completion coverage without clinical payloads or secrets. Apply configurable per-turn/time/document budgets, with checkpointed continuation rather than silent truncation. Fewer visible stages do not guarantee lower latency or cost.

## 8. Repository changes

| Owner | Work |
|---|---|
| `tarous89/intel_mcp` | New agent-session adapter/executor alongside the legacy path; raw evidence preparation; restricted retrieval MCP surface; analysis/template instructions; calculations/provenance; versioned artifact handling; event reconciliation; targeted correction and recovery. |
| Customer App | Report/session/revision metadata migration; authenticated revision endpoint and composer; run state/progress integration; new isolated HTML renderer and PDF/download wiring; history and atomic publication; report-bound leases and revised document allowances. |
| `tarous89/intel-agent` Engine | Extend existing report-artifact storage beyond the current JSONL/XLSX pair for HTML/PDF/code/results/document evidence, with checksums and bounded streaming; ensure authorized Max document/profile read parity across current profile states. |
| Public/report design source | Reuse the mCRC HTML/design reference. No public-site deployment is required solely for this Max redesign. |

Confirmed MCP touchpoints: `max_report_execution.py`, `max_report.py`, `max_report_quality.py`, `max_group_analysis.py`, `report_dataset.py`, `report_artifacts.py`, `server.py`, `control_plane.py`, `engine_database.py`, and `engine_read/*`. Prefer a new executor/module set over expanding the legacy executor further.

Confirmed local App touchpoints: `app/app/page.tsx`, `app/components/LightReportProgress.tsx`, `app/components/ReportPackageDialog.tsx`, `app/lib/report-package-copy.ts`, and `app/lib/report-pdf-pagination.ts`. Shared components need tier-aware changes and regression checks. Exact backend migration/route paths require the complete current App checkout; the local App copy contains only part of the project. The existing MCP artifact client accepts only `jsonl.gz` and `xlsx`, so arbitrary new artifacts require a coordinated Engine change.

## 9. Delivery sequence and acceptance

1. **Contract and pilot:** implement raw snapshot input, one analyst session and the template against the saved CRPC report dataset. Compare with the existing output and mCRC presentation reference. Verify actual account/model/environment access before paid runs.
2. **Evidence and tools:** implement the three-tool endpoint, backend leases, document access and source persistence. Test discovery and full-profile access without worker tools.
3. **Report integration:** add artifact storage/versioning, isolated HTML display, PDF rendering, progress and deterministic dataset export.
4. **Revisions and recovery:** add the text composer, session continuation, affected-result recomputation, version history and restart-safe tracking.
5. **Release:** enable for new Max reports behind a server-side flag; retain legacy rendering and safe rollback. Validate representative 100-trial cases, then the advertised higher-volume plan/trial envelope before raising runtime limits. Update both report-execution context files to describe only verified shipped behavior.

Required acceptance evidence:

- Named disease stays first; 3–5 valid groups; every relevant analysis/group receives a recorded assessment.
- Graphs display at most ten items; subgroup leaders outside the broad top ten are discovered; n=0 output is absent; supported n>0 zero values remain correct.
- Counts deduplicate trial IDs and distinguish group size from contributing sample size. No addition of overlapping groups or inference of site performance from participation alone.
- Agent tool discovery lists exactly the three permitted retrieval tools; direct calls to worker/start/admin tools are denied. Cross-report and cross-user accesses are denied.
- Raw profiles survive interruption before analysis. Document parts and calculations can be traced to report-version evidence.
- A text-only formatting revision preserves data hashes and metrics; a subgroup revision updates dependent findings; a new-evidence request creates a new dataset version. None needs a refresh button.
- Failed or simultaneous revisions cannot overwrite a completed report. Restart/replayed callbacks cannot create duplicate analyst sessions or double-consume entitlements.
- Online HTML, PDF and XLSX agree; ten-label charts and long sections render without clipping or missing text; untrusted scripts cannot execute.
- Existing Light, stored report rendering, checkout and dataset downloads continue to work. Record cost, runtime and memory for initial runs and revisions before production expansion.

Scope readiness: the implementation direction is settled. The source implementation is now drafted across MCP, App and Engine, but live managed-agent/model access, full integration, document budget sizing, PDF appearance and quality/cost at scale remain release gates. Production has not been changed.

## References

- Existing MCP and App `REPORT_EXECUTION_CONTEXT.md`, plus inspected local source. MCP main context was also retrieved on 2026-09-16; App backend/Engine files were not fully available in the local copies.
- [mCRC presentation reference](https://trialagents.com/reports/eu-metastatic-colorectal-phase-3-mss-pmmr-sites)
- [OpenAI Agents API MCP connections](https://developers.openai.com/api/docs/guides/agents-api/tools/mcp): managed remote or environment-based MCP connections. Enforce the narrow tool surface in our own endpoint rather than assuming a particular client allowlist field.
- [OpenAI Agents API files and artifacts](https://developers.openai.com/api/docs/guides/agents-api/environments/files): hosted input files and immutable turn artifacts; copy required work to application storage.
- [OpenAI Agents API sessions](https://developers.openai.com/api/docs/guides/agents-api/sessions): continuing work through session turns.
