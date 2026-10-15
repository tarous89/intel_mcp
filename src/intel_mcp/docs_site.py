"""Static documentation generated from the App's shared public chrome.

Rebuild with: node ui/research/build-docs.mjs /path/to/intel_agent_app
Never redirect transport or authorization routes when changing this page.
"""
from importlib.resources import files

DOCS_HTML = files("intel_mcp").joinpath("ui/mcp-documentation.html").read_text(encoding="utf-8")
