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
    connected=False
    blocked=False
    project='00000000-0000-0000-0000-000000000001'
    preview={'preview_id':project,'selection_id':'s'*43,'title':'Report research','snapshot_key':'a'*64,'cache_token':'b'*43}
    class Control:
        async def research_workspace(self,body):
            calls.append(deepcopy(body))
            op=body['operation']
            if op=='report_document_authorize' and not allowed:raise ControlPlaneError('DOCUMENT_NOT_IN_PREVIEW','Preview excludes documents',403)
            if op=='report_context':return {'dataset_id':'snapshot','revision':1,'access_scope':'preview'}
            if op=='report_save' and blocked:raise ControlPlaneError('REPORT_SNAPSHOT_CHANGED','Snapshot changed',409)
            if op=='report_save':return {'report':{'id':'saved-report'},'temporary':not connected,'project_id':project if connected else None}
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
        assert descriptors['read_report_document'].annotations.read_only_hint is False
        assert descriptors['read_report_document'].annotations.idempotent_hint is False
        assert descriptors['save_project_report'].annotations.destructive_hint is True
        prepared=await client.call_tool('prepare_project_report',{'preview':preview,'include_template':True})
        assert not prepared.is_error
        assert 'Revisions pass report_id and expected_version' in prepared.structured_content['report_guidance']
        assert 'report_saved=true' in prepared.structured_content['report_guidance']
        evidence_context=await client.call_tool('prepare_project_report',{'preview':preview})
        assert 'report_guidance' not in evidence_context.structured_content
        assert 'report_html_example' not in evidence_context.structured_content
        assert '<svg' in prepared.structured_content['report_html_example']
        assert 'Nuances and implications' not in prepared.structured_content['report_html_example']
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
        assert calls[-4]['operation']=='report_save'
        assert calls[-3]['operation']=='report_read'
        opened=await client.call_tool('open_project_report',{'preview':preview,'report_id':'saved-report'})
        assert not opened.is_error and '<p>' in opened.structured_content['report']['html']
        count=len(calls)
        denied=await client.call_tool('prepare_project_report',{'project_id':project})
        assert denied.is_error and len(calls)==count
        monkeypatch.setattr('intel_mcp.project_reports.current_oauth_subject',lambda:'owner')
        assert not (await client.call_tool('prepare_project_report',{'project_id':project})).is_error

        connected=True
        saved=await client.call_tool('save_project_report',{'preview':preview,'title':'Analysis','query':'Compare the evidence','summary':'Stored version','html':'<h1>Evidence analysis</h1>','source_ids':['a'*64],'dataset_id':'snapshot','revision':1,'request_key':'report-2'})
        assert not saved.is_error
        assert saved.structured_content['temporary_report'] is False
        assert calls[-2]['operation']=='canonical_read'
        assert calls[-2]['projectId']==project and 'preview' not in calls[-2]
        before=len(calls)
        offered=await client.call_tool('offer_visualization_save',{'title':'Site tracker','project_id':project})
        assert offered.structured_content['visualization_save_offer']['title']=='Site tracker'
        assert not any(c['operation']=='report_save' for c in calls[before:])
        blocked=True
        failed=await client.call_tool('save_project_report',{'project_id':project,'title':'Tracker','query':'Track sites','summary':'','html':'<h1>Site tracker</h1>','source_ids':[],'evidence_basis':'project_tables','artifact_kind':'tracker','dataset_id':'snapshot','revision':1,'request_key':'retry-1'})
        assert failed.structured_content['report_saved'] is False
        assert failed.structured_content['visualization_save_offer']['retry'] is True
        assert 'REPORT_SNAPSHOT_CHANGED' in failed.structured_content['save_error']

@pytest.mark.anyio
@pytest.mark.parametrize('case',['preview_revision','canonical_revision','changed_dataset','source_revision','view_version','transient'])
async def test_retained_retry_reconciles_conflicts_without_blind_overwrite(monkeypatch,case):
    monkeypatch.setattr('intel_mcp.project_reports.current_oauth_subject',lambda:'owner')
    calls=[]
    preview={'preview_id':'00000000-0000-0000-0000-000000000001','snapshot_key':'a'*64,'cache_token':'b'*43}
    project=preview['preview_id']
    class Control:
        async def research_workspace(self,b):
            calls.append(deepcopy(b))
            if b['operation']=='report_context':return {'dataset_id':'changed' if case=='changed_dataset' else 'same','revision':1}
            if b['operation']=='report_save':
                count=sum(c['operation']=='report_save' for c in calls)
                if count==1:raise ControlPlaneError('REPORT_VERSION_CHANGED' if case=='view_version' else 'TEMPORARY_FAILURE' if case=='transient' else 'REVISION_CHANGED','Conflict',409)
                return {'report':{'id':'saved'},'temporary':False}
            if b['operation']=='report_read':return {'report':{'id':'saved'}}
            if b['operation']=='report_list':return {'reports':[]}
            return {'project_id':project,'result':{'entity_type':'trials','entities':[]}}
    server,*_=create_research_server(SimpleNamespace(mcp_public_resource_url='https://mcp.synthetic.invalid/mcp',oauth_authorization_server_url='https://app.synthetic.invalid'),lambda:None,lambda:Control())
    args={'title':'Tracker','query':'Track items','summary':'','html':'<h1>Original content</h1>','source_ids':['a'*64] if case=='source_revision' else [],'evidence_basis':'trial_evidence' if case=='source_revision' else 'project_tables','dataset_id':'same','revision':9,'request_key':'original-key',**({'project_id':project} if case=='canonical_revision' else {'preview':preview})}
    async with Client(server) as client:
        failed=(await client.call_tool('save_project_report',args)).structured_content
        assert failed['active_tab']=='custom'
        assert failed['pending_custom_view']['html']==args['html']
        retried=(await client.call_tool('retry_project_report',{'retry_id':failed['retry_id']})).structured_content
        writes=[c for c in calls if c['operation']=='report_save']
        if case in ('preview_revision','transient'):
            assert retried['report_saved'] is True and len(writes)==2
            assert writes[1]['revision']==(1 if case=='preview_revision' else 9)
            assert writes[1]['requestKey']=='original-key' and writes[1]['html']==args['html']
        else:
            assert retried['recovery']['action']=='reconcile' and len(writes)==1
            assert retried['current_context']['revision']==1
