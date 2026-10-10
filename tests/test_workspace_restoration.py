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
