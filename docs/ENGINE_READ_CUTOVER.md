# Engine read cutover

The production target removes the cold-starting Engine HTTP hop from the five MCP
clinical reads without moving any Engine write responsibility into MCP.

## Preconditions

1. Deploy the paired Engine migration that owns the `mcp_serving` v1 views and
   `intel_mcp_reader_v1` role.
2. Generate one random password of at least 32 characters. Store the same secret as
   `MCP_ENGINE_DATABASE_PASSWORD` on the Engine profile service and MCP; never place it
   in git, logs or this document.
3. Run `trial-profile provision-mcp-reader --execute`, then
   `trial-profile audit-mcp-reader`. The audit must report `safe: true`.
4. Configure MCP with the Engine database host, port and name, and username
   `intel_mcp_reader_v1`. Do not copy the Engine owner `DATABASE_URL`.

## Canary order

1. Leave `MCP_ENGINE_SOURCE=http`; deploy Engine and verify its health plus all five
   existing authenticated HTTP reads.
2. Deploy MCP code while it remains in HTTP mode and verify `/health` plus all six MCP
   tool schemas.
3. Set `MCP_ENGINE_SOURCE=database`. `/health` must report
   `engine=read_only_database_ok`.
4. Smoke-test filter, classification, profile, document and extraction-source reads
   with approved test trials. Verify an unapproved trial is unavailable.
5. Verify the reader cannot select Engine base tables and cannot execute a write.
6. Keep the HTTP URL/token configured through the observation window.

## Rollback

Set only `MCP_ENGINE_SOURCE=http` and redeploy MCP. This restores the previous
authenticated Engine HTTP read path. Do not revoke the reader or remove views during
rollback; investigate first. The Engine ingestion/generation path is unaffected either
way.
