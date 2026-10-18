#!/usr/bin/env python3
"""Validate and reproducibly zip the explicit public plugin payload (no repo secrets)."""
import argparse
import json
from pathlib import Path
import zipfile
import struct

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'plugins/trialagents-intel'
FILES = ('references/server-instructions.md', 'skills/create-custom-view/references/design-patterns.md', 'skills/create-custom-view/assets/custom-view-examples.html', 'skills/answer-in-trialagents/SKILL.md', 'skills/answer-in-trialagents/agents/openai.yaml', 'references/custom-style.md', 'plugin.json', 'mcp.json', 'assets/logo.png', 'assets/composer-icon.png', 'assets/logo-dark.png', 'assets/composer-icon-dark.png', 'references/presentation-standard.md', 'references/access-and-evidence.md', 'references/research-workflow.md', 'skills/find-clinical-partners/SKILL.md', 'skills/find-clinical-partners/agents/openai.yaml', 'skills/analyze-trial-evidence/SKILL.md', 'skills/analyze-trial-evidence/agents/openai.yaml', 'skills/create-custom-view/SKILL.md', 'skills/create-custom-view/agents/openai.yaml', 'skills/manage-research-projects/SKILL.md', 'skills/manage-research-projects/agents/openai.yaml', 'skills/find-clinical-partners/references/tool-contract.md', 'skills/find-clinical-partners/references/prostate-landscape.json', 'skills/create-custom-view/references/custom-view-guidance.md', 'skills/create-custom-view/assets/custom-view-shell.html', 'skills/create-custom-view/assets/visual-examples.html')

def validate():
    for name in FILES:
        path = PACKAGE / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f'Missing or symlinked package file: {name}')
    manifest = json.loads((PACKAGE / 'plugin.json').read_text())
    ext = manifest['extensions']['com.openai']
    ui = ext['interface']
    for key, maximum in [('displayName',30),('shortDescription',30),('longDescription',4000),('developerName',80)]:
        if not 0 < len(ui[key]) <= maximum:
            raise ValueError(f'Invalid listing field: {key}')
    for key in ('websiteURL','supportURL','privacyPolicyURL','termsOfServiceURL'):
        if not ui[key].startswith('https://'):
            raise ValueError(f'Expected HTTPS URL: {key}')
    prompts = ui['defaultPrompt']
    if not 1 <= len(prompts) <= 3 or len(set(prompts)) != len(prompts) or any(len(p)>128 or '@' in p for p in prompts):
        raise ValueError('Invalid starter prompts')
    for ref in (ui['logo'],ui['composerIcon'],ui['logoDark'],ui['composerIconDark'],ext['onboardingSkill']):
        if not ref.startswith('./') or ref[2:] not in FILES:
            raise ValueError(f'Unpackaged reference: {ref}')
    cases = ext['review']['test_cases']
    for kind, count in [('positive',5),('negative',3)]:
        if len(cases[kind]) != count:
            raise ValueError(f'Expected {count} {kind} review cases')
        for case in cases[kind]:
            required = {'description','prompt'}
            if kind == 'positive': required |= {'tools_triggered','expected_behavior'}
            allowed = required | {'file_attachment_urls','expected_output_url'}
            if not required <= case.keys() or not case.keys() <= allowed:
                raise ValueError('Invalid review case fields')
            if any(not isinstance(case[key],str) or not case[key].strip() for key in required):
                raise ValueError('Incomplete review case')
    server = json.loads((PACKAGE/'mcp.json').read_text())['mcpServers']
    if server != {'trialagents-research': {'type':'streamable-http','url':'https://mcp.trialagents.com/research/mcp','extensions':{'com.openai':{'auth':{'type':'mixed'}}}}}:
        raise ValueError('Unexpected server configuration; no static authorization headers allowed')
    for key in ('logo','composerIcon','logoDark','composerIconDark'):
        data = (PACKAGE/ui[key][2:]).read_bytes()
        if len(data) < 33 or data[:16] != b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR':
            raise ValueError(f'Expected PNG asset: {key}')
        width,height = struct.unpack('>II',data[16:24])
        minimum = 256 if key.startswith('logo') else 48
        if width != height or not minimum <= width <= 4096 or len(data) > 5*1024*1024:
            raise ValueError(f'Invalid PNG asset dimensions/size: {key}')
    if manifest.get('apps') or ext.get('apps') or (PACKAGE/'.app.json').exists():
        raise ValueError('Public submission must not include registered-app bindings')
    # Check the shipped example against the actual implementation, not a copied schema.
    from intel_mcp.selection import SelectionCriteria
    SelectionCriteria.model_validate_json((PACKAGE/'skills/find-clinical-partners/references/prostate-landscape.json').read_text())
    import re
    for name in FILES:
        if not name.endswith('SKILL.md'): continue
        skill=PACKAGE/name; content=skill.read_text()
        if f"name: {skill.parent.name}\n" not in content or 'description:' not in content:
            raise ValueError(f'Invalid skill frontmatter: {name}')
        if '[TODO' in content: raise ValueError(f'Unfinished skill: {name}')
        for link in re.findall(r'\]\(([^)#]+)(?:#[^)]*)?\)',content):
            if '://' in link: continue
            target=(skill.parent/link).resolve()
            if not target.is_relative_to(PACKAGE.resolve()) or not target.is_file():
                raise ValueError(f'Broken or external skill reference: {name}: {link}')
            if str(target.relative_to(PACKAGE.resolve())) not in FILES:
                raise ValueError(f'Unpackaged skill reference: {link}')
    return manifest

def build(destination):
    manifest = validate()
    destination.mkdir(parents=True,exist_ok=True)
    output = destination / f"{manifest['name']}-{manifest['version']}.zip"
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(FILES):
            info = zipfile.ZipInfo(name, date_time=(2026,10,6,0,0,0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info,(PACKAGE/name).read_bytes())
    return output

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=ROOT/'dist')
    args=parser.parse_args()
    print(build(args.output_dir))
