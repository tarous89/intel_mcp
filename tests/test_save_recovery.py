"""Real tool calls against synthetic storage: bounded retries and exact identities."""
import asyncio
from collections import Counter
from copy import deepcopy
from types import SimpleNamespace

import pytest
from mcp import Client
from intel_mcp.control_plane import ControlPlaneError
from intel_mcp.research_server import create_research_server
from intel_mcp.save_recovery import retry_storage, with_save_retries
from test_selection import criteria, record
from test_selection_service import Engine

SETTINGS=SimpleNamespace(mcp_public_resource_url='https://synthetic.invalid/mcp',oauth_authorization_server_url='https://synthetic.invalid')
PROJECT='00000000-0000-0000-0000-000000000001'
PREVIEW={'preview_id':PROJECT,'selection_id':'s'*43,'title':'Synthetic','snapshot_key':'a'*64,'cache_token':'b'*43}
VIEW={'preview':PREVIEW,'title':'Comparison','query':'Compare','summary':'','html':'<h1>Synthetic comparison</h1>',
      'source_ids':[],'dataset_id':'a'*64,'revision':1,'request_key':'same-original-key','evidence_basis':'project_tables'}


@pytest.mark.anyio
@pytest.mark.parametrize('operation',['stream','canonical_commit','canonical_read'])
@pytest.mark.parametrize('failures',[1,2,3])
async def test_project_retries_keep_identity_and_never_repeat_research(monkeypatch,operation,failures):
    monkeypatch.setattr('intel_mcp.research_workspace.current_oauth_subject',lambda:'owner')
    calls=[];counts=Counter();stored_project=None
    def attempt(name,body):
        calls.append((name,deepcopy(body)));counts[name]+=1
        if name==operation and counts[name]<=failures:raise ControlPlaneError('TEMPORARY_FAILURE','Unavailable',503)
    class Control:
        async def research_access(self,*_):return {'fullAccess':True}
        async def stream_research_preview(self,*args):attempt('stream',args)
        async def research_workspace(self,body):
            nonlocal stored_project
            # A lost response may occur after the write has committed.
            if body['operation']=='canonical_commit':stored_project=body['input']['proposedProjectId']
            attempt(body['operation'],body)
            if body['operation']=='canonical_commit':return {'project_id':stored_project}
            return {'project_id':stored_project,'saved':True,'canonical':True,'revision':1,'result':{'entity_type':'sites','entities':[]}}
    engine=Engine([record()]);server,_,store,*_=create_research_server(SETTINGS,lambda:engine,lambda:Control())
    selection,_=await store.search(criteria())
    async with Client(server) as client:
        out=(await client.call_tool('publish_research_workspace',{'selection_id':selection,'title':'Original'})).structured_content
    assert counts[operation]==min(3,failures+1)
    assert engine.calls==1
    attempted=[body for name,body in calls if name==operation]
    assert all(body==attempted[0] for body in attempted)
    if failures<3:assert out['saved'] is True
    else:
        assert out['saved'] is False and out['automatic_retry_complete'] is True
        assert out['recovery']['retry_tool']=='save_project'
        assert out['result'] and out['draft']
    if operation=='canonical_read':assert counts['canonical_commit']==1


@pytest.mark.anyio
async def test_publication_shares_one_retry_budget_across_storage_stages(monkeypatch):
    monkeypatch.setattr('intel_mcp.research_workspace.current_oauth_subject',lambda:'owner')
    counts=Counter()
    def attempt(name):
        counts[name]+=1
        if counts[name]==1:raise ControlPlaneError('TEMPORARY_FAILURE','Unavailable',503)
    class Control:
        async def research_access(self,*_):return {'fullAccess':True}
        async def stream_research_preview(self,*_):attempt('stream')
        async def research_workspace(self,b):
            attempt(b['operation'])
            return {'project_id':PROJECT}
    server,_,store,*_=create_research_server(SETTINGS,lambda:Engine([record()]),lambda:Control())
    selection,_=await store.search(criteria())
    async with Client(server) as client:
        out=(await client.call_tool('publish_research_workspace',{'selection_id':selection,'title':'Original'})).structured_content
    assert counts=={'stream':2,'canonical_commit':2,'canonical_read':1}
    assert out['automatic_retry_complete'] and out['save_status']=='failed'


@pytest.mark.anyio
@pytest.mark.parametrize('operation',['report_save','report_read'])
@pytest.mark.parametrize('failures',[1,2,3])
async def test_custom_view_retries_only_failed_step_and_retains_exact_content(operation,failures):
    calls=[];counts=Counter()
    report={'id':'view','version':1,'html':VIEW['html']}
    class Control:
        async def research_workspace(self,b):
            calls.append(deepcopy(b));counts[b['operation']]+=1
            if b['operation']==operation and counts[operation]<=failures:raise ControlPlaneError('TEMPORARY_FAILURE','Unavailable',503)
            if b['operation']=='report_save':return {'report':report,'temporary':True}
            if b['operation']=='report_read':return {'report':report}
            return {'project_id':PROJECT,'reports':[report],'result':{'entity_type':'trials','entities':[]}}
    server,*_=create_research_server(SETTINGS,lambda:None,lambda:Control())
    async with Client(server) as client:
        out=(await client.call_tool('save_project_custom_view',VIEW)).structured_content
    assert counts[operation]==min(3,failures+1)
    attempted=[b for b in calls if b['operation']==operation]
    assert all(b==attempted[0] for b in attempted)
    if operation=='report_read':assert counts['report_save']==1
    if failures<3:assert out['custom_view_saved'] is True
    else:
        assert out['custom_view_saved'] is False and out['retry_id']
        assert out['automatic_retry_complete'] and 'result' not in out


@pytest.mark.anyio
@pytest.mark.parametrize('status',[400,401,403,404,409,410,413,429])
@pytest.mark.parametrize('tool',['save_project','save_project_custom_view'])
async def test_nontransient_failures_are_not_retried(monkeypatch,status,tool):
    monkeypatch.setattr('intel_mcp.research_workspace.current_oauth_subject',lambda:'owner')
    calls=[]
    class Control:
        async def research_workspace(self,b):
            calls.append(b)
            raise ControlPlaneError('NONRETRYABLE','Needs correction or permission',status)
    server,*_=create_research_server(SETTINGS,lambda:None,lambda:Control())
    async with Client(server) as client:
        await client.call_tool(tool,{'preview':PREVIEW} if tool=='save_project' else VIEW)
    assert len(calls)==1


@pytest.mark.anyio
async def test_cancelled_save_is_not_retried():
    calls=0
    async def operation():
        nonlocal calls
        calls+=1
        raise asyncio.CancelledError()
    @with_save_retries
    async def save():return await retry_storage(operation)
    with pytest.raises(asyncio.CancelledError):await save()
    assert calls==1


@pytest.mark.anyio
async def test_read_only_calls_do_not_acquire_a_write_retry_budget():
    calls=[]
    class Control:
        async def research_workspace(self,b):
            calls.append(b)
            raise ControlPlaneError('TEMPORARY_FAILURE','Unavailable',503)
    server,*_=create_research_server(SETTINGS,lambda:None,lambda:Control())
    async with Client(server) as client:
        await client.call_tool('read_project_custom_view',{'preview':PREVIEW,'custom_view_id':'view'})
    assert len(calls)==1
