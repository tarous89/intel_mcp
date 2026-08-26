# Intel MCP

Remote Model Context Protocol service for TrialAgents Intel Agent.

Implemented tools:

- `start_analysis` receives only an app-created `report_run_id`, calls the Intel Agent app's service-authenticated control plane, and returns the existing or newly reserved 60-minute analysis lease.
- `filter_trials` deterministically queries approved structured Trial Profiles through the Intel Engine's versioned internal endpoint. It then asks the app control plane to validate the `analysis_id` and atomically meter the unique trial IDs that may be returned.

User identity, plan approval, package, enabled tools and allowances remain app-owned. MCP has no application or clinical database credentials.

## `filter_trials` contract

`filter_trials` is a shortlist tool. It does not search the whole profile, run semantic search, classify trials, retrieve complete profiles/documents, extract variables or write report prose.

General behavior:

- Only `approval_status = approved` Trial Profiles are eligible.
- All text comparisons are case-insensitive.
- `contains` is the default text operator; `is` means a complete case-insensitive match.
- Negative text operators are `does_not_contain` and `is_not`. A missing value never satisfies a negative filter.
- Controlled-array operators are `contains_any`, `contains_all` and `contains_none`.
- Different fields combine with AND. Put multiple alternatives for the same field in one condition. If OR is needed across different fields, make separate calls.
- Conditions within one `countries` group must match the same country row. Multiple country groups combine with AND and may match different rows.
- Default order is `latest_country_submission_or_approval_date desc`, with `eu_number asc` as the stable tie-breaker.
- Pages are capped at 100. Continue only with the opaque `next_cursor` returned for identical filters and sort.
- Light analyses may receive 100 unique filtered trial IDs; Max analyses may receive 1,000. Repeated IDs in retries or revisions do not consume allowance twice.
- The MCP annotation uses `readOnlyHint: false`: the Engine query is read-only, but admitting a previously unseen trial ID updates the analysis's observable allowance state.

Exposed structured fields:

- Text: `eu_number`, `trial_title`, `trial_acronym`, `sponsor_name`.
- Dates: latest country submission/approval, initial CTIS submission, first CTIS authorization and latest CTIS authorization.
- Document availability: normalized extracted document types and individual document names.
- Controlled arrays: therapeutic areas, phases, modalities, administration routes, country codes, eligible sexes and comparator types.
- Booleans: rare-disease, orphan-designation, paediatric and first-in-human flags. Boolean values may also be checked for `unknown`.
- Numbers: planned sample size, number of countries and number of sites.
- Controlled scalars: allocation, masking and intervention model.
- Same-country fields: country code, normalized recruitment status, country dates, country site count and country planned sample size.

Controlled vocabularies are embedded directly in the MCP JSON Schema. Country codes use ISO 3166-1 alpha-2. Known normalized country statuses are `Authorised`, `Not authorised`, `Under evaluation`, `Ended`, `Halted`, `Lapsed`, `Withdrawn`, `Expired`, `Suspended`, `Not valid`, `Pending` and `Revoked`.

Sponsor-name limitation: the structured CTIS sponsor value can sometimes refer to a subsidy or funding source, or omit part of the complete legal entity name. Use sponsor-name filtering to shortlist records; do not treat it as definitive legal-entity resolution.

## Local setup

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
export INTEL_APP_CONTROL_URL=http://localhost:3000
export INTEL_APP_SERVICE_TOKEN=replace-me
export INTEL_ENGINE_API_URL=http://localhost:10000
export INTEL_ENGINE_SERVICE_TOKEN=replace-with-a-separate-engine-service-token
export MCP_INBOUND_SERVICE_TOKEN=replace-me-too
intel-mcp
```

The Streamable HTTP endpoint is `/mcp`; the unauthenticated liveness endpoint is `/health`.

Required production settings:

- `INTEL_APP_CONTROL_URL`: service-authenticated Intel Agent app base URL.
- `INTEL_APP_SERVICE_TOKEN`: shared service credential stored only in Render secrets.
- `INTEL_ENGINE_API_URL`: Intel Engine Trial Profile service base URL.
- `INTEL_ENGINE_SERVICE_TOKEN`: dedicated MCP-to-Engine credential; do not reuse the extraction run token.
- `MCP_INBOUND_SERVICE_TOKEN`: bearer credential required on every request to `/mcp`.
- `MCP_ALLOWED_HOSTS`: comma-separated exact public/private Host allowlist entries.
- `PORT`: HTTP port assigned by the platform.

The initial free Render deployment is public at the network layer but `/mcp` is closed to callers without the internal service bearer. Public OAuth is a later profile and must not reuse the internal service credential as end-user authentication.
