# `get_profiles` contract

## Purpose

Return current approved Trial Profile 10.0.0 data for explicit EU trial numbers. The tool is a bounded deterministic read path: it performs no model work, summarization, semantic search or profile generation.

Every `get_profiles` call accepts up to **10 trial IDs**, regardless of whether the caller requests selected sections or the complete profile. The per-analysis profile allowance is separate from the per-call cap: Light may retrieve up to **100 unique profiles** across calls and Max up to 500.

Use `sections` when only part of the structured profile is needed. Omit `sections` or pass `[]` when the complete profile is needed. There is no separate allowance or call-size tier for section versus complete-profile reads.

## Input

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

Complete-profile request:

```json
{
  "analysis_id": "ana_...",
  "trial_ids": ["2024-500001-00-00"]
}
```

- `analysis_id`: active 60-minute analysis lease.
- `trial_ids`: 1–10 syntactically valid EU trial numbers.
- Duplicate IDs are removed while preserving first occurrence order.
- `sections`: optional array of the controlled section names below. Duplicate section names are removed while preserving caller order.
- Omitting `sections` and passing `sections: []` are equivalent: both request complete profiles.

The only input added to the original `get_profiles` contract is optional `sections`. `analysis_id` and `trial_ids` retain their original meaning.

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

## Projection example

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

The Engine profile-read boundary is also capped at ten IDs per request. The HTTP rollback path therefore uses the same ten-profile batch size as the public MCP call.

Missing, candidate and rejected records are indistinguishable to the MCP caller and appear only in `unavailable_trial_ids`. There is no raw CTIS fallback.

## Allowance

The app control plane meters unique successfully returned EU trial numbers through:

```text
POST /api/internal/mcp/profile-access
```

Current per-analysis limits are:

- **Light: 100 unique profiles**
- **Max: 500 unique profiles**

Repeated retrieval of the same trial ID does not consume allowance again, even when different sections are requested later. Missing/unapproved profiles are never metered.

The profile allowance counts profile IDs, not sections. A section-projected read and a later full read of the same trial therefore count as one unique profile against the analysis allowance.

## Output

The output contract is unchanged from the original `get_profiles` tool:

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

Every returned profile item still contains exactly:

- `eu_number`
- `profile_schema_version`
- `approved_at`
- `profile`

When `sections` is supplied, `profile` contains the requested deterministic projection. When `sections` is omitted or empty, `profile` contains the complete approved structured profile. No output field was added, removed or renamed.

## Guidance

1. Use `filter_trials` for broad structured screening.
2. Use `get_profiles(..., sections=[...])` when only selected profile domains are needed.
3. Repeat `get_profiles` in batches of up to ten while the analysis needs additional profiles, up to the plan's unique-profile allowance.
4. Omit `sections` when the complete profile is needed.
5. Use `get_documents` or `extract_variables` only when the profile is insufficient for the needed fact.

## Exclusions

The tool does not generate or refresh Trial Profiles, expose candidate/rejected state, retrieve raw CTIS fallback data or document text, classify trials, search semantically, extract variables, summarize profiles, or generate report prose.