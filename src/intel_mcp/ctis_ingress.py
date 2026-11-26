"""Route TrialAgents CTIS's public Claude MCP paths on mcp.trialagents.com to the shared web process.

The CTIS MCP server runs inside the web service (tarous89/intel_agent_app, /ctis/claude). This forwards the
exact public paths there, as Pipeline's ingress does, and leaves every other path to the shared MCP app.
"""
from http.cookiejar import CookieJar, DefaultCookiePolicy

import httpx
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse


CLAUDE_RESOURCE = "/ctis/claude"
CLAUDE_DISCOVERY = "/.well-known/oauth-protected-resource/ctis/claude"
RESOURCES = {CLAUDE_RESOURCE}
DISCOVERIES = {CLAUDE_DISCOVERY}
UPSTREAM = "http://intel-agent-app:10000"
# The workspace inside Claude uploads files up to 8 MB through the MCP connection, sent as base64 in JSON.
MAX_BODY = 12_000_000
REQUEST_HEADERS = {
    "accept", "authorization", "content-type", "mcp-protocol-version",
    "mcp-method", "mcp-name", "mcp-session-id", "last-event-id", "origin",
}
RESPONSE_HEADERS = {
    "allow", "content-type", "www-authenticate", "mcp-session-id",
    "mcp-protocol-version", "retry-after", "cache-control", "content-encoding",
}


class _NoCookies(DefaultCookiePolicy):
    """The shared upstream client serves every user, so it must never keep or replay cookies."""

    def set_ok(self, cookie, request):
        return False

    def return_ok(self, cookie, request):
        return False


class CtisIngress:
    def __init__(self, app, *, transport=None):
        self.app = app
        self.client = httpx.AsyncClient(
            base_url=UPSTREAM, transport=transport, trust_env=False,
            cookies=CookieJar(policy=_NoCookies()),
            # Filling a Word file or reading a long source can take longer than an ordinary MCP call.
            timeout=httpx.Timeout(120, connect=5), follow_redirects=False,
        )

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            try:
                await self.app(scope, receive, send)
            finally:
                await self.client.aclose()
            return
        if scope["type"] != "http" or scope["path"] not in RESOURCES | DISCOVERIES:
            return await self.app(scope, receive, send)
        allowed = ("GET", "HEAD") if scope["path"] in DISCOVERIES else ("POST", "GET", "DELETE")
        if scope["method"] not in allowed:
            return await Response(status_code=405, headers={"Allow": ", ".join(allowed)})(scope, receive, send)
        request = Request(scope, receive)
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > MAX_BODY:
                return await Response(status_code=413)(scope, receive, send)
            body.extend(chunk)
        headers = {k: v for k, v in request.headers.items() if k in REQUEST_HEADERS}
        headers["accept-encoding"] = "identity"
        outbound = self.client.build_request(request.method, scope["path"], headers=headers, content=bytes(body))
        try:
            upstream = await self.client.send(outbound, stream=True)
        except httpx.RequestError:
            return await Response(status_code=502, headers={"Cache-Control": "no-store"})(scope, receive, send)
        try:
            headers = {k: v for k, v in upstream.headers.items() if k in RESPONSE_HEADERS}
            await StreamingResponse(upstream.aiter_raw(), status_code=upstream.status_code, headers=headers)(scope, receive, send)
        finally:
            await upstream.aclose()
