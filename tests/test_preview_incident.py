import json
import gzip
import base64
import hashlib
from types import SimpleNamespace
from copy import deepcopy
import pytest
from mcp import Client
from intel_mcp.control_plane import ControlPlaneError
from intel_mcp.research_server import create_research_server
from intel_mcp.preview_stream import snapshot_chunks, MAX_CHUNK
from intel_mcp.prepared_selection import prepare_selection
from intel_mcp.research_workspace import workspace_payload
from intel_mcp.selection import SelectionDataset, SelectionError
from test_selection import record, criteria
from test_selection_service import Engine

SETTINGS=SimpleNamespace(mcp_public_resource_url='https://synthetic.invalid/research/mcp',oauth_authorization_server_url='https://synthetic.invalid')


def test_stream_protocol_preserves_exact_rows_profiles_and_checksum():
    data=SelectionDataset(criteria(),[record(i) for i in range(1,13)])
    payload=workspace_payload(data,'Synthetic exact research')
    prepared=prepare_selection(data)
    packets=list(snapshot_chunks('t'*43,'a'*64,payload,prepared))
    raw=[gzip.decompress(base64.b64decode(json.loads(p)['gzip'])) for p in packets[:-1]]
    assert all(len(p)<=MAX_CHUNK for p in raw)
    assert json.loads(packets[-1])['finish']==hashlib.sha256(b''.join(p+b'\n' for p in raw)).hexdigest()
    decoded=[json.loads(p) for p in raw]
    assert [p['row'] for p in decoded if p['type']=='profile']==prepared['records']
    for section in payload['sections']:
        assert [r for p in decoded if p.get('kind')==section['entity_type'] for r in p['rows']]==section['result']['entities']
    payload['sections'][0]['result']['entities'][0]['oversized']='x'*(MAX_CHUNK+1)
    with pytest.raises(SelectionError,match='SNAPSHOT_CHUNK_TOO_LARGE'):
        list(snapshot_chunks('t'*43,'a'*64,payload,prepared))


@pytest.mark.anyio
async def test_failed_storage_retains_identity_then_recovers_without_search(monkeypatch):
    monkeypatch.setattr('intel_mcp.research_workspace.current_oauth_subject',lambda:'owner')
    failed=True;uploads=[];operations=[]
    class Control:
        async def research_access(self,*_):return {'fullAccess':False}
        async def stream_research_preview(self,token,snapshot,payload,prepared):
            uploads.append((token,snapshot,deepcopy(payload),deepcopy(prepared)))
            if failed:raise ControlPlaneError('PREVIEW_STORAGE_UNAVAILABLE','Unavailable',502)
        async def research_workspace(self,b):
            operations.append(b)
            if b['operation']=='canonical_commit':return {'project_id':b['input']['proposedProjectId']}
            if b['operation']=='canonical_read':return {'project_id':b['projectId'],'saved':True,'canonical':True,'result':{'entity_type':'sites','entities':[]}}
            return {'project_id':b['preview']['preview_id'],'saved':False,'draft':b['preview'],'result':{'entity_type':'cros','entities':[]}}
    engine=Engine([record()]);server,_,store,_,_=create_research_server(SETTINGS,lambda:engine,lambda:Control())
    selection,_=await store.search(criteria())
    async with Client(server) as client:
        tools={x.name:x for x in (await client.list_tools()).tools}
        assert tools['publish_research_workspace'].annotations.read_only_hint is False
        first=await client.call_tool('publish_research_workspace',{'selection_id':selection,'title':'Exact original'})
        out=first.structured_content
        assert not first.is_error and out['storage_status']=='unavailable'
        assert out['saved'] is False and out['draft']['cache_token']
        assert operations==[]
        # No new search is allowed during any recovery.
        async def no_search(*a,**k):raise AssertionError('recovery repeated search')
        monkeypatch.setattr(store,'search',no_search)
        failed=False
        saved=await client.call_tool('save_project',{'preview':out['draft']})
        assert saved.structured_content['saved'] is True
        assert saved.structured_content['project_id']==out['project_id']
        assert uploads[0]==uploads[1]
        assert [b['operation'] for b in operations]==['canonical_commit','canonical_read']


@pytest.mark.anyio
async def test_report_failure_retains_exact_payload_without_table_and_retries(monkeypatch):
    owner='owner';monkeypatch.setattr('intel_mcp.project_reports.current_oauth_subject',lambda:owner)
    failed=True;calls=[]
    class Control:
        async def research_workspace(self,b):
            calls.append(deepcopy(b))
            if failed:raise ControlPlaneError('WORKSPACE_UNAVAILABLE','Unavailable',503)
            if b['operation']=='report_save':return {'report':{'id':'report'},'temporary':False,'project_id':'00000000-0000-0000-0000-000000000001'}
            if b['operation']=='report_read':return {'report':{'id':'report','html':'<h1>Exact</h1>'}}
            if b['operation']=='report_list':return {'reports':[]}
            return {'project_id':b['projectId'],'result':{'entity_type':'trials','entities':[]}}
    server,*_=create_research_server(SETTINGS,lambda:None,lambda:Control())
    preview={'preview_id':'00000000-0000-0000-0000-000000000001','cache_token':'c'*43,'snapshot_key':'d'*64,'selection_id':'s'*43,'title':'Extra legacy metadata'}
    args={'preview':preview,'title':'Cards','query':'Compare labs','summary':'','html':'<h1>Exact cards</h1><p>Unverified capability</p>','source_ids':[],'dataset_id':'d'*64,'revision':1,'request_key':'original-key','artifact_kind':'cards','evidence_basis':'project_tables'}
    async with Client(server) as client:
        desc={t.name:t for t in (await client.list_tools()).tools}
        assert 'selection_id' not in json.dumps(desc['save_project_report'].input_schema)
        result=(await client.call_tool('save_project_report',args)).structured_content
        assert result['report_saved'] is False and result['retry_id'] and 'result' not in result
        assert 'selection_id' not in json.dumps(calls)
        original=calls[0]
        owner='other'
        assert (await client.call_tool('retry_project_report',{'retry_id':result['retry_id']})).is_error
        assert len(calls)==2
        owner='owner';failed=False
        retried=(await client.call_tool('retry_project_report',{'retry_id':result['retry_id']})).structured_content
        assert retried['report_saved'] is True
        assert calls[2]==original
        assert (await client.call_tool('retry_project_report',{'retry_id':result['retry_id']})).is_error
