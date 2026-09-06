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
    :root{color-scheme:dark;--bg:#101311;--panel:#171c19;--line:rgba(255,255,255,.11);--text:#f5f7f5;--muted:#aab2ac;--green:#55b985;--green2:#82d7a7;--amber:#f3bb67;--r:15px}
    *{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:radial-gradient(900px 500px at 85% -10%,rgba(85,185,133,.14),transparent 65%),var(--bg);color:var(--text);font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;line-height:1.55;-webkit-font-smoothing:antialiased}
    a{color:inherit}.shell{width:min(1120px,calc(100% - 40px));margin:auto}.header{position:sticky;top:0;z-index:20;border-bottom:1px solid var(--line);background:rgba(16,19,17,.9);backdrop-filter:blur(16px)}
    .header .shell{height:68px;display:flex;align-items:center;justify-content:space-between;gap:24px}.brand{display:flex;align-items:center;gap:10px;text-decoration:none;font-weight:750}.brand i{width:11px;height:11px;border-radius:50%;background:var(--green);box-shadow:0 0 0 6px rgba(85,185,133,.1)}
    nav{display:flex;gap:22px}nav a{color:var(--muted);text-decoration:none;font-size:.86rem}.hero{padding:82px 0 66px}.eyebrow{color:var(--green2);font-size:.73rem;font-weight:800;letter-spacing:.12em;text-transform:uppercase}.hero h1{max-width:860px;margin:16px 0 18px;font-size:clamp(2.6rem,6vw,5.2rem);line-height:.98;letter-spacing:-.055em}.hero p{max-width:760px;color:var(--muted);font-size:1.12rem}.endpoint{margin-top:32px;padding:18px 20px;border:1px solid var(--line);border-radius:var(--r);background:rgba(255,255,255,.025);font-family:ui-monospace,SFMono-Regular,Menlo,monospace}.live{float:right;color:var(--green2);font:700 .78rem Inter,system-ui}
    section{padding:58px 0;border-top:1px solid var(--line)}.head{display:grid;grid-template-columns:.7fr 1.3fr;gap:40px;margin-bottom:28px}.kicker{color:var(--green2);font-size:.72rem;font-weight:800;letter-spacing:.12em;text-transform:uppercase}.head h2{margin:8px 0 0;font-size:clamp(1.8rem,3vw,2.5rem);line-height:1.08}.head p{margin:3px 0 0;color:var(--muted)}
    .grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.card{padding:20px;border:1px solid var(--line);border-radius:var(--r);background:var(--panel)}.card code{color:var(--green2);font-weight:750}.card h3{margin:16px 0 7px;font-size:1rem}.card p{margin:0;color:var(--muted);font-size:.88rem}.limit{display:block;margin-top:13px;color:#808a83;font-size:.76rem}
    .callout{margin-top:18px;padding:18px 20px;border-left:2px solid var(--green);background:rgba(85,185,133,.06);color:var(--muted)}.callout strong{color:var(--text)}
    .connect{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.connect .card{min-height:245px}.status{display:inline-block;padding:5px 9px;border:1px solid rgba(243,187,103,.28);border-radius:999px;color:#f4cb8b;background:rgba(243,187,103,.07);font-size:.7rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase}.connect ol{padding-left:20px;color:var(--muted);font-size:.86rem}.connect li{margin:7px 0}
    .code{margin-top:14px;border:1px solid var(--line);border-radius:12px;background:#0b0e0c;overflow:hidden}.code b{display:block;padding:9px 13px;border-bottom:1px solid var(--line);color:#7f8982;font-size:.72rem}pre{margin:0;padding:16px;overflow:auto;color:#d9e2dc;font: .8rem/1.65 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
    table{width:100%;border-collapse:collapse;border:1px solid var(--line);border-radius:var(--r);overflow:hidden;background:var(--panel)}th,td{padding:12px 14px;border-bottom:1px solid var(--line);vertical-align:top;text-align:left}th{color:var(--green2);font-size:.75rem;text-transform:uppercase;letter-spacing:.07em}td{color:var(--muted);font-size:.86rem}td code{color:#dce7df}.examples{display:grid;gap:16px}.example{display:grid;grid-template-columns:220px 1fr;gap:18px}.example h3{margin:2px 0 5px}.example p{margin:0;color:var(--muted);font-size:.84rem}.footer{padding:30px 0 42px;border-top:1px solid var(--line);color:#7f8982;font-size:.82rem}
    @media(max-width:900px){.head,.example{grid-template-columns:1fr}.grid,.connect{grid-template-columns:1fr 1fr}}@media(max-width:620px){.shell{width:calc(100% - 28px)}nav{display:none}.grid,.connect{grid-template-columns:1fr}.hero{padding-top:58px}.live{float:none;display:block;margin-top:10px}}
  </style>
</head>
<body>
  <header class="header"><div class="shell"><a class="brand" href="/"><i></i><span>TrialAgents Intel MCP</span></a><nav><a href="#connect">Connect</a><a href="#tools">Tools</a><a href="#profiles">Profile sections</a><a href="#examples">Examples</a></nav></div></header>
  <main>
    <div class="hero shell">
      <div class="eyebrow">Clinical-trial intelligence over MCP</div>
      <h1>Approved EU trial intelligence, exposed as bounded tools.</h1>
      <p>Connect ChatGPT, Claude, or your own software to TrialAgents Intel. The service separates structured screening, semantic classification, profile review, document retrieval and typed extraction so clients can use the lightest evidence surface that answers the question.</p>
      <div class="endpoint">https://mcp.trialagents.com/mcp <span class="live">Service endpoint</span></div>
    </div>

    <section id="connect"><div class="shell">
      <div class="head"><div><div class="kicker">Connect</div><h2>Use TrialAgents OAuth from hosted clients</h2></div><p>ChatGPT and Claude authenticate with your existing Intel Agent account. Private software integrations use a TrialAgents-issued bearer credential.</p></div>
      <div class="connect">
        <article class="card"><span class="status">TrialAgents OAuth live</span><h3>ChatGPT</h3><p>Enable Developer mode, add a custom MCP connection, and use the server URL above.</p><ol><li>Open ChatGPT Settings and enable Developer mode.</li><li>Add a developer-mode MCP connection named TrialAgents Intel.</li><li>Sign in with your existing Intel Agent account and approve the scoped connection.</li></ol></article>
        <article class="card"><span class="status">TrialAgents OAuth live</span><h3>Claude</h3><p>Add TrialAgents Intel as a remote custom connector, then connect it to the conversation.</p><ol><li>Open Connectors and add a custom remote connector.</li><li>Enter the MCP URL above.</li><li>Sign in with your existing Intel Agent account and approve the scoped connection.</li></ol></article>
        <article class="card"><span class="status">Private integration beta</span><h3>Own software</h3><p>Use the standard MCP Streamable HTTP transport with a TrialAgents-issued credential. Keep the credential server-side and never expose it in a browser.</p><div class="code"><b>Python SDK</b><pre><code>python -m pip install "mcp&gt;=2,&lt;3"</code></pre></div></article>
      </div>
    </div></section>

    <section id="tools"><div class="shell">
      <div class="head"><div><div class="kicker">Tool map</div><h2>Use the lightest tool that answers the question</h2></div><p>Start with deterministic filtering. Review shortlisted profiles in batches of up to ten, using only relevant profile sections when appropriate. Use document text or typed extraction when the structured profile is insufficient.</p></div>
      <div class="grid">
        <article class="card"><code>start_analysis</code><h3>Open the analysis lease</h3><p>Turns an approved report run into the active analysis ID used by every later tool.</p><span class="limit">One active 60-minute lease</span></article>
        <article class="card"><code>filter_trials</code><h3>Build a shortlist</h3><p>Applies structured Trial Profile filters and returns only EU number, trial title and sponsor.</p><span class="limit">Up to 100 results per page</span></article>
        <article class="card"><code>classify_trials</code><h3>Classify eligibility</h3><p>Uses complete contact-redacted profiles in independent Terra worker calls and returns eligible, ineligible and uncertain trial buckets.</p><span class="limit">Up to 25 trials per call</span></article>
        <article class="card"><code>get_profiles</code><h3>Read relevant profile evidence</h3><p>Returns exact Trial Profile 10.0.0 sections when requested, or complete approved profiles when sections are omitted.</p><span class="limit">Up to 10 profiles per call</span></article>
        <article class="card"><code>get_documents</code><h3>Read one extracted document</h3><p>Uses an exact filename from <code>filtering_variables.available_extracted_documents</code> and returns bounded extracted text parts.</p><span class="limit">One document per call</span></article>
        <article class="card"><code>extract_variables</code><h3>Extract typed values</h3><p>Uses one complete profile plus its profile-listed protocol when available, returning only requested typed values.</p><span class="limit">Up to 20 variables per call</span></article>
      </div>
      <div class="callout"><strong>Profile sections are projections, not summaries.</strong> <code>get_profiles</code> copies exact stored values and original nesting from approved Trial Profile 10.0.0. No model creates a card or rewrites the profile.</div>
    </div></section>

    <section id="profiles"><div class="shell">
      <div class="head"><div><div class="kicker">get_profiles</div><h2>Choose the profile evidence needed for the task</h2></div><p>Every call accepts up to 10 trial IDs. Pass a non-empty <code>sections</code> array to return only those deterministic profile sections, or omit <code>sections</code> / pass <code>[]</code> to return complete profiles. Light can retrieve up to 100 unique profiles across the analysis.</p></div>
      <table>
        <thead><tr><th>Section</th><th>Contains</th></tr></thead>
        <tbody>
          <tr><td><code>overview</code></td><td>Trial title/acronym, disease, therapeutic area, phase, classification summary and core rare/orphan/paediatric/FIH flags.</td></tr>
          <tr><td><code>population</code></td><td>Target population, stage/severity, treatment settings, characteristics, biomarkers and eligible sexes.</td></tr>
          <tr><td><code>trial_design</code></td><td>Planned sample size, allocation, masking, intervention model and comparator types.</td></tr>
          <tr><td><code>interventions</code></td><td>Modality, administration routes, molecular targets, mechanisms and products.</td></tr>
          <tr><td><code>eligibility</code></td><td>Inclusion and exclusion criteria.</td></tr>
          <tr><td><code>objectives</code></td><td>Primary and secondary objectives.</td></tr>
          <tr><td><code>endpoints</code></td><td>Structured endpoints.</td></tr>
          <tr><td><code>sponsor_and_organizations</code></td><td>Sponsor, legal representative and third-party organizations.</td></tr>
          <tr><td><code>contacts</code></td><td>Trial management, scientific, recruitment and public CTIS contacts.</td></tr>
          <tr><td><code>countries</code></td><td>Country codes/count and structured country records.</td></tr>
          <tr><td><code>sites</code></td><td>Site count and structured site records, including nested site contacts.</td></tr>
          <tr><td><code>documents</code></td><td>The six-category <code>available_extracted_documents</code> inventory with exact document names.</td></tr>
          <tr><td><code>lifecycle</code></td><td>The complete dated <code>ctis_lifecycle</code> object.</td></tr>
          <tr><td><code>results</code></td><td>The complete results object: participant flow, country enrollment, endpoint/safety results and operational findings.</td></tr>
        </tbody>
      </table>
      <div class="callout"><strong>Simple contract:</strong> the only new input is optional <code>sections</code>. The output fields are unchanged. Light analyses may retrieve up to 100 unique profiles; Max analyses up to 500. Re-reading the same trial with different sections or later as a complete profile does not consume the profile allowance twice.</div>
    </div></section>

    <section id="examples"><div class="shell">
      <div class="head"><div><div class="kicker">Copyable calls</div><h2>Profile retrieval examples</h2></div><p>These are MCP tool arguments. Use the same <code>analysis_id</code> returned by <code>start_analysis</code>.</p></div>
      <div class="examples">
        <div class="example"><div><h3>Review selected profile sections</h3><p>Request only the exact profile sections relevant to the decision, in batches of up to ten trials.</p></div><div class="code"><b>get_profiles · sections</b><pre><code>{
  "analysis_id": "ana_...",
  "trial_ids": [
    "2024-500001-00-00",
    "2024-500002-00-00"
  ],
  "sections": [
    "overview",
    "trial_design",
    "endpoints",
    "countries"
  ]
}</code></pre></div></div>
        <div class="example"><div><h3>Read complete profiles</h3><p>Omit sections when the whole profile is needed. The same 10-profile per-call cap applies.</p></div><div class="code"><b>get_profiles · complete profile</b><pre><code>{
  "analysis_id": "ana_...",
  "trial_ids": ["2024-500001-00-00"]
}</code></pre></div></div>
        <div class="example"><div><h3>Find a document name</h3><p>The documents section is enough when the next step is document retrieval.</p></div><div class="code"><b>get_profiles · documents only</b><pre><code>{
  "analysis_id": "ana_...",
  "trial_ids": ["2024-500001-00-00"],
  "sections": ["documents"]
}</code></pre></div></div>
      </div>
    </div></section>
  </main>
  <footer class="footer"><div class="shell">TrialAgents Intel MCP · Approved-only Trial Profile reads · OAuth protected resource</div></footer>
</body>
</html>"""