# Light Report v1 — current MCP execution context

Last updated: 2026-09-04

This file records the current Light Report execution contract and the production reliability fixes that affect MCP report generation. `PROJECT_CONTEXT.md` remains the repository-wide canonical context; this file is the focused current handoff for Light Report execution.

## Light Report execution contract

- One `gpt-5.6-sol` selection call receives the approved brief, plan and the first four report categories.
- Selection may use only `filter_trials`, `classify_trials` and `get_profiles`.
- Light may screen up to 100 unique trials and must freeze exactly 20 selected trials for the report. Selected trials are labeled `priority` or `adjacent`; no backup set is created in v1.
- The first four approved report categories run as four independent Sol objective calls over the same frozen 20 trials.
- Objective calls may use `get_profiles`, `get_documents` and `extract_variables`; they may not discover, add, remove or replace trials.
- A final no-tool Sol synthesis combines the structured section outputs.
- Max Report remains a separate future path and is not implemented by the Light executor.

## Deep-tool reliability fix — 2026-09-04

The first production Light Report exposed three MCP failures:

1. `classify_trials` reached the Terra worker but its OpenAI Responses request returned HTTP 400.
2. `get_documents` returned `ENGINE_UNAVAILABLE`.
3. `extract_variables` returned `ENGINE_UNAVAILABLE` before its Terra extraction request.

MCP PR #29 / squash `8e7930ee3abc91002a86ca6cab16d41335027708` fixes all three paths.

### Terra service tier

Legacy MCP configuration used `service_tier=standard` as a human/internal label. The OpenAI Responses API uses `default` for standard processing. MCP now normalizes an empty or legacy `standard` environment value to `default`, and both classifier/extractor defaults are `default`. This lets existing production environment values self-heal without a coordinated secret change.

### Document and extraction-source reads

The restricted Engine reader has a 15-second PostgreSQL statement timeout. The former deep-read queries joined `mcp_serving.documents_v1` to `mcp_serving.document_text_v1`; because both are security-barrier serving views, this could force a broad document-text scan and exceed the timeout even though filtering/profile retrieval remained healthy.

The read path is now two-stage and bounded:

1. Resolve the selected document from the lightweight `mcp_serving.documents_v1` catalogue using the trial/document identity.
2. Retrieve text from `mcp_serving.document_text_v1` using the exact `document_id`.

`get_documents` retains its existing contract, page markers, parting and document-access key. `extract_variables` still receives the complete approved Trial Profile plus the profile-selected protocol when available; only the internal source retrieval query changed.

Production DB probes confirmed the exact-id path on a real 459,153-character protocol: catalogue lookup and exact `document_id` text lookup both completed successfully.

## Validation and deployment

- MCP CI run #66 passed after the fix, including the existing suite plus new regression coverage for classifier/extractor service-tier payloads and the two-stage document/extraction-source SQL paths.
- Production Render deployment: `dep-dadathbm8hqs738h4s40`.
- Deployment commit: `8e7930ee3abc91002a86ca6cab16d41335027708`.
- Build succeeded and the MCP process started successfully in Frankfurt.

The next real Light Report is the end-to-end production canary for the repaired tool calls. Do not treat a report as fully evidence-complete if a required deep MCP tool fails; surface the failure rather than silently presenting fallback profile-only output as equivalent evidence.
