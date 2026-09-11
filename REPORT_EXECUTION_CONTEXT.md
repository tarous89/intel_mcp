# Intel MCP — Report Execution Current Context

Last updated: 2026-09-11

This is the source of truth for report planning and Light/Max execution. Light remains capped at 20 analyzed trials. Max screens a broad candidate pool and freezes at most 100 approved Trial Profiles for report analysis.

## Report-plan v4

Planning uses `gpt-5.6-sol`, medium reasoning, strict structured output and no MCP tools. New/revised plans are v4; stored v2/v3 plans remain compatible.

### Trial groups

Every v4 plan has one shared Light + Max group and 2–4 Max-only groups. The shared group uses exactly one supported dimension:

```text
disease | therapeutic_area | phase | modality | country
```

Disease is backed by persisted approved Trial Profile disease names. Stage, biomarker, subtype, line of therapy, treatment setting and multi-dimension combinations belong to Max-only groups.

Every group also contains backend-only execution metadata: one supported high-recall `discoveryFilter` plus stable `selectionSegments` with unique keys and literal inclusion/exclusion criteria. Stored v4 plans without this metadata remain usable for Light but must be regenerated before Max execution.

### Analysis pairs

Every plan has 1–7 request-aligned pairs, each containing one shared analysis and one deeper Max analysis. Each distinct user-requested decision or output maps to one pair; closely related considerations stay inside that pair as details. There is no user-facing Objectives layer.

Shared titles normally begin with direct evidence verbs such as `List`, `Name`, `Count`, `Rank`, `Report`, `Calculate`, `Summarize`, `Show`, `Compare` or `Collect`. Max titles normally begin with decision verbs such as `Analyze`, `Assess`, `Evaluate`, `Prioritize`, `Recommend`, `Estimate`, `Determine`, `Identify`, `Match` or `Synthesize`.

Question titles, hard-coded result breadth and generic labels such as `strategy fit`, `benchmark fit`, `best fitting` and `operational fit` are rejected. Max must add at least two genuine decision factors rather than restating the shared analysis.

Every planned analysis must be medical, clinical-development or trial-operational. Database coverage, data completeness, missingness, field availability, documentation rates and “how many trials reported a field” are prohibited. When evidence cannot support the requested method or precision, the planner uses the closest supported medical method that still answers the same requested decision.

Step 1 suggested analyses do not include planned sample size versus actual enrollment.

## Light projection and cohort

Light receives only:

- the shared single-dimension trial group;
- all 1–7 request-aligned shared analyses;
- no Max group or Max analysis for execution.

The paired Max card is passed only to the objective writer after the Light result exists, solely to create upgrade copy.

Sol/high/Flex screens up to 100 approved profiles using `filter_trials` and `get_profiles`, then selects exactly 20. All shared evidence needs influence selection. MCP freezes and retrieves the same 20 complete profiles in two calls of 10; every shared analysis receives that identical bundle.

## Objective analysis

Each shared analysis runs independently with `gpt-5.6-terra`, high reasoning, Flex and no tools.

Required behavior:

- answer the approved medical/clinical/operational question using the available 20-profile evidence;
- substitute a supported medical calculation, comparison, ranking or pattern when the requested lens is unsupported;
- never return database coverage/completeness commentary, missing-field analysis, reporting-subset counts or documentation-rate analysis;
- return an empty legacy `limitations` array;
- preserve evidence-linked findings and deterministic investigator-role handling.

A deterministic content gate retries one violating draft with an explicit medical-substitution instruction. If the corrected draft still violates the rule, the section fails safely and is not returned.

After a valid Light result, the same objective writer generates exactly two objective-specific sentences:

1. `This report is limited to …`
2. `Upgrade to Max to …`

The copy may describe future Max value across up to 100 Trial Profiles but must not claim Max work or outcomes already exist.

## Final report

Sol/high/Flex final synthesis writes only the title, short introduction and closing note. It does not rewrite sections or upgrade copy.

The App is responsible for presentation:

- the only database/evidence-base mention appears once, directly after the title and introduction;
- that band states the overall number of trials analyzed and a high-level selection description;
- no per-objective completeness, coverage or “N of 20 reported” messaging is shown;
- per-analysis decision-implication blocks are replaced by the two upgrade sentences;
- completed output remains `final_report.version = 2` for renderer compatibility.

Prompt/schema names:

```text
planner:   intel_agent_report_plan_v4
selection: intel_light_trial_selection_v5
analysis:  intel_light_objective_v8
synthesis: intel_light_synthesis_v5
```

## Max execution v1

### Hard limits

- target 500 compact candidate profiles after deterministic discovery, with a hard 1,000-ID discovery ceiling;
- 100 unique trials in the final frozen report-wide cohort;
- 10 complete, untruncated, group-stratified profile examples for the SAP;
- 20 total non-deterministic profile variables, including Boolean segment membership;
- no protocol or source-document extraction;
- one profile-only semantic extraction call per selected trial;
- 1–7 objective analyst calls and one reducer call.

Candidate-filter planning and compact-profile screening use Sol/medium/Flex. SAP, final profile extraction, objective analysis and reduction use Terra/high/Flex. The shared report planner remains Sol/medium and is not constrained to deterministic screening fields.

### Stages

1. Preserve every approved group's existing discovery filter as an exact seed, then have a report-start candidate planner create an ordered focused-to-broad progression using only reliable `therapeutic_areas`, `phase`, `modalities` and `country_codes` fields. Disease remains a seed rather than the sole recall gate.
2. Execute the seed and broad filters in bounded round-robin pages, deduplicate and stop at the 500-candidate target or when the available approved pool is exhausted.
3. Load only compact `overview`, `population`, `trial_design` and `interventions` projections for candidates. Sol screens them in batches of 25 against the approved rich disease, biomarker, treatment-setting and population segments, assigning `exact`, `close`, `adjacent` or `exclude` without changing any approved analysis.
4. Select at most 100 non-excluded profiles deterministically while reserving representation for planned adjacent groups. Reload those selected profiles completely and classify every planned segment from the full profile during final extraction.
5. Build one SAP from the approved brief/plan, an ephemeral catalogue of short fields across every selected profile and up to 10 whole profile examples. Deterministic fields are preferred; narrative interpretation uses the remaining semantic-variable budget. Trial Profile 11 investigators are exposed as one deterministic entity list per trial so names remain aligned with site, country, department and public email; every listed person is a PI by contract.
6. Populate one frozen row dataset. Deterministic values are resolved directly; all semantic values for a trial are extracted together from its complete approved Trial Profile. Up to 10 extraction requests run concurrently.
7. Run one analyst per main analysis pair, then one reducer over the completed sections and cohort summary. Analysts receive only planned variables and the frozen selected dataset; no new report objectives are introduced.

SAP semantic-variable instructions target 500 compact characters. The executor normalizes whitespace and deterministically bounds any model-produced overrun to the extractor's 600-character contract while preserving both the extraction task and trailing return/missing-value guidance. An overlong instruction therefore cannot stop an otherwise valid paid run.

Output stays compatible with the shared App/PDF renderer:

```text
final_report.version = 2
final_report.tier = max
```

`analyzedCohort` may also carry the screened-candidate count and selected `exact`/`close`/`adjacent` composition. Existing renderers ignore unknown fields, so the version-2 output contract remains backward compatible.

### Control-plane boundary

The private `/internal/max-report/start` route launches Max. Its six-hour lease excludes `get_documents`, zeros document allowances, authorizes up to 1,000 filtered IDs, 500 profiles and 500 screening classifications, and keeps final extraction at 100 trials. Leases capped at 100 by an older App deployment automatically use the legacy bounded workflow. Once an expanded lease is issued, candidate-stage failures stop the run for safe retry rather than silently falling back to a smaller cohort. Successful completion consumes the reserved entitlement; system failure leaves it unconsumed.

## Runtime boundary

The App creates and owns report runs, plan approval, tier, entitlement and progress state. MCP executes through service-authenticated internal endpoints. Light and Max still use an in-process async launcher and can be interrupted by a service restart; durable claim/heartbeat/retry execution remains pending.
