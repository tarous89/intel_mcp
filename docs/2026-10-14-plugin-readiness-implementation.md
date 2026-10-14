# Plugin readiness implementation — 2026-10-14

Owner authorized the six identified fixes on 14 October, with publication requirements first and preservation of UX/performance second. This candidate implements source changes; it is not a public Directory submission or a live deployment.

Remote status: the owner explicitly approved repository upload and deployment on 14 October at 10:26 Europe/Berlin, resolving the previous automatic upload rejection. Release execution is in progress. Public company wording is now simply TrialAgents is operated by Atlas Consulting, without a publisher-of-ChatGPT-plugin phrase.

## Implemented

1. Declare the dedicated https://mcp.trialagents.com UI origin on all four resource entries, including compatibility metadata. Existing CSP, HTML, display modes and controls are unchanged.
2. Make tool declarations match existing persisted evidence and overwrite behavior. Evidence readers remain functional with the same stored provenance; document reads correctly disclose non-idempotent dated source storage. Saves, report retries and view/state replacements declare overwrite potential. No new confirmation UI.
3. Reuse connected-owner publish identity and its server-keyed preview capability after a lost response. Preserve independent guest capabilities, separate owners, explicit new projects and existing revision saves. No new query, cache, scheduler or additional research data retained; one 32-byte server key.
4. Declare output schemas for the three legacy tools while preserving their explicit result content and OAuth challenges. All 37 tools now declare schemas.
5. Correct public-page source: Atlas Consulting identity, owner-confirmed street number in Terms only, current account-wide access, no retired Max Report price or production-draft footer, explicit plugin data/retention descriptions.
6. Correct review/release documentation and conditional evidence/contact test instructions. Build candidate package 0.7.5; existing skills, icons, starter prompts, UI bundle and product naming remain intact.

## Material UX alert and decision

Existing evidence source hashes refer to persisted, scope-bound records. Delaying registration until save would require a new source-reference mechanism, compatibility design, and either larger returned data, repeat retrieval or a new evidence cache. None is introduced in this narrow correction. Accurate metadata can cause ChatGPT to show additional evidence/write/overwrite approvals. Actual host prompts must be reviewed before release; no promise of unchanged prompt count.

The new origin must be accepted for this plugin by the real host/Portal. Existing nested srcDoc rendering still needs host validation and the applicable iframe justification. No renderer rewrite or wider network policy was introduced.

## Validation

- MCP suite: 486 passed, four PostgreSQL integration checks skipped locally; CI must run them.
- Focused protocol checks: all 37 schemas, accurate affected annotations, all UI resource origins, preserved OAuth challenge and legacy results.
- Synthetic retry regression: a committed-but-lost response returns the same project on retry, matching the entire App command including its cache-token hash; intentional separate projects and different owners stay separate; anonymous guests keep independent private capabilities.
- Evidence/profile/document, save/retry, ownership, access and preview regressions pass.
- Public source renders checked for Terms, Privacy, Support and the Intel landing footer; exact identity, street number, product name, stale-copy removal and address placement verified. CTIS/Custom Agent footers do not gain publisher/address text.
- Existing synthetic memory benchmark: baseline 186.44 MiB / 35.23 s; candidate 187.04 MiB / 35.40 s. All original snapshot/page/prepared-source/fallback hashes match. These are single local runs over 420 trials and 5,040 sites/PIs, not production latency guarantees.
- Guidance synchronization and package validation pass. Package is a candidate, not evidence of complete submission materials.

## Public pages and release dependencies

| Public URL | Source and correction |
| --- | --- |
| https://trialagents.com/intel-agent | Shared Intel landing footer uses the common Atlas Consulting publisher disclosure and EU Trial Intelligence name. |
| https://trialagents.com/privacy-policy | Controller identity, plugin inputs/results/recipients, saved state, preview expiry and actual retained evidence. |
| https://trialagents.com/terms-of-service | Exact owner-confirmed postal address; current service/account access; retired offer removed. |
| https://intel.trialagents.com/support/intel | Same publisher; account-wide access and frozen-project/retry guidance. |

App source owns these page components. The first three are delivered through the separate trialagents-public snapshot. Source deployment must precede its normal exact-head predeploy/snapshot refresh. Verify the four rendered live URLs afterwards; no source commit alone establishes publication.

Publisher name is Atlas Consulting in package author/developerName and public disclosure. The provided business details are not a claim that the OpenAI verified publisher account has been inspected or changed.

## Remaining gates

Real ChatGPT desktop/mobile workflows, dedicated-origin/nested-frame acceptance and actual approval UX; actual reviewer login and sample account; accessible demo; publisher/domain verification; current Portal scans; owner confirmation of retention/rights practices. Existing evidence records have no automatic deletion deadline and removal is not immediate backend erasure: the draft wording describes that behavior rather than inventing a purge promise. Log, account/billing and legal retention decisions still require owner confirmation before policy sign-off. No retention/deletion feature was added.

Do not submit or label this candidate publication-ready solely because its code/package checks pass.
