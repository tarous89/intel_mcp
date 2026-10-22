# Workspace loading copy and account connection — 2026-10-22

Owner-requested presentation-only follow-up to the disclosure release:

- CROs, PIs, Sites and Trials awaiting an explicit load reuse the Custom views empty-state layout, with a count-based headline, category-specific explanation and existing Load button. Counts come from the existing project table inventory; no additional fetch is introduced.
- Remove the generic account-switch/reconnection/transfer paragraph from connection login. Retain the existing saved-project login sentence. In connection/OAuth login, the existing signup control reads “No TrialAgents account? Create account for free”. Explicit account-mismatch handling and authorization behavior are unchanged.
- Rebuild the embedded workspace against the matching App source and retain its previous resource URI for compatibility.

No tool schema, disclosure, data, storage, authentication, account ownership or loading behavior changes. ZIP revision and resubmission remain deferred. Validate the existing desktop/mobile disclosure and workspace browser tests plus repository CI; actual ChatGPT host rendering is separate from synthetic browser verification.

