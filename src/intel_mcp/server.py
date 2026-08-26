from __future__ import annotations

import secrets
from typing import Annotated

import uvicorn
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import Field
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

from intel_mcp.config import Settings
from intel_mcp.control_plane import ControlPlaneClient, ControlPlaneError
from intel_mcp.models import AnalysisLimits, StartAnalysisOutput

settings = Settings.from_environment()
mcp = MCPServer(
    "TrialAgents Intel MCP",
    instructions=(
        "Use start_analysis once after the Intel Agent app has created an approved report run. "
        "Pass the returned analysis_id to every later Intel tool."
    ),
)


def control_plane_client() -> ControlPlaneClient:
    return ControlPlaneClient(settings)


@mcp.tool(
    title="Start Intel analysis",
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def start_analysis(
    report_run_id: Annotated[
        str,
        Field(
            min_length=1,
            max_length=128,
            description="Stable report run ID created by the authenticated Intel Agent app after plan approval.",
        ),
    ],
) -> StartAnalysisOutput:
    """Reserve or recover the current user's one active 60-minute analysis lease.

    This lifecycle tool performs no trial filtering, retrieval, classification, extraction or report writing.
    Identity, plan approval, package, enabled tools and remaining allowance are resolved by the app control plane.
    Repeating the call while the user has an active analysis returns that existing lease without another charge.
    """
    try:
        response = await control_plane_client().start_analysis(report_run_id)
    except ControlPlaneError as error:
        raise ToolError(f"{error.code}: {error.message}") from error

    analysis = response.analysis
    return StartAnalysisOutput(
        analysis_id=analysis.analysis_id,
        report_run_id=analysis.report_run_id,
        tier=analysis.tier,
        expires_at=analysis.expires_at,
        enabled_tools=analysis.enabled_tools,
        limits=AnalysisLimits.model_validate(analysis.limits.model_dump()),
        reused=analysis.reused,
    )


@mcp.custom_route("/health", methods=["GET"])
async def health(_request: Request) -> Response:
    return JSONResponse({"status": "ok", "service": "intel-mcp"})


transport_security = TransportSecuritySettings(allowed_hosts=list(settings.allowed_hosts))


class MCPServiceAuthMiddleware:
    """Require the internal service bearer on every MCP protocol request."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope.get("path", "").startswith("/mcp"):
            await self.app(scope, receive, send)
            return

        try:
            settings.validate_inbound_auth()
        except RuntimeError:
            response = JSONResponse(
                {"error": {"code": "MCP_AUTH_NOT_CONFIGURED", "message": "MCP authentication is not configured."}},
                status_code=503,
            )
            await response(scope, receive, send)
            return

        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        authorization = headers.get(b"authorization", b"").decode("latin-1")
        scheme, separator, token = authorization.partition(" ")
        valid = (
            bool(separator)
            and scheme.lower() == "bearer"
            and secrets.compare_digest(token, settings.mcp_inbound_service_token)
        )
        if not valid:
            response = JSONResponse(
                {"error": {"code": "UNAUTHORIZED", "message": "A valid MCP service credential is required."}},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


app = MCPServiceAuthMiddleware(mcp.streamable_http_app(transport_security=transport_security))


def main() -> None:
    uvicorn.run("intel_mcp.server:app", host="0.0.0.0", port=settings.port, proxy_headers=True)
