from __future__ import annotations

from typing import Annotated

import uvicorn
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import Field
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

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
app = mcp.streamable_http_app(transport_security=transport_security)


def main() -> None:
    uvicorn.run("intel_mcp.server:app", host="0.0.0.0", port=settings.port, proxy_headers=True)
