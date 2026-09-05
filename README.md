# Intel MCP

Remote Model Context Protocol service for TrialAgents Intel Agent.

The service root serves the public Intel MCP documentation page. It explains
the report-run lifecycle, platform-specific ChatGPT and Claude connector setup,
an official Python MCP SDK example, copyable tool arguments and the complete
six-tool workflow. Hosted ChatGPT and Claude clients sign in through TrialAgents
OAuth linked to the existing Intel Agent account; the page never exposes or asks a
customer to reuse the internal service credential.

Implemented tools:

- `start_analysis` receives only an app-created `report_run_id`, calls the Intel Agent app's service-authenticated control plane, and returns the existing or newly reserved 60-minute analysis lease.
- `filter_trials` deterministically queries approved structured Trial Profiles through the Engine-owned `mcp_serving` v1 read contract. It then asks the app control plane to validate the `analysis_id` and atomically meter the unique trial IDs that may be returned.
- `classify_trials` classifies approved contact-redacted Trial Profiles against bounded user criteria and returns deterministic eligible/ineligible/uncertain trial ID buckets with counts.
- `get_profiles` returns current approved Trial Profile 10.0.0 data for explicit EU trial numbers. With `sections`, it returns exact deterministic profile projections for up to 100 trials; with `sections` omitted or empty, it returns complete profiles for up to 20 trials.
- `get_documents` returns extracted text for one explicitly named document, in parts of at most 200,000 characters, and meters unique documents through the app control plane.
- `extract_variables` extracts up to 20 typed values from one approved trial in one Terra request using its complete profile plus the single profile-listed protocol when available.

User identity, plan approval, package, enabled tools and allowances remain app-owned. MCP has no app/control-plane database credential and no Engine owner or write credential. Its only clinical-store login is the exact `intel_mcp_reader_v1` role, which PostgreSQL restricts to approved-only versioned views and read-only transactions.

Every MCP business-tool invocation emits best-effort operational telemetry to the
app control plane: response duration, success/error code and, for worker-backed tools,
the selected model plus actual Responses API token usage. Clinical inputs and results
are never included. The app reservation response selects the model independently for
`classify_trials` and `extract_variables`, so admin changes apply on the next call
without restarting MCP.

## `extract_variables` contract

`extract_variables` accepts one `trial_id` and 1–20 variable definitions with a
snake-case name, precise instruction and optional value type. Supported types
are string, integer, number, boolean and string array.

The local Engine-read adapter supplies the complete approved Trial Profile and the complete text of
the single protocol named in its
`filtering_variables.available_extracted_documents.protocol` array
when available. Both are sent in one Terra request. Output is
limited to the trial ID, a values object containing every requested key (with
`null` when unresolved), and the standard analysis allowance. Status,
explanation, evidence, document name, page and source metadata are excluded from
both the worker schema and public result.

No on-demand download, OCR or extraction occurs. The tool uses one model request
per invocation with no automatic model retry. Stable trial-plus-variable-set
keys make exact retries allowance-safe. Detailed contract:
`docs/extract-variables.md`.

## `filter_trials` contract

`filter_trials` is a shortlist tool. It does not search the whole profile, run semantic search, classify trials, retrieve complete profiles/documents, extract variables or write report prose.

Use it as the first screening step. Apply broad structured conditions to reduce the approved-profile population to a focused shortlist, then use `classify_trials` for complex inclusion/exclusion logic or `get_profiles` with selected sections when the shortlist needs objective-specific profile review. Classification accepts at most 25 trials per call, so split larger shortlists into consistent batches rather than classifying the full discovery population.

Each shortlist item contains only `eu_number`, `trial_title` and `sponsor_name`.
Document names, phase and dates are not repeated in filtering results. Retrieve relevant
profile sections or a complete selected profile with `get_profiles`; its
`filtering_variables.available_extracted_documents` object is available through the
`documents` section and contains the exact names accepted by `get_documents`. Output counts contain
total approved profiles, total matches and records returned in this call. Analysis
allowance separately reports its limit, cumulative unique IDs used and remaining capacity.

General behavior:

- Only `approval_status = approved` Trial Profiles are eligible.
- All text comparisons are case-insensitive.
- `contains` is the default text operator; `is` means a complete case-insensitive match.
- Negative text operators are `does_not_contain` and `is_not`. A missing value never satisfies a negative filter.
- Controlled-array operators are `contains_any`, `contains_all` and `contains_none`.
- Different fields combine with AND. Put multiple alternatives for the same field in one condition. If OR is needed across different fields, make separate calls.
- Conditions within one `countries` group must match the same country row. Multiple country groups combine with AND and may match different rows.
- Default order is `latest_country_submission_or_approval_date desc`, with `eu_number asc` as the stable tie-breaker.
- Pages are capped at 100. Use `offset: 0` first, then increase offset by the prior call's limit while more matches remain.
- Light analyses may receive 100 unique filtered trial IDs; Max analyses may receive 1,000. Repeated IDs in retries or revisions do not consume allowance twice.
- The MCP annotation uses `readOnlyHint: false`: the Engine query is read-only, but admitting a previously unseen trial ID updates the analysis's observable allowance state.

Exposed structured fields:

- Text: `eu_number`, `trial_title`, `trial_acronym`, `sponsor_name`.
- Dates: latest country submission/approval, initial CTIS submission, first CTIS authorization and latest CTIS authorization.
- Document availability: normalized extracted document types and individual document names.
- Controlled arrays: therapeutic areas, phases, administration routes, country codes, eligible sexes and comparator types. The `modalities` filter targets the profile's single scalar `modality` through the Engine compatibility projection.
- Booleans: rare-disease, orphan-designation, paediatric and first-in-human flags. Boolean values may also be checked for `unknown`.
- Numbers: planned sample size, number of countries and number of sites.
- Controlled scalars: allocation, masking and intervention model.
- Same-country fields: country code, normalized recruitment status, country dates, country site count and country planned sample size.

Controlled vocabularies are embedded directly in the MCP JSON Schema. Country codes use ISO 3166-1 alpha-2. Known normalized country statuses are `Authorised`, `Not authorised`, `Under evaluation`, `Ended`, `Halted`, `Lapsed`, `Withdrawn`, `Expired`, `Suspended`, `Not valid`, `Pending` and `Revoked`.

The controlled filter vocabularies are aligned with Trial Profile contract
10.0.0. The 34 therapeutic areas include separate Blood Disorders, Gynecology, Obstetrics,
Reproductive Medicine, Emergency Medicine and Critical Care values.

Sponsor-name limitation: the structured CTIS sponsor value can sometimes refer to a subsidy or funding source, or omit part of the complete legal entity name. Use sponsor-name filtering to shortlist records; do not treat it as definitive legal-entity resolution.

## `get_profiles` contract

`get_profiles` accepts `analysis_id`, `trial_ids`, and optional `sections`.

- In **section mode**, request 1–100 EU trial numbers and one or more controlled Trial Profile sections.
- In **complete-profile mode**, omit `sections` or pass `[]`; request at most 20 unique EU trial numbers.
- Duplicate trial IDs and section names are removed while preserving first occurrence order.
- Section mode is an exact deterministic projection of the stored profile. It performs no LLM summarization, rewriting or inference.
- Complete-profile mode returns the complete stored current approved Trial Profile, including contacts, extracted-document inventory and results.
- Candidate/rejected/missing profiles are reported in `unavailable_trial_ids`; there is no raw-CTIS fallback.
- Light analyses may retrieve **100 unique profiles**; Max analyses may retrieve 500. Exact repeated IDs do not consume allowance twice, even if a later call requests different sections or the complete profile.
- Every approved profile admitted by the allowance is returned without field-level truncation within the requested projection. Unavailable IDs and IDs blocked because allowance was reached are returned as separate ID arrays.
- The tool does not refresh profiles, retrieve document text, classify, search semantically, extract variables or write report prose.
- Because returning a newly seen profile updates observable allowance state, annotations are non-read-only, non-destructive, idempotent and closed-world.

### Trial Profile 10.0.0 section vocabulary

- `overview` — therapeutic area, phase, disease, trial title/acronym and core flags.
- `population` — target population, stage/severity, settings, population characteristics, biomarkers and eligible sexes.
- `trial_design` — sample size, allocation, masking, intervention model and comparator types.
- `interventions` — modality, administration routes, targets, mechanisms and products.
- `eligibility` — inclusion and exclusion criteria.
- `objectives` — primary and secondary objectives.
- `endpoints` — structured endpoints.
- `sponsor_and_organizations` — sponsor, legal representative and third-party organizations.
- `contacts` — management, scientific, recruitment and public CTIS contacts.
- `countries` — country counts/codes and structured country records.
- `sites` — site count and structured site records with nested site contacts.
- `documents` — six-category `available_extracted_documents` inventory.
- `lifecycle` — complete dated `ctis_lifecycle` object.
- `results` — complete results object, including participant flow, endpoint/safety results and operational findings.

Example shortlist projection:

```json
{
  "analysis_id": "ana_...",
  "trial_ids": ["2024-500001-00-00", "2024-500002-00-00"],
  "sections": ["overview", "trial_design", "endpoints", "countries"]
}
```

Example complete-profile request:

```json
{
  "analysis_id": "ana_...",
  "trial_ids": ["2024-500001-00-00"]
}
```

Production uses the restricted direct database read path. The legacy Engine HTTP rollback endpoint remains capped at ten trial IDs internally; MCP automatically batches larger public requests into groups of ten and preserves caller order. Detailed contract: `docs/get-profiles.md`.

## `get_documents` contract

`get_documents` accepts `analysis_id`, one `trial_id`, one exact
case-insensitive `document_name`, and optional one-based `part` (default 1).

- The document must be listed in one of the approved Trial Profile's six
  `filtering_variables.available_extracted_documents` arrays. Obtain the exact name with
  `get_profiles(sections=["documents"])` or a complete profile before calling `get_documents`.
- Each response returns extracted text only, with preserved page markers, and
  never returns a PDF, binary, link, page count or character count.
- Each part is limited to 200,000 characters. If `next_part` is a number, call
  the tool again with that part; `null` means the document is complete.
- Light analyses may retrieve 10 unique documents; Max analyses may retrieve
  50. Continuation parts and exact retries do not consume another document.
- The tool performs no on-demand download, OCR, extraction, semantic search or
  model work.

Detailed contract: `docs/get-documents.md`.

## Local setup

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
export INTEL_APP_CONTROL_URL=http://localhost:3000
export INTEL_APP_SERVICE_TOKEN=replace-me
# Production uses the database source. The Engine host/user/password are a
# distinct restricted login, never the Engine owner DATABASE_URL.
export MCP_ENGINE_SOURCE=database
export MCP_ENGINE_DATABASE_HOST=engine-db.internal
export MCP_ENGINE_DATABASE_NAME=intel
export MCP_ENGINE_DATABASE_USER=intel_mcp_reader_v1
export MCP_ENGINE_DATABASE_PASSWORD=replace-with-a-long-random-reader-password
# Temporary rollback compatibility while the database path is canaried:
export INTEL_ENGINE_API_URL=http://localhost:10000
export INTEL_ENGINE_SERVICE_TOKEN=replace-with-a-separate-engine-service-token
export MCP_INBOUND_SERVICE_TOKEN=replace-me-too
export REPORT_PLAN_SERVICE_TOKEN=replace-with-a-separate-report-plan-token
export MCP_PUBLIC_RESOURCE_URL=https://mcp.trialagents.com/mcp
export MCP_OAUTH_AUTHORIZATION_SERVER_URL=https://intel.trialagents.com
intel-mcp
```

The public documentation page is `/`, the Streamable HTTP endpoint is `/mcp`,
and the unauthenticated liveness endpoint is `/health`.

Required production settings:

- `INTEL_APP_CONTROL_URL`: service-authenticated Intel Agent app base URL.
- `INTEL_APP_SERVICE_TOKEN`: shared service credential stored only in Render secrets.
- `MCP_ENGINE_SOURCE`: `database` in production; `http` is retained only as a reversible cutover fallback.
- `MCP_ENGINE_DATABASE_HOST`, `MCP_ENGINE_DATABASE_PORT`, `MCP_ENGINE_DATABASE_NAME`: Engine PostgreSQL endpoint coordinates.
- `MCP_ENGINE_DATABASE_USER`: must be exactly `intel_mcp_reader_v1`; the service rejects owner or broader logins.
- `MCP_ENGINE_DATABASE_PASSWORD`: separate long reader password provisioned by the Engine migration tooling.
- `MCP_ENGINE_DATABASE_SSLMODE`: defaults to `require`.
- `INTEL_ENGINE_API_URL` and `INTEL_ENGINE_SERVICE_TOKEN`: temporary authenticated HTTP rollback path; do not reuse the extraction run token.
- `MCP_INBOUND_SERVICE_TOKEN`: private server-to-server bearer retained for the Intel Agent backend.
- `REPORT_PLAN_SERVICE_TOKEN`: separate private bearer used only by the App's Report-plan endpoint.
- `MCP_PUBLIC_RESOURCE_URL`: canonical OAuth protected-resource audience for `/mcp`.
- `MCP_OAUTH_AUTHORIZATION_SERVER_URL`: Intel Agent account authorization-server issuer.
- `MCP_ALLOWED_HOSTS`: comma-separated exact public/private Host allowlist entries.
- `PORT`: HTTP port assigned by the platform.

`/mcp` accepts either the private internal service bearer or a scoped public OAuth access token issued by Intel Agent. Public clients discover OAuth through RFC 9728 protected-resource metadata; internal service credentials are never used as end-user tokens.

The private `POST /internal/report-plan` route accepts only
`REPORT_PLAN_SERVICE_TOKEN`. It sends the user's brief, requested insights and the
versioned description of all six MCP capabilities to `gpt-5.6-terra`, and returns only
the strict user-facing Report-plan structure. It is not an MCP tool and does not execute
clinical-data operations.

## Engine read isolation

The five clinical reads (`filter_trials`, classification profiles, complete/profile-section reads,
document text and extraction source) run inside MCP to remove a cold-starting Engine
web hop. Engine still owns ingestion, extraction, profile generation, approval, queues,
schema migrations and all writes. PostgreSQL enforces the split: the MCP role can select
only `mcp_serving.*_v1`, every MCP checkout begins `SET TRANSACTION READ ONLY`, and MCP
startup rejects any database URL whose username is not the restricted role. See
`docs/ENGINE_READ_CUTOVER.md` for the staged rollout and one-variable rollback.
