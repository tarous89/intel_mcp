import asyncio
from types import SimpleNamespace
from mcp import Client
from intel_mcp.auth_context import set_oauth_subject, reset_oauth_subject
from intel_mcp.research_server import create_research_server
from intel_mcp.research_views import result_view, evidence_view
from intel_mcp.research_access import public_ranking, public_evidence
from intel_mcp.research_presentation import access_info
from intel_mcp.selection import SelectionDataset
from test_selection import criteria
from test_selection_service import Engine
from test_research_access import many


def test_rank_and_evidence_views_keep_details_in_one_table_and_three_data_actions():
    dataset=SelectionDataset(criteria(),many())
    result=public_ranking(dataset).model_dump(mode='json')
    result.update(entity_type='cros',access_info=access_info(25,10))
    view=result_view(result,'selection')
    assert len(view['rows'])==10 and len(view['actions'])==3
    assert all(len(row['cells'])==len(view['columns']) for row in view['rows'])
    assert view['actions'][-1]['label']=='Access full list'
    assert not any('narrow' in a['label'].lower() for a in view['actions'])
    assert 'contact1@' not in str(view)
    evidence=public_evidence(dataset,result['entities'][0]['id']).model_dump(mode='json')
    table=evidence_view(evidence,'selection',result['entities'][0]['id'])
    assert len(table['rows'])==1 and len(table['actions'])==3
    assert 'operational_findings' not in table['rows'][0]['details']['text']


def test_private_save_requires_oauth_reuses_snapshot_and_never_starts_analysis():
    async def run():
        calls=[]
        class Control:
            async def research_access(self,*args): return {'fullAccess':False,'account_message':'Free research'}
            async def research_project(self,payload):
                calls.append(payload)
                return {'project_id':'00000000-0000-0000-0000-000000000001','title':payload['title'],
                        'url':'https://intel.trialagents.com/research/projects/00000000-0000-0000-0000-000000000001','message':'Saved'}
        engine=Engine(many());settings=SimpleNamespace(mcp_public_resource_url='https://mcp.synthetic.invalid/mcp',oauth_authorization_server_url='https://app.synthetic.invalid')
        server,*_=create_research_server(settings,lambda:engine,Control)
        async with Client(server) as client:
            search=await client.call_tool('search_research_trials',{'criteria':criteria().model_dump(mode='json')})
            args={'selection_ids':[search.structured_content['selection_id']],'title':'My research'}
            denied=await client.call_tool('save_research_project',args)
            assert denied.is_error and not calls
            marker=set_oauth_subject('owner')
            try:
                saved=await client.call_tool('save_research_project',args)
                assert not saved.is_error
                assert len(calls)==1 and engine.calls==1
                assert calls[0]['sections'][0]['result']['total_entities']==25
                assert len(calls[0]['sections'][0]['result']['entities'])==25
                assert 'contact1@' not in str(calls[0])
                assert 'entities' not in saved.structured_content
                tools=(await client.list_tools()).tools
                save=next(t for t in tools if t.name=='save_research_project')
                assert save.annotations.read_only_hint is False
            finally: reset_oauth_subject(marker)
    asyncio.run(run())
