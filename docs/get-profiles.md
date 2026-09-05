# `get_profiles` contract

## Purpose

Return current approved Trial Profile 10.0.0 data for explicit EU trial numbers. The tool is a bounded deterministic read path: it performs no model work, summarization, semantic search or profile generation.

`get_profiles` has two modes:

- **Section mode** — request one or more named profile sections and retrieve up to **100** profiles in one call.
- **Complete-profile mode** — omit `sections` or pass `[]` and retrieve up to **20** complete profiles in one call.

Use section mode when comparing a larger shortlist. Use complete-profile mode only when the task genuinely needs the whole structured profile.

## Input

### Section mode

```json
{
  "analysis_id": "ana_...",
  "trial_ids": [
    "2024-500001-00-00",
    "2024-500002-00-00"
  ],
  "sections": ["overview", "trial_design", "endpoints", "countries"]
}
```

### Complete-profile mode

```json
{
  "analysis_id": "ana_...",
  "trial_ids": ["2024-500001-00-00"]
}
```

- `analysis_id`: active 60-minute analysis lease.
- `trial_ids`: 1–100 syntactically valid EU trial numbers in section mode; 1–20 unique EU trial numbers in complete-profile mode.
- Duplicate IDs are removed while preserving first occurrence order.
- `sections`: optional array of the controlled section names below. Duplicate section names are removed while preserving caller order.
- Omitting `sections` and passing `sections: []` are equivalent: both request complete profiles.

If a caller requests more than 20 unique IDs without sections, the tool returns `PROFILE_REQUEST_TOO_LARGE` rather than silently projecting or truncating profiles.

## Current profile contract

The current approved Trial Profile schema is **10.0.0**. Stored profiles contain four top-level objects:

```text
filtering_variables
classification_variables
ctis_lifecycle
results
```

The `sections` field does **not** introduce a second summary schema. It is an exact deterministic projection over those stored objects. Values are copied as stored and the original nesting is retained. Unrequested fields are omitted; requested fields are never summarized or rewritten.

## Section vocabulary

| Section | Trial Profile 10.0.0 fields |
|---|---|
| `overview` | therapeutic areas, phase, rare-disease/orphan/paediatric/FIH flags, trial title, acronym, diseases, classification summary |
| `population` | eligible sexes, target-population summary, disease stage/severity, treatment settings, population characteristics, biomarkers |
| `trial_design` | planned sample size, allocation, masking, intervention model, comparator types |
| `interventions` | modality, routes of administration, molecular targets, mechanisms of action, interventional and non-interventional products |
| `eligibility` | inclusion criteria, exclusion criteria |
| `objectives` | primary objectives, secondary objectives |
| `endpoints` | structured endpoints |
| `sponsor_and_organizations` | sponsor, legal representative, third-party organizations |
| `contacts` | trial management, scientific, recruitment and public CTIS contacts |
| `countries` | country codes, number of countries, structured country records |
| `sites` | number of sites, structured site records and nested site contacts |
| `documents` | `filtering_variables.available_extracted_documents` with the exact document names accepted by `get_documents` |
| `lifecycle` | complete `ctis_lifecycle` object, including dated overall and country updates |
| `results` | complete `results` object, including participant flow, country enrollment, endpoint/safety results and operational findings |

The mapping is versioned against Trial Profile 10.0.0. Older approved profiles may naturally lack fields that were introduced later; absent stored fields are simply absent from the projection.

## Projection examples

Request:

```json
{
  "analysis_id": "ana_...",
  "trial_ids": ["2024-500001-00-00"],
  "sections": ["overview", "endpoints"]
}
```

Representative shape:

```json
{
  "profiles": [
    {
      "eu_number": "2024-500001-00-00",
      "profile_schema_version": "10.0.0",
      "approved_at": "2026-08-27T12:00:00+00:00",
      "profile": {
        "filtering_variables": {
          "therapeutic_areas": ["Solid Tumor Oncology"],
          "phase": [3]
        },
        "classification_variables": {
          "trial_title": "...",
          "diseases": ["..."],
          "endpoints": []
        }
      }
    }
  ]
}
```

This is a projection of the stored profile, not a generated card or model summary.

## Data boundary

Production MCP reads from the Engine-owned approved-only `mcp_serving` PostgreSQL contract using the restricted MCP reader. Projection is applied inside MCP **after** the approved-only read and after app control-plane authorization.

The legacy Engine HTTP rollback endpoint remains unchanged at ten IDs per request. If MCP is switched back to that path, a larger `get_profiles` request is split internally into batches of ten and reassembled in caller order. The public MCP contract therefore remains the same in both production and rollback modes.

Missing, candidate and rejected records are indistinguishable to the MCP caller and appear only in `unavailable_trial_ids`. There is no raw CTIS fallback.

## Allowance

The app control plane meters unique successfully returned EU trial numbers through:

```text
POST /api/internal/mcp/profile-access
```

Current intended per-analysis limits are:

- **Light: 100 unique profiles**
- **Max: 500 unique profiles**

Repeated retrieval of the same trial ID does not consume allowance again, even when different sections are requested later. Missing/unapproved profiles are never metered.

The profile allowance counts profile IDs, not sections. A section-projected read and a later full read of the same trial therefore count as one unique profile against the analysis allowance.

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
    "limit": 100,
    "used": 0,
    "remaining": 100
  }
}
```

Every returned profile item contains:

- `eu_number`
- `profile_schema_version`
- `approved_at`
- `profile`

In section mode, `profile` contains only the requested deterministic projection. In complete-profile mode, `profile` contains the complete approved structured profile.

## Guidance

Prefer the smallest evidence surface that can answer the decision:

1. Use `filter_trials` for broad structured screening.
2. Use `get_profiles(..., sections=[...])` to inspect the relevant profile data across a larger shortlist.
3. Use complete `get_profiles` only for the final smaller evidence set or when cross-domain profile context is necessary.
4. Use `get_documents` or `extract_variables` only when the profile is insufficient for the needed fact.

## Exclusions

The tool does not generate or refresh Trial Profiles, expose candidate/rejected state, retrieve raw CTIS fallback data or document text, classify trials, search semantically, extract variables, summarize profiles, or generate report prose.
