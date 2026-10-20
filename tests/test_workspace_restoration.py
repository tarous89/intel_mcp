from copy import deepcopy
from intel_mcp.research_workspace import workspace_payload
from intel_mcp.selection import SelectionDataset
from intel_mcp.workspace_enrichment import enrich
from test_selection import criteria,record

def test_rich_workspace_preserves_order_contacts_and_frozen_six_metrics():
    records=[record(1),record(2)]
    records[1]['profile']['ctis_lifecycle']['countries'][0]['updates'][0]['date']='2024-01-01'
    c=criteria('sites',direct={'diseases':{'values':['Lung cancer']},'phase':{'values':[2]},'modalities':{'values':['Small molecule']}},as_of='2026-10-06')
    ds=SelectionDataset(c,records)
    before=ds.rank(full_cohort=True).model_dump(mode='json')
    payload=workspace_payload(ds,'Frozen research',False,[])
    site=next(s for s in payload['sections'] if s['entity_type']=='sites')['result']['entities'][0]
    native=site['workspace_row'];m=native['metrics']
    assert site['id']==before['entities'][0]['id'] and site['rank']==before['entities'][0]['rank']
    assert native['contact']=={'name':'Ada Example','email':'ada@example.test'}
    assert [m[k] for k in ('therapeuticAreaTrials','diseaseMatchedTrials','phaseMatchedTrials','modalityMatchedTrials','recentActivityTrials')]==[2,2,2,2,1]
    assert m['paediatricMatchedTrials'] is None
    assert m['bands']['therapeuticAreaTrials']=='typical'
    assert ds.snapshot==SelectionDataset(c,records).snapshot
    assert payload==workspace_payload(ds,'Frozen research',False,[])
    trial=next(s for s in payload['sections'] if s['entity_type']=='trials')['result']['entities'][0]['workspace_row']
    assert trial['countries']==['DE'] and trial['listedSiteCount']==1

def test_old_payload_enrichment_keeps_membership_and_order_and_masks_contacts():
    r=record();r['profile']['classification_variables']['sites'][0]['investigators'][0]['email']='masked@example.test'
    ds=SelectionDataset(criteria('sites'),[r]);payload=workspace_payload(ds,'Saved',False,[])
    old=deepcopy(payload)
    for section in old['sections']:
        for e in section['result']['entities']:e.pop('workspace_row',None)
    restored=enrich(old,list(ds.records.values()),ds.criteria.model_dump(mode='json'))
    for a,b in zip(old['sections'],restored['sections']):assert [e['id'] for e in a['result']['entities']]==[e['id'] for e in b['result']['entities']]
    assert next(s for s in restored['sections'] if s['entity_type']=='sites')['result']['entities'][0]['workspace_row']['contact'] is None

import pytest

@pytest.mark.parametrize('email', ['ada@example', 'ada@example.test;other@example.test', 'Ada <ada@example.test>', 'withheld@example.test', 'xxx@example.test', 'masked@example.test', 'ada@example.test', ''])
def test_contact_variants_preserve_frozen_pi_identity(email):
    r=record();r['profile']['classification_variables']['sites'][0]['investigators'][0]['email']=email
    ds=SelectionDataset(criteria('pis'),[r])
    before=ds.rank(full_cohort=True).model_dump(mode='json')['entities']
    payload=workspace_payload(ds,'Contact compatibility')
    pis=next(s for s in payload['sections'] if s['entity_type']=='pis')['result']['entities']
    assert [e['id'] for e in pis]==[e['id'] for e in before]
    assert [e['rank'] for e in pis]==[e['rank'] for e in before]
    assert len(pis)==1 and pis[0]['workspace_row']['metrics']['therapeuticAreaTrials']==1
    assert pis[0]['workspace_row']['email']==('ada@example.test' if email=='ada@example.test' else None)

@pytest.mark.anyio
async def test_search_to_workspace_with_malformed_contact_data():
    from types import SimpleNamespace
    import base64,gzip,json
    from mcp import Client
    from intel_mcp.research_server import create_research_server
    from intel_mcp.research_workspace import RESOURCE
    from test_selection_service import Engine
    emails=['ada@example','withheld@example.test','Ada <ada@example.test>','ada@example.test']
    rows=[]
    for i,email in enumerate(emails,1):
        r=record(i);site=r['profile']['classification_variables']['sites'][0]
        site['name']='Hospital '+str(i);site['investigators'][0]['email']=email;rows.append(r)
    class Control:
        cached=[]
        async def cache_research_preview(self,body):
            self.cached.append(json.loads(gzip.decompress(base64.b64decode(body['gzip']))))
    control=Control();engine=Engine(rows)
    settings=SimpleNamespace(mcp_public_resource_url='https://mcp.synthetic.invalid/mcp',oauth_authorization_server_url='https://app.synthetic.invalid')
    server,*_=create_research_server(settings,lambda:engine,lambda:control)
    async with Client(server) as client:
        search=await client.call_tool('search_research_trials',{'criteria':criteria('pis').model_dump(mode='json')})
        assert not search.is_error
        token=search.structured_content['selection_id']
        out=await client.call_tool('prepare_research_workspace',{'selection_id':token,'title':'PI workspace','kind':'pis'})
        assert not out.is_error
        data=out.structured_content
        assert set(data['preview_tables'])=={'pis'}
        assert data['result']['returned']==4 and data['saved'] is False
        assert data['draft']['cache_token'] and len(control.cached)==1
        assert (await client.read_resource(RESOURCE)).contents[0].mime_type=='text/html;profile=mcp-app'
        assert engine.calls==1,'workspace preparation never reruns search'
