from __future__ import annotations

import secrets

import uvicorn
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from intel_mcp import server
from intel_mcp.light_report_execution import start_light_report_task
from intel_mcp.max_report_execution import start_max_report_task
from intel_mcp.site_search_routes import register_site_search
from intel_mcp.report_artifacts import register_report_dataset
from intel_mcp.max_agent_tools import register_max_tools
from intel_mcp.light_report_execution import ReportExecutionControl


def _authorized(request: Request) -> bool:
    authorization = request.headers.get("authorization", "")
    scheme, separator, supplied = authorization.partition(" ")
    configured = server.settings.report_plan_service_token
    return bool(
        separator
        and scheme.casefold() == "bearer"
        and configured
        and secrets.compare_digest(supplied.strip(), configured)
    )


@server.mcp.custom_route("/internal/light-report/start", methods=["POST"])
async def start_light_report(request: Request) -> Response:
    if not _authorized(request):
        return JSONResponse({"error": "Unauthorized."}, status_code=401)
    try:
        body = await request.json()
    except ValueError:
        return JSONResponse({"error": "A valid JSON request is required."}, status_code=400)
    report_run_id = body.get("reportRunId") if isinstance(body, dict) else None
    if not isinstance(report_run_id, str) or not report_run_id.strip() or len(report_run_id) > 128:
        return JSONResponse({"error": "A valid reportRunId is required."}, status_code=400)
    started = start_light_report_task(server.settings, report_run_id.strip())
    return JSONResponse(
        {"reportRunId": report_run_id.strip(), "started": started},
        status_code=202,
    )


@server.mcp.custom_route("/internal/max-report/start", methods=["POST"])
async def start_max_report(request: Request) -> Response:
    if not _authorized(request):
        return JSONResponse({"error": "Unauthorized."}, status_code=401)
    try:
        body = await request.json()
    except ValueError:
        return JSONResponse({"error": "A valid JSON request is required."}, status_code=400)
    report_run_id = body.get("reportRunId") if isinstance(body, dict) else None
    if not isinstance(report_run_id, str) or not report_run_id.strip() or len(report_run_id) > 128:
        return JSONResponse({"error": "A valid reportRunId is required."}, status_code=400)
    # The durable run marker, never the current feature flag, selects execution.
    # New jobs are picked up by the supervised Max worker, including after restart.
    run = await ReportExecutionControl(server.settings).load(report_run_id.strip())
    if (run.get("progress") or {}).get("executionKind") == "max_agent_v1":
        return JSONResponse({"reportRunId": report_run_id.strip(), "started": True, "durable": True}, status_code=202)
    started = start_max_report_task(server.settings, report_run_id.strip())
    return JSONResponse(
        {"reportRunId": report_run_id.strip(), "started": started},
        status_code=202,
    )


register_site_search(server.mcp, server.settings, server.engine_client)
register_report_dataset(server.mcp, server.settings, _authorized)
register_max_tools(server.mcp, server.settings)

# server.app is built before this module registers the routes. Rebuild the ASGI app
# so the production entrypoint contains the public MCP and private app boundaries.
app = server.MCPServiceAuthMiddleware(
    server.mcp.streamable_http_app(transport_security=server.transport_security)
)


def main() -> None:
    uvicorn.run("intel_mcp.bootstrap:app", host="0.0.0.0", port=server.settings.port, proxy_headers=True)
