#!/usr/bin/env python3
"""Mirror canonical plugin guidance into the installed MCP wheel; --check prevents drift."""
from pathlib import Path
import argparse
ROOT=Path(__file__).resolve().parents[1]
PACKAGE=ROOT/'plugins/trialagents-intel'
MIRRORS={
 'server-instructions.md':'references/server-instructions.md',
 'design-patterns.md':'skills/create-custom-view/references/design-patterns.md',
 'custom-view-examples.html':'skills/create-custom-view/assets/custom-view-examples.html',
 'custom-style.md':'references/custom-style.md',
 'presentation-standard.md':'references/presentation-standard.md',
 'access-and-evidence.md':'references/access-and-evidence.md',
 'research-workflow.md':'references/research-workflow.md',
 'custom-view-guidance.md':'skills/create-custom-view/references/custom-view-guidance.md',
 'custom-view-shell.html':'skills/create-custom-view/assets/custom-view-shell.html',
}
def sync(check=False):
 for target,source in MIRRORS.items():
  expected=(PACKAGE/source).read_bytes();path=ROOT/'src/intel_mcp'/target
  if check:
   if not path.exists() or path.read_bytes()!=expected:raise ValueError(f'Guidance drift: {target}; run scripts/sync_plugin_guidance.py')
  else:path.write_bytes(expected)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');sync(p.parse_args().check)
