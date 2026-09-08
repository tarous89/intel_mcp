# Engine read boundary and rollback

Last updated: 2026-09-08

Production MCP reads the Engine database directly through the exact restricted role `intel_mcp_reader_v1`. The role is read-only and limited to approved-only `mcp_serving.*_v1` views. Engine retains every write, migration, ingestion, extraction and profile-generation responsibility.

Required production settings use the Engine host/port/database plus `MCP_ENGINE_DATABASE_USER=intel_mcp_reader_v1` and its separate reader password. Never copy the Engine owner `DATABASE_URL` into MCP.

Provision or audit the role from Engine:

```bash
trial-profile provision-mcp-reader --execute
trial-profile audit-mcp-reader
```

The audit must report `safe: true`. MCP startup also rejects an unexpected database username and starts every checkout read-only.

The authenticated Engine HTTP path remains rollback compatibility. A deliberate rollback sets `MCP_ENGINE_SOURCE=http` and redeploys MCP; it does not change Engine ingestion or revoke the database reader. Restore database mode after the incident is understood and approved-only reads are verified.

