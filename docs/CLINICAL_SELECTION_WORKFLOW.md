# Clinical partner discovery workflow

Current contract, 2026-10-08. This document supersedes earlier top-five/private-selection workflow drafts; implementation history remains in SELECTION_IMPLEMENTATION_LOG.md.

The deployable ChatGPT instructions are [the packaged skill](../plugins/trialagents-intel/skills/find-clinical-partners/SKILL.md). Tool details and the executable prostate landscape example are bundled alongside it. Maintain those files when changing user-facing behavior, then rebuild the plugin.

1. Establish indication, population, phase, modality, countries, entity types and optional provider function. Separate hard constraints from exploratory preferences.
2. Announce a clinically defensible landscape; aim for approximately 200–500 where supported, never pad or silently relax hard requirements. Search available structured fields and explicit lexical title/profile fields. Disclose incomplete clinical matching and missing phase.
3. Define ordered direct/related/broader groups. Show one compact primary trial-group breakdown in the overview; do not repeat match-tier columns in entity rows. Base limits fail closed; there is no partial-result fallback.
4. Search and rank sequentially per category using the same criteria/reference date. Return up to TEN entities per category, never five by default. Show full cohort/entity totals even when lists are limited. Distinct category trial totals must not be summed.
5. Use one branded table per requested category with in-row green bars, expandable evidence and actual distinct-trial experience, functions/affiliations, evidence links and recorded professional contacts. Hide CRO emails unless explicitly requested. Public ranking uses whole-cohort distinct trial totals, then stable name/ID ties. Preserve conservative identity normalization. Explain the deterministic ranking and do not infer performance or direct collaboration from participation.
6. End with three supported data actions such as supporting studies, functions, contacts or full lists; avoid generic narrowing suggestions. Explicit save/Open in Intel Agent requests use private saved snapshots and current account access. No raw profile, outreach or response-tracking tool is exposed here.
7. Anonymous usage requires no login and gives ten per category/selection; legitimate new research can return different tens. Do not partition to evade access limits. Expanded results require supported OAuth plus active paid account access; no project matching is required and login alone is insufficient.

All current available study profiles are eligible under the deployed migration policy. Legacy internal schema strings mentioning approval are not a restriction to model-enriched studies. Explain dataset coverage as available TrialAgents profiles, not all worldwide trials.

See [release operations](CHATGPT_PLUGIN_RELEASE.md) for build, review and publication gates. Packaging does not change the production ranking, pricing or website.
