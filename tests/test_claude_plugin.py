"""Claude plugin package (plugins/trialagents-intel-claude): one skill, Claude endpoint, separate from ChatGPT."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLAUDE = ROOT / 'plugins/trialagents-intel-claude'
CHATGPT = ROOT / 'plugins/trialagents-intel'


def test_manifest_and_endpoint():
    manifest = json.loads((CLAUDE / '.claude-plugin/plugin.json').read_text())
    assert manifest['name'] == 'trialagents'
    servers = json.loads((CLAUDE / '.mcp.json').read_text())['mcpServers']
    assert [s['url'] for s in servers.values()] == ['https://mcp.trialagents.com/claude/mcp']


def test_single_user_facing_skill():
    skills = sorted(p.parent.name for p in (CLAUDE / 'skills').glob('*/SKILL.md'))
    assert skills == ['ask-trialagents']
    text = (CLAUDE / 'skills/ask-trialagents/SKILL.md').read_text()
    front = re.match(r'---\nname: (.+)\ndescription: "(.+)"\n---\n', text)
    assert front and front.group(1) == 'ask-trialagents' and len(front.group(2)) <= 1024


def test_links_resolve_and_no_chatgpt_wording():
    for path in CLAUDE.rglob('*'):
        if path.suffix not in ('.md', '.html', '.json') or not path.is_file():
            continue
        text = path.read_text()
        assert 'ChatGPT' not in text or path.name == 'README.md', path
        assert '/research/mcp' not in text or path.name == 'README.md', path
        if path.suffix == '.md':
            for target in re.findall(r'\]\(([^)#]+)(?:#[^)]*)?\)', text):
                if not target.startswith('http'):
                    assert (path.parent / target).resolve().is_file(), (path, target)


def test_chatgpt_plugin_still_points_to_research_endpoint():
    servers = json.loads((CHATGPT / 'mcp.json').read_text())['mcpServers']
    assert servers['trialagents-research']['url'] == 'https://mcp.trialagents.com/research/mcp'
    assert len(list((CHATGPT / 'skills').glob('*/SKILL.md'))) == 5
