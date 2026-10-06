from dataclasses import replace
import pytest
from mcp import Client
from mcp.server import MCPServer
from mcp.types import ToolAnnotations
from intel_mcp import server
from test_selection import criteria, record
from test_selection_service import Control, Engine


class TelemetryControl(Control):
    def __init__(self):
        super().__init__()
        self.telemetry = []
    async def record_tool_call(self, payload):
        self.telemetry.append(payload)


@pytest.mark.anyio
async def test_real_mcp_serialization_workflow_no_model_tokens(monkeypatch):
    control = TelemetryControl()
    monkeypatch.setattr(server, 'control_plane_client', lambda: control)
    monkeypatch.setattr(server, 'engine_client', lambda: Engine([record()]))
    mcp = MCPServer('selection-test')
    monkeypatch.setattr(server, 'mcp', mcp)
    monkeypatch.setattr(server, 'settings', replace(server.settings, selection_enabled=True))
    for function in (server.search_trial_cohort, server.get_cohort_trials, server.rank_entities, server.get_entity_evidence):
        server.selection_tool(meta=server.OAUTH_TOOL_META, annotations=ToolAnnotations(
            read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))(function)
    async with Client(mcp) as client:
        tools = (await client.list_tools()).tools
        assert len(tools) == 4 and all(tool.output_schema for tool in tools)
        arguments = {'analysis_id': 'ana_' + '1' * 24, 'criteria': criteria().model_dump(mode='json')}
        cohort = await client.call_tool('search_trial_cohort', arguments)
        assert not cohort.is_error
        arguments['expected_snapshot'] = cohort.structured_content['snapshot']
        listed = await client.call_tool('get_cohort_trials', arguments)
        assert not listed.is_error and listed.structured_content['total_trials'] == 1
        assert listed.structured_content['trials'][0]['title'] == 'Study 1'
        bad_group = await client.call_tool('rank_entities', {**arguments, 'subgroup_ids': ['missing']})
        assert bad_group.is_error
        ranked = await client.call_tool('rank_entities', arguments)
        assert not ranked.is_error
        entity = ranked.structured_content['entities'][0]
        evidence = await client.call_tool('get_entity_evidence', {**arguments, 'entity_id': entity['id'], 'sections': ['overview']})
        assert not evidence.is_error
        trial = evidence.structured_content['trials'][0]
        assert trial['profile_sections']['classification_variables']['trial_title'] == 'Study 1'
        invalid = await client.call_tool('rank_entities', {**arguments, 'limit': 11})
        assert invalid.is_error
        stale = await client.call_tool('rank_entities', {**arguments, 'expected_snapshot': '0' * 64})
        assert stale.is_error
    assert control.telemetry and all(call['workerCalls'] == 0 and call['totalTokens'] == 0 for call in control.telemetry)


def test_registration_disabled_by_default(monkeypatch):
    mcp = MCPServer('disabled-selection')
    monkeypatch.setattr(server, 'settings', replace(server.settings, selection_enabled=False))
    monkeypatch.setattr(server, 'mcp', mcp)
    assert server.selection_tool()(server.rank_entities) is server.rank_entities


@pytest.mark.anyio
async def test_catalogue_is_static_and_exposes_function_vocabulary():
    result = await server.get_selection_catalogue()
    assert result.function_codes['1'] == 'On site monitoring'
    assert 'diseases' in result.filter_fields and result.max_results == 10
    assert result.default_results == 10 and 'title' in result.discovery_fields
