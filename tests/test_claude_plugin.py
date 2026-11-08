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


def test_listing_icon_is_a_square_png_within_limits():
    import struct
    manifest = json.loads((CLAUDE / '.claude-plugin/plugin.json').read_text())
    icon = CLAUDE / manifest['icon']
    data = icon.read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n' and len(data) < 2 * 1024 * 1024
    width, height = struct.unpack('>II', data[16:24])
    assert width == height and 512 <= width <= 2048


def test_icon_has_only_image_chunks_and_plugin_has_no_html_files():
    # Metadata chunks (C2PA, text) can trip the directory's download-and-run scan;
    # .html files will only be accepted from Verified organizations.
    import struct
    data = (CLAUDE / '.claude-plugin/icon.png').read_bytes()
    chunks, i = set(), 8
    while i < len(data):
        n, = struct.unpack('>I', data[i:i + 4])
        chunks.add(data[i + 4:i + 8])
        i += 12 + n
    assert chunks <= {b'IHDR', b'PLTE', b'tRNS', b'IDAT', b'IEND'}
    assert not list(CLAUDE.rglob('*.html'))


def test_icon_is_small_and_has_no_shell_like_byte_runs():
    # A large, noisy PNG contains random byte runs that the directory's
    # download-and-run scan reads as shell syntax; a flat-palette icon has none.
    import re
    data = (CLAUDE / '.claude-plugin/icon.png').read_bytes()
    assert len(data) < 16 * 1024
    for pattern in (rb'(curl|wget|iwr|irm|iex|powershell|bash)', rb'\|\s*(ba|z|da|k)?sh', rb'\bsh\b',
                    rb'sh\s*-c', rb'\$\(', rb'https?:', rb'/bin/', rb'eval', rb'exec', rb'base64', rb'chmod'):
        assert not re.search(pattern, data, re.I), pattern
