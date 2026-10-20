from copy import deepcopy
from types import SimpleNamespace
import json
import pytest
from mcp import Client
from intel_mcp.disclosure import mask_contacts, project_response
from intel_mcp.research_server import create_research_server


def page(kind):
    return {'entity_type':kind,'entities':[{'id':'stable-id','name':'Dr Public PI' if kind=='pis' else 'Example institution',
        'email':'person@example.invalid','contacts':[{'name':'Private contact','email':'contact@example.invalid'}],
        'workspace_row':{'id':'stable-id','name':'Dr Public PI' if kind=='pis' else 'Example institution',
          'email':'person@example.invalid','contact':{'name':'Private contact','email':'contact@example.invalid'},
          'matchedPIs':[{'name':'Other investigator','email':'other@example.invalid'}]}}]}


def test_scoped_projection_is_nonmutating_and_retains_pi_names():
    source={'account':{'connected':True,'email':'owner@example.invalid','user_id':'private','fullAccess':False},
            'result':page('pis'),'preview_tables':{k:page(k) for k in ('pis','sites','cros','trials')}}
    before=deepcopy(source);out=project_response(source)
    assert source==before
    assert set(out['preview_tables'])=={'pis'}
    assert out['account']=={'connected':True,'fullAccess':False}
    assert out['result']['entities'][0]['name']=='Dr Public PI'
    assert '@' not in json.dumps(out)
    assert 'Private contact' not in json.dumps(out)
    assert 'Other investigator' not in json.dumps(out)
    revealed=project_response(source,reveal=True)
    assert revealed['result']['entities'][0]['email']=='person@example.invalid'
    assert 'owner@example.invalid' not in json.dumps(revealed)


def test_profile_contacts_always_masked_including_nested_sites_but_prose_preserved():
    profile={'classification_variables':{'sites':[{'name':'Hospital','investigators':[
        {'first_name':'Jane','last_name':'Smith','email':'jane@example.invalid','function':'PI'}]}],
        'sponsor':{'name':'Sponsor','contact':{'first_name':'John','email':'john@example.invalid'}},
        'service_providers':[{'name':'CRO','contact_first_name':'Jo','email':'jo@example.invalid'}]},
        'results':{'summary':'Unchanged clinical prose'}}
    out=project_response({'profile':profile},reveal=True)['profile']
    assert '@' not in json.dumps(out) and 'Jane' not in json.dumps(out)
    assert out['classification_variables']['sites'][0]['name']=='Hospital'
    assert out['classification_variables']['service_providers'][0]['name']=='CRO'
    assert out['results']==profile['results']


@pytest.mark.anyio
async def test_actual_transport_masks_both_outputs_and_explicit_read_reveals_contacts(monkeypatch):
    import intel_mcp.research_workspace as workspace
    import intel_mcp.research_server as research
    monkeypatch.setattr(workspace,'current_oauth_subject',lambda:'owner')
    monkeypatch.setattr(research,'current_oauth_subject',lambda:'owner')
    payload={'project_id':'00000000-0000-0000-0000-000000000001','result':page('sites'),
             'account':{'connected':True,'email':'owner@example.invalid','fullAccess':False}}
    class Control:
        async def research_workspace(self,body):return deepcopy(payload)
        async def research_access(self,*args):return {'connected':True,'email':'owner@example.invalid','fullAccess':False,'account_message':'Connected','limits':{'trialsPerSelection':1000,'entitiesPerPage':100}}
    settings=SimpleNamespace(mcp_public_resource_url='https://mcp.synthetic.invalid/mcp',oauth_authorization_server_url='https://app.synthetic.invalid')
    server,*_=create_research_server(settings,lambda:None,Control)
    async with Client(server) as client:
        for reveal in (False,True):
            response=await client.call_tool('read_project',{'project_id':payload['project_id'],'kind':'sites','include_contacts':reveal})
            assert not response.is_error
            assert json.loads(response.content[0].text)==response.structured_content
            raw=json.dumps(response.structured_content)
            assert 'owner@example.invalid' not in raw
            assert ('contact@example.invalid' in raw)==reveal
            assert ('Private contact' in raw)==reveal
        account=await client.call_tool('get_account_access',{})
        assert not account.is_error and 'owner@example.invalid' not in str(account)


def test_legacy_contact_display_column_is_masked_without_rewriting_other_text():
    source={'view':{'columns':['Partner','Recorded contacts'], 'rows':[{'cells':['Dr Public PI','email: private@example.invalid']} ]}}
    before=deepcopy(source)
    assert project_response(source)['view']['rows'][0]['cells']==['Dr Public PI','***']
    assert project_response(source,reveal=True)==source
    assert source==before
