from types import SimpleNamespace
import pytest
from mcp import Client
from intel_mcp.research_server import create_research_server
from intel_mcp.research_workspace import workspace_payload
from intel_mcp.selection import SelectionDataset
from test_selection import record,provider,criteria
from test_selection_service import Engine


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
async def test_workspace_write_and_page_metadata_and_retry_token():
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
        assert descriptors['prepare_research_workspace'].annotations.read_only_hint is False
        assert descriptors['get_research_workspace'].annotations.read_only_hint is True
        assert descriptors['prepare_research_workspace'].meta['ui']['resourceUri']=='ui://trialagents/workspace-v1'
        assert 'ui' not in descriptors['rank_research_entities'].meta
        resource=await client.read_resource('ui://trialagents/workspace-v1')
        assert resource.contents[0].meta['openai/ui']['preferredDisplayMode']=='fullscreen'
        search=await client.call_tool('search_research_trials',{'criteria':criteria().model_dump(mode='json')})
        assert search.structured_content['presentation']['tool']=='prepare_research_workspace'
        assert search.structured_content['presentation']['selection_id']==search.structured_content['selection_id']
        for _ in range(2):
            out=await client.call_tool('prepare_research_workspace',{'selection_id':token,'title':'Research'})
            assert not out.is_error and len(out.structured_content['preview_token'])==43
            assert out.structured_content['url'].endswith('#preview='+out.structured_content['preview_token'])
        assert control.calls[0]['previewToken']==control.calls[2]['previewToken']
        assert len(control.calls[0]['payload']['sections'])==4
        denied=await client.call_tool('claim_research_workspace',{'project_id':out.structured_content['project_id'],'preview_token':out.structured_content['preview_token']})
        assert denied.is_error and denied.meta['mcp/www_authenticate']
