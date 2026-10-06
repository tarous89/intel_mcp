import asyncio
from types import SimpleNamespace
import pytest
import httpx
import os
import subprocess
import sys
from mcp import Client
from intel_mcp.research_access import ResearchStore,public_ranking,public_evidence
from intel_mcp.research_server import create_research_server,ResearchAuth
from intel_mcp.selection import SelectionDataset,SelectionError
from intel_mcp.auth_context import set_oauth_subject,reset_oauth_subject,current_oauth_subject
from test_selection import criteria,record,provider
from test_selection_service import Engine


def many():
    return [record(i,providers=[{**provider(f'CRO {i:02d}'),'email':f'contact{i}@synthetic.invalid'}]) for i in range(1,26)]


def test_free_boundary_counts_contacts_and_no_evidence_enumeration():
    d=SelectionDataset(criteria(),many())
    r=public_ranking(d)
    assert r.total_entities==25 and r.returned==10
    assert r.entities[0].contacts[0]['email']=='contact1@synthetic.invalid'
    assert 'operational_findings' not in r.entities[0].evidence[0]
    eleventh=d.rank(11).entities[-1].id
    for kwargs in ({'offset':10},{'limit':11}):
        with pytest.raises(SelectionError,match='ACCOUNT_ACCESS_REQUIRED'): public_ranking(d,**kwargs)
    with pytest.raises(SelectionError,match='ENTITY_ACCESS_REQUIRED'): public_evidence(d,eleventh)
    assert public_evidence(d,eleventh,full_access=True).total_trials==1
    assert len(public_ranking(d,offset=10,limit=100,full_access=True).entities)==15


@pytest.mark.anyio
async def test_cache_and_expiry_do_not_reread_every_tool():
    engine=Engine(many());store=ResearchStore(lambda:engine)
    token,d=await store.search(criteria())
    assert (await store.search(criteria()))[0]==token and engine.calls==1
    store.entries[token]['expires']=0
    with pytest.raises(SelectionError,match='EXPIRED'): store.get(token)
    new,_=await store.search(criteria());assert new!=token and engine.calls==2


@pytest.mark.anyio
async def test_public_mcp_surface_and_project_entitlement_rechecks():
    settings=SimpleNamespace(mcp_public_resource_url='https://mcp.synthetic.invalid/mcp',oauth_authorization_server_url='https://app.synthetic.invalid')
    class Control:
        allowed=True
        calls=0
        async def research_access(self,project,ids):
            assert current_oauth_subject()=='owner'
            self.calls+=1
            return {'fullAccess':self.allowed,'projects':[]}
    control=Control();engine=Engine(many())
    server,_,_,_,_=create_research_server(settings,lambda:engine,lambda:control)
    async with Client(server) as client:
        names={t.name for t in (await client.list_tools()).tools}
        assert names=={'search_research_trials','rank_research_entities','get_research_entity_evidence','list_research_projects'}
        linking=await client.call_tool('list_research_projects',{})
        assert linking.is_error and linking.meta['mcp/www_authenticate']
        search=await client.call_tool('search_research_trials',{'criteria':criteria().model_dump(mode='json')})
        assert not search.is_error
        token=search.structured_content['selection_id']
        rank=await client.call_tool('rank_research_entities',{'selection_id':token})
        assert not rank.is_error and rank.structured_content['returned']==10
        assert (await client.call_tool('rank_research_entities',{'selection_id':token,'offset':10})).is_error
        evidence = await client.call_tool('get_research_entity_evidence',{'selection_id':token,'entity_id':rank.structured_content['entities'][0]['id'],'sections':['sites']})
        assert 'sections' not in str(evidence.structured_content) and 'operational_findings' not in str(evidence.structured_content)
    # Full access is enforced independently of tool metadata and rechecked per call.
    marker=set_oauth_subject('owner')
    try:
        async with Client(server) as client:
            args={'selection_id':token,'offset':10,'project_id':'00000000-0000-0000-0000-000000000001'}
            paid=await client.call_tool('rank_research_entities',args)
            assert not paid.is_error and paid.structured_content['access']=='full'
            assert control.calls==2
            control.allowed=False
            assert (await client.call_tool('rank_research_entities',args)).is_error
    finally: reset_oauth_subject(marker)


@pytest.mark.anyio
async def test_mixed_auth_never_downgrades_invalid_token_to_anonymous():
    subjects=[]
    async def downstream(scope,receive,send):
        subjects.append(current_oauth_subject())
        from starlette.responses import JSONResponse
        await JSONResponse({'ok':True})(scope,receive,send)
    class Control:
        async def introspect_access_token(self,token):
            return {'active':token=='valid','sub':'owner','scope':'mcp:tools','resource':'research'}
    app=ResearchAuth(downstream,Control,'research','Bearer')
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://example.test') as client:
        assert (await client.get('/mcp')).status_code==200
        assert (await client.get('/mcp',headers={'Authorization':'Bearer invalid'})).status_code==401
        assert (await client.get('/mcp',headers={'Authorization':'Bearer valid'})).status_code==200
    assert subjects==[None,'owner'] and current_oauth_subject() is None


def test_enabled_http_mount_lifespans_metadata_and_private_isolation():
    script='''
from starlette.testclient import TestClient
from intel_mcp.server import app
with TestClient(app) as client:
    metadata=client.get('/research/.well-known/oauth-protected-resource')
    assert metadata.status_code==200, metadata.text
    assert metadata.json()['resource'].endswith('/research/mcp')
    assert client.post('/mcp',json={}).status_code==401
    response=client.post('/research/mcp',headers={'Accept':'application/json, text/event-stream'},json={'jsonrpc':'2.0','id':1,'method':'tools/list','params':{}})
    assert response.status_code==200,response.text
    assert 'search_research_trials' in response.text
    assert 'get_trial_profiles' not in response.text
'''
    result=subprocess.run([sys.executable,'-c',script],env={**os.environ,'MCP_RESEARCH_ENABLED':'true','MCP_ALLOWED_HOSTS':'testserver','MCP_INBOUND_SERVICE_TOKEN':'synthetic-only'},capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
