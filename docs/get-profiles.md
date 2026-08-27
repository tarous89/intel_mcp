# `get_profiles` contract

## Purpose

Return complete current approved Trial Profiles for a small explicit set of EU trial numbers. The tool is a bounded deterministic read path; it performs no model work.

## Input

```json
{
  "analysis_id": "ana_...",
  "trial_ids": ["2024-500001-00-00"]
}
```

- `analysis_id`: active 60-minute analysis lease.
- `trial_ids`: 1–10 syntactically valid EU trial numbers.
- Duplicate IDs are removed while preserving first occurrence order.
- No projection, limit, cursor or contact flag is accepted.

## Data boundary

MCP calls the service-authenticated Engine endpoint:

```text
POST /api/internal/mcp/profiles
```

Engine returns only current `approval_status = approved` profile JSON plus the public profile schema version and approval timestamp. Missing, candidate and rejected records are indistinguishable to the MCP caller and appear only as unavailable. Contacts and extracted-document inventory remain part of the complete stored profile.

Every approved profile admitted by the analysis allowance is returned complete. The tool never truncates individual profiles.

## Allowance

The app control plane meters unique successfully returned EU trial numbers through:

```text
POST /api/internal/mcp/profile-access
```

Current per-analysis limits are Light 50 and Max 500. Repeated IDs, including later retrieval during revisions, do not consume allowance again. Profiles deferred solely for response size are not metered until returned. Missing/unapproved profiles are never metered.

## Output

```json
{
  "profiles": [],
  "unavailable_trial_ids": [],
  "allowance_reached_trial_ids": [],
  "counts": {
    "requested": 1,
    "returned": 0,
    "unavailable": 1,
    "allowance_reached": 0
  },
  "analysis_allowance": {
    "limit": 50,
    "used": 0,
    "remaining": 50
  }
}
```

Every `profiles` item contains `eu_number`, `profile_schema_version`, `approved_at` and the complete `profile` object.

## Exclusions

The tool does not generate or refresh Trial Profiles, expose candidate/rejected state, retrieve raw CTIS fallback data or document text, classify trials, search semantically, extract variables, or generate report prose.
