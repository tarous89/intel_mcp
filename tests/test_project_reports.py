from types import SimpleNamespace
from copy import deepcopy
import pytest
from mcp import Client
from intel_mcp.research_server import create_research_server
from intel_mcp.control_plane import ControlPlaneError

@pytest.mark.anyio
async def test_report_tools_authorize_documents_before_fetch_and_open_saved_report(monkeypatch):
    calls=[]
    allowed=False
    project='00000000-0000-0000-0000-000000000001'
    preview={'preview_id':project,'selection_id':'s'*43,'title':'Report research','snapshot_key':'a'*64,'cache_token':'b'*43}
    class Control:
        async def research_workspace(self,body):
            calls.append(deepcopy(body))
            op=body['operation']
            if op=='report_document_authorize' and not allowed:raise ControlPlaneError('DOCUMENT_NOT_IN_PREVIEW','Preview excludes documents',403)
            if op=='report_context':return {'dataset_id':'snapshot','revision':1,'access_scope':'preview'}
            if op=='report_save':return {'report':{'id':'saved-report'},'temporary':True}
            if op=='report_read':return {'report':{'id':'saved-report','html':'<p>Saved evidence report</p>'}}
            if op=='report_list':return {'reports':[{'id':'saved-report','title':'Analysis'}]}
            if op in ('preview_read','canonical_read'):return {'project_id':project,'draft':preview,'result':{'entity_type':'trials','entities':[]}}
            return {'authorized':True}
    class Engine:
        async def get_document(self,**kwargs):
            calls.append({'operation':'engine_document',**kwargs})
            return SimpleNamespace(model_dump=lambda **_: {'trial_id':kwargs['trial_id'],'document_name':kwargs['document_name'],'part':kwargs['part'],'text':'Authorized text'})
    settings=SimpleNamespace(mcp_public_resource_url='https://mcp.synthetic.invalid/mcp',oauth_authorization_server_url='https://app.synthetic.invalid')
    server,*_=create_research_server(settings,lambda:Engine(),lambda:Control())
    async with Client(server) as client:
        descriptors={t.name:t for t in (await client.list_tools()).tools}
        assert descriptors['save_project_report'].annotations.read_only_hint is False
        assert descriptors['save_project_report'].annotations.idempotent_hint is True
        assert descriptors['read_report_document'].annotations.read_only_hint is True
        prepared=await client.call_tool('prepare_project_report',{'preview':preview})
        assert not prepared.is_error
        assert 'ABOVE the graph' in prepared.structured_content['report_guidance']
        assert 'Do not display sources' in prepared.structured_content['report_guidance']
        assert '<svg' in prepared.structured_content['report_html_example']
        assert 'Qualitative comparison matrix' in prepared.structured_content['report_html_example']
        args={'preview':preview,'trial_id':'2025-000001-00-00','document_name':'protocol.pdf'}
        denied=await client.call_tool('read_report_document',args)
        assert denied.is_error
        assert not any(c['operation']=='engine_document' for c in calls)
        allowed=True
        read=await client.call_tool('read_report_document',args)
        assert not read.is_error
        assert [c['operation'] for c in calls[-3:]]==['report_document_authorize','engine_document','report_document_store']
        saved=await client.call_tool('save_project_report',{'preview':preview,'title':'Analysis','query':'Compare the evidence','summary':'Preview only','html':'<h1>Evidence analysis</h1>','source_ids':['a'*64],'dataset_id':'snapshot','revision':1,'request_key':'report-1'})
        assert not saved.is_error
        assert saved.structured_content['active_report_id']=='saved-report'
        assert saved.structured_content['report_saved'] is True
        assert saved.structured_content['temporary_report'] is True
        assert calls[-3]['operation']=='report_save'
        opened=await client.call_tool('open_project_report',{'preview':preview,'report_id':'saved-report'})
        assert not opened.is_error and '<p>' in opened.structured_content['report']['html']
        count=len(calls)
        denied=await client.call_tool('prepare_project_report',{'project_id':project})
        assert denied.is_error and len(calls)==count
        monkeypatch.setattr('intel_mcp.project_reports.current_oauth_subject',lambda:'owner')
        assert not (await client.call_tool('prepare_project_report',{'project_id':project})).is_error
