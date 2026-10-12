from types import SimpleNamespace
import pytest
from mcp import Client
from intel_mcp.research_server import create_research_server
from intel_mcp.followups import followup_payload,RESOURCE
from intel_mcp.control_plane import ControlPlaneError
from mcp.server.mcpserver.exceptions import ToolError

QUESTIONS=['Which services are most often recorded for these CROs?', 'How does trial coverage differ across countries?', 'What operational findings occur in their associated trials?']

def test_suggestions_do_not_depend_on_entitlement_but_notice_does():
    free=followup_payload(QUESTIONS,{'access_scope':'preview','available_trials':10},{'preview':'opaque'})
    paid=followup_payload(QUESTIONS,{'access_scope':'full','available_trials':71},{'project_id':'owned'})
    assert free['questions']==paid['questions']==QUESTIONS
    assert free['access_notice']=='Preview: up to 10 trials; connect your account to use existing full access.'
    assert '10' not in paid['access_notice'] and 'connect your account' not in paid['access_notice']
    assert '3 available trials' in followup_payload(QUESTIONS,{'access_scope':'preview','available_trials':3},{})['access_notice']
    assert 'No trials' in followup_payload(QUESTIONS,{'access_scope':'preview','available_trials':0},{})['access_notice']
    connected=followup_payload(QUESTIONS,{'access_scope':'preview','available_trials':10},{},connected=True)
    assert 'connect your account' not in connected['access_notice']
    for questions in [QUESTIONS[:2],[QUESTIONS[0]]*3,['x',*QUESTIONS[1:]],['not a question.',*QUESTIONS[1:]]]:
        with pytest.raises(ToolError): followup_payload(questions,{}, {})

@pytest.mark.anyio
async def test_question_tool_checks_scope_without_reading_or_saving_evidence(monkeypatch):
    calls=[]
    class Control:
        async def research_workspace(self,b):
            calls.append(b)
            assert b['operation']=='report_context'
            if b.get('projectId')=='wrong-owner':raise ControlPlaneError('PROJECT_NOT_FOUND','Denied',404)
            return {'access_scope':'preview','available_trials':10,'revision':1}
    settings=SimpleNamespace(mcp_public_resource_url='https://test.invalid/mcp',oauth_authorization_server_url='https://test.invalid')
    server,*_=create_research_server(settings,lambda:None,lambda:Control())
    preview={'preview_id':'00000000-0000-0000-0000-000000000001','selection_id':'s'*43,'title':'Research','snapshot_key':'a'*64,'cache_token':'b'*43}
    async with Client(server) as client:
        tool=next(t for t in (await client.list_tools()).tools if t.name=='show_research_followups')
        assert tool.annotations.read_only_hint is True
        assert tool.meta['ui']['resourceUri']==RESOURCE
        out=await client.call_tool('show_research_followups',{'questions':QUESTIONS,'preview':preview})
        assert not out.is_error and out.structured_content['questions']==QUESTIONS
        assert all(out.structured_content['context']['preview'][k]==v for k,v in preview.items())
        assert len(calls)==1
        denied=await client.call_tool('show_research_followups',{'questions':QUESTIONS,'project_id':'wrong-owner'})
        assert denied.is_error and len(calls)==1
        monkeypatch.setattr('intel_mcp.project_reports.current_oauth_subject',lambda:'owner')
        denied=await client.call_tool('show_research_followups',{'questions':QUESTIONS,'project_id':'wrong-owner'})
        assert denied.is_error
        resource=await client.read_resource(RESOURCE)
        assert 'Explore further' in resource.contents[0].text
