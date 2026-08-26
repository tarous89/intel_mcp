# Intel MCP — Project Context

**Canonical handoff file for the TrialAgents Intel MCP service.**

Last updated: 2026-08-26  
Repository: `tarous89/intel_mcp`  
Status: `start_analysis` implemented on `main`; app control plane live; MCP hosting/authentication topology pending.

## Purpose

Intel MCP is the fifth component of the TrialAgents platform. It exposes the existing Intel Agent clinical-trial intelligence backend to ChatGPT, the OpenAI API, Claude, the Claude API, and other MCP clients.

This repository is a distribution and access layer. It must not duplicate CTIS ingestion, document extraction, Trial Profile generation, or profile refresh logic owned by `tarous89/intel-agent`. Prefer a versioned internal API boundary to direct database coupling. The MCP service is independently deployable so MCP changes cannot interrupt the underlying data-building engine.

## Final public tool surface

### 1. `filter_trials`

Deterministically filters structured Trial Profile fields.

- Inputs: supported field/operator conditions, sort, page size, cursor.
- Outputs: matching trial IDs, normalized applied filters, total/coverage and next cursor.
- No free-form SQL or semantic search.
- Annotation: `readOnlyHint: true`, `destructiveHint: false`, `openWorldHint: false`.

### 2. `classify_trials`

Uses an LLM worker to classify selected Trial Profiles against user-supplied criteria.

- Inputs: trial IDs, criterion, allowed labels or requested output definition.
- Outputs per trial: classification, concise rationale, confidence/status and evidence references.
- Must use bounded batches and disclose that it consumes the account's analysis allowance.
- If it consumes allowance or persists job/usage state: `readOnlyHint: false`, `destructiveHint: false`, `openWorldHint: false`.

### 3. `get_profiles`

Returns selected structured Trial Profiles.

- Inputs: trial IDs, requested field projection, page size and cursor.
- Outputs: bounded profile data, sources, coverage and continuation cursor.
- Exclude contact personal data by default.
- Annotation: `readOnlyHint: true`, `destructiveHint: false`, `openWorldHint: false`.

### 4. `get_documents`

Returns extracted CTIS documents. This name supersedes `get_protocols`.

- Inputs: trial IDs, document types, optional document names/IDs, page or character bounds and cursor.
- Supported normalized types: `protocol`, `recruitment_arrangements`, `patient_information_and_informed_consent`, `assessments_and_forms`, and `results_report`.
- Use the Trial Profile's available extracted document types and document names.
- Outputs: document metadata and bounded text chunks with source/page references, truncation state and continuation cursor.
- Never dump every full document by default.
- Annotation: `readOnlyHint: true`, `destructiveHint: false`, `openWorldHint: false`.

### 5. `extract_variables`

Uses internal semantic retrieval plus an LLM worker to extract requested variables from selected documents.

- Inputs: trial IDs, document types or IDs, requested variables and optional population/context.
- Outputs per trial and variable: value, `found | not_found | ambiguous | not_applicable | error`, concise evidence and source/page references.
- Semantic passage search remains internal; there is no public search tool.
- Must use bounded batches and disclose analysis-allowance consumption.
- If it consumes allowance or persists job/usage state: `readOnlyHint: false`, `destructiveHint: false`, `openWorldHint: false`.

Excluded tools: `search_protocols`, `aggregate`, and `get_evidence`. Evidence is returned with substantive results.

## Common result contract

Use concise MCP `structuredContent` with a common envelope:

```json
{
  "data": {},
  "evidence": [],
  "coverage": {},
  "warnings": [],
  "next_cursor": null
}
```

- `content`: short human-readable summary only.
- `_meta`: client-only presentation metadata; never secrets or sensitive information.
- Stable public trial/profile/document IDs.
- Absolute, user-openable CTIS source URLs.
- Evidence includes document ID/type plus page or section.
- Per-item statuses allow partial success.
- Mark truncation and supply a cursor.
- Never expose tokens, prompts, chain-of-thought, internal traces, database IDs or debug data.
- Keep schemas strict, versioned and backward compatible; prefer additive changes.

## Remote MCP architecture

Deploy one universal production endpoint:

```text
https://mcp.trialagents.com/mcp
```

Requirements:

- Public HTTPS with a recognized certificate.
- Streamable HTTP using an official MCP SDK.
- Tools-only first release for widest OpenAI and Claude API compatibility.
- Stateless request handling where possible.
- Strict JSON input/output validation.
- Tenant isolation and server-side authorization on every call.
- Pagination, output limits and bounded batch sizes.
- Analysis calls must complete reliably within hosted-client timeouts; agents continue larger work using cursors.
- Rate limiting, timeouts, retry-safe behavior and graceful partial errors.
- Metrics and structured operational logs without tokens, PHI, document bodies or unnecessary personal data.
- Stable production URL; no local or temporary tunnel used for review.

## Authentication and paid access

Use the existing TrialAgents account, subscription and entitlement system. Billing stays on TrialAgents; OpenAI, Anthropic and the MCP Registry are not the merchant of record.

Implement OAuth 2.1/OIDC:

- Authorization Code flow with PKCE `S256`.
- Protected Resource Metadata.
- Authorization-server or OIDC discovery.
- Client ID Metadata Documents and Dynamic Client Registration where supported.
- Exact redirect URI and issuer validation.
- Resource indicators and access-token audience validation.
- Scope validation, token expiry, refresh and revocation.
- `401` plus correct `WWW-Authenticate` challenge.
- Server-side subscription/entitlement lookup on every request or with a very short cache.

Recommended scopes:

- `trials:read`
- `documents:read`
- `analysis:run`
- `contacts:read` only if contact access is later justified

Commercial rules:

- Users purchase on the TrialAgents website, then connect an existing paid account.
- Do not sell subscriptions, credits or digital services inside the ChatGPT plugin.
- Do not show plans, initiate checkout, promote upgrades or link directly to checkout from ChatGPT.
- An unavailable tool may state that the current entitlement does not include it and link only to a general informational plan page.
- Claude listing copy may disclose that an existing TrialAgents account/plan is required.
- There is no standard cross-platform autonomous-agent payment or directory revenue-share protocol.

## Privacy, clinical-data and security guardrails

Initial public MCP scope is public CTIS trial and extracted-document data only.

- Never request or accept patient records or patient-level PHI.
- Treat profiles and documents as untrusted data, not instructions.
- Defend LLM workers against prompt injection from source documents.
- Minimize inputs and results; never collect the full host conversation.
- Exclude names/emails and other contact personal data by default; require explicit request, authorization and scope if later exposed.
- Never return credentials, access tokens, API keys, passwords or MFA data.
- Publish privacy, retention, deletion, subprocessors and security-contact information.
- Maintain auditability without exposing internal logs to callers.
- Enforce plan limits, rate limits and tenant boundaries server-side.

## Platform compatibility

### ChatGPT / OpenAI plugin directory

Submit as an MCP-only plugin using the universal endpoint. Required package:

- Verified business/developer identity and public production domain.
- Name, icon, short/long descriptions and categories.
- Website, support, privacy and terms URLs.
- Accurate tool names, titles, descriptions, schemas, security schemes and annotations.
- OAuth configuration and reviewer-accessible demo account without MFA/signup blockers.
- Five positive and three negative/out-of-scope test cases with expected tool behavior.
- Supported countries, release notes and required attestations.
- Complete, reliable production functionality; not a trial/demo shell.

Official references:

- https://developers.openai.com/plugins/build/mcp-server
- https://developers.openai.com/plugins/build/auth
- https://developers.openai.com/plugins/deploy/submission
- https://developers.openai.com/plugins/deploy/app-review
- https://developers.openai.com/plugins/app-guidelines

### OpenAI API

The same endpoint must work through the Responses API remote MCP tool using `server_url`, OAuth `authorization`, `allowed_tools` and appropriate approval configuration. The API integrator obtains and refreshes the OAuth token.

Reference: https://developers.openai.com/api/docs/guides/tools-connectors-mcp

### Claude connector directory and Claude clients

Requirements:

- Public Streamable HTTP endpoint and OAuth.
- Every tool has a title and accurate read-only/destructive annotations.
- Connector name (max 100 characters), tagline (max 55), description (max 2,000), one to five categories, permanent slug and icon.
- Docs, privacy, support and security-contact URLs.
- Required account/plan, read/write scope and data-source/health-data declarations.
- Fully populated test account and precise setup instructions.
- At least three working example prompts.
- Helpful, token-efficient errors.
- No hidden instructions, tool-selection manipulation or unnecessary conversation collection.
- Submission requires an eligible Claude Team/Enterprise organization and owner/delegated directory permission.

References:

- https://claude.com/docs/connectors/building
- https://claude.com/docs/connectors/building/submission
- https://support.claude.com/en/articles/13145358-anthropic-software-directory-policy

### Claude API

The same public HTTPS endpoint must work through the Messages API `mcp_servers` configuration using an OAuth bearer token. The API consumer obtains and refreshes that token. The hosted connector currently supports MCP tools, so resources/prompts are not required for v1.

Reference: https://platform.claude.com/docs/en/agents-and-tools/mcp-connector

### Official MCP Registry

Publish immutable versioned metadata under a verified domain namespace, proposed:

```text
com.trialagents/intel-agent
```

The `server.json` must contain the current schema URL, name, title, description, semantic version and a `streamable-http` remote pointing to the universal endpoint. Registry listing provides discovery only, not billing.

References:

- https://modelcontextprotocol.io/registry/about
- https://modelcontextprotocol.io/registry/remote-servers
- https://modelcontextprotocol.io/registry/authentication
- https://modelcontextprotocol.io/registry/versioning

## Proposed repository structure

```text
src/
  server/
  tools/
    filter_trials
    classify_trials
    get_profiles
    get_documents
    extract_variables
  schemas/
  clients/
    intel_backend
    llm_worker
  auth/
  entitlements/
  policies/
  observability/
tests/
  contract/
  integration/
  security/
  review_cases/
docs/
  setup/
  privacy/
  support/
registry/
  server.json
```

Do not add client-specific business logic to tools. Platform adapters should remain thin around the same MCP contracts.

## Build sequence

1. Decide implementation language after inspecting the existing Intel Agent stack; reuse its language unless there is a strong reason not to.
2. Define the versioned internal Intel Agent read API and LLM-worker boundary.
3. Finalize strict JSON schemas, limits, errors and annotations for the five tools.
4. Scaffold the Streamable HTTP MCP server plus health checks and observability.
5. Implement OAuth discovery, PKCE, token validation, scopes and TrialAgents entitlement checks.
6. Implement and contract-test the three deterministic read tools.
7. Implement bounded `classify_trials` and `extract_variables` worker calls.
8. Add prompt-injection defenses, PHI rejection, data minimization, rate limits and security tests.
9. Test with MCP Inspector, ChatGPT developer mode, OpenAI Responses API, Claude connectors/Claude Code and Claude Messages API.
10. Deploy the stable production endpoint, then prepare OpenAI, Claude and MCP Registry submission packages.

## Documentation rule

Update this file after every important architectural decision, implementation milestone, production learning or listing-policy change. Keep prior decisions when superseded and mark their replacement explicitly.


## Use-case and access-profile architecture (2026-08-26)

This section supersedes the earlier assumption that every consumer uses one public OAuth-protected endpoint. Build one shared MCP codebase and tool implementation, but support distinct access and feature profiles.

### Use case 1 — Intel Agent application backend

- Intel MCP powers report generation inside the Intel Agent application.
- The user authenticates only once with the Intel Agent application.
- MCP must run transparently in the backend with no second login, OAuth consent, account-linking screen or user-facing MCP authentication step.
- The internal MCP surface must not be an unauthenticated public endpoint. Preferred safeguard: a Render private-network endpoint callable only by the Intel Agent backend. A service identity may be used if network topology requires it, but it must not create another user authentication flow.
- The Intel Agent backend remains responsible for user/session authentication and passes trusted user, tenant and entitlement context needed for authorization, usage attribution and limits.
- The app orchestrates MCP calls into reports; Intel MCP remains the bounded data/tool layer rather than owning the application UI.

### Use case 2 — external ChatGPT and Claude access

- Expose a public HTTPS Streamable HTTP MCP endpoint for ChatGPT, Claude and API consumers.
- Reuse the existing Intel Agent/TrialAgents account system and subscriptions.
- Use native OAuth account linking. Authentication is protocol-level OAuth, not a public `authenticate` MCP tool that accepts credentials.
- Provide a dedicated connection/consent page, either within the Intel Agent app or on a dedicated MCP route/domain.
- Validate OAuth token, user/tenant, scopes, subscription entitlement and limits on every request.
- External API consumers obtain and refresh a bearer token outside the MCP call.

### Feature profiles

Support centrally selectable tool bundles without forking the business logic:

1. **Core / no-worker profile** — deterministic retrieval tools only.
2. **Worker-enabled profile** — core tools plus approved AI-worker tools.

The exact membership remains pending because `classify_trials` also uses an LLM worker, while the user specifically described the no-worker version as “without basically the extraction tool.” Confirm whether the core profile excludes both `classify_trials` and `extract_variables`, or only `extract_variables`.

Feature availability must be controlled server-side by deployment profile, client registration, tenant/subscription entitlement or an explicit combination. Disabled tools must not be callable even if a client fabricates the request. Prefer one codebase with configuration-driven profiles; decide later whether public profiles use separate endpoints/listings or one OAuth endpoint with entitlement-based tool exposure.

### Centrally controlled limits

Every potentially large operation must accept a bounded requested limit and enforce a server-controlled hard maximum. “All” must never mean an unbounded synchronous request.

Limits must be independently configurable for:

- Trial IDs returned by `filter_trials`.
- Profiles returned by `get_profiles`.
- Trials processed by `classify_trials`.
- Documents returned per request and per trial by `get_documents`.
- Text chunks/pages/characters returned per document and per call.
- Trials, documents and variables processed by `extract_variables`.
- Total output size, worker runtime, concurrent calls, daily/monthly analysis allowance and pagination depth.

Use defaults plus hard caps. The caller may request any value up to its effective cap; the server clamps or rejects larger values and returns the applied limit, truncation state and continuation cursor. Effective limits may vary by internal-app profile, public profile, subscription tier and deployment environment. Store the policy centrally rather than hard-coding values into tool handlers.

“Top N” requires an explicit stable ordering. Deterministic filters should support approved sort keys such as relevance, latest submission/approval date or another defined field, with a deterministic tie-breaker. The ranking and default sort remain to be decided.

### Foundation questions still open

- Which exact report types and workflows will the Intel Agent app generate first?
- Which tools should the internal app profile expose?
- Does “no-worker” exclude both LLM-backed tools or only `extract_variables`?
- Are Core and Worker-enabled public access separate products/listings/endpoints, or one connector whose tools depend on entitlement?
- What default and hard maximum should apply to each trial, profile, document, text and worker dimension?
- What defines “top” results when the caller does not specify a sort?
- Will Intel Agent and Intel MCP run in the same Render private network?
- Should the connection/consent page live at `intel.trialagents.com/mcp` or a dedicated MCP subdomain?


## Confirmed report, packaging and deployment direction (2026-08-26)

### Report workflow and scope

Intel Agent reports are composable multi-tool workflows:

1. Filter trials deterministically using Trial Profile filtering variables.
2. If deterministic filtering is insufficient, classify only the shortlisted trials.
3. Retrieve profiles and/or documents and extract requested variables based on the report questions.
4. Combine the results, evidence and coverage into one report.

High-value examples include:

- All participating EU sites for Phase 2 head-and-neck cancer trials.
- Endpoint benchmarking.
- Inclusion/exclusion criteria comparisons.
- Principal investigators with names and emails.
- Sites with full contact details.
- Other specific variables extracted from documents.
- Multi-factor reports evaluating any combination of fields available in `intel_agent_db`.

Any information in the Intel Agent database may become a report topic. Tool outputs therefore must be composable, consistently identified, evidence-linked and able to share one report/analysis context. The app/report orchestrator, not an individual MCP tool, assembles the final report.

The internal Intel Agent app profile may use all five tools. Package policy (initially Light versus Max) controls the total trials, profiles, documents, variables and worker work available to a report.

### Feature control

Maintain independent server-side feature switches/entitlements rather than only two hard-coded bundles:

- `filter_trials`
- `get_profiles`
- `get_documents`
- `classify_trials`
- `extract_variables`

This permits at least:

- Core: deterministic tools only.
- Classification-enabled: core plus `classify_trials`.
- Full analysis: all five tools.

The user may enable either or both worker tools without maintaining separate implementations. External distribution uses one connector; the server enforces the connected account's tool and usage entitlements.

### Analysis as the commercial unit — proposed

Prefer “analyses per month” for customer-facing pricing, with internal compute metering for margin protection.

One analysis should be a server-side report workspace identified by an `analysis_id` and defined by:

- One report objective/brief.
- One base trial cohort/search definition.
- A package-specific maximum scope and compute budget.
- All filtering, classification, profile/document retrieval and variable extraction needed for that report.
- Revisions and follow-up questions within the same report workspace and base cohort.

A revision remains part of the same analysis when it refines presentation, filters, variables or questions for the same underlying report/cohort. A new analysis begins when the user starts a new report objective, materially changes the base cohort (for example a different indication, phase or geography), or exhausts the analysis scope/compute budget.

Do not bill each internal MCP call as a separate analysis. Track trials classified, documents processed, variables extracted, model tokens/cost and revisions internally. The exact revision window and package budgets remain to be agreed.

Because MCP hosts do not reliably provide a reusable conversation identifier, tools should accept an optional `analysis_id` and return it. The first report call may create the ID automatically; later calls and revisions must reuse it. Avoid adding a separate public `create_analysis` tool unless testing shows automatic creation is unreliable.

### Default ordering

The default trial order is latest update first, using `latest_country_submission_or_approval_date DESC`, with EU trial number as a stable tie-breaker. Callers may select other approved deterministic sort keys. “Top N” always means the first N records under the declared order.

### Deployment isolation — proposed

Use one repository/codebase deployed as separate Render services in the same workspace:

1. **Private internal MCP service** — reachable only through Render's private network by the Intel Agent app/backend. No second user login or OAuth flow. The app forwards trusted user, tenant, package and `analysis_id` context; a private service identity or signed internal context protects the service without creating user-visible authentication.
2. **Public MCP gateway/service** — stable public HTTPS endpoint for the single ChatGPT/Claude connector. Performs OAuth, entitlement, rate-limit and public-policy enforcement before invoking the same core tool layer.
3. **Worker service/queue** — isolated AI classification and extraction execution so expensive or failed worker tasks cannot destabilize retrieval.

Deploy the same image/configurable modules where practical; do not fork the tool implementations. The public service must not expose the private internal endpoint or directly broaden database access.

### Domain direction — proposed hybrid

Use:

- `https://intel.trialagents.com/mcp` for the user-facing product, connection, consent, documentation and account-management page.
- `https://mcp.trialagents.com/mcp` for the stable machine-facing MCP protocol endpoint.

This preserves Intel Agent discovery and conversion while isolating protocol routing, rate limits, security, logs and availability. The OAuth consent page can return users to Intel Agent. Do not force the machine endpoint to share the application deployment merely for marketing visibility.

### Initial limit proposal for discussion

Use both per-call caps and per-analysis package budgets. The following are starting values, not final decisions:

| Dimension | Per-call hard cap | Light per analysis | Max per analysis |
|---|---:|---:|---:|
| Filtered trial IDs returned | 100 | 100 | 1,000 |
| Profiles returned | 25 | 50 | 500 |
| Trials classified | 20 | 25 | 200 |
| Document metadata records | 100 | 100 | 1,000 |
| Document text returned | 5 documents / 150k characters total | 25 documents | 200 documents |
| Trials sent to variable extraction | 10 | 20 | 200 |
| Documents processed by extraction | 25 | 50 | 500 |
| Requested variables | 20 | 20 | 50 |

All larger work is paginated/batched. Public interactive calls remain bounded; the internal app may orchestrate multiple batches up to the package's analysis budget. Limits must be admin-configurable without redeployment and recorded with every analysis for reproducibility.

### Remaining decisions

- Approve or revise the proposed definition of one analysis and how revisions stay within it.
- Approve or revise the Light/Max starting limits after cost/performance measurement.
- Decide whether external users may retrieve investigator/site names and emails, and under which plan/scope.
- Decide whether analyses expire for revisions after a defined time window.
- Decide whether limit overages are blocked, require a new analysis, or are offered only through an externally managed add-on.


## SOL orchestration and short-lived analysis lease (2026-08-26)

This section supersedes any implication that the Intel Agent application itself manually sequences individual MCP calls.

### Orchestration ownership

- After the user approves the report plan, the Intel Agent app makes one initial call to OpenAI SOL and waits for the completed report.
- SOL receives the approved report plan plus access to the permitted Intel MCP tools.
- SOL decides which tools to call, in which order, whether deterministic filtering is sufficient, when classification is needed, whether profiles or documents are required, and which variables must be extracted.
- SOL may paginate and make repeated calls within the analysis limits.
- Each MCP tool performs only its narrow declared operation. Tools do not generate the overall report, decide the workflow or silently invoke other public tools.
- SOL synthesizes the final report from structured tool outputs, coverage and public source references.

Public investigator, site and contact data may be returned within applicable limits and accompanied by the public sources from which it was obtained. Detailed contact-field privacy and presentation rules are deferred.

### Confirmed limits and result behavior

- The previously proposed Light and Max starting limits are accepted for now and remain centrally configurable.
- The orchestrator chooses how many results to request up to the effective per-call and per-analysis limits.
- Tools should enable retrieval of as many valid matching results as the entitlement permits through deterministic pagination.
- When more results exist, return `has_more`, `next_cursor`, the applied limit and remaining analysis budget. Never silently discard valid results or interpret “all” as an unbounded call.
- The single external connector supports entitlement-controlled Core, classification-enabled and full-analysis capabilities.

### Analysis lease requirements

Use a short-lived `analysis_id` to correlate, meter and constrain all calls belonging to one report execution or revision session.

Confirmed behavior:

- Initial expiry: 60 minutes.
- The ID may be reused for repeated filtering and revisions while still valid.
- Every substantive tool after analysis creation requires the same `analysis_id`.
- The ID is bound server-side to the authenticated user/account, tenant, package, enabled tools, limit snapshot, usage counters, creation time, expiry and status.
- Expired, blocked or exhausted IDs cannot be revived.
- On expiry or budget exhaustion, return a typed error instructing SOL to start a new analysis. Creating a replacement must recheck authentication, entitlement and remaining monthly analyses.
- Already-running calls may finish, but no new call may begin after expiry.
- Default expiry is absolute from creation, not indefinitely extended by activity, unless this is changed later.

Security boundary:

- `analysis_id` is not the user's authentication token and must never replace OAuth or the trusted internal app/service identity.
- Treat it as an opaque analysis lease/handle. Validate both the real authenticated principal and the ID binding on every call.
- Prefer an opaque high-entropy identifier with server-side state over a self-contained JWT so it can be revoked, blocked and atomically metered.

### Recommended lifecycle tool — pending final approval

Add a narrow control-plane tool, proposed name `start_analysis`, rather than making `filter_trials` create IDs.

Reasons:

- Session creation, entitlement reservation and filtering are different operations.
- Some valid workflows begin with known trial IDs and do not need filtering.
- Coupling billing/session creation to filtering violates the rule that tools do only their declared task.
- Expiry and allowance errors can consistently tell SOL to call one lifecycle tool.
- `filter_trials` remains reusable with an existing valid ID for flexible revisions.

Proposed `start_analysis` behavior:

- Input: concise approved report objective/plan reference and requested capabilities.
- Authenticates the caller, verifies remaining analyses and creates a 60-minute lease.
- Output: `analysis_id`, `expires_at`, enabled tools, effective Light/Max limits and analysis status.
- It performs no filtering or report work.
- Starting alone should not unfairly consume an analysis if no substantive tool ever succeeds; implement reservation/activation semantics and limit abandoned reservations.
- Annotation: `readOnlyHint: false`, `destructiveHint: false`, `openWorldHint: false`.

If approved, the public surface contains five business/data tools plus one lifecycle/control tool. A new analysis begins through `start_analysis`; `filter_trials` never creates or authenticates an analysis.


## Confirmed app orchestration, progress and concurrency (2026-08-26)

### Two-call report flow

The Intel Agent app owns the report lifecycle:

1. The user submits the initial report request.
2. A first SOL call, without report-execution MCP access, proposes a report plan.
3. The app stores and displays the plan.
4. The user may edit the plan and explicitly approves it.
5. The app starts a second SOL call with the approved plan and only the entitled Intel MCP tools.
6. SOL calls `start_analysis`, orchestrates the required MCP tools and writes the final report.
7. The app stores the final report and presents it to the user.

The app owns the initial user input, plan versions, approval state, OpenAI response/run identifiers, visible progress, final report and report revision history. Intel MCP owns only its narrow tool operations, analysis lease, usage limits and minimal audit/evidence references. MCP does not own report planning, orchestration, prose generation or final report storage.

### Reliable background SOL execution and visible progress

Run the second SOL request through the OpenAI Responses API with both background execution and event streaming enabled.

- Background execution allows the run to continue if the user's browser disconnects or an HTTP connection times out.
- The Intel Agent backend stores the OpenAI response ID and latest event sequence number.
- The browser receives progress from the Intel Agent backend through SSE or WebSocket.
- If the app-to-OpenAI stream disconnects, resume from the last sequence number; do not restart the whole report.
- Poll/retrieve the existing response when status is uncertain. Start a replacement response only after the original is definitively failed/cancelled.
- OpenAI streaming exposes response status and MCP list/call in-progress, completed and failed events. Convert these into concise user-facing stages; never expose hidden reasoning or chain-of-thought.

Initial user-facing stages:

- Preparing analysis
- Filtering trials
- Classifying shortlisted trials
- Retrieving trial profiles
- Reviewing documents
- Extracting requested variables
- Writing report
- Completed / retrying / failed

Where MCP results provide counts, show factual progress such as “42 trials matched” or “12 of 20 documents reviewed.” Do not fabricate percentage completion when the total work is not yet known.

Retries must be idempotent:

- The app creates a stable `report_run_id` for the approved plan and passes it to SOL.
- `start_analysis` accepts `report_run_id`.
- A repeated `start_analysis` for the same user and run returns the existing valid analysis rather than consuming another allowance.
- Because only one active analysis is allowed per user, an accidental repeated start also returns that active analysis.
- Read-tool retries must preserve `analysis_id`, cursor and request bounds.
- Worker retry and usage accounting must avoid double charging the same accepted worker job.

Official OpenAI references:

- https://developers.openai.com/api/docs/guides/background
- https://developers.openai.com/api/docs/guides/streaming-responses
- https://developers.openai.com/api/reference/cli/resources/beta/subresources/responses

### Confirmed ownership and concurrency

- Analysis allowances belong to individual users in v1. Company/workspace sharing is out of scope.
- Every package allows only one active `analysis_id` per user.
- A second start request while an analysis is valid returns the active analysis instead of creating another.
- The 60-minute absolute expiry remains.
- After expiry or blocking, a new start checks the user's remaining analysis allowance.
- The app persists report content and history; MCP does not.

### Confirmed tool discovery

- `start_analysis` is approved as the sixth, separate lifecycle tool.
- The five business tools remain narrow and do not orchestrate each other.
- Worker tools that are disabled for a deployment/profile or unavailable to a user must not be visible to SOL.
- For the Intel Agent app, pass only the entitled tools in the SOL request/allowed-tools configuration.
- For public ChatGPT/Claude access, return an authenticated entitlement-filtered tool list. Reconnection may be required after a subscription/tool entitlement changes.
- Do not advertise unavailable tools merely to return entitlement errors in v1.


## Implementation discovery: app authentication and allowance prerequisite (2026-08-26)

Inspection of `tarous89/intel_agent_app` before implementing `start_analysis` found:

- The current signup/login/session is an explicit browser-local prototype. Accounts, plaintext prototype passwords and sessions are stored in `localStorage`; no server can trust this identity.
- The app's Drizzle schema is intentionally empty and there is no durable user, session, project, order, entitlement, analysis or report storage.
- The ChatGPT-auth header helper belongs to the earlier hosting integration and is not production authentication for the canonical Render app.
- Stripe Checkout currently sells one €450 Max Report and carries project metadata, but the signed webhook only logs successful checkout.
- The payment-success page stores a browser-local demo order. A payment does not yet create a durable user-bound report entitlement.
- Light Report is currently labeled as a free preview; its real allowance has not been defined.
- Therefore `start_analysis` cannot yet truthfully authenticate a user or atomically consume/check a durable analysis allowance.

Security constraint: never accept user ID, plan, payment status or remaining allowance directly from the browser/localStorage. Never treat an email header or unsigned internal header as app authentication.

Required dependency order:

1. Add production app authentication and durable user/session storage.
2. Add durable projects, Stripe orders and per-user analysis entitlement/allowance ledger.
3. Make the Stripe webhook idempotently grant the purchased entitlement to the authenticated user/project.
4. Add a private app-to-MCP identity assertion or internal entitlement endpoint protected by a service credential and private network.
5. Implement `start_analysis` with an atomic one-active-analysis-per-user transaction, 60-minute expiry, allowance reservation/activation and idempotent `report_run_id`.
6. Only then connect the approved-plan SOL background run.

Recommended isolation remains a separate app/MCP control-plane PostgreSQL database, not the Intel Agent clinical-trial warehouse. Final authentication provider, database provisioning and Light/Max allowance rules require owner confirmation before implementation.


## Approved implementation foundation (2026-08-26)

The owner confirmed the implementation foundation:

- No parallel reports are supported. Every user, regardless of Light or Max, may have only one active report/`analysis_id` at a time.
- `start_analysis` is a separate sixth lifecycle tool.
- The app uses a two-SOL-call flow: plan proposal/revision first, then a background MCP-enabled SOL call only after approval.
- Unavailable worker tools are hidden from the orchestrator rather than exposed with entitlement errors.
- The app owns user input, project, plan versions/approval, background response progress, final report and revision history. MCP remains narrow.
- Analysis ownership is per individual user in v1; organizations/workspaces are deferred.
- Production app authentication and durable users/sessions must replace the browser-local prototype.
- Create an isolated app/MCP control-plane PostgreSQL database; never use the clinical-trial warehouse for identity, commerce or analysis leases.
- Initial allowance policy: one free Light analysis per user; every successful €450 Max Report purchase grants one Max analysis tied to that user/project.
- System failures before successful report fulfillment restore the reserved allowance.
- Stripe remains fail-closed/test-mode until its verified webhook creates durable, idempotent user-bound entitlements.
- Implement the private app-to-MCP identity bridge only after production app authentication exists.

The one-active-analysis rule also provides start idempotency: while a valid lease exists, repeated `start_analysis` calls for that authenticated user return the existing analysis rather than reserving another allowance.

## start_analysis implementation checkpoint (2026-08-26)

The first MCP implementation now exists on branch `feat/start-analysis`.

- Selected Python to match the extraction/intelligence stack.
- Selected the official stable MCP Python SDK v2 line, which supports the 2026-07-28 sessionless Streamable HTTP protocol. The previous planning text that assumed the v1 FastMCP API is superseded for new code.
- Added a tools-only `MCPServer` with Streamable HTTP at `/mcp`, an unauthenticated non-sensitive `/health` route, and explicit DNS-rebinding Host allowlisting through `MCP_ALLOWED_HOSTS`.
- Implemented `start_analysis(report_run_id)` as the only visible tool in this checkpoint.
- The tool accepts only the stable app-created `report_run_id`. It does not accept user ID, email, package, payment state, remaining allowance, plan content or requested tool entitlements from the model.
- The tool calls the private app endpoint `POST /api/internal/mcp/start-analysis` with a shared Render service credential. End users authenticate only with the Intel Agent app; there is no second user login or MCP authentication prompt for the internal app profile.
- The app resolves the authenticated user, project, approved plan, tier, enabled tools and allowance server-side, then atomically returns or creates the one active 60-minute lease.
- The typed MCP result contains `analysis_id`, actual `report_run_id`, `active` status, tier, absolute expiry, visible enabled tools, the immutable limit snapshot and whether the lease was reused.
- `start_analysis` is annotated non-read-only, non-destructive, idempotent and closed-world. It performs no filtering, retrieval, classification, extraction or report writing.
- Expected allowance and state failures are surfaced as typed, model-readable tool errors without leaking internal HTTP details or service credentials.
- Tests cover private bearer propagation, response validation, allowance errors, tool discovery annotations and structured output. Current result: 3 passing tests.

Cross-repository dependency:

- App branch `feat/production-auth-start-analysis` owns PostgreSQL users/sessions, one free Light entitlement, paid Max entitlements, approved report runs and the atomic lease endpoint.
- Both services must receive the same secret as `MCP_INTERNAL_SERVICE_TOKEN` in the app and `INTEL_APP_SERVICE_TOKEN` in MCP.
- `INTEL_APP_CONTROL_URL` must use the app's Render private-network URL in production.
- Do not deploy the MCP service until the app migration and private endpoint are deployed and verified.


## Production deployment checkpoint — 2026-08-26

- Merged the `start_analysis` implementation to `main` at commit `2c5fe7afb8cfb899945594967043036ed8c566e6`.
- The Intel Agent app control plane is now live on Render. Its PostgreSQL migration completed successfully, the health endpoint is healthy and unauthenticated calls to the internal start-analysis endpoint are rejected with `401 UNAUTHORIZED`.
- The MCP service itself is not deployed yet. Render's official hosted MCP server manages Render infrastructure and is not a hosting product for the TrialAgents MCP. TrialAgents MCP is deployed as an ordinary web or private service, with ordinary instance pricing and no MCP-specific surcharge.
- The MCP will reuse the existing isolated app/MCP control-plane PostgreSQL database for authentication-derived entitlement, allowance and lease state; it does not need another database. The existing app web service could technically host the protocol too, but that would couple the Node app and Python MCP runtimes, deployments, failures and scaling.
- The cleaner boundary remains a separate MCP service. During pre-user development it may be a separate free public web service only after inbound service-token authentication is enforced on `/mcp`. Before real production use, move to a paid private service for the internal app profile or retain a separately authenticated public service for external ChatGPT/Claude connections.
- Render free web services can send private-network requests but cannot receive them. The current free app can therefore receive MCP control-plane calls only through its authenticated public HTTPS endpoint unless it is upgraded.
- When the MCP service is created, use a fresh high-entropy service credential as app `MCP_INTERNAL_SERVICE_TOKEN` and MCP `INTEL_APP_SERVICE_TOKEN`, and require authenticated inbound MCP requests as well. Never expose either credential to browsers or model tool arguments.
- Initial MCP deployment configuration remains: Python runtime, `pip install .`, `intel-mcp`, Frankfurt region, automatic deploy from `main`, and a strict `MCP_ALLOWED_HOSTS` allowlist.
- Before enabling real report execution, verify private/public control-plane connectivity (according to the chosen topology), `/health`, MCP initialization/tool discovery, authenticated `start_analysis`, retry reuse, one-active-analysis enforcement and typed allowance failures.
