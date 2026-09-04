from __future__ import annotations

import secrets

import uvicorn
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from intel_mcp import server
from intel_mcp.light_report_execution import start_light_report_task


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


# server.app is built before this module registers the route. Rebuild the ASGI app once
# so the production entrypoint contains both the public MCP surface and Light execution route.
app = server.MCPServiceAuthMiddleware(
    server.mcp.streamable_http_app(transport_security=server.transport_security)
)


def main() -> None:
    uvicorn.run("intel_mcp.bootstrap:app", host="0.0.0.0", port=server.settings.port, proxy_headers=True)
