"""TrialAgents CTIS forwarding: /ctis/claude and its resource metadata go to the shared web service.

Staged from tarous89/trialagents_ctis (integration/shared-mcp, scripts/stage-ingress.py)."""
import asyncio

import httpx
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from intel_mcp.ctis_ingress import CtisIngress

seen = []


def upstream(request: httpx.Request) -> httpx.Response:
    seen.append(request)
    if request.url.path.startswith("/.well-known/"):
        return httpx.Response(200, headers={"content-type": "application/json"},
                              stream=httpx.ByteStream(b'{"resource": "https://mcp.trialagents.com/ctis/claude"}'))
    if "authorization" not in request.headers:
        return httpx.Response(401, headers={"www-authenticate": 'Bearer resource_metadata="x"', "set-cookie": "a=b"}, stream=httpx.ByteStream(b""))
    return httpx.Response(200, headers={"content-type": "text/event-stream", "x-internal": "1"}, stream=httpx.ByteStream(b"data: {}\n\n"))


shared = Starlette(routes=[Route("/mcp", lambda r: PlainTextResponse("shared"), methods=["POST"])])


def call(method, path, **kw):
    async def go():
        app = CtisIngress(shared, transport=httpx.MockTransport(upstream))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://mcp.trialagents.com") as c:
            return await c.request(method, path, **kw)
    return asyncio.run(go())


def test_forwards_the_exact_ctis_paths_only():
    seen.clear()
    assert call("POST", "/mcp").text == "shared"
    assert call("POST", "/ctis/claude/extra").status_code == 404
    assert not seen
    meta = call("GET", "/.well-known/oauth-protected-resource/ctis/claude")
    assert meta.json()["resource"].endswith("/ctis/claude")
    assert str(seen[-1].url) == "http://intel-agent-app:10000/.well-known/oauth-protected-resource/ctis/claude"


def test_passes_auth_and_mcp_headers_and_drops_the_rest():
    seen.clear()
    r = call("POST", "/ctis/claude", content=b'{"jsonrpc":"2.0"}', headers={
        "authorization": "Bearer t", "mcp-protocol-version": "2025-11-25", "cookie": "s=1", "x-forwarded-for": "1.2.3.4",
        "content-type": "application/json"})
    assert r.status_code == 200 and r.text == "data: {}\n\n" and "x-internal" not in r.headers
    sent = seen[-1].headers
    assert sent["authorization"] == "Bearer t" and sent["mcp-protocol-version"] == "2025-11-25"
    assert "cookie" not in sent and "x-forwarded-for" not in sent and seen[-1].content == b'{"jsonrpc":"2.0"}'
    r = call("POST", "/ctis/claude", content=b"{}")
    assert r.status_code == 401 and "www-authenticate" in r.headers and "set-cookie" not in r.headers


def test_methods_size_and_upstream_errors():
    assert call("PUT", "/ctis/claude").status_code == 405
    assert call("POST", "/.well-known/oauth-protected-resource/ctis/claude").status_code == 405
    assert call("POST", "/ctis/claude", content=b"x" * 12_000_001).status_code == 413
    assert call("POST", "/ctis/claude", content=b"x" * 9_000_000, headers={"authorization": "Bearer t"}).status_code == 200

    def down(request):
        raise httpx.ConnectError("down")

    async def go():
        app = CtisIngress(shared, transport=httpx.MockTransport(down))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://x") as c:
            return await c.post("/ctis/claude")
    assert asyncio.run(go()).status_code == 502



def test_the_production_app_is_wrapped():
    from intel_mcp import bootstrap
    assert isinstance(bootstrap.app, CtisIngress)
