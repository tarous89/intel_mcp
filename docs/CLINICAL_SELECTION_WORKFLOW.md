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

## Implemented contract: selection version 2

The next implementation supports `base_text` (explicit fields, terms, any/all operator and exclusions), ordered `subgroups` (ID, label, bucket, structured filters, optional text query and optional phase title fallback), `get_cohort_trials`, and `subgroup_ids` on ranking/evidence. Default ranking limit is five. Text clauses AND with hard structured filters. To include missing therapeutic areas, omit that structured filter and supply positive disease/population text criteria.

Example discovery criteria fragment for an initial prostate landscape:

```json
{
  "base": {},
  "base_text": {
    "fields": ["title", "diseases", "population"],
    "terms": ["prostate cancer", "prostatic carcinoma"]
  },
  "subgroups": [
    {
      "id": "exact_phrase_phase3",
      "label": "Explicit mHSPC/mCSPC phrase, phase III evidence",
      "bucket": "direct",
      "filters": {"phase": {"values": [3]}},
      "phase_title_fallback": true,
      "text": {
        "fields": ["title", "population"],
        "terms": ["metastatic hormone-sensitive prostate cancer", "metastatic castration-sensitive prostate cancer", "mhspc", "mcspc"]
      }
    },
    {
      "id": "other_prostate",
      "label": "Other prostate cancer evidence; clinical review required",
      "bucket": "related",
      "text": {"fields": ["title", "diseases", "population"], "terms": ["prostate cancer", "prostatic carcinoma"]}
    }
  ],
  "include_broader": true,
  "entity_type": "cros",
  "as_of": "2026-10-06"
}
```

This is an illustrative lexical query, not a validated exhaustive clinical phenotype. Adapt explicit synonyms and inspect unresolved titles/population/eligibility. Do not label all remaining prostate studies mHSPC or equally transferable. If the landscape exceeds the cap, narrow a disclosed constraint; no partial top-five result is valid. The 200–500 target is a workflow goal, never a minimum enforced by padding.

Subgroup counts are disjoint first-match counts. `overlapping_count` and trial tags expose overlap; they are not additive. `subgroup_ids` selects the primary groups, not all overlapping tags. Reuse the same criteria/snapshot for listing, ranking and entity evidence. To rank broader groups, `include_broader` must be true in the original search. Changing criteria requires a new search/snapshot.

Corporate-group output uses a limited reviewed alias registry, with legal-entity mode available. Unmapped names remain separate. Country filters describe recorded legal entities or site affiliations, not corporate worldwide service capacity. The current historical mappings do not reconstruct acquisition timing. Site campus alias resolution remains future work.

Performance boundary: this implementation does not yet count/search a large candidate population without loading the bounded matching profiles. It makes responses compact but does not eliminate database JSON scanning, repeated authorization or source reads. Indexed lightweight discovery and prepared selections are the next scaling steps.

## Final access decision — 2026-10-06 (supersedes earlier defaults)

Owner decision:
- Initial research is free and anonymous. No registration or email collection is required. No business quota on research requests; operational rate/concurrency protections remain necessary.
- Show up to TEN results per entity category per selection, with recorded professional emails/addresses where available. This supersedes the earlier top-five presentation default. Fewer than ten eligible entities must be reported honestly.
- Always show the distinct trial population, disjoint subgroup counts, total eligible normalized entities per category, and returned count. Counts must use the same cohort, country/function filters and identity policy as the shortlist. Never imply unavailable data exists behind a paywall.
- Repeated reads of a selection reveal only its allowed top ten. Evidence/contact/profile-section/export routes must enforce the same entity allowlist; a ten-row ranking response alone is insufficient. Different legitimate queries may produce different top tens: the owner wants unrestricted research, not a lifetime ten-entity cap.
- Full access requires connecting a TrialAgents account and verifying the relevant existing Intel Agent entitlement server-side. Login alone does not confer paid access. Preserve existing per-project entitlement semantics; do not convert a project license into account-wide database access.
- Keep existing Intel Agent pricing: EUR 490/month per project or EUR 2,900/year per project, VAT extra, automatic renewal; annual access includes monthly evidence updates. Reuse existing billing/entitlement logic. No separate ChatGPT surcharge. Trial offers versus payment upfront remain a future product decision; do not introduce either automatically.
- Minimize connection friction with hosted sign-in/consent returning directly to ChatGPT. An anonymous caller's ChatGPT email is not supplied to us.

Publication boundary, checked against OpenAI's published Directory guidelines on 2026-10-06:
- A plugin may explain missing entitlement, connect an existing account, and link to an informational access page.
- Do not initiate digital-subscription checkout, promote upgrades or link directly to Stripe/another page that starts a subscription. The owner's wish to subscribe from ChatGPT is conditional on platform acceptance; it is not approved by the current guidelines.
- An independent TrialAgents subscription/account page can handle billing. The plugin's informational link must not itself initiate purchase. Use the existing Intel Agent purchase/account route where suitable rather than automatically creating a duplicate sales page.
- Proposed neutral limit response: "Your current access includes ten results per selection. Connect your TrialAgents account to check full-list access." Connection checks entitlement; it does not promise all connected accounts qualify.
- Sources: https://developers.openai.com/plugins/plugin-guidelines and https://developers.openai.com/plugins/build/auth . Recheck before Directory submission.

Implementation sequence: optimize and validate discovery; add explicit entity-bound contacts and total-count contract; introduce anonymous selection sessions plus a server-owned top-ten allowlist; connect existing paid entitlements and full pagination; validate cross-tool access; then package the ChatGPT workflow. These are agreed requirements, not claims that the current tools already allow anonymous use or enforce a free-tier boundary.
