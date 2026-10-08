# Reviewer preparation notes — 2026-10-06

Internal maintainer reference; not bundled into the public ZIP. No credentials here. Complete the release checklist before test handoff and every release.

## Tool annotations: proposed explanations, not changed flags

Current research tools advertise readOnlyHint=true, destructiveHint=false, openWorldHint=false and idempotentHint=true. These notes describe existing behavior; they are not OpenAI approval and do not override live flags. The guidelines currently say annotation justifications are no longer required while the submission error reference says they are required. Keep explanations ready, inspect portal requirements and resolve actual findings.

| Tool | Read-only explanation | Non-destructive explanation | Bounded-world explanation |
|---|---|---|---|
| search_research_trials | Reads restricted trial profiles and computes a selection. Keeps an ephemeral process-local cache/token, normally usable for 15 minutes; does not write clinical/account records, persist reports or enqueue a paid/LLM job. Evaluate whether portal treats this cache as state requiring a different hint. | No deletion, overwrite, message, purchase or access revocation. Cache eviction only requires re-search. | Searches a bounded TrialAgents catalogue through restricted database views, not arbitrary web/URL destinations. |
| rank_research_entities | Reads the cached selection; computes rankings and, when a project is supplied, reads ownership/entitlement/coverage checks. | No user-data mutation or irreversible action. | Only selected catalogue records and the authenticated user's eligible project scope. |
| get_research_entity_evidence | Returns recorded evidence for an accessible entity and checks project access when supplied; no raw-profile endpoint. | No external sends or changes to source records. | Fixed selection/entities; user cannot supply arbitrary destinations. |
| list_research_projects | Reads connected user's projects/access; unauthenticated call emits the supported OAuth challenge. The tool does not purchase or create a project. Authentication session handling belongs to the separate auth flow. | No changes to ownership, subscription or project access. | Confined to the authenticated account's projects, not public search. |

Idempotence means retrying has no additional business side effects, not byte-identical output: cache tokens/expiry and live data/access can change. Do not modify flags merely to quiet a scan. If a change is needed, document behavior, ask the owner where it affects app/workflow, deploy and rescan.

## Output minimization review (open before Gate A)

- Selection ID and entity ID enable follow-up calls. Project ID enables scoped authorization. Retain only where functionally required; these are not permission to return unrelated account identifiers.
- Trial IDs, titles, source URLs, cohort counts and recorded roles/functions support research claims.
- Professional contacts must be relevant to visible/authorized entities, recorded rather than guessed, and covered by the published privacy notice.
- `profile_sha256`, `schema_version` and snapshot/version markers need an explicit necessity assessment. Source integrity may justify some data, but review can flag unexplained technical output. No field removal has been performed in this change.
- Operational narratives and discovery excerpts are stripped from anonymous evidence. Do not claim absence of findings from absence of narrative output.
- Confirm project-list output fields and infrastructure logs against the real deployed version; do not claim the 15-minute cache lifetime is a universal data-deletion timeline.

## Dedicated reviewer setup — secure dashboard only

Prepare an isolated reviewer-owned project covering the entire cohort produced by the submitted prostate prompt, with full existing entitlement and sample data. Verify actual positive pagination and a negative uncovered/expired-entitlement case. Do not charge a card, grant real customer access, weaken global auth or add LLM calls for this task without separate authorization. The account must remain usable throughout a potentially long review, without owner-mediated email/MFA steps. Record setup procedure and credentials only through secure dashboard fields.

All five positive tests must start independently. Counts/ranks depend on source data; assert correct behavior and source evidence, not hardcoded counts or IDs. Test expired selection recovery and full-access denial separately. Include supported desktop/mobile surfaces in final evidence. Do not manufacture screenshots or video before testing.
