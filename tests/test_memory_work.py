import asyncio
import hashlib
import json
import threading
from copy import deepcopy
import pytest
from intel_mcp.memory_work import json_digest,json_size,workspace_gate,run_cpu,retained_size
from intel_mcp.research_workspace import workspace_payload,payload_key
from intel_mcp.selection import SelectionDataset,digest
from test_selection import criteria,record

@pytest.mark.parametrize('value',[{},[],{'ü':['患者',1.5,-0.0,True,None,'x'*100000]},[{'b':2,'a':1}]])
def test_incremental_json_preserves_exact_hashes_and_sizes(value):
    for options in ({'ensure_ascii':False},{'sort_keys':True,'separators':(',',':')},{'sort_keys':True,'separators':(',',':'),'ensure_ascii':False}):
        original=json.dumps(value,**options).encode()
        assert json_size(value,**options)==len(original)
        assert json_digest(value,**options)==hashlib.sha256(original).hexdigest()
    assert payload_key(value)==hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    assert digest(value)==hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def test_workspace_does_not_mutate_source_or_previous_results():
    rows=[record(i) for i in range(1,13)]
    before=deepcopy(rows)
    dataset=SelectionDataset(criteria(),rows)
    result=workspace_payload(dataset,'Exact')
    copy=deepcopy(result)
    assert workspace_payload(dataset,'Exact')==result
    assert rows==before and result==copy
    # Returned payload edits must not modify stored source profiles.
    result['sections'][0]['result']['entities'][0]['name']='Changed'
    assert rows==before
    assert workspace_payload(dataset,'Exact')==copy

@pytest.mark.anyio
async def test_gate_serializes_heavy_operations_without_dropping_requests():
    class Store:pass
    store=Store();active=0;peak=0
    @workspace_gate(store)
    async def first():
        nonlocal active,peak
        active+=1;peak=max(active,peak)
        await asyncio.sleep(.01)
        active-=1
        return 1
    @workspace_gate(store)
    async def second():return await run_cpu(lambda:2)
    assert await asyncio.gather(first(),first(),second())==[1,1,2]
    assert peak==1

@pytest.mark.anyio
async def test_cancelled_worker_keeps_gate_until_cpu_work_finishes():
    class Store:pass
    store=Store();started=threading.Event();release=threading.Event();next_started=False
    def worker():started.set();release.wait(2)
    @workspace_gate(store)
    async def first():await run_cpu(worker)
    @workspace_gate(store)
    async def second():
        nonlocal next_started
        next_started=True
    task=asyncio.create_task(first())
    await asyncio.to_thread(started.wait,2)
    task.cancel()
    other=asyncio.create_task(second())
    await asyncio.sleep(.02)
    assert not next_started
    task.cancel()
    await asyncio.sleep(.02)
    assert not next_started
    release.set()
    with pytest.raises(asyncio.CancelledError):await task
    await other
    assert next_started

def test_retained_cache_measurement_counts_derived_objects_without_policy_changes():
    from intel_mcp.research_access import ResearchStore
    store=ResearchStore(lambda:None)
    dataset=SelectionDataset(criteria(),[record()])
    token,_=store._put(dataset,'key')
    policy=(store.ttl,store.max_bytes,store.entries[token]['expires'],store.entries[token]['bytes'])
    before=store.retained_bytes()
    dataset.rank()
    assert store.retained_bytes()>before
    assert policy==(store.ttl,store.max_bytes,store.entries[token]['expires'],store.entries[token]['bytes'])
    shared=['x'*1000]
    assert retained_size([shared,shared])<retained_size([shared,deepcopy(shared)+['y'*1000]])
