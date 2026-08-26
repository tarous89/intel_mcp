# Intel MCP — Project Context

**Canonical handoff file for the TrialAgents Intel MCP service.**

Last updated: 2026-08-26  
Repository: `tarous89/intel_mcp`  
Status: Planning complete; implementation not started.

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
