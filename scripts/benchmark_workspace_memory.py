"""Synthetic full-runtime workspace benchmark. No production data or network."""
import os
import sys
import resource
# Apply before importing the MCP runtime. Includes native mappings and Python heap.
resource.setrlimit(resource.RLIMIT_AS, (512*1024*1024, 512*1024*1024))
import asyncio
import hashlib
import json
import time
from copy import deepcopy
from intel_mcp.research_server import create_research_server
from intel_mcp.research_access import ResearchStore
from intel_mcp.research_workspace import workspace_payload, payload_key, preview_page
from intel_mcp.prepared_selection import prepare_selection
from intel_mcp.selection import SelectionDataset
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tests'))
from test_selection import criteria, record, provider

async def main():
    started=time.monotonic()
    rows=[]
    for i in range(1,421):
        r=record(i,providers=[provider('Synthetic laboratory '+str(i))])
        r['profile']['classification_variables']['sites']=[
            {'name':f'Synthetic Hospital {i}-{j}', 'country_code':'DE',
             'investigators':[{'first_name':'Synthetic','last_name':f'Investigator {i}-{j}',
                              'email':f'person-{i}-{j}@example.test'}]} for j in range(12)]
        r['profile']['results']['trial_operational_findings']=[f'Synthetic finding {i} '+('evidence '*180)]
        rows.append(r)
    class Engine:
        async def selection(self,c):return SelectionDataset(c,rows)
    from types import SimpleNamespace
    server,_,store,_,_=create_research_server(SimpleNamespace(
        mcp_public_resource_url='https://synthetic.invalid/research/mcp',
        oauth_authorization_server_url='https://synthetic.invalid'),lambda:Engine(),lambda:None)
    token,dataset=await store.search(criteria())
    source=hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()
    results=[]
    # Repeated preparation and exact fallback serialization, while cache stays resident.
    for attempt in range(3):
        payload=workspace_payload(dataset,'Synthetic memory regression')
        pages=[preview_page(payload,k,0,True) for k in ('cros','sites','pis','trials')]
        prepared=prepare_selection(dataset)
        results.append({'snapshot':payload_key(payload),'prepared':hashlib.sha256(json.dumps(prepared,sort_keys=True).encode()).hexdigest(),
                        'counts':[s['result']['total_entities'] for s in payload['sections']],
                        'pages':hashlib.sha256(json.dumps(pages,sort_keys=True).encode()).hexdigest()})
        # Exercise actual website fallback, without loading its full response in the client.
        from intel_mcp.research_import import snapshot_endpoint
        from starlette.requests import Request
        body=json.dumps({'preview_id':'00000000-0000-0000-0000-000000000001','selection_id':token,
                         'title':'Synthetic memory regression','snapshot_key':results[-1]['snapshot']}).encode()
        del payload,pages,prepared
        async def receive():return {'type':'http.request','body':body,'more_body':False}
        response=await snapshot_endpoint(store,'synthetic')(Request({'type':'http','headers':[(b'authorization',b'Bearer synthetic')]},receive))
        digest=hashlib.sha256()
        if hasattr(response,'body_iterator'):
            async for part in response.body_iterator:digest.update(part)
        else:digest.update(response.body)
        results[-1]['fallback']=digest.hexdigest()
        del response
    assert source==hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()
    assert all(r==results[0] for r in results)
    # Golden values captured from the unchanged PR #119 implementation.
    assert results[0] == {
        'snapshot':'731ae4d9ea5029435425e59d27416403f607b39dbe9ad89433972b99731d07f7',
        'prepared':'67b6ddddf94dcb8ac3781525366ef4983c292959bd86228e02a101b6c6b5226d',
        'counts':[420,5040,5040,420],
        'pages':'94d5f1f1ad7793b4f01128bb13a19b0fdba07c549a44d20971b9e3cba84156bc',
        'fallback':'87990013f9fd8c6766c36e971b5fe2ac2382848661120dc631796975d53325ed'}
    assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss < 350*1024
    print(json.dumps({'peak_rss_mib':round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,2),
                      'seconds':round(time.monotonic()-started,2),'result':results[0]}))
asyncio.run(main())
