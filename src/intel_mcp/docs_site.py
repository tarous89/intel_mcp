"""Public documentation page served by the Intel MCP web service."""

DOCS_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Connect ChatGPT, Claude, or your own software to TrialAgents clinical trial intelligence through MCP.">
  <meta name="theme-color" content="#101311">
  <title>TrialAgents Intel MCP — Documentation</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #101311;
      --bg-raised: #151a17;
      --panel: rgba(24, 30, 26, .82);
      --panel-strong: #1b211d;
      --line: rgba(255, 255, 255, .10);
      --line-strong: rgba(255, 255, 255, .17);
      --text: #f6f8f6;
      --muted: #aab2ac;
      --green: #55b985;
      --green-light: #82d7a7;
      --green-dark: #0f2c1e;
      --amber: #f3bb67;
      --amber-bg: rgba(243, 187, 103, .09);
      --radius: 16px;
      --shadow: 0 24px 80px rgba(0, 0, 0, .25);
    }
    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; scroll-padding-top: 88px; }
    body {
      margin: 0;
      min-width: 320px;
      background:
        radial-gradient(900px 440px at 78% -10%, rgba(85, 185, 133, .14), transparent 65%),
        radial-gradient(700px 420px at -15% 20%, rgba(85, 185, 133, .06), transparent 62%),
        var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.55;
      -webkit-font-smoothing: antialiased;
    }
    a { color: inherit; }
    button, input { font: inherit; }
    .shell { width: min(1120px, calc(100% - 40px)); margin: 0 auto; }
    .site-header {
      position: sticky;
      top: 0;
      z-index: 30;
      border-bottom: 1px solid var(--line);
      background: rgba(16, 19, 17, .82);
      backdrop-filter: blur(18px);
    }
    .header-inner { height: 70px; display: flex; align-items: center; justify-content: space-between; gap: 28px; }
    .brand { display: inline-flex; align-items: center; gap: 11px; text-decoration: none; white-space: nowrap; }
    .brand-mark { width: 28px; height: 28px; display: grid; place-items: center; }
    .brand-name { font-weight: 700; letter-spacing: -.02em; }
    .brand-divider { width: 1px; height: 22px; background: var(--line-strong); }
    .brand-product { color: var(--muted); font-size: .94rem; }
    .top-nav { display: flex; align-items: center; gap: 24px; }
    .top-nav a { color: var(--muted); text-decoration: none; font-size: .88rem; transition: color .16s ease; }
    .top-nav a:hover { color: var(--text); }
    .button {
      display: inline-flex; align-items: center; justify-content: center; gap: 8px;
      min-height: 40px; padding: 0 16px; border: 1px solid transparent; border-radius: 10px;
      background: var(--green); color: #07140d; text-decoration: none; font-weight: 700; font-size: .88rem;
      transition: transform .16s ease, background .16s ease;
    }
    .button:hover { transform: translateY(-1px); background: var(--green-light); }
    .button.secondary { background: transparent; color: var(--text); border-color: var(--line-strong); }
    .button.secondary:hover { background: rgba(255,255,255,.04); }
    main { padding-bottom: 88px; }
    .hero { padding: 86px 0 58px; }
    .eyebrow {
      display: inline-flex; align-items: center; gap: 8px;
      color: var(--green-light); font-weight: 750; text-transform: uppercase;
      letter-spacing: .13em; font-size: .72rem;
    }
    .eyebrow::before { content: ""; width: 20px; height: 1px; background: var(--green); }
    h1 { margin: 18px 0 18px; max-width: 850px; font-size: clamp(2.45rem, 6vw, 5.25rem); line-height: .98; letter-spacing: -.055em; }
    .hero-lead { max-width: 720px; margin: 0; color: var(--muted); font-size: clamp(1.06rem, 2vw, 1.28rem); }
    .hero-actions { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 30px; }
    .endpoint-card {
      margin-top: 42px; padding: 18px 20px; border: 1px solid var(--line); border-radius: 13px;
      background: rgba(255,255,255,.025); display: flex; align-items: center; justify-content: space-between; gap: 18px;
      box-shadow: var(--shadow);
    }
    .endpoint-label { color: var(--muted); font-size: .77rem; text-transform: uppercase; letter-spacing: .1em; }
    .endpoint { margin-top: 4px; font: 600 .98rem/1.4 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; overflow-wrap: anywhere; }
    .status-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--green); box-shadow: 0 0 0 5px rgba(85,185,133,.12); }
    .live { display: inline-flex; align-items: center; gap: 10px; color: var(--green-light); font-size: .82rem; font-weight: 700; white-space: nowrap; }
    section { padding: 62px 0; border-top: 1px solid var(--line); }
    .section-head { display: grid; grid-template-columns: minmax(0, .7fr) minmax(0, 1.3fr); gap: 44px; margin-bottom: 34px; }
    .section-kicker { color: var(--green-light); text-transform: uppercase; letter-spacing: .12em; font-size: .72rem; font-weight: 750; }
    h2 { margin: 10px 0 0; font-size: clamp(1.75rem, 3vw, 2.55rem); line-height: 1.08; letter-spacing: -.035em; }
    .section-intro { margin: 3px 0 0; color: var(--muted); max-width: 670px; }
    .notice {
      display: grid; grid-template-columns: auto 1fr; gap: 15px; align-items: start;
      padding: 20px; border: 1px solid rgba(243,187,103,.28); border-radius: var(--radius); background: var(--amber-bg);
    }
    .notice-icon { width: 26px; height: 26px; display: grid; place-items: center; border-radius: 50%; background: rgba(243,187,103,.16); color: var(--amber); font-weight: 800; }
    .notice strong { display: block; color: #f9d8a5; margin-bottom: 4px; }
    .notice p { margin: 0; color: #cbbca5; font-size: .94rem; }
    .steps { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-top: 26px; }
    .step { position: relative; min-height: 178px; padding: 20px; border: 1px solid var(--line); border-radius: var(--radius); background: var(--panel); }
    .step-number { color: var(--green-light); font: 700 .78rem/1 ui-monospace, SFMono-Regular, Menlo, monospace; }
    .step h3 { margin: 25px 0 8px; font-size: 1rem; letter-spacing: -.01em; }
    .step p { margin: 0; color: var(--muted); font-size: .88rem; }
    .platform-shell { border: 1px solid var(--line); border-radius: var(--radius); background: var(--panel); overflow: hidden; }
    .tabs { display: flex; gap: 4px; padding: 9px; border-bottom: 1px solid var(--line); background: rgba(0,0,0,.12); overflow-x: auto; }
    .tab {
      appearance: none; border: 0; border-radius: 9px; padding: 10px 15px; background: transparent;
      color: var(--muted); cursor: pointer; font-weight: 700; font-size: .88rem; white-space: nowrap;
    }
    .tab[aria-selected="true"] { background: rgba(85,185,133,.13); color: var(--green-light); }
    .tab-panel { display: none; padding: 26px; }
    .tab-panel.active { display: block; }
    .platform-grid { display: grid; grid-template-columns: minmax(0, .8fr) minmax(0, 1.2fr); gap: 30px; }
    .platform-copy h3 { margin: 0 0 8px; font-size: 1.3rem; }
    .platform-copy > p { margin: 0 0 20px; color: var(--muted); font-size: .94rem; }
    .numbered { list-style: none; padding: 0; margin: 0; counter-reset: instruction; }
    .numbered li { position: relative; padding: 0 0 18px 38px; color: var(--muted); font-size: .9rem; counter-increment: instruction; }
    .numbered li::before {
      content: counter(instruction); position: absolute; left: 0; top: -1px; width: 24px; height: 24px;
      display: grid; place-items: center; border: 1px solid rgba(85,185,133,.38); border-radius: 50%; color: var(--green-light); font-size: .73rem; font-weight: 800;
    }
    .numbered strong { color: var(--text); }
    .small-link { color: var(--green-light); text-underline-offset: 3px; }
    .status-label {
      display: inline-flex; align-items: center; gap: 7px; margin-bottom: 17px; padding: 5px 9px;
      border: 1px solid rgba(243,187,103,.25); border-radius: 999px; color: #f2c882; background: rgba(243,187,103,.07);
      font-size: .72rem; font-weight: 750; text-transform: uppercase; letter-spacing: .08em;
    }
    .code-card { position: relative; border: 1px solid var(--line); border-radius: 13px; overflow: hidden; background: #0b0e0c; }
    .code-head { display: flex; align-items: center; justify-content: space-between; gap: 16px; min-height: 42px; padding: 0 12px 0 15px; border-bottom: 1px solid var(--line); color: #7f8982; font-size: .74rem; }
    .copy {
      appearance: none; border: 1px solid var(--line); border-radius: 7px; background: rgba(255,255,255,.03);
      color: var(--muted); padding: 5px 9px; cursor: pointer; font-size: .72rem; font-weight: 700;
    }
    .copy:hover { color: var(--text); border-color: var(--line-strong); }
    pre { margin: 0; padding: 18px; overflow-x: auto; color: #d9e2dc; font: .81rem/1.65 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; tab-size: 2; }
    .code-note { margin: 12px 0 0; color: var(--muted); font-size: .82rem; }
    .prompt-card { padding: 18px; border: 1px solid rgba(85,185,133,.23); border-radius: 13px; background: rgba(85,185,133,.055); }
    .prompt-label { color: var(--green-light); font-size: .72rem; font-weight: 750; text-transform: uppercase; letter-spacing: .1em; }
    .prompt-card p { margin: 9px 0 0; color: #dfe7e1; font-size: .9rem; }
    .workflow { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
    .tool-card { padding: 20px; border: 1px solid var(--line); border-radius: var(--radius); background: var(--panel); }
    .tool-top { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
    .tool-card code { color: var(--green-light); font: 700 .86rem/1.4 ui-monospace, SFMono-Regular, Menlo, monospace; }
    .tool-order { color: #707a73; font: 700 .72rem/1 ui-monospace, SFMono-Regular, Menlo, monospace; }
    .tool-card h3 { margin: 18px 0 7px; font-size: 1rem; }
    .tool-card p { margin: 0; color: var(--muted); font-size: .87rem; }
    .tool-card .limit { display: inline-block; margin-top: 14px; color: #859088; font-size: .75rem; }
    .tool-card.primary-tool { border-color: rgba(85,185,133,.27); background: linear-gradient(145deg, rgba(85,185,133,.08), var(--panel)); }
    .examples { display: grid; gap: 18px; }
    .example-row { display: grid; grid-template-columns: 210px minmax(0, 1fr); gap: 20px; align-items: start; }
    .example-copy h3 { margin: 3px 0 6px; font-size: .98rem; }
    .example-copy p { margin: 0; color: var(--muted); font-size: .84rem; }
    .callout { margin-top: 20px; padding: 18px 20px; border-left: 2px solid var(--green); background: rgba(85,185,133,.055); color: var(--muted); font-size: .9rem; }
    .callout strong { color: var(--text); }
    .footer { border-top: 1px solid var(--line); padding: 28px 0 38px; color: #7f8982; }
    .footer-inner { display: flex; justify-content: space-between; gap: 20px; font-size: .82rem; }
    .footer-links { display: flex; gap: 18px; }
    .footer a { color: var(--muted); text-decoration: none; }
    .footer a:hover { color: var(--text); }
    @media (max-width: 900px) {
      .top-nav a:not(.button) { display: none; }
      .section-head, .platform-grid { grid-template-columns: 1fr; gap: 20px; }
      .steps { grid-template-columns: repeat(2, 1fr); }
      .workflow { grid-template-columns: repeat(2, 1fr); }
      .example-row { grid-template-columns: 1fr; gap: 10px; }
    }
    @media (max-width: 620px) {
      .shell { width: min(100% - 28px, 1120px); }
      .header-inner { height: 62px; }
      .brand-product, .brand-divider, .top-nav { display: none; }
      .hero { padding: 62px 0 45px; }
      .endpoint-card { align-items: flex-start; flex-direction: column; }
      section { padding: 48px 0; }
      .steps, .workflow { grid-template-columns: 1fr; }
      .step { min-height: 0; }
      .tab-panel { padding: 19px; }
      .platform-grid { gap: 24px; }
      .footer-inner { flex-direction: column; }
    }
    @media (prefers-reduced-motion: reduce) { html { scroll-behavior: auto; } * { transition: none !important; } }
  </style>
</head>
<body>
  <header class="site-header">
    <div class="shell header-inner">
      <a class="brand" href="#top" aria-label="TrialAgents Intel MCP documentation">
        <span class="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 32 32" width="28" height="28" fill="none">
            <path d="M7 5h8v8H7zM17 5h8v8h-8zM7 15h8v12H7z" fill="#fff"/>
            <path d="M17 15h8v4h-8zM17 21h8v6h-8z" fill="#55b985"/>
          </svg>
        </span>
        <span class="brand-name">Trial Agents</span>
        <span class="brand-divider"></span>
        <span class="brand-product">Intel MCP</span>
      </a>
      <nav class="top-nav" aria-label="Documentation navigation">
        <a href="#quick-start">Quick start</a>
        <a href="#connect">Connect</a>
        <a href="#tools">Tools</a>
        <a href="https://intel.trialagents.com" class="button">Open Intel Agent <span aria-hidden="true">↗</span></a>
      </nav>
    </div>
  </header>

  <main id="top">
    <div class="shell hero">
      <div class="eyebrow">Clinical trial intelligence over MCP</div>
      <h1>Bring approved trial intelligence into your AI workflow.</h1>
      <p class="hero-lead">Connect ChatGPT, Claude, or your own software to shortlist trials, classify eligibility, retrieve approved profiles and documents, and extract structured variables.</p>
      <div class="hero-actions">
        <a class="button" href="#connect">Choose your client</a>
        <a class="button secondary" href="#workflow-examples">Copy tool calls</a>
      </div>
      <div class="endpoint-card">
        <div>
          <div class="endpoint-label">Streamable HTTP endpoint</div>
          <div class="endpoint">https://mcp.trialagents.com/mcp</div>
        </div>
        <div class="live"><span class="status-dot"></span> Service online</div>
      </div>
    </div>

    <section id="quick-start">
      <div class="shell">
        <div class="section-head">
          <div><div class="section-kicker">Quick start</div><h2>One analysis, one reusable ID</h2></div>
          <p class="section-intro">Every MCP workflow begins with an approved report run created in Intel Agent. The first tool call turns that run into a 60-minute analysis lease; every later call uses the returned <code>analysis_id</code>.</p>
        </div>
        <div class="notice">
          <div class="notice-icon">!</div>
          <div>
            <strong>Sign in with your existing Intel Agent account.</strong>
            <p>ChatGPT and Claude use TrialAgents OAuth. After login and consent, the client receives a scoped, short-lived token; your password, plan, payment details, and internal service credentials are never shared with the client.</p>
          </div>
        </div>
        <div class="steps">
          <article class="step"><span class="step-number">01</span><h3>Create a report run</h3><p>Open Intel Agent, configure the report, and complete plan approval.</p></article>
          <article class="step"><span class="step-number">02</span><h3>Connect your client</h3><p>Add the remote MCP URL, sign in at Intel Agent, and approve the connection.</p></article>
          <article class="step"><span class="step-number">03</span><h3>Start the analysis</h3><p>Call <code>start_analysis</code> once with the app-created <code>report_run_id</code>.</p></article>
          <article class="step"><span class="step-number">04</span><h3>Use the tools</h3><p>Pass the returned <code>analysis_id</code> to every filter, profile, document, classification, or extraction call.</p></article>
        </div>
      </div>
    </section>

    <section id="connect">
      <div class="shell">
        <div class="section-head">
          <div><div class="section-kicker">Connect</div><h2>Exact setup by client</h2></div>
          <p class="section-intro">Select a client for its current setup path. ChatGPT and Claude use hosted connectors; software integrations use the standard MCP SDK over Streamable HTTP.</p>
        </div>
        <div class="platform-shell">
          <div class="tabs" role="tablist" aria-label="MCP client">
            <button class="tab" type="button" role="tab" aria-selected="true" aria-controls="panel-chatgpt" id="tab-chatgpt" data-tab="chatgpt">ChatGPT</button>
            <button class="tab" type="button" role="tab" aria-selected="false" aria-controls="panel-claude" id="tab-claude" data-tab="claude">Claude</button>
            <button class="tab" type="button" role="tab" aria-selected="false" aria-controls="panel-software" id="tab-software" data-tab="software">Own software</button>
          </div>

          <div class="tab-panel active" id="panel-chatgpt" role="tabpanel" aria-labelledby="tab-chatgpt">
            <div class="platform-grid">
              <div class="platform-copy">
                <div class="status-label">TrialAgents OAuth live</div>
                <h3>Connect from ChatGPT</h3>
                <p>Custom MCP tools are connected through ChatGPT developer mode. Workspace permissions and plan availability apply.</p>
                <ol class="numbered">
                  <li>Open ChatGPT <strong>Settings → Security and login</strong> and turn on <strong>Developer mode</strong>. A workspace admin may need to allow it.</li>
                  <li>Open <strong>ChatGPT Plugins</strong>, select the plus button, and create a developer-mode MCP connection.</li>
                  <li>Name it <strong>TrialAgents Intel</strong>, add a short description, and enter the MCP URL shown here.</li>
                  <li>Sign in with your Intel Agent email and password, then approve the scoped connection.</li>
                  <li>Enable TrialAgents Intel in a new conversation and use the starter prompt.</li>
                </ol>
                <a class="small-link" href="https://developers.openai.com/api/docs/guides/developer-mode" target="_blank" rel="noreferrer">Official ChatGPT setup guide ↗</a>
              </div>
              <div>
                <div class="code-card">
                  <div class="code-head"><span>MCP server URL</span><button class="copy" type="button">Copy</button></div>
                  <pre><code>https://mcp.trialagents.com/mcp</code></pre>
                </div>
                <div class="prompt-card" style="margin-top:14px">
                  <div class="prompt-label">Starter prompt</div>
                  <p>Use TrialAgents Intel. Start the approved report run <strong>RUN_ID</strong>, shortlist phase 2 solid-tumor oncology trials recruiting in Germany, and return the EU trial number, title, and sponsor for each match.</p>
                </div>
              </div>
            </div>
          </div>

          <div class="tab-panel" id="panel-claude" role="tabpanel" aria-labelledby="tab-claude">
            <div class="platform-grid">
              <div class="platform-copy">
                <div class="status-label">TrialAgents OAuth live</div>
                <h3>Connect from Claude</h3>
                <p>Claude supports public remote MCP servers as custom connectors across its web and desktop surfaces.</p>
                <ol class="numbered">
                  <li>On Pro or Max, open Customize → Connectors. On Team or Enterprise, an Owner first opens Organization settings → Connectors.</li>
                  <li>Click <strong>+</strong>, choose <strong>Add custom connector</strong> (or Custom → Web for an organization), and enter the MCP URL.</li>
                  <li>Name it <strong>TrialAgents Intel</strong>, save it, then click <strong>Connect</strong>.</li>
                  <li>Sign in with your Intel Agent email and password, then approve the scoped connection.</li>
                  <li>In a chat, use the <strong>+</strong> menu → Connectors and enable TrialAgents Intel for that conversation.</li>
                </ol>
                <a class="small-link" href="https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp" target="_blank" rel="noreferrer">Official Claude setup guide ↗</a>
              </div>
              <div>
                <div class="code-card">
                  <div class="code-head"><span>Remote MCP server URL</span><button class="copy" type="button">Copy</button></div>
                  <pre><code>https://mcp.trialagents.com/mcp</code></pre>
                </div>
                <div class="prompt-card" style="margin-top:14px">
                  <div class="prompt-label">Starter prompt</div>
                  <p>Use TrialAgents Intel to start report run <strong>RUN_ID</strong>. Filter the approved trial profiles first, classify the shortlist against my criteria, then retrieve full profiles only for eligible trials.</p>
                </div>
              </div>
            </div>
          </div>

          <div class="tab-panel" id="panel-software" role="tabpanel" aria-labelledby="tab-software">
            <div class="platform-grid">
              <div class="platform-copy">
                <div class="status-label">Private integration beta</div>
                <h3>Connect from your software</h3>
                <p>Use a TrialAgents-issued bearer credential with the official Python MCP SDK. Never commit the credential or send it to a browser.</p>
                <ol class="numbered">
                  <li>Obtain a private integration credential from TrialAgents and store it as <strong>TRIALAGENTS_ACCESS_TOKEN</strong>.</li>
                  <li>Install Python 3.11+ and the MCP SDK with the command on the right.</li>
                  <li>Copy the example, replace <strong>run_...</strong> with an approved Intel Agent report run ID, and execute it.</li>
                  <li>Keep the returned <strong>analysis_id</strong> and pass it to every later tool call for that analysis.</li>
                </ol>
                <a class="small-link" href="https://modelcontextprotocol.io/specification/2025-11-25/basic/transports" target="_blank" rel="noreferrer">MCP Streamable HTTP specification ↗</a>
              </div>
              <div>
                <div class="code-card">
                  <div class="code-head"><span>Install</span><button class="copy" type="button">Copy</button></div>
                  <pre><code>python -m pip install "mcp&gt;=2,&lt;3"</code></pre>
                </div>
                <div class="code-card" style="margin-top:14px">
                  <div class="code-head"><span>Python · connect and call a tool</span><button class="copy" type="button">Copy</button></div>
                  <pre><code>import asyncio
import os

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

MCP_URL = "https://mcp.trialagents.com/mcp"

async def main():
    headers = {
        "Authorization": f"Bearer {os.environ['TRIALAGENTS_ACCESS_TOKEN']}"
    }
    async with httpx.AsyncClient(headers=headers) as http:
        async with streamable_http_client(MCP_URL, http_client=http) as streams:
            read_stream, write_stream = streams
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(
                    "start_analysis",
                    {"report_run_id": "run_..."},
                )
                print(result.structured_content)

asyncio.run(main())</code></pre>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section id="tools">
      <div class="shell">
        <div class="section-head">
          <div><div class="section-kicker">Tool map</div><h2>Use the lightest tool that answers the question</h2></div>
          <p class="section-intro">Start with deterministic filtering. Classify only a focused shortlist, retrieve full profiles only for selected trials, and load document text only when the profile does not contain the answer.</p>
        </div>
        <div class="workflow">
          <article class="tool-card primary-tool"><div class="tool-top"><code>start_analysis</code><span class="tool-order">01</span></div><h3>Open the analysis lease</h3><p>Turns an approved report run into the active analysis ID used by every other tool.</p><span class="limit">One active 60-minute lease</span></article>
          <article class="tool-card primary-tool"><div class="tool-top"><code>filter_trials</code><span class="tool-order">02</span></div><h3>Build a shortlist</h3><p>Applies structured filters and returns only EU number, trial title, and sponsor—not document inventory.</p><span class="limit">Up to 100 results per page</span></article>
          <article class="tool-card"><div class="tool-top"><code>classify_trials</code><span class="tool-order">03</span></div><h3>Classify eligibility</h3><p>Sends each complete contact-redacted profile to Terra, then returns only eligible, ineligible, and uncertain ID buckets.</p><span class="limit">Up to 25 trials per call</span></article>
          <article class="tool-card"><div class="tool-top"><code>get_profiles</code><span class="tool-order">04</span></div><h3>Read complete profiles</h3><p>Returns selected approved profiles, including the six document-category arrays and their exact filenames.</p><span class="limit">Up to 10 trials per call</span></article>
          <article class="tool-card"><div class="tool-top"><code>get_documents</code><span class="tool-order">05</span></div><h3>Read one document</h3><p>Uses an exact filename from the trial profile and returns extracted text in bounded continuation parts.</p><span class="limit">One document per call</span></article>
          <article class="tool-card"><div class="tool-top"><code>extract_variables</code><span class="tool-order">05</span></div><h3>Extract typed values</h3><p>Sends one complete profile and its single profile-listed protocol to Terra, returning only the requested values.</p><span class="limit">Up to 20 variables per call</span></article>
        </div>
        <div class="callout"><strong>Document filenames live in Trial Profiles.</strong> Call <code>get_profiles</code> first and copy the exact name from <code>available_extracted_documents</code> before calling <code>get_documents</code>. Empty categories are returned as empty arrays.</div>
      </div>
    </section>

    <section id="workflow-examples">
      <div class="shell">
        <div class="section-head">
          <div><div class="section-kicker">Copyable calls</div><h2>A complete analysis sequence</h2></div>
          <p class="section-intro">These are MCP tool arguments—not raw HTTP request bodies. Paste them into an MCP inspector, use them with <code>session.call_tool()</code>, or give the equivalent instruction to ChatGPT or Claude.</p>
        </div>
        <div class="examples">
          <div class="example-row">
            <div class="example-copy"><h3>1. Start analysis</h3><p>Use the report run created and approved in Intel Agent.</p></div>
            <div class="code-card"><div class="code-head"><span>start_analysis</span><button class="copy" type="button">Copy</button></div><pre><code>{
  "report_run_id": "run_..."
}</code></pre></div>
          </div>
          <div class="example-row">
            <div class="example-copy"><h3>2. Filter trials</h3><p>Different fields combine with AND. Page with <code>offset</code> if needed.</p></div>
            <div class="code-card"><div class="code-head"><span>filter_trials</span><button class="copy" type="button">Copy</button></div><pre><code>{
  "analysis_id": "ana_...",
  "filters": {
    "therapeutic_areas": {
      "operator": "contains_any",
      "values": ["Solid Tumor Oncology"]
    },
    "phase": {"operator": "contains_any", "values": [2]},
    "countries": [{
      "country_codes": {"operator": "contains_any", "values": ["DE"]},
      "recruitment_statuses": {
        "operator": "contains_any",
        "values": ["Authorised"]
      }
    }]
  },
  "limit": 20,
  "offset": 0
}</code></pre></div>
          </div>
          <div class="example-row">
            <div class="example-copy"><h3>3. Classify shortlist</h3><p>Use identical criteria across batches of no more than 25 trial IDs.</p></div>
            <div class="code-card"><div class="code-head"><span>classify_trials</span><button class="copy" type="button">Copy</button></div><pre><code>{
  "analysis_id": "ana_...",
  "trial_ids": ["2024-500001-00-00"],
  "inclusion_criteria": [
    "The trial includes adults with unresectable locally advanced disease"
  ],
  "exclusion_criteria": [
    "The trial is restricted to healthy volunteers"
  ]
}</code></pre></div>
          </div>
          <div class="example-row">
            <div class="example-copy"><h3>4. Get profiles</h3><p>Retrieve full profiles for selected trials; inspect exact document names here.</p></div>
            <div class="code-card"><div class="code-head"><span>get_profiles</span><button class="copy" type="button">Copy</button></div><pre><code>{
  "analysis_id": "ana_...",
  "trial_ids": ["2024-500001-00-00"]
}</code></pre></div>
          </div>
          <div class="example-row">
            <div class="example-copy"><h3>5a. Get a document</h3><p>Use an exact profile-listed filename. Follow <code>next_part</code> until it is null.</p></div>
            <div class="code-card"><div class="code-head"><span>get_documents</span><button class="copy" type="button">Copy</button></div><pre><code>{
  "analysis_id": "ana_...",
  "trial_id": "2024-500001-00-00",
  "document_name": "Clinical Trial Protocol v3",
  "part": 1
}</code></pre></div>
          </div>
          <div class="example-row">
            <div class="example-copy"><h3>5b. Extract variables</h3><p>Prefer targeted typed extraction when you need facts rather than complete text.</p></div>
            <div class="code-card"><div class="code-head"><span>extract_variables</span><button class="copy" type="button">Copy</button></div><pre><code>{
  "analysis_id": "ana_...",
  "trial_id": "2024-500001-00-00",
  "variables": [
    {
      "name": "planned_sample_size",
      "instruction": "Return the planned randomized population.",
      "value_type": "integer"
    },
    {
      "name": "central_imaging_review",
      "instruction": "Is central imaging review required?",
      "value_type": "boolean"
    }
  ]
}</code></pre></div>
          </div>
        </div>
      </div>
    </section>

    <section id="security">
      <div class="shell">
        <div class="section-head">
          <div><div class="section-kicker">Security &amp; behavior</div><h2>Bounded by approved data and allowances</h2></div>
          <div class="section-intro">
            <p>All clinical reads use current approved Trial Profiles. Filtering returns lean shortlist metadata; classification receives the complete contact-redacted profile but does not expose it in the result. Document text is retrieved only by an exact profile-listed filename.</p>
            <p>Calls are scoped to a time-limited analysis and metered by the plan approved in Intel Agent. Exact retries are deduplicated where the tool contract allows it.</p>
          </div>
        </div>
      </div>
    </section>
  </main>

  <footer class="footer">
    <div class="shell footer-inner">
      <span>© 2026 Trial Agents · Intel MCP</span>
      <div class="footer-links">
        <a href="https://intel.trialagents.com">Intel Agent</a>
        <a href="/health">Service health</a>
      </div>
    </div>
  </footer>

  <script>
    const tabs = document.querySelectorAll('[data-tab]');
    tabs.forEach((tab) => {
      tab.addEventListener('click', () => {
        tabs.forEach((item) => item.setAttribute('aria-selected', 'false'));
        document.querySelectorAll('.tab-panel').forEach((panel) => panel.classList.remove('active'));
        tab.setAttribute('aria-selected', 'true');
        document.getElementById('panel-' + tab.dataset.tab).classList.add('active');
      });
    });

    document.querySelectorAll('.copy').forEach((button) => {
      button.addEventListener('click', async () => {
        const code = button.closest('.code-card').querySelector('code').innerText;
        try {
          await navigator.clipboard.writeText(code);
          const original = button.textContent;
          button.textContent = 'Copied';
          setTimeout(() => { button.textContent = original; }, 1400);
        } catch (_) {
          button.textContent = 'Select text';
        }
      });
    });
  </script>
</body>
</html>
"""
