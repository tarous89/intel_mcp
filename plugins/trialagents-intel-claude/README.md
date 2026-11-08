# TrialAgents for Claude

Claude plugin for TrialAgents Intel. It exposes one skill, **Ask TrialAgents** (`/trialagents:ask`), and connects to the Claude endpoint `https://mcp.trialagents.com/claude/mcp`.

This package is separate from the ChatGPT plugin in `plugins/trialagents-intel`, which keeps its own skills and its `/research/mcp` endpoint. Nothing here is read by the ChatGPT build (`scripts/build_chatgpt_plugin.py`) or by the guidance mirror (`scripts/sync_plugin_guidance.py`); both use only `plugins/trialagents-intel`.

Layout:

- `.claude-plugin/plugin.json`: plugin manifest (name `trialagents`).
- `.mcp.json`: the Claude MCP endpoint.
- `skills/ask/SKILL.md`: the single entry skill with the routing table.
- `skills/ask/references/`: find partners, search criteria, trial evidence, Custom views, projects, access rules, and the Custom view rendering guidance adapted from the ChatGPT plugin.
- `skills/ask/assets/`: Custom view HTML shell and examples.

In Claude, install this plugin and remove the ChatGPT `trialagents-intel` plugin from the same account, so that only Ask TrialAgents appears.
