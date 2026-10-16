"""Publication contract and lost-response regression checks with synthetic data."""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from jsonschema import validate
from mcp import Client
from intel_mcp.control_plane import ControlPlaneError
from intel_mcp.research_server import create_research_server, UI_DOMAIN
from test_selection import criteria, record, provider
from test_selection_service import Engine

SETTINGS=SimpleNamespace(mcp_public_resource_url='https://mcp.synthetic.invalid/mcp',oauth_authorization_server_url='https://app.synthetic.invalid')


@pytest.mark.anyio
async def test_publication_contract_preserves_tools_and_declares_real_effects():
    server,*_=create_research_server(SETTINGS,lambda:None,lambda:None)
    async with Client(server) as client:
        descriptors={t.name:t for t in (await client.list_tools()).tools}
        assert len(descriptors)==38
        for tool in descriptors.values():
            assert tool.output_schema and tool.output_schema['type']=='object', tool.name
            assert all(isinstance(getattr(tool.annotations,key),bool) for key in ('read_only_hint','destructive_hint','open_world_hint'))
        for name in ('read_trial_profiles','read_report_evidence','read_report_document','read_trial_document'):
            hints=descriptors[name].annotations
            assert hints.read_only_hint is False and hints.destructive_hint is False
        for name in ('save_project','save_project_view','revise_research_workspace','save_project_report','retry_project_report','save_visualization_state'):
            assert descriptors[name].annotations.destructive_hint is True
        for name in ('search_research_trials','rank_research_entities','prepare_project_report','list_trial_documents','open_project','read_project_report'):
            assert descriptors[name].annotations.read_only_hint is True
        for name in ('claim_research_workspace','revise_research_workspace','save_research_project'):
            assert 'resourceUri' not in descriptors[name].meta['ui']
        for resource in (await client.list_resources()).resources:
            result=await client.read_resource(resource.uri)
            for content in result.contents:
                assert content.meta['ui']['domain']==UI_DOMAIN
                assert content.meta['openai/widgetDomain']==UI_DOMAIN
                assert content.meta['ui']['csp']['connectDomains']==[]


@pytest.mark.anyio
async def test_publish_lost_response_retry_preserves_full_commit_identity(monkeypatch):
    owner='synthetic-owner-one'
    monkeypatch.setattr('intel_mcp.research_workspace.current_oauth_subject',lambda:owner)
    receipts={}; calls=[]; cached={}; lose_response=True
    class Control:
        async def research_access(self,*_):return {'fullAccess':True}
        async def stream_research_preview(self,token,snapshot,payload,prepared):
            previous=cached.setdefault(token,snapshot)
            assert previous==snapshot
        async def research_workspace(self,body):
            nonlocal lose_response
            calls.append(deepcopy(body))
            if body['operation']=='canonical_commit':
                command=body['input'];key=(owner,command['idempotencyKey'])
                old=receipts.setdefault(key,deepcopy(command))
                assert old==command, 'A repeated receipt must have the same cache token and preview identity'
                if lose_response:
                    lose_response=False
                    raise ControlPlaneError('TEMPORARY_FAILURE','Response lost after commit',502)
                return {'project_id':command['proposedProjectId']}
            assert body['operation']=='canonical_read'
            return {'project_id':body['projectId'],'saved':True,'result':{'entities':[]}}
    control=Control()
    engine=Engine([record(providers=[provider()])])
    server,_,store,*_=create_research_server(SETTINGS,lambda:engine,lambda:control)
    token,_=await store.search(criteria())
    args={'selection_id':token,'title':'Synthetic retry case'}
    async with Client(server) as client:
        first=(await client.call_tool('publish_research_workspace',args)).structured_content
        assert first['save_status']=='failed' and first['recovery']['draft_retained']
        second=(await client.call_tool('publish_research_workspace',args)).structured_content
        assert second['saved'] is True
        assert second['project_id']==first['draft']['preview_id']
        assert len(receipts)==1
        # Retries, including a harmless tab change, retain the canonical project.
        third=(await client.call_tool('publish_research_workspace',{**args,'kind':'sites'})).structured_content
        assert third['project_id']==second['project_id'] and len(receipts)==1
        # An explicit distinct operation remains a distinct project, and is retryable.
        separate={**args,'operation_id':'intentional-new-project'}
        fourth=(await client.call_tool('publish_research_workspace',separate)).structured_content
        again=(await client.call_tool('publish_research_workspace',separate)).structured_content
        assert fourth['project_id']!=second['project_id']
        assert again['project_id']==fourth['project_id'] and len(receipts)==2
        owner='synthetic-owner-two'
        other=(await client.call_tool('publish_research_workspace',args)).structured_content
        assert other['project_id']!=second['project_id'] and len(receipts)==3
        owner=None
        guest=(await client.call_tool('publish_research_workspace',args)).structured_content
        repeated=(await client.call_tool('publish_research_workspace',args)).structured_content
        # Search results can be cached across guests. Never share their private
        # preview/report capabilities just because their public query is identical.
        assert guest['saved'] is False
        assert guest['draft']['preview_id']!=repeated['draft']['preview_id']
        assert guest['draft']['cache_token']!=repeated['draft']['cache_token']
        assert len(receipts)==3
    assert engine.calls==1


@pytest.mark.anyio
async def test_legacy_schema_preserves_structured_response_and_oauth_challenge(monkeypatch):
    class Control:
        async def research_access(self,*_):return {'fullAccess':False,'projects':[],'account_message':'Free research'}
        async def research_project(self,body):
            if body['operation']=='save':return {'project_id':'00000000-0000-0000-0000-000000000001','title':body['title'],'message':'Saved','url':'https://app.synthetic.invalid/project'}
            raise AssertionError('Unexpected operation')
    server,_,store,*_=create_research_server(SETTINGS,lambda:Engine([record(providers=[provider()])]),lambda:Control())
    token,_=await store.search(criteria())
    async with Client(server) as client:
        tools={t.name:t for t in (await client.list_tools()).tools}
        auth=await client.call_tool('list_research_projects',{})
        assert auth.is_error and auth.meta['mcp/www_authenticate']
        monkeypatch.setattr('intel_mcp.research_server.current_oauth_subject',lambda:'synthetic-owner')
        for name,args in [('list_research_projects',{}),('save_research_project',{'selection_ids':[token],'title':'Synthetic save'})]:
            result=await client.call_tool(name,args)
            assert not result.is_error and result.structured_content['view']
            validate(result.structured_content,tools[name].output_schema)
