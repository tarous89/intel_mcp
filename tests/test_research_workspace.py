from types import SimpleNamespace
import pytest
from mcp import Client
from intel_mcp.research_server import create_research_server
from intel_mcp.research_workspace import workspace_payload,compact_workspace_evidence,RESOURCE,LEGACY_RESOURCE,WORKSPACE_HTML
from intel_mcp.selection import SelectionDataset
from test_selection import record,provider,criteria
from test_selection_service import Engine

def test_shared_narratives_preserve_every_entity_and_trial_above_old_size_limit():
    from copy import deepcopy
    import json
    tid='2025-000001-00-00'
    evidence={'trial_id':tid,'title':'Synthetic trial','roles':['Monitoring'],
              'operational_findings':['Recorded trial finding '*1000],'discovery_evidence':['source']}
    sections=[{'entity_type':kind,'result':{'entities':[{'id':str(i),'evidence':[deepcopy(evidence)]} for i in range(300)]}}
              for kind in ('cros','sites','pis')]
    original=deepcopy(sections)
    assert len(json.dumps(original).encode())>12*1024*1024
    shared=compact_workspace_evidence(sections)
    assert len(shared)==1
    assert len(json.dumps({'sections':sections,'shared_evidence':shared}).encode())<1024*1024
    restored=deepcopy(sections)
    for section in restored:
        for entity in section['result']['entities']:
            entity['evidence']=[{**shared[e['trial_id']],**e} for e in entity['evidence']]
    assert restored==original


def test_four_tables_share_one_cohort_and_no_implicit_contacts():
    data=SelectionDataset(criteria(),[record(i,providers=[{**provider(),'email':'recorded@synthetic.invalid'}]) for i in range(1,3)])
    payload=workspace_payload(data,'Selected trials')
    assert {s['entity_type'] for s in payload['sections']}=={'cros','sites','pis','trials'}
    assert all(s['trial_ids']==sorted(data.records) for s in payload['sections'])
    assert 'recorded@' not in str(payload)
    assert 'recorded@' in str(workspace_payload(data,'Selected trials',True))
    trials=payload['sections'][-1]['result']['entities']
    assert len(trials)==2 and 'profile' not in str(trials) and 'providers' not in str(trials)


@pytest.mark.anyio
async def test_workspace_preview_is_read_only_and_creates_nothing():
    class Control:
        calls=[]
        async def research_workspace(self,body):
            self.calls.append(body)
            if body['operation']=='read':
                assert 'revision' not in body or (isinstance(body['revision'],int) and body['revision']>0)
            if body['operation']=='create':return {'project_id':'00000000-0000-0000-0000-000000000001','revision':1}
            return {'project_id':body['projectId'],'revision':1,'owned':False,'result':{'entity_type':'cros','entities':[]}}
    control=Control();engine=Engine([record()])
    settings=SimpleNamespace(mcp_public_resource_url='https://mcp.synthetic.invalid/mcp',oauth_authorization_server_url='https://app.synthetic.invalid')
    server,_,store,_,_=create_research_server(settings,lambda:engine,lambda:control)
    token,_=await store.search(criteria())
    async with Client(server) as client:
        descriptors={t.name:t for t in (await client.list_tools()).tools}
        for name in ('prepare_research_workspace','get_research_workspace','create_research_account_handoff'):
            assert descriptors[name].meta['ui']['visibility']==['model','app']
            assert descriptors[name].meta['openai/widgetAccessible'] is True
        assert descriptors['create_research_account_handoff'].annotations.read_only_hint is False
        assert descriptors['prepare_research_workspace'].annotations.read_only_hint is True
        assert descriptors['get_research_workspace'].annotations.read_only_hint is True
        assert descriptors['prepare_research_workspace'].meta['ui']['resourceUri']==RESOURCE
        assert 'ui' not in descriptors['rank_research_entities'].meta
        assert 'ui' not in descriptors['get_research_entity_evidence'].meta
        assert 'explicitly requests' in descriptors['get_research_entity_evidence'].description
        resource=await client.read_resource(RESOURCE)
        import hashlib
        assert RESOURCE=='ui://trialagents/workspace-'+hashlib.sha256(WORKSPACE_HTML.encode()).hexdigest()[:16]
        legacy=await client.read_resource(LEGACY_RESOURCE)
        assert legacy.contents[0].text==resource.contents[0].text
        assert resource.contents[0].meta['openai/ui']['preferredDisplayMode']=='fullscreen'
        search=await client.call_tool('search_research_trials',{'criteria':criteria().model_dump(mode='json')})
        assert search.structured_content['presentation']['tool']=='prepare_research_workspace'
        assert search.structured_content['presentation']['selection_id']==search.structured_content['selection_id']
        for _ in range(2):
            out=await client.call_tool('prepare_research_workspace',{'selection_id':token,'title':'Research'})
            assert not out.is_error
            assert out.structured_content['saved'] is False
            assert out.structured_content['draft']['selection_id']==token
            assert set(out.structured_content['preview_tables'])=={'cros','sites','pis','trials'}
            assert out.structured_content['presentation']['supporting_trials']=='only_on_explicit_request'
            assert 'url' not in out.structured_content
        assert control.calls==[]
        denied=await client.call_tool('claim_research_workspace',{'project_id':out.structured_content['project_id'],'preview_token':'a'*43})
        assert denied.is_error and denied.meta['mcp/www_authenticate']

@pytest.mark.anyio
async def test_connect_saves_original_project_and_retries_without_recreating(monkeypatch):
    from intel_mcp.auth_context import current_oauth_subject
    project_id='00000000-0000-0000-0000-000000000001'
    calls=[]
    class Control:
        async def research_workspace(self,body):
            calls.append(body)
            assert body['projectId']==project_id
            assert body['operation'] in ('claim','read')
            return {'project_id':project_id,'revision':3,'owned':True,'result':{'entity_type':'cros','entities':[]}}
    settings=SimpleNamespace(mcp_public_resource_url='https://mcp.synthetic.invalid/mcp',oauth_authorization_server_url='https://app.synthetic.invalid')
    server,*_=create_research_server(settings,lambda:Engine([record()]),lambda:Control())
    # Emulate verified OAuth identity after the host finishes login or signup.
    monkeypatch.setattr('intel_mcp.research_workspace.current_oauth_subject',lambda:'owner')
    async with Client(server) as client:
        for _ in range(2):
            out=await client.call_tool('claim_research_workspace',{'project_id':project_id,'preview_token':'a'*43})
            assert not out.is_error
            saved=out.structured_content
            assert saved['saved'] and saved['owned'] and saved['revision']==3
            assert saved['projects_url']=='https://intel.trialagents.com/projects'
            assert 'preview_token' not in saved
    assert [c['operation'] for c in calls]==['claim','read','claim','read']

@pytest.mark.anyio
async def test_direct_website_handoff_is_available_without_host_oauth():
    calls=[]
    project_id='00000000-0000-0000-0000-000000000001'
    class Control:
        async def research_workspace(self,body):
            calls.append(body)
            return {'url':'https://intel.trialagents.com/auth?mode=login&connect=1#handoff='+'b'*43}
    settings=SimpleNamespace(mcp_public_resource_url='https://mcp.synthetic.invalid/mcp',oauth_authorization_server_url='https://app.synthetic.invalid')
    server,*_=create_research_server(settings,lambda:Engine([record()]),lambda:Control())
    async with Client(server) as client:
        descriptor=next(t for t in (await client.list_tools()).tools if t.name=='create_research_account_handoff')
        assert descriptor.annotations.read_only_hint is False
        out=await client.call_tool('create_research_account_handoff',{'project_id':project_id,'preview_token':'a'*43})
        assert not out.is_error
        assert out.structured_content['url'].startswith('https://intel.trialagents.com/auth?')
    assert calls==[{'operation':'handoff','projectId':project_id,'previewToken':'a'*43}]

@pytest.mark.anyio
async def test_preview_connect_preserves_snapshot_idempotency_and_expiry(monkeypatch):
    from copy import deepcopy
    from intel_mcp.research_workspace import payload_key
    calls=[]
    class Control:
        async def research_access(self,*args):return {'fullAccess':True}
        async def research_workspace(self,body):
            calls.append(deepcopy(body))
            if body['operation']=='create':return {'project_id':'00000000-0000-0000-0000-000000000002','revision':1}
            return {'url':'https://intel.trialagents.com/auth?mode=login&connect=1#handoff='+'b'*43}
    settings=SimpleNamespace(mcp_public_resource_url='https://mcp.synthetic.invalid/mcp',oauth_authorization_server_url='https://app.synthetic.invalid')
    server,_,store,_,_=create_research_server(settings,lambda:Engine([record(i,providers=[provider(name='CRO '+str(i))]) for i in range(1,15)]),lambda:Control())
    selection,_=await store.search(criteria())
    async with Client(server) as client:
        out=await client.call_tool('prepare_research_workspace',{'selection_id':selection,'title':'Exact original'})
        assert not out.is_error
        data=out.structured_content
        assert len(data['result']['entities'])==10
        assert data['result']['next_offset'] is None
        assert calls==[]
        spec=data['draft']
        bad=await client.call_tool('prepare_research_workspace',{'selection_id':selection,'title':'Exact original','offset':10})
        assert bad.is_error
        # Signed-in users still get an unsaved read-only preview; access is honored.
        monkeypatch.setattr('intel_mcp.research_workspace.current_oauth_subject',lambda:'owner')
        paid=await client.call_tool('prepare_research_workspace',{'selection_id':selection,'title':'Exact original','offset':10})
        assert not paid.is_error and paid.structured_content['result']['access']=='full'
        assert paid.structured_content['saved'] is False and calls==[]
        for _ in range(2):
            saved=await client.call_tool('create_research_account_handoff',{'project_id':data['project_id'],'draft':spec})
            assert not saved.is_error
        assert [c['operation'] for c in calls]==['create','handoff','create','handoff']
        assert calls[0]==calls[2]
        assert payload_key(calls[0]['payload'])==spec['snapshot_key']
        assert calls[0]['payload']['title']=='Exact original'
        assert calls[1]['projectId']=='00000000-0000-0000-0000-000000000002'
        changed={**spec,'title':'Different'}
        denied=await client.call_tool('create_research_account_handoff',{'project_id':data['project_id'],'draft':changed})
        assert denied.is_error and len(calls)==4
        store.entries[selection]['expires']=0
        expired=await client.call_tool('create_research_account_handoff',{'project_id':data['project_id'],'draft':spec})
        assert expired.is_error and len(calls)==4

@pytest.mark.anyio
async def test_precomputed_preview_cache_retains_exact_four_tables_without_creating_project():
    import gzip, base64, json
    cached=[]
    class Control:
        async def cache_research_preview(self, body):
            cached.append(body)
            return {'expires_in_seconds':86400}
        async def research_workspace(self, body):
            raise AssertionError('a search cache must not create a project')
    settings=SimpleNamespace(mcp_public_resource_url='https://mcp.synthetic.invalid/mcp',oauth_authorization_server_url='https://app.synthetic.invalid')
    server,_,store,_,_=create_research_server(settings,lambda:Engine([record()]),lambda:Control())
    token,_=await store.search(criteria())
    async with Client(server) as client:
        response=await client.call_tool('prepare_research_workspace',{'selection_id':token,'title':'Exact cohort'})
        assert not response.is_error
        out=response.structured_content
        assert out['saved'] is False and out['expires_in_seconds']==86400
        assert out['draft']['cache_token']==cached[0]['token']
        from intel_mcp.research_workspace import payload_key
        payload=json.loads(gzip.decompress(base64.b64decode(cached[0]['gzip'])))
        assert payload_key(payload)==out['draft']['snapshot_key']
        assert payload==workspace_payload(store.get(token),'Exact cohort')
