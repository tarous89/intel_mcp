"""Conversational refinement must preserve source integrity and disclosure boundaries."""
from copy import deepcopy
from types import SimpleNamespace

import pytest
from mcp import Client

from intel_mcp.research_cohort import CohortRefinement, candidate_trials, refine_cohort
from intel_mcp.research_access import ResearchStore, public_ranking
from intel_mcp.research_server import create_research_server
from intel_mcp.selection import SelectionDataset, SelectionError
from intel_mcp.selection_identity import reviewed_cro_group
from intel_mcp.auth_context import set_oauth_subject, reset_oauth_subject
from test_selection import criteria, record, provider
from test_selection_service import Engine


def request(dataset, ids=None, **extra):
    return CohortRefinement(source_snapshot=dataset.snapshot,
        trial_ids=ids if ids is not None else list(dataset.records),
        rationale='Selected for the requested clinical question.',entity_type='cros',**extra)


def test_discovery_projection_is_paginated_and_does_not_release_nested_profiles():
    records=[record(i,providers=[{**provider('Hidden CRO'), 'email':'secret@synthetic.invalid'}]) for i in range(1,28)]
    records[0]['profile']['classification_variables']['diseases']=['Lung cancer',{'email':'hidden'}]
    dataset=SelectionDataset(criteria(),records)
    first=candidate_trials(dataset)
    last=candidate_trials(dataset,offset=first['next_offset'])
    assert first['returned']==25 and first['total_trials']==27
    assert not first['complete_in_this_response'] and not last['complete_in_this_response']
    assert last['next_offset'] is None and len(last['trials'])==2
    assert len({r['trial_id'] for r in first['trials']+last['trials']})==27
    assert candidate_trials(dataset,limit=100)['complete_in_this_response']
    assert 'Hidden CRO' not in str(first) and 'email' not in str(first)
    assert first['trials'][0]['diseases']==['Lung cancer']


def test_refinement_validates_origin_retains_facts_and_does_not_mutate_parent():
    parent=SelectionDataset(criteria(),[record(i) for i in range(1,4)])
    before=deepcopy(parent.records)
    ids=list(parent.records)[:2]
    child=refine_cohort(parent,request(parent,ids))
    assert len(child.records)==2 and parent.records==before
    assert child.rank().entities[0].trial_counts['total']==2
    assert child.selection_origin['source_snapshot']==parent.snapshot
    assert child.snapshot!=parent.snapshot
    assert refine_cohort(parent,request(parent,list(reversed(ids)))).snapshot==child.snapshot
    for req,code in [(request(parent,[ids[0],ids[0]]),'DUPLICATE'),
                     (request(parent,['2024-999999-00-00']),'UNKNOWN'),
                     (request(parent).model_copy(update={'source_snapshot':'0'*64}),'CHANGED'),
                     (request(parent).model_copy(update={'rationale':' '}),'RATIONALE')]:
        with pytest.raises(SelectionError,match=code):refine_cohort(parent,req)


@pytest.mark.anyio
async def test_refinement_retry_uses_cache_and_never_rereads_engine():
    engine=Engine([record(i) for i in range(1,4)])
    store=ResearchStore(lambda:engine)
    token,parent=await store.search(criteria())
    req=request(parent,list(parent.records)[:2])
    child,dataset=await store.refine(token,req)
    assert (await store.refine(token,req))[0]==child and engine.calls==1
    store.entries[token]['expires']=0
    with pytest.raises(SelectionError,match='EXPIRED'):await store.refine(token,req)
    assert store.get(child).snapshot==dataset.snapshot


@pytest.mark.anyio
async def test_mcp_refinement_preserves_free_entity_cap_and_tool_contract():
    engine=Engine([record(i,providers=[provider(f'CRO {i}')]) for i in range(1,26)])
    settings=SimpleNamespace(mcp_public_resource_url='https://mcp.synthetic.invalid/mcp',oauth_authorization_server_url='https://app.synthetic.invalid')
    server,_,_,_,_=create_research_server(settings,lambda:engine,lambda:None)
    async with Client(server) as client:
        initial=await client.call_tool('search_research_trials',{'criteria':criteria().model_dump(mode='json')})
        token=initial.structured_content['selection_id']
        candidates=(await client.call_tool('inspect_research_trials',{'selection_id':token})).structured_content
        refined=await client.call_tool('refine_research_cohort',{'selection_id':token,'refinement':{
            'source_snapshot':candidates['snapshot'],'trial_ids':[r['trial_id'] for r in candidates['trials']],
            'entity_type':'cros','rationale':'Keep candidates matching the stated scope.'}})
        assert not refined.is_error
        new=refined.structured_content['selection_id']
        ranked=(await client.call_tool('rank_research_entities',{'selection_id':new})).structured_content
        assert ranked['returned']==10 and ranked['total_entities']==25
        assert ranked['selection_origin']['source_snapshot']==candidates['snapshot']
        assert ranked['cohort']['coverage']=='model_selected_source_subset'
        assert (await client.call_tool('rank_research_entities',{'selection_id':new,'offset':10})).is_error


def test_canonical_cro_and_reviewed_country_entities_share_distinct_trial_counts():
    rows=[record(1,providers=[provider('IQVIA'),provider('IQVIA RDS GmbH')]),
          record(2,providers=[provider('iqvia'),provider('IQVIA Research Independent')])]
    result=SelectionDataset(criteria(),rows).rank()
    assert result.total_entities==2
    group=next(e for e in result.entities if e.name=='IQVIA')
    assert group.trial_counts['total']==2
    assert any('IQVIA RDS GmbH' in e['names'] for e in group.legal_entities)
    assert SelectionDataset(criteria(cro_identity='legal_entity'),rows).rank().total_entities==3
    assert reviewed_cro_group({'IQVIA RDS GmbH'},{'FR'}) is None
    assert reviewed_cro_group({'IQVIA','Unreviewed company'},{'DE'}) is None
    assert reviewed_cro_group({'IQVIA','Syneos Health'},{'DE'}) is None


def test_same_trial_cohort_can_feed_sites_and_pis_without_cro_function_filter():
    parent=SelectionDataset(criteria(function_code=1),[record()])
    for kind in ['sites','pis']:
        child=refine_cohort(parent,request(parent).model_copy(update={'entity_type':kind}))
        assert child.criteria.function_code is None
        assert child.rank().returned==1
        assert child.records==parent.records


@pytest.mark.anyio
async def test_save_passes_selected_source_ids_and_attributed_rationale_to_app():
    class Control:
        payload=None
        async def research_project(self,payload):
            self.payload=payload
            return {'project_id':'00000000-0000-0000-0000-000000000001','title':'Selected trials',
                    'message':'Saved','url':'https://intel.trialagents.com/research/projects/00000000-0000-0000-0000-000000000001'}
    engine=Engine([record(1),record(2)])
    control=Control()
    settings=SimpleNamespace(mcp_public_resource_url='https://mcp.synthetic.invalid/mcp',oauth_authorization_server_url='https://app.synthetic.invalid')
    server,_,store,_,_=create_research_server(settings,lambda:engine,lambda:control)
    parent_id,parent=await store.search(criteria())
    ids=list(parent.records)[:1]
    child_id,child=await store.refine(parent_id,request(parent,ids))
    marker=set_oauth_subject('synthetic-owner')
    try:
        async with Client(server) as client:
            saved=await client.call_tool('save_research_project',{'selection_ids':[child_id],'title':'Selected trials'})
            assert not saved.is_error
    finally:
        reset_oauth_subject(marker)
    section=control.payload['sections'][0]
    assert section['trial_ids']==ids and section['snapshot']==child.snapshot
    assert section['result']['selection_origin']['source_snapshot']==parent.snapshot
    assert section['result']['cohort']['coverage']=='model_selected_source_subset'
    assert section['result']['entities'][0]['trial_counts']['total']==1
