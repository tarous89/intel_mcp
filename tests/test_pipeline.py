import asyncio
from contextlib import AsyncExitStack, asynccontextmanager
from types import SimpleNamespace
import httpx
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from intel_mcp import pipeline


def test_chatgpt_and_claude_transport(monkeypatch):
    async def scenario():
        base = "https://mcp.trialagents.com"
        settings = SimpleNamespace(mcp_public_resource_url=base+"/mcp", oauth_authorization_server_url="https://intel.trialagents.com",app_control_url="https://pipeline.trialagents.com")
        class Auth:
            async def introspect_access_token(self, token):
                return {"active":True,"sub":"member","scope":"mcp:tools","resource":base+"/"+token+"/mcp"}
        async def call(self,request):
            assert pipeline.TOKEN.get() in ("pipeline","pipeline-claude")
            if request["op"]=="records.read":
                return {"total":0,"records":[]}
            return {"title":"One","workspace":"w","revision":1,"role":"reader","workspaces":[],"tabs":[],"views":[],"items":[],"accent":"#112233"}
        monkeypatch.setattr(pipeline.PipelineGateway,"call",call)
        routes,apps=pipeline.pipeline_routes(settings,Auth,TransportSecuritySettings(allowed_hosts=["mcp.trialagents.com"]))
        @asynccontextmanager
        async def lifespan(app):
            async with AsyncExitStack() as stack:
                for http in apps:
                    await stack.enter_async_context(http.router.lifespan_context(http))
                yield
        app=Starlette(routes=routes,lifespan=lifespan)
        async with app.router.lifespan_context(app),httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url=base) as client:
            for path in ("pipeline","pipeline-claude"):
                endpoint="/"+path+"/mcp"
                challenge=await client.post(endpoint,json={})
                assert challenge.status_code==401
                meta=(await client.get("/.well-known/oauth-protected-resource"+endpoint)).json()
                assert meta["resource"]==base+endpoint
                headers={"Authorization":"Bearer "+path,"Accept":"application/json, text/event-stream"}
                async def rpc(method,params):
                    reply=await client.post(endpoint,headers=headers,json={"jsonrpc":"2.0","id":1,"method":method,"params":params})
                    assert reply.status_code==200,reply.text[:300]
                    if reply.headers["content-type"].startswith("text/event-stream"):
                        import json
                        return json.loads(next(line[6:] for line in reply.text.splitlines() if line.startswith("data: ")))["result"]
                    return reply.json()["result"]
                listing=await rpc("tools/list",{})
                assert len(listing["tools"])==6
                opened=await rpc("tools/call",{"name":"open_pipeline","arguments":{}})
                assert opened["_meta"]["pipeline"]["title"]=="One" and not opened.get("isError")
                read=await rpc("tools/call",{"name":"read_pipeline","arguments":{}})
                assert read["structuredContent"]["result"]["total"]==0
                ui=await rpc("resources/read",{"uri":pipeline.RESOURCE})
                assert "pipelineMount" in ui["contents"][0]["text"]
                wrong={**headers,"Authorization":"Bearer elsewhere"}
                assert (await client.post(endpoint,headers=wrong,json={})).status_code==401
    asyncio.run(scenario())
