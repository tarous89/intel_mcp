# `extract_variables`

`extract_variables` extracts a bounded caller-defined schema from one clinical
trial in one Terra worker request.

## Input

```json
{
  "analysis_id": "ana_...",
  "trial_id": "2024-500001-00-00",
  "variables": [
    {
      "name": "planned_sample_size",
      "instruction": "Return the planned randomized population.",
      "value_type": "integer"
    },
    {
      "name": "central_imaging_review",
      "instruction": "Is central imaging review required?",
      "value_type": "boolean"
    }
  ]
}
```

- exactly one EU trial number per call;
- 1–20 uniquely named variables;
- names are lower-case `snake_case`, up to 64 characters;
- instructions are 1–600 characters after whitespace normalization;
- supported value types are `string`, `integer`, `number`, `boolean` and
  `string_array`; omitted `value_type` defaults to `string`.

## Source policy

The Engine requires a current approved Trial Profile and returns that complete
profile only. Neither the Engine compatibility endpoint nor the MCP public tool
retrieves protocol or other source-document text for variable extraction.

Terra receives the complete profile in one request. The tool never downloads,
OCRs or extracts a document on demand and does not use external knowledge.
Missing or unsupported values are `null`.

## Output

```json
{
  "trial_id": "2024-500001-00-00",
  "values": {
    "planned_sample_size": 420,
    "central_imaging_review": null
  },
  "analysis_allowance": {
    "limit": 20,
    "used": 1,
    "remaining": 19
  }
}
```

Every requested name appears exactly once. Neither the worker schema nor the MCP
result contains status, explanation, evidence, document name, page or source
metadata. No separate unresolved list is returned because `null` is sufficient.

## Allowance and failure semantics

One extraction unit is the stable SHA-256 fingerprint of the EU trial number,
normalized variable definitions and extraction schema version. Version 2.0.0
is profile-only, so its keys cannot collide with legacy protocol-backed work.
Current per-analysis limits are Light 20 and Max 100 extraction units. Exact retries do
not consume allowance twice; changed variable definitions create new work.

MCP validates the source, reserves the extraction key, makes exactly one Terra
request, then commits on success or releases on failure. There is no automatic
Terra retry, keeping synchronous tool latency bounded. The worker timeout is 300
seconds by default and is environment-configurable.

Annotations:

```text
readOnlyHint: false
destructiveHint: false
idempotentHint: false
openWorldHint: false
```
