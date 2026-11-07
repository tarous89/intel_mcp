"""Claude endpoint (/claude/mcp): Claude-facing text, and no change to the ChatGPT endpoint."""
import asyncio
import json
import re
from types import SimpleNamespace

import pytest

from intel_mcp import claude_research, research_server
from intel_mcp.claude_research import (
    PARAMETER_TEXT, RESULT_TEXT, TOOL_TEXT, _claude_value, apply_claude_text, claude_results,
    create_claude_research_server,
)
from intel_mcp.research_presentation import RESEARCH_WORKFLOW

SETTINGS = SimpleNamespace(mcp_public_resource_url='https://mcp.synthetic.invalid/mcp',
                           oauth_authorization_server_url='https://app.synthetic.invalid')
DIRECTIVE = re.compile(r"\b(Do not|Never call|Always|You must|Keep chat|Present ONLY|in chat)\b")


def _chatgpt():
    return research_server.create_research_server(SETTINGS, lambda: None, lambda: None)


def _listing(server):
    tools = asyncio.run(server.list_tools())
    return {
        'instructions': server._lowlevel_server.instructions,
        'middleware': [getattr(m, '__name__', type(m).__name__) for m in server._lowlevel_server.middleware],
        'tools': {t.name: t.model_dump(by_alias=True, exclude_none=True) for t in tools},
    }


def test_chatgpt_endpoint_is_identical_before_and_after_claude_is_built():
    before_server, *_ = _chatgpt()
    before = json.dumps(_listing(before_server), sort_keys=True)
    create_claude_research_server(SETTINGS, lambda: None, lambda: None, research_server.ResearchStore(lambda: None))
    after_server, *_ = _chatgpt()
    # Same ChatGPT instance and a freshly built one both keep the original text.
    assert json.dumps(_listing(before_server), sort_keys=True) == before
    assert json.dumps(_listing(after_server), sort_keys=True) == before
    assert before_server._lowlevel_server.instructions == RESEARCH_WORKFLOW
    assert research_server.ResearchStore.__name__ == 'ResearchStore'


def test_claude_instance_shares_the_research_store(monkeypatch):
    built = []
    real = research_server.ResearchStore
    store = real(lambda: None)
    monkeypatch.setattr(research_server, 'ResearchStore', lambda f: built.append(f) or real(f))
    create_claude_research_server(SETTINGS, lambda: None, lambda: None, store)
    assert built == []
    # The workspace memory gate is the store's own, so both endpoints share one budget.
    assert hasattr(store, '_workspace_memory_lock')


def test_claude_tools_have_titles_and_descriptive_text():
    server, _auth, resource, challenge = create_claude_research_server(SETTINGS, lambda: None, lambda: None, research_server.ResearchStore(lambda: None))
    assert resource == 'https://mcp.synthetic.invalid/claude/mcp'
    assert '/claude/.well-known/oauth-protected-resource' in challenge
    listing = _listing(server)
    assert set(listing['tools']) == set(TOOL_TEXT)
    for name, tool in listing['tools'].items():
        assert (tool['title'], tool['description']) == TOOL_TEXT[name]
        assert not DIRECTIVE.search(tool['description']), name
        assert 'ChatGPT' not in tool['description'], name
        schema = json.dumps(tool['inputSchema'])
        for old in PARAMETER_TEXT:
            assert json.dumps(old)[1:-1] not in schema, (name, old[:40])
    assert listing['instructions'] == claude_research.CLAUDE_INSTRUCTIONS
    assert 'ChatGPT' not in listing['instructions'] and not DIRECTIVE.search(listing['instructions'])
    assert listing['middleware'][-1] == 'claude_results'


def test_unreviewed_tool_fails_claude_startup():
    server, *_ = _chatgpt()

    @server.tool()
    def unreviewed_tool() -> str:
        """Unreviewed."""
        return ''

    with pytest.raises(RuntimeError, match='unreviewed_tool'):
        apply_claude_text(server)


def test_results_keep_data_and_drop_directives():
    payload = {
        'selection_id': 's1',
        'presentation': {'tool': 'publish_research_workspace', 'selection_id': 's1',
                         'instruction': next(k for k, v in RESULT_TEXT.items() if v is None)},
        'discovery_guidance': {'status': 'within_target',
                               'next_step': next(k for k in RESULT_TEXT if k.startswith('Discovery is ready')),
                               'presentation': next(k for k in RESULT_TEXT if k.startswith('After broadening'))},
        'rows': [1, 2],
    }
    out = _claude_value(payload)
    assert out['presentation'] == {'tool': 'publish_research_workspace', 'selection_id': 's1'}
    assert out['discovery_guidance'] == {'status': 'within_target',
                                         'next_step': RESULT_TEXT[payload['discovery_guidance']['next_step']]}
    assert out['rows'] == [1, 2] and out['selection_id'] == 's1'

    async def call_next(_ctx):
        return {'structuredContent': payload, 'content': [{'type': 'text', 'text': json.dumps(payload)}]}

    result = asyncio.run(claude_results(SimpleNamespace(method='tools/call'), call_next))
    assert result['structuredContent'] == out
    assert json.loads(result['content'][0]['text']) == out


def test_enabled_app_serves_claude_and_leaves_research_unchanged():
    import os
    import subprocess
    import sys
    script = '''
import json
from starlette.testclient import TestClient
from intel_mcp.bootstrap import app

def tools(client, path):
    response = client.post(path, headers={'Accept': 'application/json, text/event-stream'},
                           json={'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list', 'params': {}})
    assert response.status_code == 200, response.text
    if response.headers['content-type'].startswith('text/event-stream'):
        payload = json.loads(next(l[6:] for l in response.text.splitlines() if l.startswith('data: ')))
    else:
        payload = response.json()
    return {tool['name']: tool for tool in payload['result']['tools']}

with TestClient(app) as client:
    research = client.get('/.well-known/oauth-protected-resource/research/mcp').json()
    assert research['resource'].endswith('/research/mcp')
    for path in ('/.well-known/oauth-protected-resource/claude/mcp', '/claude/.well-known/oauth-protected-resource'):
        claude = client.get(path)
        assert claude.status_code == 200, claude.text
        assert claude.json()['resource'].endswith('/claude/mcp')
        assert claude.json()['authorization_servers'] == research['authorization_servers']
    chatgpt_tools = tools(client, '/research/mcp')
    claude_tools = tools(client, '/claude/mcp')
    assert set(chatgpt_tools) == set(claude_tools) and len(claude_tools) == 38
    assert 'access_info.message' in chatgpt_tools['rank_research_entities']['description']
    assert all(t.get('title') for t in claude_tools.values())
    assert claude_tools['rank_research_entities']['description'].startswith('Ranks the CROs')
    for name, tool in claude_tools.items():
        assert tool['securitySchemes'] == chatgpt_tools[name]['securitySchemes']
        assert tool['_meta'] == chatgpt_tools[name]['_meta']
        assert tool['annotations'] == chatgpt_tools[name]['annotations']
'''
    env = {**os.environ, 'MCP_RESEARCH_ENABLED': 'true', 'MCP_CLAUDE_ENABLED': 'true',
           'MCP_ALLOWED_HOSTS': 'testserver', 'MCP_INBOUND_SERVICE_TOKEN': 'synthetic-only'}
    result = subprocess.run([sys.executable, '-c', script], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_disabled_app_has_no_claude_endpoint():
    import os
    import subprocess
    import sys
    script = '''
from starlette.testclient import TestClient
from intel_mcp.bootstrap import app
with TestClient(app) as client:
    assert client.get('/.well-known/oauth-protected-resource/claude/mcp').status_code != 200 or \\
        not client.get('/.well-known/oauth-protected-resource/claude/mcp').json().get('resource', '').endswith('/claude/mcp')
    response = client.post('/claude/mcp', json={})
    assert response.status_code in (401, 404), response.status_code
'''
    env = {**os.environ, 'MCP_RESEARCH_ENABLED': 'true', 'MCP_CLAUDE_ENABLED': 'false',
           'MCP_ALLOWED_HOSTS': 'testserver', 'MCP_INBOUND_SERVICE_TOKEN': 'synthetic-only'}
    result = subprocess.run([sys.executable, '-c', script], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
