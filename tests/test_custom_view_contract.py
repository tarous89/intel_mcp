from types import SimpleNamespace
import json
import pytest
from mcp import Client
from intel_mcp.custom_view_contract import custom_view_envelope, custom_view_contract
from intel_mcp.research_server import create_research_server


def test_translation_changes_only_envelopes_not_evidence_or_user_state():
    stored={'id':'original-id','html':'report_id report_saved', 'state':{'report':'user text'}}
    source={'report':stored,'reports':[stored], 'active_report_id':'original-id',
            'sources':[{'data':{'report':'clinical report'}}],
            'presentation_recovery':{'custom_view_id':'original-id'}}
    result=custom_view_envelope(source)
    assert result['custom_view'] is stored
    assert result['custom_views'][0] is stored
    assert result['active_custom_view_id']=='original-id'
    assert result['sources']==source['sources']
    assert 'report' not in result and 'reports' not in result


@pytest.mark.anyio
async def test_new_tool_contract_has_no_old_names_or_id_parameters():
    settings=SimpleNamespace(mcp_public_resource_url='https://mcp.synthetic.invalid/mcp',oauth_authorization_server_url='https://app.synthetic.invalid')
    server,*_=create_research_server(settings,lambda:None,lambda:None)
    async with Client(server) as client:
        tools={tool.name:tool for tool in (await client.list_tools()).tools}
        assert 'get_account_access' in tools and 'list_research_projects' not in tools
        assert not any('report' in name for name in tools)
        for name in ('save_project_custom_view','open_project_custom_view','read_project_custom_view','save_visualization_state'):
            properties=tools[name].input_schema['properties']
            assert 'custom_view_id' in properties and 'report_id' not in properties
        result=await client.call_tool('get_account_access',{})
        assert result.is_error  # anonymous account reads remain gated; no backend request


@pytest.mark.anyio
async def test_text_and_structured_contract_agree():
    payload={'report_saved':True,'report':{'id':'old-id','html':'original'}}
    async def next_call(_):return {'structuredContent':payload,'content':[{'type':'text','text':json.dumps(payload)}]}
    out=await custom_view_contract(SimpleNamespace(method='tools/call'),next_call)
    assert out['structuredContent']==json.loads(out['content'][0]['text'])
    assert out['structuredContent']['custom_view_saved'] is True
