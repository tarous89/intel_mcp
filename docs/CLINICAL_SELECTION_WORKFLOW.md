# Clinical selection workflow requirements

Updated 2026-10-06. Owner-requested product direction; implementation status is tracked in SELECTION_IMPLEMENTATION_LOG.md. This is a workflow specification, not an installed ChatGPT workflow or a claim that all required tools exist.

## First response: broad relevant landscape, then depth

- Present a useful landscape on the first query, with visible relevance subgroups and an evidence-backed shortlist.
- Recommended working target: approximately 200–500 distinct relevant trials when coverage supports it. Treat 100–199 as useful coverage, not failure; return fewer when clinically appropriate. These are discovery targets, never quotas.
- Preserve the user's exact brief as the highest-relevance subgroup. Build an explicit expansion ladder: exact population and phase → same disease across phases/settings → related disease family → adjacent therapeutic area where transferable experience is justified.
- Example: phase III metastatic hormone-sensitive prostate cancer → other prostate cancer trials → selected genitourinary oncology populations such as bladder/urothelial or renal cancer. Do not include benign urology merely to increase volume.
- Rare haematological malignancy queries may expand to appropriate related malignancies, but relevance depends on disease biology, intervention, procedures and entity type. Never treat all blood cancers as equivalent.
- Geography, modality, population and phase can be binding constraints or preferences. Respect explicit hard requirements; show relaxed preferences and use outside-scope evidence only as clearly labelled context.
- Broad experience is often more transferable for CRO operational functions than for PI/site clinical expertise. Use different relevance treatment for each entity type.
- Count candidate groups before retrieving large profiles. Stop expansion when coverage is sufficient or the next group adds little defensible relevance.
- Current execution cap remains 500 base profiles and 16 MiB processed records. Broad candidate counts can exceed this, but ranking must not silently use the first 500 or a sample. Narrow transparently or implement complete-cohort indexed aggregation before expanding the cap.
- Multiple discovery branches may overlap. Deduplicate trial identities, assign a primary mutually exclusive relevance group for additive counts, and retain secondary tags for cross-cutting analyses.

## Search beyond structured fields

- Search structured fields plus titles/acronyms and supported profile text sections. Empty phase/therapeutic-area/disease fields are unknown, not negative evidence.
- Stage retrieval: lightweight candidate IDs/titles/counts → selected eligibility/population/design sections for ambiguous cases → supporting documents only when needed and available.
- Preserve exact search expressions, synonyms, filters, field scope, relaxed constraints, unresolved candidates, source section and evidence basis for every match decision.
- Distinguish structured values, explicit text evidence, and interpretation; retain contradictions for review rather than silently overwriting a source.
- The prostate preview proved operator-side title and eligibility retrieval is feasible. Public MCP needs a tested fallback path; the current mandatory positive therapeutic-area filter cannot exclude records solely because their structured area is missing.
- Keep matching/group assignment auditable. ChatGPT may interpret returned passages; membership and counts must then be validated and bound to a reproducible cohort on the server.
- No backend LLM calls are required for retrieval, counting, entity aggregation or ranking. Interpreted clinical equivalence is not a deterministic database fact.

## Normalize before counting and ranking

- CROs: default display by verified corporate group, with legal entities, country, recorded role and historical identity available underneath. Collapse known subsidiaries/aliases of IQVIA, Syneos, ICON/PRA, etc. only using a reviewed identity mapping with provenance and temporal context; naming here is not a complete or verified acquisition map.
- Corporate-group experience counts the union of trial IDs, never the sum of subsidiary counts. Apply function restrictions at the trial/legal-entity evidence level before corporate rollup.
- Sites: reconcile spelling, language and historical aliases for the same institution/campus. Do not silently merge separate campuses or hospital-network members into one physical site; expose both institution and campus levels where supported.
- PIs: normalize spelling/diacritics/name order and consolidate supported identities using multiple identifiers and recorded affiliations. A shared name or shared departmental email alone is insufficient. Retain uncertainty and historical affiliations.
- Correct duplicate site-block/person-record collisions and add regressions before public enablement.
- Expose identity IDs, aliases, merge basis and unresolved cases so users can inspect the counts.

## Default presentation

Recommended default, resolving the owner's five-versus-ten discussion: top five CRO groups, five sites and five PIs in compact tables; offer top ten or full authorized lists on request. The tool may continue to support limits up to ten.

Always show:
1. Exact brief and actual search/expansion scope.
2. Distinct trial count, subgroup counts and evidence/coverage limitations.
3. Distinct normalized CRO/provider, site and PI counts; distinguish provider types/functions.
4. Three ranked tables with counts by relevance subgroup and a concise reason/evidence reference per entry.
5. Available next actions relevant to this dataset.

Prefer tables for the first answer. Offer a report/export after the initial useful answer; do not force a format question before providing results. Charts are optional for distributions, country coverage or comparisons, not a replacement for inspectable tables.

Never present all third-party providers as full-service CROs. Offer a general provider landscape plus explicit operational/function-based shortlists. Do not silently choose monitoring as the sole definition of a CRO.

## Ranking and drill-down

- Prioritize direct evidence over adjacent volume. A large broad cohort must not overwhelm strong exact-match experience.
- Current rank version uses direct count, related count, recent authorization, broader count and stable tie-breaks. More subgroup levels and corporate normalization require a new documented ranking version; do not imply the current version already implements this workflow.
- Show the date basis for recency; regulatory authorization is not recruitment capacity.
- Sponsor co-occurrence is descriptive, not proof of a contract. Trial findings are not provider performance unless attribution is supported.
- Offer concrete follow-ups: restrict to a subgroup; compare phases/modalities; filter countries; rank CROs by function; compare candidate evidence; inspect supporting trials; explore sponsor co-occurrence; retrieve operational findings; inspect PI affiliations or authorized contact availability; export a report.
- Only offer data actually present or mark it unavailable. No recruitment-speed, quality, capacity or contact-completeness claims without supporting records.
- Drill-down should retain the cohort/group identities and source fingerprint, support subset combinations with deduplication, and explain any re-ranking or source change.

## Implementation order and ownership

1. MCP/Engine: fix missing-field discovery and section retrieval with provenance; correct duplicate entity handling.
2. Data/Engine: reviewed corporate/site/PI identity mappings and union-based experience aggregation.
3. MCP: lightweight count/discovery tools, subgroup membership and subset ranking contracts, compact evidence payloads, full-cohort authorization and performance tests.
4. Validate broad-to-narrow examples for prostate cancer and a rare haematological indication, including no-padding and >500 overflow cases.
5. ChatGPT workflow: expansion policy, top-five tables and contextual follow-up options.
6. Packaging/description after validation: describe capabilities accurately and avoid unsupported coverage promises.

Proposed description for later packaging: “Find CROs, investigators and trial sites using recorded clinical-trial experience. Explore a relevant trial landscape, compare evidence-backed shortlists, and drill into diseases, phases, countries and provider functions.”

Keep tools disabled until existing enablement gates pass. This document records agreed direction and recommendations; it does not enable or deploy these capabilities.
