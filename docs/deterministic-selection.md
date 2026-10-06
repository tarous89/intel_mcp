# Deterministic selection tools (backend pilot)

This opt-in extension ranks CROs/providers, sites and principal investigators using existing approved Trial Profile 11 evidence. It performs no LLM requests. See [implementation log](SELECTION_IMPLEMENTATION_LOG.md) for validation, decisions, iterations and rollout gates.

## Enable and authenticate

Set `MCP_SELECTION_ENABLED=true` on a staging/pilot MCP deployment configured with `MCP_ENGINE_SOURCE=database` and the existing `intel_mcp_reader_v1` login. Use normal TrialAgents OAuth. The tools require an existing analysis lease with `filter_trials` and `get_profiles` permissions; they do not create a ChatGPT-native session. Leave the flag false in production until live validation.

## Request sequence

1. `get_selection_catalogue()` describes supported fields and function codes.
2. Call `search_trial_cohort` with the analysis ID and criteria below.
3. Call `rank_entities` with the same analysis ID, unchanged criteria and returned `expected_snapshot`; `limit` defaults to 10 (maximum 10).
4. Call `get_entity_evidence` with those same fields plus `entity_id`. `offset` starts at 0; `limit` is 1–10. Optional `sections` uses the existing `get_profiles` section vocabulary and exact projections.

Example criteria (illustrative, not a claim about available matches):

```json
{
  "entity_type": "cros",
  "base": {"therapeutic_areas": {"values": ["Solid Tumor Oncology"]}},
  "direct": {
    "diseases": {"values": ["non-small cell lung cancer"]},
    "phase": {"values": [2]},
    "modalities": {"values": ["Monoclonal antibody"]}
  },
  "related": {"diseases": {"values": ["lung cancer"]}},
  "function_code": 1,
  "entity_countries": [],
  "include_broader": false,
  "as_of": "2026-10-06"
}
```

Base filters are mandatory. Direct/related are additional trial predicates inside that base, not independent databases or samples. Alternatives inside a field follow the existing set operator; different fields combine with AND. Related matches exclude direct matches. `include_broader` adds remaining base trials. No disease synonym or semantic inference is performed. If the base exceeds a safety/allowance limit, refine it explicitly; no top ten is returned from a partial cohort.

`entity_countries` refers to a CRO's registered country or recorded site/PI affiliation. Trial `country_codes` refers to trial participation. Neither proves that a CRO performed a particular function in every trial country.

## Evidence and ranking

Results include disjoint distinct-trial counts, provider functions, organization types, PI recorded affiliations, sponsor co-occurrence, six-month authorization recency, supporting EU trial references, profile hashes and trial-level operational findings. General provider rankings include laboratories/vendors, not only full-service CROs.

Rank order: direct experience, related experience, recent authorization count, broader experience, name and ID. Each requested CRO function is verified per trial. Co-occurring functions remain visible for those qualifying trials. Operational findings are never converted into a provider quality score. Unknown functions do not satisfy a requested known function.

No hidden five-year window is applied; use explicit date filters. No present-day recruitment capacity or site performance is inferred from authorization recency. PI identity reuses existing conservative normalization but same-name/therapeutic-area merging still needs quality review.

The snapshot is a SHA-256 fingerprint of version, criteria and complete returned source content. It detects changes across calls; it does not persist old data. Changed source/criteria requires a new search. Evidence sections come from the same freshly verified source content, not separate unbound profile reads.

## Costs, limits and errors

- Zero backend LLM calls. Existing ingestion/profile-generation costs are unchanged.
- Maximum 500 base profiles, 16 MiB serialized cohort, 10 ranked results, 10 evidence trials per call. Overflow fails explicitly.
- Existing App filter/profile allowances apply to every base profile. Authorization can require many calls (up to 5 filter and 50 profile batches, plus preflight/revalidation). Larger cohorts need a later atomic admission endpoint and indexed/durable preparation.
- No persistent selection storage or results cache; each request rereads the bounded cohort.
- `SELECTION_ALLOWANCE_INSUFFICIENT`: no partial results; already admitted IDs remain metered by existing App APIs.
- `SELECTION_CHANGED`: repeat search and use the new fingerprint.
- `AMBIGUOUS_PROFILE`, `UNSUPPORTED_PROFILE`: correct source inconsistency/schema before returning recommendations.
- `COHORT_TOO_LARGE`, `COHORT_BYTES_EXCEEDED`: narrow base criteria; never interpret these as no matching entities.
- `SELECTION_DATABASE_REQUIRED`: HTTP compatibility reader is intentionally unsupported for this pilot.

Tools remain disabled by default. Code tests do not establish live coverage, latency, ranking quality, or production readiness.

### Live validation status

Read-only aggregate validation confirmed profile/filter alignment and expected schema structure. Actual restricted-login execution, full workflow performance and clinical review remain rollout gates. The serialized-record size limit applies after lifecycle projection and does not bound raw SQL transfer; compact lifecycle/source projection must be evaluated before production scale. Broad cohorts may require narrower filters. Missing provider evidence does not establish absence of participation.

### Revised population policy

The owner requested all profiled studies, including deterministic-only studies. Engine migration 047 makes each study available through one current approved profile while preserving duplicate versions and enrichment provenance. Existing view names remain compatible. Deploy that migration before claiming all-trial coverage; migration deployment and restricted-login verification are pending. The 500-trial per-query cap still requires narrowing and never samples. Selection reads now stream ten raw profiles per batch; total transfer volume is unchanged.
