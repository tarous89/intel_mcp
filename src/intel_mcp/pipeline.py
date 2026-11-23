"""Private Pipeline MCP routes on the existing Intel service.

The Pipeline audience is checked at the transport and again at the app.
All operations use the member's bearer token; there is no privileged fallback.
"""
from contextvars import ContextVar
from importlib.resources import files
from typing import Any

import httpx
from mcp.server import MCPServer
from mcp.server.apps import APP_MIME_TYPE, Apps
from mcp.server.mcpserver.resources import TextResource
from mcp.types import CallToolResult, TextContent, ToolAnnotations
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from .research_server import research_tool_security_schemes

TOKEN = ContextVar("pipeline_member_token", default=None)
RESOURCE = "ui://trialagents-pipeline/workspace-v1"
OAUTH = {"securitySchemes": [{"type": "oauth2", "scopes": ["mcp:tools"]}]}
READ = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)
WRITE = ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=True, open_world_hint=False)
VISIBLE = {**OAUTH, "ui": {"resourceUri": RESOURCE}, "openai/outputTemplate": RESOURCE}
WIDGET_OPS = {"bootstrap", "items.save", "attachment.get", "view.list", "view.save", "view.remove", "logs",
              "preferences.save", "settings.save", "design.save", "team.list", "team.invite", "team.revoke",
              "team.member"}


def result(summary, data=None, *, private=False, view=None):
    content = [TextContent(type="text", text=summary)]
    if private:
        return CallToolResult(content=content, _meta={"pipeline": data, "view": view})
    return CallToolResult(content=content, structured_content={"result": data})


class PipelineGateway:
    def __init__(self, endpoint, transport=None):
        self.endpoint = endpoint
        self.transport = transport

    async def call(self, request):
        token = TOKEN.get()
        if not token:
            raise ValueError("Connect your Pipeline account.")
        async with httpx.AsyncClient(timeout=30, transport=self.transport) as client:
            reply = await client.post(self.endpoint, json=request, headers={"Authorization": "Bearer " + token})
        if not reply.is_success:
            try:
                message = reply.json().get("error")
            except ValueError:
                message = None
            raise ValueError(message or "Pipeline is unavailable.")
        return reply.json()


def pipeline_server(gateway):
    apps = Apps()
    apps.add_resource(TextResource(
        uri=RESOURCE, name="Pipeline workspace", mime_type=APP_MIME_TYPE,
        text=files("intel_mcp").joinpath("ui/pipeline-widget.html").read_text(),
        meta={"ui": {"domain": "https://pipeline.trialagents.com", "csp": {"connectDomains": [], "resourceDomains": ["https://intel.trialagents.com"]}},
              "openai/widgetDomain": "https://pipeline.trialagents.com",
              "openai/widgetCSP": {"connect_domains": [], "resource_domains": ["https://intel.trialagents.com"], "redirect_domains": ["https://pipeline.trialagents.com"]}},
    ))
    server = MCPServer("TrialAgents Pipeline", extensions=[apps], middleware=[research_tool_security_schemes],
        instructions="Open the signed-in workspace on the first request to see Pipeline. For follow-ups choose an answer, a relevant view, or a workspace link. Identify the correct workspace and record before editing. Use the current revision and a stable request UUID when retrying. Owner administration and checkout belong in Settings.")
    @server.tool(meta=VISIBLE, annotations=READ)
    async def open_pipeline(workspace: str | None = None, view_id: str | None = None) -> CallToolResult:
        """Open the interactive Pipeline workspace or a shared custom view inline."""
        snap = await gateway.call({"op": "bootstrap", "workspace": workspace})
        return result("Opened " + snap["title"], snap, private=True, view=view_id)

    @server.tool(meta=OAUTH, annotations=READ)
    async def read_pipeline(workspace: str | None = None, search: str = "", record_type: str = "",
                            record_id: str = "", offset: int = 0, limit: int = 25) -> CallToolResult:
        """List available workspaces, roles, views and matching records. Use record_id for one complete record."""
        snap = await gateway.call({"op": "bootstrap", "workspace": workspace})
        rows = [r for r in snap["items"] if (not record_id or r["id"] == record_id)
                and (not record_type or r["type"] == record_type) and search.casefold() in r["name"].casefold()]
        offset, limit = max(0, offset), min(100, max(1, limit))
        fields = ("id", "type", "name", "status", "risk", "start", "end", "owner", "budget", "parents", "deps")
        page = rows[offset:offset+limit]
        return result(f"{len(rows)} matching records.", {"workspace": snap["workspace"], "revision": snap["revision"],
            "role": snap["role"], "workspaces": snap["workspaces"], "views": snap["views"], "tabs": snap["tabs"],
            "accent": snap["accent"], "title":snap["title"], "total":len(rows),
            "records": page if record_id else [{k:r[k] for k in fields if k in r} for r in page]})

    @server.tool(meta=OAUTH, annotations=WRITE)
    async def save_pipeline_records(workspace: str, revision: int, request_id: str,
                                    upsert: list[dict[str, Any]], remove: list[str]) -> CallToolResult:
        """Save complete changed records and explicit deletions atomically. Read each existing record by ID first. New plans need id, name, type, owner, status, start/end, parents and deps. Use empty arrays for absent changes."""
        data = await gateway.call({"op":"items.save","workspace":workspace,"revision":revision,"requestId":request_id,
                                   "input":{"upsert":upsert,"remove":remove}})
        return result("Saved Pipeline records.",data)

    @server.tool(meta=OAUTH, annotations=WRITE)
    async def save_pipeline_view(workspace: str, revision: int, request_id: str, title: str,
                                 filters: dict[str, str], chart: str = "", view_id: str | None = None) -> CallToolResult:
        """Save an editor-authored view to Custom views. Filters include program ID, owner, type, status, risk, budget, from, until and search. Optional chart groups by type, owner or status."""
        data = await gateway.call({"op":"view.save","workspace":workspace,"revision":revision,"requestId":request_id,
            "input":{"id":view_id,"title":title,"filters":filters,"chart":chart}})
        return result("Saved custom view.",data)

    @server.tool(meta=OAUTH, annotations=WRITE)
    async def customize_pipeline(workspace: str, revision: int, request_id: str, workspace_title: str,
                                 accent: str, tabs: list[dict[str,str]]) -> CallToolResult:
        """Owner only. Preview the exact changes in the conversation and apply the agreed full design. Preserve existing entries. A pinned tab has id (UUID), view (saved view UUID) and label; a renamed built-in has builtin and label."""
        data=await gateway.call({"op":"design.save","workspace":workspace,"revision":revision,"requestId":request_id,
                                 "input":{"title":workspace_title,"accent":accent,"tabs":tabs}})
        return result("Updated Pipeline appearance.",data)

    @server.tool(meta={**OAUTH,"ui":{"visibility":["app"]}}, annotations=WRITE)
    async def pipeline_widget_action(request: dict[str,Any]) -> CallToolResult:
        """Run an authenticated interaction from the embedded Pipeline interface."""
        if request.get("op") not in WIDGET_OPS:
            raise ValueError("Unknown workspace action.")
        return result("Workspace updated.",await gateway.call(request),private=True)
    return server


class PipelineAuth:
    def __init__(self, app, control_factory, resource, metadata):
        self.app,self.control,self.resource,self.metadata=app,control_factory,resource,metadata

    async def __call__(self,scope,receive,send):
        if scope["type"]!="http":
            return await self.app(scope,receive,send)
        raw=dict(scope["headers"]).get(b"authorization",b"").decode("latin1")
        scheme,_,token=raw.partition(" ")
        try:
            info=await self.control().introspect_access_token(token) if scheme.lower()=="bearer" and token else {}
        except Exception:
            return await JSONResponse({"error":"Authorization unavailable"},status_code=503)(scope,receive,send)
        if not (info.get("active") is True and info.get("sub") and info.get("resource")==self.resource
                and "mcp:tools" in str(info.get("scope","")).split()):
            return await JSONResponse({"error":"Connect Pipeline"},status_code=401,
                headers={"WWW-Authenticate":f'Bearer resource_metadata="{self.metadata}", scope="mcp:tools"'})(scope,receive,send)
        ctx=TOKEN.set(token)
        try:
            return await self.app(scope,receive,send)
        finally:
            TOKEN.reset(ctx)


def pipeline_routes(settings,control_factory,transport_security):
    base=settings.mcp_public_resource_url.removesuffix("/mcp")
    apps,routes=[],[]
    for prefix in ("/pipeline","/pipeline-claude"):
        resource=base+prefix+"/mcp"
        path="/.well-known/oauth-protected-resource"+prefix+"/mcp"
        async def metadata(_request,resource=resource):
            return JSONResponse({"resource":resource,"authorization_servers":[settings.oauth_authorization_server_url.rstrip("/")+"/oauth/intel"],
                                 "scopes_supported":["mcp:tools"],"bearer_methods_supported":["header"]})
        server=pipeline_server(PipelineGateway(settings.app_control_url.rstrip("/")+"/api/pipeline"))
        app=server.streamable_http_app(stateless_http=True,transport_security=transport_security)
        routes.extend([Route(path,metadata,methods=["GET"]),Mount(prefix,app=PipelineAuth(app,control_factory,resource,base+path))])
        apps.append(app)
    return routes,apps
