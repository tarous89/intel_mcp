# Light Report v1 — superseded historical context

Last updated: 2026-09-06

> **Historical only.** This file describes the earlier Light Report v1 execution and reliability fixes. It is **not** a current tool or report contract. For current behavior use repository-root `REPORT_EXECUTION_CONTEXT.md`, then `PROJECT_CONTEXT.md`. In particular, current Light is profile-only and current `get_profiles` supports optional section projections with one 10-profile per-call cap.

## Historical Light Report v1 execution contract

At the time of this v1 implementation:

- One `gpt-5.6-sol` selection call received the approved brief, plan and the first four report categories.
- Selection could use `filter_trials`, `classify_trials` and `get_profiles`.
- Light could screen up to 100 unique trials and froze exactly 20 selected trials for the report. Selected trials were labeled `priority` or `adjacent`; no backup set existed in v1.
- The first four approved report categories ran as four independent Sol objective calls over the same frozen 20 trials.
- Objective calls could use `get_profiles`, `get_documents` and `extract_variables`; they could not discover, add, remove or replace trials.
- A final no-tool Sol synthesis combined the structured section outputs.
- Max Report remained a separate future path.

These bullets are retained only to explain older production incidents below. They are superseded by the current report execution context.

## Deep-tool reliability fix — 2026-09-04

The first production Light Report exposed three MCP failures:

1. `classify_trials` reached the Terra worker but its OpenAI Responses request returned HTTP 400.
2. `get_documents` returned `ENGINE_UNAVAILABLE`.
3. `extract_variables` returned `ENGINE_UNAVAILABLE` before its Terra extraction request.

MCP PR #29 / squash `8e7930ee3abc91002a86ca6cab16d41335027708` fixed all three paths.

### Terra service tier

Legacy MCP configuration used `service_tier=standard` as a human/internal label. The OpenAI Responses API uses `default` for standard processing. MCP normalized an empty or legacy `standard` environment value to `default`, and both classifier/extractor defaults became `default`.

### Document and extraction-source reads

The restricted Engine reader has a 15-second PostgreSQL statement timeout. The former deep-read queries joined `mcp_serving.documents_v1` to `mcp_serving.document_text_v1`; because both are security-barrier serving views, this could force a broad document-text scan and exceed the timeout even though filtering/profile retrieval remained healthy.

The read path was changed to two bounded stages:

1. Resolve the selected document from the lightweight `mcp_serving.documents_v1` catalogue using the trial/document identity.
2. Retrieve text from `mcp_serving.document_text_v1` using the exact `document_id`.

`get_documents` retained its existing contract, page markers, parting and document-access key. `extract_variables` continued to receive the complete approved Trial Profile plus the profile-selected protocol when available; only the internal source retrieval query changed.

Production DB probes confirmed the exact-id path on a real 459,153-character protocol: catalogue lookup and exact `document_id` text lookup both completed successfully.

## Historical validation and deployment

- MCP CI run #66 passed after the fix, including regression coverage for classifier/extractor service-tier payloads and the two-stage document/extraction-source SQL paths.
- Historical production Render deployment: `dep-dadathbm8hqs738h4s40`.
- Historical deployment commit: `8e7930ee3abc91002a86ca6cab16d41335027708`.
