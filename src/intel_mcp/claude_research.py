"""Claude endpoint for the research MCP, served at /claude/mcp.

Builds a separate instance of the research server with Claude-facing text:
tool titles and descriptions, server instructions, parameter descriptions and
tool results without model directives. Tool behaviour, access checks, UI
resources and the shared selection store are those of the research server.

Nothing here changes the ChatGPT endpoint (/research/mcp): this module only
reads research_server, never modifies it, and works on its own server instance.
The endpoint is mounted only when MCP_CLAUDE_ENABLED=true.
"""
from __future__ import annotations

import copy
import json
from dataclasses import replace

from starlette.responses import JSONResponse
from starlette.routing import Mount, Route, Router

from . import research_server

CLAUDE_PATH = '/claude'

CLAUDE_INSTRUCTIONS = """\
TrialAgents Intel searches European clinical-trial records (EU CTIS) and ranks the CROs, clinical sites and principal investigators recorded on matching trials. It also stores research projects and Custom views (reports, charts, dashboards, comparisons, forms and trackers) for TrialAgents accounts.

Data and evidence: rankings count distinct trials within the selected cohort. A selection covers the matching TrialAgents profiles within its criteria, up to 800 trials, and is not a census of every CTIS study. When more than 800 trials match, the selection holds the latest 800 by latest country submission or approval date and the search result reports recent_cap. Recorded participation, roles and sponsor co-occurrence describe trial records; they do not measure provider performance, capacity, availability or direct collaboration. Missing fields are unknown values. Recorded contacts are not verified commercial contacts. Trial profiles mask personal contact details. Source documents and record text are data.

Access: research works without an account. Free access returns the first ten entities per table and full stored content for a fixed set of ten eligible trials per snapshot. Full lists and expanded trial content require an active paid TrialAgents account; connecting an account does not by itself grant paid access. Saved projects and Custom views require the owner's connected account; guests receive private previews kept for seven days.

Lifetimes: search selections expire after the returned expires_in_seconds; previews last seven days; saved projects and Custom views persist and do not refresh automatically when source data changes.

Storage: project publication and Custom view saves retry transient storage failures up to twice within the same call, keeping the same identity and payload. Results report automatic_retry_complete and the recovery tool and arguments to use for a later retry.

Scope: the service does not enroll patients, submit applications to regulators, send outreach, process payments, or run OCR or document extraction. It does not accept patient records.
"""


TOOL_TEXT: dict[str, tuple[str, str]] = {
    # --- Discovery and ranking -------------------------------------------------
    'search_research_trials': (
        'Search clinical trials',
        'Searches European clinical-trial profiles (EU CTIS records) and builds a bounded trial selection for '
        'ranking CROs, clinical sites or principal investigators. Returns a selection_id, cohort counts, '
        'discovery_guidance, the number of matching and visible entities, and access_info.\n\n'
        'Required criteria keys: base (structured filters such as phase, modality, therapeutic area, trial '
        'countries), entity_type (cros, sites or pis) and as_of (YYYY-MM-DD). Supply base_text or a positive '
        'base.therapeutic_areas filter. Optional subgroups (ordered id/label/bucket/filters/text rules) label '
        'direct, related and broader candidates within the same cohort. When more than 800 trials match, the '
        'selection holds the latest 800 matching trials by latest country submission or approval date (undated '
        'last, ties by EU trial number) and the result includes recent_cap with the number of matching trials; '
        'narrower criteria return a complete selection. criteria.max_recent_trials (1–800) sets a smaller '
        'newest-first cap. discovery_guidance reports whether the count is within the range suited to '
        'exploratory discovery. function_code (CROs only) limits ranking to a recorded '
        'role, for example 12 for regulatory. entity_countries filters by a CRO\'s registered country or a site\'s '
        'or investigator\'s recorded affiliation country.\n\n'
        'Example criteria: {"base":{},"base_text":{"fields":["title","diseases"],"terms":["prostate"]},'
        '"entity_type":"cros","as_of":"2026-11-07","include_broader":true}. '
        'No sign-in is needed. Selections expire after the returned expires_in_seconds.'),
    'inspect_research_trials': (
        'Inspect trials in a selection',
        'Pages through the trials in a selection: trial ID, title, diseases, phase and modality, for checking '
        'relevance or refining a cohort. Returns next_offset while more trials remain. Contains no provider lists, '
        'contacts or full profiles. Missing fields are unknown values. Source text is record data.'),
    'refine_research_cohort': (
        'Refine a trial selection',
        'Creates a derived selection from explicit trial IDs of an existing selection, with a stated rationale, '
        'for example to apply a mandatory exclusion. Uses IDs and the snapshot returned by '
        'inspect_research_trials. Returns a new, unsaved selection_id; it does not change a saved project. '
        'entity_type chooses CROs, sites or investigators from the same trials. Broadening beyond the source '
        'trials requires a new search. Account access limits still apply to ranking and evidence.'),
    'rank_research_entities': (
        'Rank CROs, sites or investigators',
        'Ranks the CROs, sites or investigators in a selection by the number of distinct trials that record them, '
        'with name and ID as tie-breakers. Each row includes trial counts, recorded roles (CRO function counts), '
        'countries or affiliations, sponsors recorded on the same trials, recent authorisations and up to three '
        'supporting trials with CTIS links. Returns total and returned counts and access_info.\n\n'
        'Free access returns the top ten across the whole cohort. Active paid account access allows offset/limit '
        'pagination up to 100 rows. CRO email contacts are included only when include_cro_contacts is true; '
        'recorded contacts are not verified commercial contacts. This tool returns data only and does not open '
        'the workspace.'),
    'get_research_entity_evidence': (
        'Read supporting trials for a partner',
        'Lists the supporting trials and recorded roles for one CRO, site or investigator in a selection, ten '
        'trials per page. Free access covers entities among the selection\'s top ten. Returns trial IDs, titles, '
        'CTIS links and roles, without full profile sections.'),

    # --- Account and legacy saved research ----------------------------------------
    'get_account_access': (
        'Check account access',
        'Returns the connected TrialAgents account\'s access level and research capabilities, or connection '
        'guidance when no account is connected. Does not list projects, change subscriptions or start purchases. '
        'Research without an account remains available.'),
    'save_research_project': (
        'Save research project (legacy)',
        'Saves up to three computed selections as a private TrialAgents project and returns its link. Reuses the '
        'computed snapshots; starts no analysis, payment, email or public sharing. Repeat saves of the same '
        'snapshots return the same project. Used by the workspace; requires a connected account.'),
    'get_saved_research_project': (
        'Read saved research project (legacy)',
        'Reads a private project saved with save_research_project under current account access, without new '
        'analysis. Free accounts read the top ten; paid accounts can page the full list. Ownership and access are '
        'rechecked on every read.'),

    # --- Workspace: previews and projects ---------------------------------------
    'prepare_research_workspace': (
        'Preview research workspace',
        'Displays the interactive TrialAgents workspace (Sites, PIs, CROs and Trials tables) for an existing '
        'selection without saving an account project. Writes a private preview to temporary storage for 7 days. '
        'Each call without preview_id creates a separate preview; passing preview_id with an updated selection, '
        'title or recommendations revises that preview. Returns only the requested table kind; other tabs load '
        'on request. Contact details are included only on explicit request. Account access controls pagination '
        'and evidence. A preview is not a saved project; save_project or the workspace Connect control saves it.'),
    'publish_research_workspace': (
        'Publish research workspace',
        'Stores final research and displays it in the interactive workspace. Without an account, it stores a '
        'private seven-day preview; with a connected account, it saves a project in that account. Repeating the '
        'same selection and inputs for a connected account returns the same project; anonymous calls create a '
        'separate preview each time. Transient storage failures are retried up to twice inside the call; '
        'automatic_retry_complete=true reports that those retries ran. Recovery after a failure uses save_project '
        '(connected) or recover_research_preview (guest) with the returned draft. operation_id distinguishes an '
        'intentionally separate project created from the same selection; it is not an access token. Custom views '
        'are stored separately with save_project_custom_view.'),
    'recover_research_preview': (
        'Recover preview storage',
        'Retries temporary storage of a preview whose storage failed, keeping its identity and selection. Does not '
        'save an account project or repeat research.'),
    'read_project_preview': (
        'Read preview table',
        'Reads one table of an existing preview without opening or changing the workspace. Paid accounts may '
        'choose limit 1–100 and follow next_offset; free accounts receive the first ten results.'),
    'list_projects': (
        'List saved projects',
        'Lists the connected account\'s saved research projects, including projects created on the TrialAgents '
        'website or other assistants.'),
    'save_project': (
        'Save project',
        'Stores a research preview in the connected owner\'s account project, synchronised with the TrialAgents '
        'website, without rerunning research. project_id with expected_revision updates an existing project; '
        'omitting both creates or attaches the preview\'s project. A stale revision is rejected. Returns the '
        'verified saved state. Transient storage failures are retried up to twice inside the call.'),
    'read_project': (
        'Read project table',
        'Reads one table of the latest saved project without opening or changing the workspace. Paid accounts may '
        'choose limit 1–100 and follow next_offset; free accounts receive the first ten results. Omitting kind '
        'reads the most recently active table. Omitting controls applies the owner\'s saved filters and ranking; '
        'supplying controls (including {} for none) applies a temporary read-only override. Returns the applied '
        'view controls and version and access-limited counts. Does not create projects, repeat searches or '
        'prepare reports.'),
    'open_project': (
        'Open project in workspace',
        'Displays a saved project table in the interactive workspace, ten rows per page. Omitting kind and '
        'controls shows the latest saved view. read_project reads the same data without displaying it.'),
    'save_project_view': (
        'Save table view',
        'Saves table filters and ranking as the connected user\'s view of a project. Changes only the view, never '
        'the dataset or cohort. Requires the view version and project revision returned by open_project; an empty '
        'controls object resets the view. A version conflict is rejected without overwriting.'),
    'read_workspace_trial': (
        'Read trial for workspace',
        'Reads an authorised frozen trial profile for the workspace\'s trial detail dialog. Called by the '
        'workspace interface.'),
    'get_research_workspace': (
        'Read saved workspace table',
        'Opens or pages a saved project table, or reads a previous revision, under current access. Applies to '
        'saved projects only; unsaved previews are read with read_project_preview. Free access returns ten rows '
        'per table; active paid access allows later pages.'),
    'open_research_workspace': (
        'Reopen workspace preview',
        'Displays an existing workspace preview again without changing saved data.'),
    'revise_research_workspace': (
        'Revise project cohort',
        'Saves a new revision of the same project after a cohort or priority change, keeping the project ID. '
        'expected_revision prevents overwriting intervening changes; a conflict is rejected. recommendations '
        'replace the revision\'s recommendation list; [] clears it. Called by the workspace interface.'),
    'create_research_account_handoff': (
        'Connect account via website',
        'Saves a preview and returns a private, short-lived link that opens TrialAgents sign-in or sign-up to '
        'attach the exact preview to the chosen account, without rerunning research. Called by the workspace '
        'Connect control when in-host authorisation is unavailable. Starts no purchase. The link carries a '
        'one-time capability for saving this project.'),
    'claim_research_workspace': (
        'Claim preview for account',
        'Saves a preview to the connected account. Requires the preview owner\'s authorisation; repeated claims '
        'by the owner keep the same research. After claiming, the anonymous preview capability stops working. '
        'Connecting an account does not activate paid access. Starts no payment.'),

    # --- Follow-ups, profiles and documents -------------------------------------
    'show_research_followups': (
        'Suggest follow-up analyses',
        'Displays one to three optional next-analysis questions supported by the current dataset. Each button '
        'sends its question as a message when the user clicks it. Reads the current scope only; performs no '
        'analysis and does not expand access.'),
    'describe_trial_profile_schema': (
        'Describe trial profile fields',
        'Returns the trial profile schema: the 14 section names, field types, meanings and nesting used by '
        'read_trial_profiles.'),
    'read_trial_profiles': (
        'Read trial profiles',
        'Reads complete frozen trial profiles, or selected sections, for up to ten trials. Sections: overview, '
        'population, trial_design, interventions, eligibility, objectives, endpoints, sponsor_and_organizations, '
        'contacts, countries, sites, documents, lifecycle, results. Personal contacts are masked; sites and '
        'document names remain. Large profiles return profile_json_part with next_part; the parts concatenate '
        'into one JSON document. Free access covers the selection\'s fixed set of ten eligible trials; paid '
        'access covers all authorised trials. Each read registers a frozen evidence record for later report '
        'provenance (an additive write; the trial catalogue is unchanged).'),
    'list_trial_documents': (
        'List trial documents',
        'Lists the extracted documents available for an eligible trial, such as protocols, recruitment '
        'arrangements, patient information and consent forms, assessments, clinical study reports and results '
        'summaries. This is the extracted-text inventory, not every file held in CTIS.'),
    'read_trial_document': (
        'Read trial document',
        'Reads the extracted text of one document of an eligible trial, including protocols, in parts with page '
        'markers; next_part is null on the last part. Exact names come from list_trial_documents. Missing or '
        'unextracted documents are unavailable; no OCR or new extraction runs. Each read stores a dated evidence '
        'record with a report-compatible source ID (an additive write).'),

    # --- Custom views ---------------------------------------------------------------
    'prepare_project_custom_view': (
        'Prepare custom view context',
        'Returns the dataset ID, revision, authorised evidence scope and eligible trial IDs needed to build a '
        'Custom view (report, chart, dashboard, comparison, form or tracker). include_template adds the rendering '
        'contract, a static HTML shell and styled examples. Neither generates nor saves a view.'),
    'read_custom_view_evidence': (
        'Read evidence for a custom view',
        'Reads up to five complete authorised frozen trial profiles with the source IDs that '
        'save_project_custom_view accepts as evidence. Trial IDs come from the project\'s Trials table. Free '
        'access covers the fixed set of ten eligible trials. Registers frozen evidence records for provenance '
        '(an additive write).'),
    'read_custom_view_document': (
        'Read document for a custom view',
        'Reads one part of an extracted document of an eligible trial, such as a protocol, using an exact name '
        'from the profile\'s available documents. Stores the text as a dated source record usable as Custom view '
        'evidence; repeated reads may add another record. No arbitrary URLs, extraction or OCR.'),
    'save_project_custom_view': (
        'Save custom view',
        'Creates or updates a Custom view (report, chart, comparison cards, table, form, tracker or calculator) '
        'from self-contained HTML and displays it in the workspace Custom tab. Stores to temporary preview storage '
        'for guests or to the account for connected owners. custom_view_id with expected_version updates an '
        'existing view with a concurrency check. request_key makes the write idempotent; changed content needs a '
        'new key. dataset_id and revision come from prepare_project_custom_view. trial_evidence views require '
        'registered source_ids; project_tables and user_provided views accept an empty list. Interactive HTML '
        'runs in an isolated renderer without network or account access; custom CSS requires '
        'renderer=interactive, and static mode accepts only the semantic HTML/SVG shell. custom_view_saved=true '
        'confirms the stored view was read back; failures return save_status, save_error and a retry_id. '
        'Transient storage failures are retried up to twice inside the call. Returned custom_url (also url) is '
        'the view\'s website link.'),
    'retry_project_custom_view': (
        'Retry custom view save',
        'Retries a failed Custom view save using the retained visualization and its original idempotency key. '
        'Rechecks account and evidence access; a conflict returns current context. Does not repeat research, '
        'regenerate HTML or create a copy. Retained for up to 30 minutes in this server session.'),
    'offer_visualization_save': (
        'Offer to save a visualization',
        'Displays a Save to TrialAgents button for a candidate Custom view. The button sends a save request only '
        'when the user clicks it; this tool does not store anything.'),
    'save_visualization_state': (
        'Save form or tracker state',
        'Stores versioned state entered in a saved form or tracker through the workspace Save changes control.'),
    'list_project_custom_views': (
        'List custom views',
        'Lists the saved Custom views of a project or preview, without generating analysis.'),
    'read_project_custom_view': (
        'Read custom view',
        'Reads an authorised saved Custom view for the workspace, without rebuilding tables.'),
    'open_project_custom_view': (
        'Open custom view',
        'Displays an existing Custom view and its original question in the workspace Custom tab. Returned '
        'custom_url (also url) is the view\'s website link.'),
}


# Exact parameter-description texts of the shared research tools and their
# Claude wording. Replaced only in this instance's own copies of the schemas.
PARAMETER_TEXT: dict[str, str] = {
    "Required: base (hard structured filters), entity_type (cros/sites/pis), as_of (today YYYY-MM-DD). "
    "Also supply base_text or positive base.therapeutic_areas. For exploratory discovery use a broad "
    "disease-family base, named subgroups for population/phase, and include_broader=true. "
    "Preserve explicit mandatory constraints in base.":
        "Required: base (hard structured filters), entity_type (cros/sites/pis), as_of (YYYY-MM-DD). "
        "base_text or a positive base.therapeutic_areas filter is also required. Filters in base are hard "
        "constraints; subgroups label direct, related and broader candidates within the cohort; "
        "include_broader keeps unmatched trials in the cohort as broader.",
    "True only for the final requested entity category; optionally show known dataset-supported next actions when useful.":
        "True displays dataset-supported follow-up questions with the ranking.",
    "Show access notice once, in the final requested category chart.":
        "True includes the access notice in the ranking view.",
    "Set true only when the user explicitly requests CRO/provider contacts. Source contacts are not verified commercial contacts.":
        "True includes recorded CRO/provider email contacts. Recorded contacts are not verified commercial contacts.",
    "True only when CRO emails were explicitly requested for the saved project.":
        "True keeps recorded CRO email contacts in the saved project.",
    "True only for an explicit request to show professional contact details.":
        "True includes professional contact details, which are masked by default.",
}

# Directive strings that the shared tools place in results, with their
# descriptive Claude replacement. None removes the field.
RESULT_TEXT: dict[str, str | None] = {
    'Complete relevant broadening first. Present ONLY the final broadest relevant cohort in one workspace; no separate subgroup lists or Markdown tables.': None,
    'Use the final broadest relevant cohort only. Open its workspace; keep chat to summary and insights, without duplicate tables. Supporting-trial lists require an explicit user request, including after workspace failure.': None,
    'Use evidence internally for concise insights. Do not output supporting-trial lists unless explicitly requested, even after workspace failure.': None,
    'The workspace holds the result tables. Keep chat to concise summary and insights. Supporting-trial lists require an explicit user request.': None,
    'After broadening finishes, use only the final broadest relevant selection_id with publish_research_workspace. Do not rank or display intermediate cohorts.': None,
    'Call prepare_research_workspace for a new final cohort, then save_project with project_id and expected_revision when committing a saved-project refinement. Do not output an additional cohort list.':
        'Unsaved derived selection. prepare_research_workspace displays it; save_project with project_id and expected_revision commits it to an existing saved project.',
    'For initial exploratory discovery, broaden through a relevant therapeutic area, phase or modality before finalizing; retain requested population/phase as named subgroups. Preserve explicit mandatory constraints. If no relevant broadening is possible, report the actual count and why.':
        'Fewer than 30 trials matched. A broader therapeutic area, phase or modality, with the requested population or phase as named subgroups, usually returns a larger cohort; explicit mandatory constraints in the request may justify a smaller one.',
    'Discovery is ready. Call publish_research_workspace once with this final broadest relevant selection_id. Return one top-ten list per requested category in the workspace, not separate cohort lists or chat tables.':
        'The selection is within the exploratory range and can be published with publish_research_workspace.',
    'Show these optional dataset-supported questions only when useful; if the card renders, do not duplicate them in prose. Suggestions do not grant access or imply the analysis was performed.':
        'Optional dataset-supported questions. Suggestions do not grant access and do not indicate that the analysis was performed.',
    'Save private research projects and reopen them in ChatGPT or TrialAgents Intel without new analysis':
        'Save private research projects and reopen them in Claude or on the TrialAgents website without new analysis',
}
_REMOVED = object()


def _claude_value(value):
    if isinstance(value, str):
        replaced = RESULT_TEXT.get(value, value)
        return _REMOVED if replaced is None else replaced
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            item = _claude_value(item)
            if item is not _REMOVED:
                out[key] = item
        return out
    if isinstance(value, list):
        return [item for item in map(_claude_value, value) if item is not _REMOVED]
    return value


async def claude_results(ctx, call_next):
    """Replace model directives in this instance's tool results with descriptive text."""
    result = await call_next(ctx)
    if ctx.method != 'tools/call' or not isinstance(result, dict):
        return result
    out = dict(result)
    if isinstance(out.get('structuredContent'), dict):
        out['structuredContent'] = _claude_value(out['structuredContent'])
    if isinstance(out.get('content'), list):
        content = []
        for block in out['content']:
            if isinstance(block, dict) and block.get('type') == 'text':
                try:
                    parsed = json.loads(block['text'])
                except (ValueError, TypeError, KeyError):
                    parsed = None
                if isinstance(parsed, dict):
                    block = {**block, 'text': json.dumps(_claude_value(parsed), ensure_ascii=False)}
            content.append(block)
        out['content'] = content
    return out


# Newest-first cap for Claude searches. The shared selection limit stays 1,000
# and max_recent_trials stays optional, so the ChatGPT endpoint keeps rejecting
# over-limit searches; only this instance reruns them with the cap.
RECENT_CAP = 800
_TOO_LARGE = 'COHORT_TOO_LARGE'


def _search_matches(result):
    """Matching-trial count above RECENT_CAP, 'more_than_1000', or None when within the cap."""
    if not isinstance(result, dict):
        return None
    if result.get('isError'):
        texts = [b.get('text', '') for b in result.get('content') or [] if isinstance(b, dict)]
        return 'more_than_1000' if any(_TOO_LARGE in str(t) for t in texts) else None
    structured = result.get('structuredContent')
    try:
        count = structured['cohort']['counts']['base']
    except (KeyError, TypeError):
        return None
    return count if isinstance(count, int) and count > RECENT_CAP else None


def _recent_cap(matches):
    label = 'more than 1,000' if matches == 'more_than_1000' else f'{matches:,}'
    return {
        'applied': True,
        'max_recent_trials': RECENT_CAP,
        'matching_trials': None if matches == 'more_than_1000' else matches,
        'matching_trials_label': label,
        'description': (f'{label[0].upper()}{label[1:]} trials matched the criteria. This selection holds the '
                        f'latest {RECENT_CAP} by latest country submission or approval date (undated last, ties '
                        'by EU trial number); older matching trials are excluded. Narrower criteria return a '
                        'complete selection.'),
    }


def _with_recent_cap(result, cap):
    out = dict(result)
    if isinstance(out.get('structuredContent'), dict):
        out['structuredContent'] = {**out['structuredContent'], 'recent_cap': cap}
    if isinstance(out.get('content'), list):
        content = []
        for block in out['content']:
            if isinstance(block, dict) and block.get('type') == 'text':
                try:
                    parsed = json.loads(block['text'])
                except (ValueError, TypeError, KeyError):
                    parsed = None
                if isinstance(parsed, dict):
                    block = {**block, 'text': json.dumps({**parsed, 'recent_cap': cap}, ensure_ascii=False)}
            content.append(block)
        out['content'] = content
    return out


async def claude_recent_cap(ctx, call_next):
    """Rerun a Claude search that matches more than RECENT_CAP trials with the newest-first cap.

    A search that already sets max_recent_trials, or matches RECENT_CAP trials or
    fewer, is returned unchanged. The rerun adds only max_recent_trials to the
    same criteria, so selection, snapshot and limitations come from the shared engine.
    """
    params = ctx.params if isinstance(ctx.params, dict) else None
    if ctx.method != 'tools/call' or not params or params.get('name') != 'search_research_trials':
        return await call_next(ctx)
    args = params.get('arguments')
    criteria = args.get('criteria') if isinstance(args, dict) else None
    if not isinstance(criteria, dict) or criteria.get('max_recent_trials') is not None:
        return await call_next(ctx)
    result = await call_next(ctx)
    matches = _search_matches(result)
    if matches is None:
        return result
    capped_params = {**params, 'arguments': {**args, 'criteria': {**criteria, 'max_recent_trials': RECENT_CAP}}}
    capped = await call_next(replace(ctx, params=capped_params))
    if not isinstance(capped, dict) or capped.get('isError'):
        return capped
    return _with_recent_cap(capped, _recent_cap(matches))


def _without_ui_domain(meta):
    """Drop the ChatGPT-format ui.domain: Claude validates the field and shows an error instead of the app."""
    if not isinstance(meta, dict) or not isinstance(meta.get('ui'), dict) or 'domain' not in meta['ui']:
        return meta
    return {**meta, 'ui': {k: v for k, v in meta['ui'].items() if k != 'domain'}}


async def claude_ui_resources(ctx, call_next):
    """Serve this instance's UI resources without ui.domain, so Claude uses its default app sandbox."""
    result = await call_next(ctx)
    key = {'resources/list': 'resources', 'resources/read': 'contents',
           'resources/templates/list': 'resourceTemplates'}.get(ctx.method)
    if key is None or not isinstance(result, dict) or not isinstance(result.get(key), list):
        return result
    items = [{**item, '_meta': _without_ui_domain(item['_meta'])} if isinstance(item, dict) and '_meta' in item
             else item for item in result[key]]
    return {**result, key: items}


def _claude_schema(value):
    if isinstance(value, dict):
        return {key: (PARAMETER_TEXT.get(item, item) if key == 'description' and isinstance(item, str)
                      else _claude_schema(item)) for key, item in value.items()}
    if isinstance(value, list):
        return [_claude_schema(item) for item in value]
    return value


def apply_claude_text(server) -> None:
    """Give this instance's tools Claude titles, descriptions and parameter text.

    Fails at startup if a tool has no reviewed entry, so a new research tool
    cannot reach Claude without Claude-facing text.
    """
    manager = server._tool_manager
    names = {tool.name for tool in manager.list_tools()}
    missing = sorted(names - TOOL_TEXT.keys())
    if missing:
        raise RuntimeError(f'Claude endpoint has no title/description for tools: {", ".join(missing)}')
    for name in names:
        tool = manager.get_tool(name)
        tool.title, tool.description = TOOL_TEXT[name]
        tool.parameters = _claude_schema(copy.deepcopy(tool.parameters))
    server._lowlevel_server.instructions = CLAUDE_INSTRUCTIONS
    server._lowlevel_server.middleware.extend((claude_ui_resources, claude_recent_cap, claude_results))


def create_claude_research_server(settings, engine_factory, control_factory, store):
    """Build the Claude instance on the research server's shared selection store."""
    original_store = research_server.ResearchStore
    research_server.ResearchStore = lambda _engine_factory: store
    try:
        server, auth, _store, _resource, _challenge = research_server.create_research_server(
            settings, engine_factory, control_factory)
    finally:
        research_server.ResearchStore = original_store
    apply_claude_text(server)
    origin = settings.mcp_public_resource_url.removesuffix('/mcp')
    resource = origin + CLAUDE_PATH + '/mcp'
    metadata_url = origin + CLAUDE_PATH + '/.well-known/oauth-protected-resource'
    challenge = f'Bearer resource_metadata="{metadata_url}", scope="mcp:tools"'
    return server, auth, resource, challenge


def claude_routes(settings, engine_factory, control_factory, store, transport_security):
    """Routes and lifespan app for /claude; added to the main app only when enabled."""
    server, auth, resource, challenge = create_claude_research_server(
        settings, engine_factory, control_factory, store)
    http = server.streamable_http_app(stateless_http=True, transport_security=transport_security)
    issuer = settings.oauth_authorization_server_url.rstrip('/') + '/oauth/intel'

    async def metadata(_request):
        return JSONResponse({
            'resource': resource,
            'authorization_servers': [issuer],
            'scopes_supported': ['mcp:tools'],
            'bearer_methods_supported': ['header'],
        }, headers={'Cache-Control': 'no-store'})

    routes = [
        Route(f'/.well-known/oauth-protected-resource{CLAUDE_PATH}/mcp', metadata, methods=['GET']),
        Mount(CLAUDE_PATH, app=Router(routes=[
            Route('/.well-known/oauth-protected-resource', metadata, methods=['GET']),
            Mount('/', app=auth(http, control_factory, resource, challenge)),
        ])),
    ]
    return routes, http
