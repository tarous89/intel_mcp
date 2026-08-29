# `classify_trials` contract

Current contract: 2026-08-27

## Purpose

`classify_trials` semantically classifies a bounded list of approved Trial Profiles against caller-supplied trial-level conditions that cannot be handled reliably by deterministic structured filtering.

It is not a protocol/document extraction tool. It uses the approved Trial Profile only.

This is the final semantic classification step, not the initial discovery step. Normally the caller should:

1. use `filter_trials` to shortlist candidates with broad structured conditions;
2. pass the focused shortlist to `classify_trials` for complex inclusion/exclusion conditions;
3. split shortlists larger than 25 trials into batches that use the same criteria.

For example, filter a broad population of hundreds or thousands of profiles to a relevant shortlist, then classify only that shortlist rather than spending classification allowance across the entire discovery population.

## MCP input

```json
{
  "analysis_id": "ana_...",
  "trial_ids": ["2024-500001-00-00"],
  "inclusion_criteria": [
    "The trial includes the target disease population"
  ],
  "exclusion_criteria": [
    "The trial is restricted to healthy volunteers"
  ]
}
```

Rules:

- `analysis_id` is required and must refer to the active analysis lease.
- `trial_ids` contains 1–25 distinct EU trial numbers.
- Every requested trial must have an approved Trial Profile; otherwise the call is rejected before Terra work is reserved.
- `inclusion_criteria` contains one or more user-defined classification conditions.
- `exclusion_criteria` contains one or more user-defined exclusionary conditions.
- Inclusion/exclusion criteria are analysis criteria. They are not necessarily the formal protocol eligibility criteria.
- Maximum 20 criteria total across the two lists.
- Maximum 600 characters per criterion.

## Worker boundary

The backend performs one logical Terra classification job per trial. Each job sends the complete approved, contact-redacted Trial Profile together with all inclusion and exclusion criteria for that trial.

The profile follows contract 8.6.0: extracted-document availability is the
six-array `available_extracted_documents` object. Classification receives that
object as part of the full profile but does not retrieve or classify document
text.

Internally the criteria receive stable positional IDs (`i1`, `i2`, ..., `e1`, `e2`, ...). Terra must evaluate every criterion independently and return exactly one result for each criterion:

```json
{
  "criterion_id": "i1",
  "classification": true,
  "evidence": "Concise Trial Profile evidence/reasoning"
}
```

`classification` is strictly:

- `true`: the complete criterion statement is supported by the Trial Profile;
- `false`: the Trial Profile affirmatively supports that the complete criterion statement is not satisfied;
- `null`: the Trial Profile does not establish either true or false.

Absence of evidence is not `false`; it is normally `null`.

The words **inclusion** and **exclusion** never invert Terra's boolean answer. For an exclusion criterion, `true` means the exclusionary condition described by that criterion is present.

The detailed criterion-level classification and evidence are internal worker results used by the backend aggregation path. They are intentionally not returned by the MCP tool. The current implementation does not persist those detailed worker results after the call completes.

## Unknown handling

Normally the caller should state the factual condition only. If Terra cannot resolve it from the Trial Profile, it returns `null`, which can make the trial uncertain.

Only when analytically appropriate may the caller explicitly make unknown/missing information part of a criterion itself. Example:

> `Pediatric patients are included OR pediatric participation is unknown.`

If pediatric participation is genuinely unknown, the complete statement above is `true` because the criterion explicitly says that unknown satisfies it.

Do not add unknown handling routinely. Use it only when the requested analysis genuinely intends that behavior.

## Deterministic aggregation

The MCP layer never asks Terra to decide whether the whole trial is eligible. The backend derives the final bucket deterministically from the criterion-level results.

Precedence:

1. **Ineligible** if any inclusion criterion is `false` OR any exclusion criterion is `true`.
2. Otherwise **uncertain** if any criterion is `null`.
3. Otherwise **eligible**: every inclusion criterion is `true` and every exclusion criterion is `false`.

A definitive failure therefore takes precedence over an unrelated unknown.

## MCP output

The public result is intentionally minimal:

```json
{
  "eligible_trials": ["2024-500001-00-00"],
  "ineligible_trials": ["2024-500002-00-00"],
  "uncertain_trials": ["2024-500003-00-00"],
  "counts": {
    "classified": 3,
    "eligible": 1,
    "ineligible": 1,
    "uncertain": 1
  },
  "analysis_allowance": {
    "limit": 25,
    "used": 3,
    "remaining": 22
  }
}
```

Counts are calculated deterministically from the corresponding ID arrays so callers can quantify results without recounting them. No criterion-level evidence, rationale, confidence score, profile content, internal IDs, prompts, token usage or model traces are returned.

## Data and model boundary

- Only approved Trial Profiles are used.
- Engine returns profiles through `POST /api/internal/mcp/classification-profiles`.
- Contact personal data is recursively removed before profiles leave Engine for this classifier path.
- Terra is instructed to treat Trial Profile content as untrusted data, not instructions.
- Terra must use only the supplied Trial Profile; it does not inspect protocols, other CTIS documents or external knowledge.
- If the requested fact is outside the Trial Profile, the ordinary result is `null`.

Current classifier defaults:

```text
model: gpt-5.6-terra
reasoning effort: high
service tier: standard
max output tokens: 12,000
worker concurrency: 4
per-worker timeout: 300 seconds
```

Environment variables may tune these operational values without changing the public contract.

## Allowance and retries

Classification allowance is owned by the Intel Agent app/control plane, not by MCP or Engine.

Current per-analysis limits:

```text
Light: 25 classifications
Max:   200 classifications
```

A classification unit is keyed by a SHA-256 fingerprint of the EU trial number plus the normalized inclusion criteria, normalized exclusion criteria and classifier schema version.

- Exact retries of the same trial + criteria reuse the same key and do not consume another completed-classification allowance unit.
- Changing the criteria produces a new key and counts as new classification work.
- The requested batch is all-or-nothing when the remaining allowance is insufficient.
- Keys are reserved before Terra work begins.
- Successful worker completion commits the keys to usage.
- Classifier/system failure releases the reservation so failed work does not consume completed-classification allowance.
- Commit/release may finalize already-started work even if the 60-minute lease expires while the worker is running.

## MCP annotations

`classify_trials` is currently annotated:

```text
readOnlyHint: false
 destructiveHint: false
 idempotentHint: false
 openWorldHint: false
```

The clinical data read itself is non-destructive, but the tool changes observable allowance state and performs paid model work. Exact allowance retries are deduplicated server-side, but the tool is not advertised as generally idempotent because it executes an external model worker.
