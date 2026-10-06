# TrialAgents Intel ChatGPT plugin release

## Status and decisions — 2026-10-06

Owner reported all requested signed-in acceptance checks confirmed and asked to proceed. This records user confirmation, not a new automated paid-account test.

Package source: `plugins/trialagents-intel/`, version 0.1.0. Uses the portable Agent Plugins format: root plugin.json, root mcp.json, workflow skill and assets. Remote MCP: https://mcp.trialagents.com/research/mcp. No legacy ai-plugin.json, duplicated custom GPT Actions API or static token. Anonymous and OAuth modes remain server-owned.

The package implements broad relevant discovery, explicit subgroup counts, top-ten tables, professional contacts, ranking explanations and evidence follow-ups. The MCP still performs deterministic selection; no added backend LLM calls. Existing website, auth, project entitlements, checkout and subscription prices are unchanged. Connecting an account does not itself unlock uncovered cohorts.

## Reproducible build and pilot

From repository root, install the project/dev dependencies, then run:

```sh
python scripts/build_chatgpt_plugin.py
python -m pytest -q tests/test_chatgpt_plugin.py
```

Output: `dist/trialagents-intel-0.1.0.zip`. Only seven explicitly allowlisted public package files are included; no repository, environment files, source credentials or reviewer credentials. ZIP paths start at plugin.json, not a containing directory. The builder validates local constraints and the bundled criteria against the actual SelectionCriteria model; this is not OpenAI certification or full remote schema validation.

The GitHub `ChatGPT plugin package` workflow builds and uploads the ZIP as an Actions artifact. Download that artifact and use the supported plugin upload/testing flow. Exercise the five positive and three negative cases in plugin.json before submission, particularly sparse cohorts, ten-result enforcement and full-project coverage. Evidence/account follow-up cases require the preceding research selection. Use a dedicated non-customer review project.

## Public directory gates

1. Select the verified developer identity and appropriate category in the OpenAI Plugins dashboard; upload the ZIP and inspect scan/import results. Adjust to any current schema errors before submitting.
2. Complete the dashboard-generated MCP domain verification. Publish its exact challenge under the specified well-known path. No token has been fabricated or deployed by this packaging change.
3. Test the package in actual ChatGPT: anonymous three-category discovery, contacts/evidence, expired selections, account connection, covered project expansion and denied uncovered project. Prior owner acceptance covers the app journey, not this newly packaged plugin.
4. Provide a reviewer-accessible walkthrough video and dedicated reviewer credentials through the secure dashboard. Neither is included in the ZIP. Reviewer access must not require private email/MFA approval from the owner. Do not weaken production authentication globally to create review access.
5. Confirm listing support/privacy/terms accurately describe this MCP data flow and contact handling. Current supportURL is the product page with its public contact@trialagents.com footer, not a newly built support centre; replace with a dedicated support page if required by review. Recheck the legal pages and public support contact in the dashboard.
6. Review the live tools' read-only/open-world annotations and any required justification fields against current submission checks. This package does not alter live tool metadata. Complete reviewer access, country targeting, legal declarations and final submission as the verified owner. After approval, explicitly publish; upload/PR merge is not public listing.

No public submission or publication has been performed by the package builder. Do not claim approval or automatic installation.

## Assets and sources

The icon reuses intel_agent_app/public/favicon.svg at commit d88bb67e7bcb6f5e38e60786488a0f5a008cb54c; only intrinsic dimensions change from 24 to 96 pixels to satisfy packaging size requirements, with paths/viewBox preserved. No new logo or license grant is introduced.

Official guidance checked 2026-10-06:
- https://developers.openai.com/plugins/build/plugins
- https://developers.openai.com/plugins/deploy/submission

Submission metadata includes five positive and three negative cases. The skill makes no raw-profile, performance, patient-treatment, email-sending or payment-tool claims. Operational narratives are not disclosed by free evidence; do not advertise their availability as an anonymous feature.
