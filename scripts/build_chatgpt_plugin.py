#!/usr/bin/env python3
"""Validate and reproducibly zip the explicit public plugin payload (no repo secrets)."""
import argparse
import json
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'plugins/trialagents-intel'
FILES = ('skills/answer-in-trialagents/SKILL.md', 'skills/answer-in-trialagents/agents/openai.yaml', 'references/custom-style.md', 'plugin.json', 'mcp.json', 'assets/icon.svg', 'references/presentation-standard.md', 'references/access-and-evidence.md', 'references/research-workflow.md', 'skills/find-clinical-partners/SKILL.md', 'skills/find-clinical-partners/agents/openai.yaml', 'skills/analyze-trial-evidence/SKILL.md', 'skills/analyze-trial-evidence/agents/openai.yaml', 'skills/create-trial-report/SKILL.md', 'skills/create-trial-report/agents/openai.yaml', 'skills/manage-research-projects/SKILL.md', 'skills/manage-research-projects/agents/openai.yaml', 'skills/find-clinical-partners/references/tool-contract.md', 'skills/find-clinical-partners/references/prostate-landscape.json', 'skills/create-trial-report/references/report-guidance.md', 'skills/create-trial-report/assets/report-example.html', 'skills/create-trial-report/assets/visual-examples.html')

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
    for ref in (ui['logo'],ui['composerIcon'],ext['onboardingSkill']):
        if not ref.startswith('./') or ref[2:] not in FILES:
            raise ValueError(f'Unpackaged reference: {ref}')
    cases = ext['review']['test_cases']
    for kind, count in [('positive',5),('negative',3)]:
        if len(cases[kind]) != count:
            raise ValueError(f'Expected {count} {kind} review cases')
        for case in cases[kind]:
            if not all(key in case for key in ('description','prompt','tools_triggered','expected_behavior')):
                raise ValueError('Incomplete review case')
    server = json.loads((PACKAGE/'mcp.json').read_text())['mcpServers']
    if server != {'trialagents-research': {'type':'streamable-http','url':'https://mcp.trialagents.com/research/mcp'}}:
        raise ValueError('Unexpected server configuration; no static authorization headers allowed')
    icon = ET.parse(PACKAGE/'assets/icon.svg').getroot()
    if float(icon.attrib['width']) != float(icon.attrib['height']) or float(icon.attrib['width']) < 48:
        raise ValueError('Icon must be square and at least 48 pixels')
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
