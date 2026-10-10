from types import SimpleNamespace
from copy import deepcopy
import pytest
from mcp import Client
from intel_mcp.research_server import create_research_server
from test_selection import criteria, record
from test_selection_service import Engine


@pytest.mark.anyio
async def test_canonical_save_is_oauth_write_and_preview_paging_never_rebuilds(monkeypatch):
    calls = []
    project = '00000000-0000-0000-0000-000000000001'
    class Control:
        async def research_workspace(self, body):
            calls.append(deepcopy(body))
            if body['operation'] == 'canonical_commit': return {'project_id': project}
            if body['operation'] == 'canonical_list': return {'projects': [{'project_id': project}]}
            return {'canonical': True, 'project_id': project, 'owned': True, 'saved': True,
                    'revision': 3, 'result': {'entity_type': 'sites', 'entities': []}}
    settings=SimpleNamespace(mcp_public_resource_url='https://mcp.synthetic.invalid/mcp',oauth_authorization_server_url='https://app.synthetic.invalid')
    server,_,store,*_=create_research_server(settings,lambda:Engine([record()]),lambda:Control())
    preview={'preview_id':project,'selection_id':'s'*43,'title':'Refined research','snapshot_key':'a'*64,'cache_token':'b'*43}
    async with Client(server) as client:
        tools={t.name:t for t in (await client.list_tools()).tools}
        assert tools['save_project'].annotations.read_only_hint is False
        assert tools['save_project'].meta['securitySchemes']==[{'type':'oauth2','scopes':['mcp:tools']}]
        for name in ('open_project','list_projects','read_project_preview'):
            assert tools[name].annotations.read_only_hint is True
        for name in ('save_research_project','revise_research_workspace','claim_research_workspace','create_research_account_handoff'):
            assert tools[name].meta['ui']['visibility']==['app'], 'new model saves must use the canonical writer'
        denied=await client.call_tool('save_project',{'preview':preview})
        assert denied.is_error and denied.meta['mcp/www_authenticate'] and not calls
        # No selection in the in-memory store: cache reads/saves must survive it.
        assert not store.entries
        page=await client.call_tool('read_project_preview',{'preview':preview,'kind':'sites'})
        assert not page.is_error and calls[-1]['operation']=='preview_read'
        monkeypatch.setattr('intel_mcp.research_workspace.current_oauth_subject',lambda:'owner')
        for _ in range(2):
            saved=await client.call_tool('save_project',{'preview':preview})
            assert not saved.is_error and saved.structured_content['project_id']==project
        writes=[c for c in calls if c['operation']=='canonical_commit']
        assert len(writes)==2 and writes[0]==writes[1]
        assert writes[0]['input']['proposedProjectId']==project
        revised=await client.call_tool('save_project',{'preview':preview,'project_id':project,'expected_revision':3})
        assert not revised.is_error
        assert calls[-2]['input']['projectId']==project and calls[-2]['input']['expectedRevision']==3
        listed=await client.call_tool('list_projects',{})
        assert listed.structured_content['projects'][0]['project_id']==project
