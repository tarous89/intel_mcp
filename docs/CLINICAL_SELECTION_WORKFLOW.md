# Clinical partner discovery workflow

Current contract, 2026-10-06. This document supersedes earlier top-five/private-selection workflow drafts; implementation history remains in SELECTION_IMPLEMENTATION_LOG.md.

The deployable ChatGPT instructions are [the packaged skill](../plugins/trialagents-intel/skills/find-clinical-partners/SKILL.md). Tool details and the executable prostate landscape example are bundled alongside it. Maintain those files when changing user-facing behavior, then rebuild the plugin.

1. Establish indication, population, phase, modality, countries, entity types and optional provider function. Separate hard constraints from exploratory preferences.
2. Announce a clinically defensible landscape; aim for approximately 200–500 where supported, never pad or silently relax hard requirements. Search available structured fields and explicit lexical title/profile fields. Disclose incomplete clinical matching and missing phase.
3. Define ordered direct/related/broader groups. Report primary counts separately from overlap tags and unmatched records. Base limits fail closed; there is no partial-result fallback.
4. Search and rank sequentially per category using the same criteria/reference date. Return up to TEN entities per category, never five by default. Show full cohort/entity totals even when lists are limited. Distinct category trial totals must not be summed.
5. Use tables with actual distinct-trial experience, functions/affiliations, evidence links and recorded professional contacts. Preserve conservative identity normalization. Explain the deterministic ranking and do not infer performance or direct collaboration from participation.
6. Offer concrete subgroup/function/geography/evidence follow-ups. No raw profile, saved shortlist, outreach or response-tracking tool is exposed here. An in-chat report may summarize accessible evidence.
7. Anonymous usage requires no login and gives ten per category/selection; legitimate new research can return different tens. Do not partition to evade access limits. Expanded results require supported OAuth plus an owned entitled project covering the entire cohort; login alone is insufficient.

All current available study profiles are eligible under the deployed migration policy. Legacy internal schema strings mentioning approval are not a restriction to model-enriched studies. Explain dataset coverage as available TrialAgents profiles, not all worldwide trials.

See [release operations](CHATGPT_PLUGIN_RELEASE.md) for build, review and publication gates. Packaging does not change the production ranking, pricing or website.
