# Request-scoped MCP disclosure — 2026-10-20

## Scope

This release responds to review feedback about unnecessary personal identifiers in tool results. It does not claim OpenAI approval. ZIP rebuilding, version bump and resubmission are deferred by the owner.

- Remove connected-account email/name/IDs from account summaries and nested account objects using an allowlist. Existing access capabilities remain. The extension can no longer prefill the account email from MCP responses; hosted authentication/account choice is unchanged.
- Return only the selected category in workspace preview tables. Keep all categories in the stored project. Unloaded extension tabs show a centered Load button and do not request data until clicked. Loaded tabs retain normal paging/filter behavior.
- Keep PI names in explicitly requested PI lists. Mask structured emails/phones and nested contact-person names by default. Explicit Show contact details uses include_contacts=true on read_project_preview, read_project, open_project or get_research_workspace. Legacy ranking retains its explicit include_cro_contacts flag. Tool instructions require a user request; the flag is not a new authorization mechanism.
- Always mask structured trial-profile contact identifiers, including nested site, sponsor, provider and investigator fields, before chunking profiles. Keep institution names and clinical prose. Protocol/document reads, Custom HTML and stored Custom state are unchanged.
- Filter both structuredContent and serialized JSON text, including the legacy Recorded contacts display column. Stored snapshots are not modified.
- Add save_project.kind (default cros) and preserve the selected category through publication and connection save/recovery. This corrects the previous forced Sites response.
- New prepared snapshots retain CRO contact data server-side for later explicit reads; initial MCP responses still mask it. Old snapshots are not backfilled. Existing prepare/publish include_cro_contacts no longer exposes contacts in the initial response; use an explicit contact read.
- Add disclosure metadata: category, contacts_included, other_categories=load_on_request. UI resource identity changes with the rebuilt bundle; the previous URI remains registered for compatibility.

## Shared App changes

WorkspaceTables accepts optional pendingKind/onLoad/onContacts callbacks used by the extension. Normal website callers retain their existing behavior. Masked email placeholders render as text rather than mailto links. No persistence, API, access, billing, computation, report or database changes in the App.

## Validation and remaining release work

Synthetic MCP tests cover account omission, category-only envelopes, nonmutation, explicit contacts, nested structured profiles and legacy display columns. Chromium tests cover desktop/mobile lazy tabs, PI-name retention and explicit contact reveal. Existing connection, navigation, browser and Python regression suites are run. Repository CI must pass on the published candidate. Live-host OAuth/rendering and OpenAI review remain separate acceptance steps.

For the later ZIP revision: package the synchronized canonical guidance and current tool schemas; update review examples/screenshots for Load and Show contact details; describe omission of account email and structured trial contacts; rerun package validation. No ZIP or submission metadata is changed in this release.

