# Intel MCP

Remote Model Context Protocol service for TrialAgents Intel Agent.

The first implemented tool is `start_analysis`. It receives only an app-created `report_run_id`, calls the Intel Agent app's service-authenticated control-plane endpoint, and returns the existing or newly reserved 60-minute analysis lease. User identity, plan approval, package, enabled tools and allowances are resolved server-side by the app.

## Local setup

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
export INTEL_APP_CONTROL_URL=http://localhost:3000
export INTEL_APP_SERVICE_TOKEN=replace-me
export MCP_INBOUND_SERVICE_TOKEN=replace-me-too
intel-mcp
```

The Streamable HTTP endpoint is `/mcp`; the unauthenticated liveness endpoint is `/health`.

Required production settings:

- `INTEL_APP_CONTROL_URL`: service-authenticated Intel Agent app base URL.
- `INTEL_APP_SERVICE_TOKEN`: shared service credential stored only in Render secrets.
- `MCP_INBOUND_SERVICE_TOKEN`: bearer credential required on every request to `/mcp`.
- `MCP_ALLOWED_HOSTS`: comma-separated exact public/private Host allowlist entries.
- `PORT`: HTTP port assigned by the platform.

The initial free Render deployment is public at the network layer but `/mcp` is closed to callers without the internal service bearer. Public OAuth is a later profile and must not reuse the internal service credential as end-user authentication.
