import json
from types import SimpleNamespace
import pytest
from mcp import Client
from intel_mcp.research_server import create_research_server
from intel_mcp.profiles import PROFILE_SECTIONS, PROFILE_SECTION_FIELDS, project_profile
from intel_mcp.profile_catalog import SCHEMA, profile_catalog
from intel_mcp.control_plane import ControlPlaneError

def test_schema_covers_every_field_and_section_union_is_complete():
    covered = {}
    for roots in PROFILE_SECTION_FIELDS.values():
        for root, fields in roots.items():
            covered.setdefault(root, set()).update(fields or SCHEMA['properties'][root]['properties'])
    assert covered == {k:set(v['properties']) for k,v in SCHEMA['properties'].items()}
    sample = {k:{f: {'nested':['exact', None, 12]} for f in fields} for k,fields in covered.items()}
    assert project_profile(sample, list(PROFILE_SECTIONS)) == sample
    assert len(profile_catalog()['sections']) == 14
    selected = profile_catalog(['eligibility','sites'])
    assert set(selected['schema']['properties']['filtering_variables']['properties']) == {'inclusion_criteria','exclusion_criteria','number_of_sites'}
    assert 'investigators' in selected['schema']['properties']['classification_variables']['properties']['sites']['items']['properties']

@pytest.mark.anyio
async def test_anonymous_model_tools_sections_inventory_and_complete_document_text():
    tid='2025-000001-00-00'
    preview={'preview_id':'00000000-0000-0000-0000-000000000001','selection_id':'s'*43,'title':'Research','snapshot_key':'a'*64,'cache_token':'b'*43}
    profile={'filtering_variables':{'available_extracted_documents':{'protocol':['protocol.pdf']},'inclusion_criteria':['x'*60000]},'classification_variables':{'trial_title':'Stored title','sites':[{'name':str(i)} for i in range(15)]}}
    fetched=[]
    class Control:
        async def research_workspace(self,b):
            if b['operation']=='report_evidence':
                if b.get('trialIds')!=[tid]:raise ControlPlaneError('TRIAL_NOT_IN_PREVIEW','Outside eligible set',403)
                return {'sources':[{'source_id':'c'*64,'data':{'profile':profile,'datasetId':'frozen','revision':1,'complete':True}}]}
            if b.get('trialId')!=tid:raise ControlPlaneError('TRIAL_NOT_IN_PREVIEW','Outside eligible set',403)
            if b['operation']=='trial_profile':return {'profile':profile,'datasetId':'frozen','revision':1,'profile_schema_version':'11.0.0','complete':True}
            if b['operation']=='report_document_authorize':return {'authorized':True}
            if b['operation']=='report_document_store':return {'source':{'source_id':'c'*64,'data':b['document']}}
            raise AssertionError(b)
    class Engine:
        async def get_document(self,**b):
            fetched.append(b)
            return SimpleNamespace(model_dump=lambda **_:dict(b,text=['[[PAGE 1]]\nFirst','\n[[PAGE 2]]\nLast'][b['part']-1],next_part=2 if b['part']==1 else None))
    settings=SimpleNamespace(mcp_public_resource_url='https://test.invalid/mcp',oauth_authorization_server_url='https://test.invalid')
    server,*_=create_research_server(settings,lambda:Engine(),lambda:Control())
    async with Client(server) as client:
        tools={t.name:t for t in (await client.list_tools()).tools}
        for name in ['describe_trial_profile_schema','read_trial_profiles','list_trial_documents','read_trial_document']:
            assert tools[name].annotations.read_only_hint
            assert 'model' in tools[name].meta['ui']['visibility']
            assert {'type':'noauth'} in tools[name].meta['securitySchemes']
        schema=await client.call_tool('describe_trial_profile_schema',{})
        assert not schema.is_error and len(schema.structured_content['sections'])==14
        args={'preview':preview,'trial_ids':[tid]}
        partial=await client.call_tool('read_trial_profiles',{**args,'sections':['overview','sites']})
        assert not partial.is_error
        item=partial.structured_content['profiles'][0]
        assert item['source_id']=='c'*64
        assert len(item['profile']['classification_variables']['sites'])==15
        assert 'filtering_variables' not in item['profile'] or 'inclusion_criteria' not in item['profile']['filtering_variables']
        chunks=[];part=1
        while part:
            result=await client.call_tool('read_trial_profiles',{**args,'part':part})
            assert not result.is_error
            item=result.structured_content['profiles'][0]
            chunks.append(item['profile_json_part']);part=item['next_part']
        assert json.loads(''.join(chunks))==profile
        inventory=await client.call_tool('list_trial_documents',{'preview':preview,'trial_id':tid})
        assert inventory.structured_content['documents']['protocol']==['protocol.pdf']
        docs=[]
        for part in [1,2]:
            doc=await client.call_tool('read_trial_document',{'preview':preview,'trial_id':tid,'document_name':'protocol.pdf','part':part})
            assert not doc.is_error
            docs.append(doc.structured_content['source']['data'])
        assert ''.join(d['text'] for d in docs)=='[[PAGE 1]]\nFirst\n[[PAGE 2]]\nLast'
        assert docs[-1]['next_part'] is None
        denied=await client.call_tool('read_trial_document',{'preview':preview,'trial_id':'2025-000011-00-00','document_name':'protocol.pdf'})
        assert denied.is_error and len(fetched)==2
        denied=await client.call_tool('read_trial_profiles',{'preview':preview,'trial_ids':['2025-000011-00-00']})
        assert denied.is_error
