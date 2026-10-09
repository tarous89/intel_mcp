from starlette.applications import Starlette
from starlette.routing import Route
from starlette.testclient import TestClient
from intel_mcp.research_import import snapshot_endpoint
from intel_mcp.research_workspace import workspace_payload,payload_key
from intel_mcp.selection import SelectionDataset
from test_selection import record,criteria


def test_website_snapshot_requires_service_auth_and_exact_existing_snapshot():
    dataset=SelectionDataset(criteria(),[record()])
    class Store:
        def get(self,token):
            assert token=='s'*43
            return dataset
    payload=workspace_payload(dataset,'Exact research')
    spec={'preview_id':'00000000-0000-0000-0000-000000000001','selection_id':'s'*43,'title':'Exact research','snapshot_key':payload_key(payload)}
    app=Starlette(routes=[Route('/snapshot',snapshot_endpoint(Store(),'service-test'),methods=['POST'])])
    with TestClient(app) as client:
        assert client.post('/snapshot',json=spec).status_code==401
        auth={'Authorization':'Bearer service-test'}
        response=client.post('/snapshot',json=spec,headers=auth)
        assert response.status_code==200 and response.json()['payload']==payload
        assert response.headers['cache-control']=='no-store'
        assert client.post('/snapshot',json={**spec,'title':'Changed'},headers=auth).status_code==410
        assert client.post('/snapshot',content='x'*131073,headers=auth).status_code==413
