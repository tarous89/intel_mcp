"""One persisted cohort for the shared TrialAgents Intel workspace; no model jobs."""
from copy import deepcopy
import asyncio
import time
import secrets
import gzip
import logging
import hashlib
import hmac
import json
import base64
from uuid import uuid4, uuid5, NAMESPACE_URL
from importlib.resources import files
from typing import Annotated, Any, Literal
from pydantic import Field
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from .auth_context import current_oauth_subject
from .selection import Contract, SelectionCriteria, SelectionDataset, SelectionError
from .research_cohort import candidate_trials
from .research_presentation import public_cohort
from .control_plane import ControlPlaneError
from .prepared_selection import prepare_selection
from .memory_work import json_digest, workspace_gate, run_cpu

# A bundle change must change the resource identity: hosts can cache UI by URI.
WORKSPACE_HTML=files('intel_mcp').joinpath('ui/workspace-v1.html').read_text()
RESOURCE='ui://trialagents/workspace-'+hashlib.sha256(WORKSPACE_HTML.encode()).hexdigest()[:16]
LEGACY_RESOURCE='ui://trialagents/workspace-v1'
# Retain published host snapshots when the current bundle identity changes.
COMPATIBILITY_RESOURCES=('ui://trialagents/workspace-263a005fe3972424','ui://trialagents/workspace-c874f734c130ebdb','ui://trialagents/workspace-17ca07c3bf878f04','ui://trialagents/workspace-db4093082aae2be8')
Kind=Literal['cros','sites','pis','trials']
SHARED_EVIDENCE_FIELDS=('discovery_evidence','operational_findings')

def compact_workspace_evidence(sections):
    """Store trial-level narratives once, retaining every entity/trial association."""
    shared={}
    for section in sections:
        for entity in section['result']['entities']:
            for evidence in entity.get('evidence',[]):
                common={key:evidence[key] for key in SHARED_EVIDENCE_FIELDS if key in evidence}
                if not common:
                    continue
                tid=evidence['trial_id']
                if tid in shared and shared[tid]!=common:
                    raise SelectionError('INCONSISTENT_TRIAL_EVIDENCE')
                shared[tid]=common
                for key in common:
                    del evidence[key]
    return shared

class Recommendation(Contract):
    entity_type: Literal['cros','sites','pis']
    entity_id: Annotated[str,Field(pattern=r'^[a-f0-9]{24}$')]
    rationale: Annotated[str,Field(min_length=1,max_length=2000)]
    trial_ids: Annotated[list[str],Field(min_length=1,max_length=20)]


class PreviewSpec(Contract):
    preview_id: Annotated[str, Field(pattern=r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$')]
    selection_id: Annotated[str, Field(min_length=40, max_length=64)]
    title: Annotated[str, Field(min_length=1, max_length=160)]
    include_cro_contacts: bool = False
    recommendations: Annotated[list[Recommendation], Field(max_length=30)] = []
    snapshot_key: Annotated[str, Field(pattern=r'^[a-f0-9]{64}$')]
    cache_token: Annotated[str, Field(pattern=r'^[A-Za-z0-9_-]{43}$')]|None = None


def payload_key(payload):
    return json_digest(payload, sort_keys=True, separators=(',', ':'))


def preview_page(payload, kind, offset, full):
    if not full and offset:
        raise SelectionError('PAID_ACCOUNT_REQUIRED')
    section = next(s for s in payload['sections'] if s['entity_type'] == kind)
    result = {**section['result'], 'entities': deepcopy(section['result']['entities'][offset:offset+10])}
    for entity in result['entities']:
        for evidence in entity.get('evidence', []):
            if full:
                evidence.update(deepcopy(payload['shared_evidence'].get(evidence['trial_id'], {})))
            else:
                evidence.pop('discovery_evidence', None)
                evidence.pop('operational_findings', None)
    result['returned'] = len(result['entities'])
    result['access'] = 'full' if full else 'top_ten'
    more = offset + result['returned'] < result['total_entities']
    result['access_info'] = {'mode': result['access'], 'total_matching': result['total_entities'],
        'returned': result['returned'], 'offset': offset, 'has_more': more,
        'message': 'Your account includes full-list access.' if full else 'Free research includes ten results per category.'}
    result['next_offset'] = offset + result['returned'] if full and more else None
    return result


def workspace_payload(dataset,title,include_cro_contacts=False,recommendations=()):
    sections=[]
    for kind in ('cros','sites','pis'):
        criteria=dataset.criteria.model_dump(mode='json')
        criteria['entity_type']=kind
        if kind!='cros':criteria['function_code']=None
        child=SelectionDataset(SelectionCriteria.model_validate(criteria),list(dataset.records.values()))
        result=child.rank(limit=50000,full_cohort=True).model_dump(mode='json')
        if result['returned']!=result['total_entities']:raise SelectionError('SNAPSHOT_TOO_LARGE')
        origin=getattr(dataset,'selection_origin',None)
        result['cohort']=public_cohort(result['cohort'],origin)
        result['entity_type']=kind
        memberships=child._entities_for_selection(None,True)
        for entity in result['entities']:
            entity['subgroup_tags']=sorted({g.id for tid in memberships[entity['id']]['trials'] for g,match in zip(child.criteria.subgroups,child.records[tid].get('subgroup_matches',[])) if match})
        if origin:result['selection_origin']=origin
        if kind=='cros' and not include_cro_contacts:
            for e in result['entities']:e['contacts']=[c for c in e['contacts'] if 'email' not in c]
        sections.append({'entity_type':kind,'snapshot':child.snapshot,'trial_ids':sorted(dataset.records),'result':result})
    # Membership indexes are no longer needed during rich-row enrichment.
    del child, memberships
    trials=[]
    for offset in range(0,len(dataset.records),100):
        trials.extend({'id':t['trial_id'],**t} for t in candidate_trials(dataset,offset=offset,limit=100)['trials'])
    cohort=public_cohort(dataset.summary().model_dump(mode='json'),getattr(dataset,'selection_origin',None))
    result={'entity_type':'trials','entities':trials,'total_entities':len(trials),'returned':len(trials),'cohort':cohort}
    if hasattr(dataset,'selection_origin'):result['selection_origin']=dataset.selection_origin
    sections.append({'entity_type':'trials','snapshot':dataset.snapshot,'trial_ids':sorted(dataset.records),'result':result})
    shared=compact_workspace_evidence(sections)
    from .workspace_enrichment import enrich
    return enrich({'title':title,'sections':sections,'shared_evidence':shared,
            'recommendations':[r.model_dump(mode='json') for r in recommendations]},
            [dict(trial_id=tid,**{k:v for k,v in r.items() if k!='trial_id'}) for tid,r in dataset.records.items()],dataset.criteria.model_dump(mode='json'), in_place=True)


def with_workspace_destinations(result):
    if not isinstance(result, dict) or not result.get('result'):
        return result
    return {**result, 'workspace_destinations': {
        'tables': {'tabs': ['sites', 'pis', 'cros', 'trials'], 'uses': ['new searches', 'query revisions', 'ranking', 'sorting', 'filtering', 'paging', 'record details']},
        'custom': {'label': 'Custom views', 'uses': ['visual analyses', 'alternative presentations', 'comparisons', 'charts', 'forms', 'trackers', 'reusable coded outputs'], 'save_tool': 'save_project_custom_view', 'open_tool': 'open_project_custom_view'},
        'chat': {'uses': ['ordinary explanations']},
    }}

def register_workspace_tools(server,store,control_factory,mixed,oauth,read_annotations,connect_result):
    write=ToolAnnotations(read_only_hint=False,destructive_hint=False,idempotent_hint=True,open_world_hint=False)
    overwrite=ToolAnnotations(read_only_hint=False,destructive_hint=True,idempotent_hint=True,open_world_hint=False)
    app_callable={'ui':{'visibility':['model','app']},'openai/widgetAccessible':True}
    ui={**app_callable,'ui':{**app_callable['ui'],'resourceUri':RESOURCE}}
    pending_previews = {}
    # Process-local, like the selection store. Publicly shared search tokens and
    # account IDs alone must never let someone derive a private preview capability.
    preview_token_key = secrets.token_bytes(32)

    async def persist_preview(spec, payload=None):
        if payload is None:
            payload = await run_cpu(preview_payload, spec)
        dataset = store.get(spec.selection_id)
        control = control_factory()
        stream = getattr(control, 'stream_research_preview', None)
        legacy = getattr(control, 'cache_research_preview', None)
        if not stream and not legacy:
            return False
        spec.cache_token = spec.cache_token or secrets.token_urlsafe(32)
        prepared = await run_cpu(prepare_selection, dataset)
        if stream:
            await stream(spec.cache_token, spec.snapshot_key, payload, prepared)
        else:
            frozen = {**payload, 'prepared_selection': prepared}
            compressed = base64.b64encode(gzip.compress(json.dumps(frozen, separators=(',', ':')).encode(), compresslevel=1)).decode()
            await legacy({'token': spec.cache_token, 'snapshot_key': spec.snapshot_key, 'gzip': compressed})
        pending_previews.pop(spec.preview_id, None)
        return True

    @workspace_gate(store)
    async def recover_preview(preview):
        pending = pending_previews.get(preview.preview_id)
        if not pending or pending['expires'] < time.monotonic():
            raise ToolError('PREVIEW_RECOVERY_UNAVAILABLE: The original preview cannot be recovered in this session. Do not replace its research silently.')
        spec = pending['spec']
        if preview.cache_token != spec.cache_token or preview.snapshot_key != spec.snapshot_key or pending['owner'] != current_oauth_subject():
            raise ToolError('PREVIEW_RECOVERY_UNAVAILABLE')
        try:
            await persist_preview(spec)
            return spec
        except (ControlPlaneError, SelectionError, OSError) as error:
            raise ToolError('PREVIEW_STORAGE_UNAVAILABLE: Retry this same preview; its research has not been replaced.') from error

    @server.tool(meta={**mixed,**ui},annotations=read_annotations,structured_output=True)
    async def recover_research_preview(preview: PreviewSpec, kind: Kind='cros') -> dict[str, Any]:
        """Retry storage of the exact failed preview, retaining its identity and selection. Does not save an account project or repeat research."""
        spec = await recover_preview(preview)
        out = await read_project_preview(spec, kind)
        return {**out, 'storage_status': 'ready'}

    @server.tool(meta={**mixed,**app_callable},annotations=read_annotations,structured_output=True)
    async def read_project_preview(preview:PreviewSpec,kind:Kind='sites',offset:Annotated[int,Field(ge=0)]=0,controls:dict[str,str]|None=None,limit:Annotated[int,Field(ge=1,le=100)]=10)->dict[str,Any]:
        """Read an existing preview without opening or changing the workspace.

        Paid accounts may choose limit 1–100; use 100 for broad analysis and fewer
        for detailed evidence. Free accounts are limited to the first ten results.
        Follow next_offset for additional paid pages; do not repeat the search.
        """
        try:return with_workspace_destinations(await control_factory().research_workspace({'operation':'preview_read','preview':preview.model_dump(mode='json'),'kind':kind,'offset':offset,'limit':limit,'controls':controls or {}}))
        except ControlPlaneError as error:raise ToolError(str(error)) from error

    @server.tool(meta={**oauth,**app_callable},annotations=read_annotations,structured_output=True)
    async def list_projects()->dict[str,Any]:
        """List the connected account's canonical projects, created on the website or in ChatGPT."""
        if not current_oauth_subject():return connect_result()
        try:return await control_factory().research_workspace({'operation':'canonical_list'})
        except ControlPlaneError as error:raise ToolError(str(error)) from error

    @server.tool(meta={**oauth,**ui},annotations=overwrite,structured_output=True)
    async def save_project(
        preview:PreviewSpec,
        project_id:Annotated[str,Field(pattern=r'^[a-f0-9-]{36}$')]|None=None,
        expected_revision:Annotated[int,Field(ge=1)]|None=None,
    )->dict[str,Any]:
        """Store a finalized research preview in an authenticated owner's canonical project.

        Synchronizes the exact cached results with the TrialAgents website without rerunning
        research. project_id and expected_revision together update an existing project;
        omitting both creates or attaches the preview's project. Returns verified saved state.
        """
        if not current_oauth_subject():
            return connect_result()
        if preview.preview_id in pending_previews:
            preview = await recover_preview(preview)
        if not preview.cache_token:
            raise ToolError('PREVIEW_UNAVAILABLE: Retry storage of the original preview before saving.')
        if (project_id is None) != (expected_revision is None):
            raise ToolError('INVALID_REVISION: Supply both project_id and expected_revision for updates.')
        command={'cacheToken':preview.cache_token,'snapshotKey':preview.snapshot_key,
                 'idempotencyKey':hashlib.sha256(json.dumps([preview.preview_id,preview.snapshot_key,project_id,expected_revision]).encode()).hexdigest()}
        if project_id is None:command['proposedProjectId']=preview.preview_id
        else:command.update(projectId=project_id,expectedRevision=expected_revision)
        try:
            saved=await control_factory().research_workspace({'operation':'canonical_commit','input':command})
            return with_workspace_destinations(await control_factory().research_workspace({'operation':'canonical_read','projectId':saved['project_id'],'kind':'sites','offset':0,'limit':10}))
        except ControlPlaneError as error:raise ToolError(str(error)) from error

    @server.tool(meta={**oauth,**app_callable},annotations=read_annotations,structured_output=True)
    async def read_project(
        project_id:Annotated[str,Field(pattern=r'^[a-f0-9-]{36}$')],
        kind:Kind|None=None,offset:Annotated[int,Field(ge=0)]=0,controls:dict[str,str]|None=None,
        limit:Annotated[int,Field(ge=1,le=100)]=10,
    )->dict[str,Any]:
        """Read the latest canonical project without opening or changing the workspace.

        Paid accounts choose limit 1–100: use 100 for broad analysis, fewer for
        detailed evidence. Free accounts get only the first ten results. Follow
        next_offset for further paid pages. Use open_project only to present the
        final table, or save_project_custom_view to present the final Custom view.

        Omit kind to open the most recently saved active table. Omit controls to use
        the owner's latest saved filters/ranking from either client. Supply controls
        (including {} for no filtering) for a temporary read-only override. Read
        this tool again before analyzing the user's current view; UI context may be stale.
        Responses include applied view controls/version and access-limited counts.
        The same project ID opens on the website. Reads do not create projects,
        repeat searches, prepare reports or pin the view to an obsolete revision.
        """
        if not current_oauth_subject():return connect_result()
        try:
            result=await control_factory().research_workspace({'operation':'canonical_read','projectId':project_id,'kind':kind,'offset':offset,'limit':limit,**({'controls':controls} if controls is not None else {})})
            if not result:raise ToolError('PROJECT_NOT_FOUND')
            return with_workspace_destinations(result)
        except ControlPlaneError as error:raise ToolError(str(error)) from error

    @server.tool(meta={**oauth,**ui},annotations=read_annotations,structured_output=True)
    async def open_project(
        project_id:Annotated[str,Field(pattern=r'^[a-f0-9-]{36}$')],
        kind:Kind|None=None,offset:Annotated[int,Field(ge=0)]=0,controls:dict[str,str]|None=None,
    )->dict[str,Any]:
        """Present a canonical project's table in the workspace as the final display step.

        For analysis and pagination use read_project, which leaves the current
        workspace visible and supports paid reads up to 100 rows. Call this once
        when ready to show the table; do not open tables before a final Custom view.
        Omit kind/controls to use the latest saved view. Display pages contain ten rows.
        """
        out=await read_project(project_id,kind,offset,controls)
        return {**out,'active_tab':'tables'} if isinstance(out,dict) else out

    @server.tool(meta={**oauth,**app_callable},annotations=overwrite,structured_output=True)
    async def save_project_view(
        project_id:Annotated[str,Field(pattern=r'^[a-f0-9-]{36}$')],kind:Kind,
        controls:dict[str,str],expected_version:Annotated[int,Field(ge=0)],
        expected_revision:Annotated[int,Field(ge=1)],
    )->dict[str,Any]:
        """Save applied table filters/ranking for the connected user's project.

        Explicit preference write only; never changes the dataset or research cohort.
        Use the view version and project revision returned by open_project. An empty
        controls object resets the view. On conflict, reopen and reconcile; never
        blindly overwrite. Call only for a user-requested view change.
        """
        if not current_oauth_subject():return connect_result()
        try:return await control_factory().research_workspace({'operation':'view_save','projectId':project_id,'kind':kind,'controls':controls,'expectedVersion':expected_version,'expectedRevision':expected_revision})
        except ControlPlaneError as error:raise ToolError(str(error)) from error

    @server.tool(meta={**mixed,'ui':{'visibility':['app']},'openai/widgetAccessible':True},annotations=read_annotations,structured_output=True)
    async def read_workspace_trial(trial_id:str,project_id:str|None=None,preview:PreviewSpec|None=None,revision:int|None=None)->dict[str,Any]:
        """Read an authorized frozen trial profile for the workspace detail dialog."""
        if not preview and not current_oauth_subject():return connect_result()
        try:return await control_factory().research_workspace({'operation':'trial_profile','trialId':trial_id,'projectId':project_id,'preview':preview.model_dump(mode='json') if preview else None,'revision':revision})
        except ControlPlaneError as error:raise ToolError(str(error)) from error

    async def read(project_id,token,kind='cros',offset=0,revision=None):
        body={'operation':'read','projectId':project_id,'previewToken':token,'kind':kind,'offset':offset,'limit':10}
        # The App distinguishes an omitted revision (latest) from JSON null (invalid).
        if revision is not None:body['revision']=revision
        out=await control_factory().research_workspace(body)
        out['presentation']={'supporting_trials':'only_on_explicit_request',
            'instruction':'The workspace holds the result tables. Keep chat to concise summary and insights. Supporting-trial lists require an explicit user request.'}
        # A bearer preview capability is necessary to resume an unclaimed project.
        # Once owned, OAuth ownership is required and the capability is omitted.
        if not out['owned']:
            out['preview_token']=token
            out['url']=f"https://intel.trialagents.com/share/research/{project_id}#preview={token}"
        return out

    async def preview_access():
        if not current_oauth_subject():
            return {'connected': False, 'fullAccess': False}
        return {**await control_factory().research_access(None, []), 'connected': True}

    def preview_payload(spec):
        payload = workspace_payload(store.get(spec.selection_id), spec.title,
                                    spec.include_cro_contacts, spec.recommendations)
        if payload_key(payload) != spec.snapshot_key:
            raise SelectionError('PREVIEW_CHANGED: Reopen the current preview before connecting.')
        return payload

    @workspace_gate(store)
    async def materialize(spec):
        # Only explicit connection/save tools call this writer. Preview rendering never does.
        payload = preview_payload(spec)
        token = base64.urlsafe_b64encode(hashlib.sha256(
            (spec.preview_id + ':' + spec.selection_id + ':' + spec.snapshot_key + ':' + (current_oauth_subject() or '')).encode()).digest()).decode().rstrip('=')
        out = await control_factory().research_workspace(
            {'operation': 'create', 'previewToken': token, 'payload': payload})
        return out['project_id'], token

    @server.tool(meta={**mixed,**ui},annotations=read_annotations,structured_output=True)
    @workspace_gate(store)
    async def prepare_research_workspace(
        selection_id:Annotated[str,Field(min_length=40,max_length=64)],
        title:Annotated[str,Field(min_length=1,max_length=160)],
        include_cro_contacts:bool=False,
        recommendations:Annotated[list[Recommendation],Field(max_length=30)]=[],
        kind:Kind='cros',offset:Annotated[int,Field(ge=0)]=0,
        preview_id:Annotated[str,Field(pattern=r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$')]|None=None,
    )->dict[str,Any]:
        """Display the interactive Intel workspace from an existing search, without saving a project.

        DEFAULT initial results: call after broadening is complete with the final selection_id.
        This is read-only computation over the existing short-lived search snapshot: no project,
        account change or project job is created, even for connected users. Prepared query
        results may be cached internally for 7 days, separately from user projects.
        Reuse this tool with updated selection/title/recommendations to refine an unsaved preview.
        Commit saved-project refinements with save_project using project_id and expected_revision. Keep chat to concise insights.
        Four tables are available immediately. Account access controls pagination and evidence.
        Connect account opens website login immediately. The website imports the exact preview only after authentication.
        The cached import expires after 7 days; never claim a preview is already a saved project.
        """
        try:
            payload=await run_cpu(workspace_payload,store.get(selection_id),title,include_cro_contacts,recommendations)
            access=await preview_access()
            full=access.get('fullAccess') is True
            pages={k:preview_page(payload,k,0,full) for k in ('cros','sites','pis','trials')}
            for rec in recommendations:
                if not any(e['id']==rec.entity_id for e in pages[rec.entity_type]['entities']) and not full:
                    raise SelectionError('ENTITY_ACCESS_REQUIRED')
            result=preview_page(payload,kind,offset,full)
            visible={e['id'] for e in result['entities']}
            spec=PreviewSpec(preview_id=preview_id or str(uuid4()),selection_id=selection_id,title=title,include_cro_contacts=include_cro_contacts,
                             recommendations=recommendations,snapshot_key=payload_key(payload))
            if preview_id:
                # Bind the token to the original operation, owner and content with
                # a server-only key. Replays must also reuse the token:
                # the App's idempotency receipt includes its hash, not just the UUID.
                identity=json.dumps(['preview-cache-v1',selection_id,preview_id,current_oauth_subject(),spec.snapshot_key],separators=(',',':'))
                spec.cache_token=base64.urlsafe_b64encode(hmac.new(preview_token_key,identity.encode(),hashlib.sha256).digest()).decode().rstrip('=')
            storage_ready=False
            storage_error=None
            try:
                storage_ready=await persist_preview(spec,payload)
            except (ControlPlaneError,OSError) as error:
                storage_error=getattr(error,'code','PREVIEW_STORAGE_UNAVAILABLE')
                # Keep the capability and identity for an exact retry, never advertise this as stored.
                for key in list(pending_previews):
                    if pending_previews[key]['expires'] < time.monotonic(): pending_previews.pop(key,None)
                if len(pending_previews)>=128:pending_previews.pop(next(iter(pending_previews)))
                pending_previews[spec.preview_id]={'spec':spec.model_copy(deep=True),'owner':current_oauth_subject(),'expires':time.monotonic()+store.remaining_seconds(selection_id)}
                logging.getLogger(__name__).warning('preview_storage_failed code=%s',storage_error)
            return {'project_id':spec.preview_id,
                'title':title,'revision':1,'current_revision':1,'owned':False,'saved':False,
                'draft':spec.model_dump(mode='json'),'preview_tables':pages,
                'expires_in_seconds':604800 if storage_ready else store.remaining_seconds(selection_id),'account':access,
                'storage_status':'ready' if storage_ready else 'unavailable','storage_error':storage_error,
                'recovery_tool':'recover_research_preview' if storage_error else None,
                'result':result,'recommendations':[r.model_dump(mode='json') for r in recommendations
                    if r.entity_type==kind and r.entity_id in visible],
                'tables':[{'kind':s['entity_type'],'total':s['result']['total_entities']} for s in payload['sections']],
                'presentation':{'supporting_trials':'only_on_explicit_request',
                    'save_tool':'save_project','account_connected':bool(access.get('connected')),'preview_saved_to_account':False}}
        except (SelectionError,ControlPlaneError) as e:raise ToolError(str(e)) from e

    @server.tool(meta={**mixed,**ui},annotations=write,structured_output=True)
    async def publish_research_workspace(
        selection_id: Annotated[str,Field(min_length=40,max_length=64)],
        title: Annotated[str,Field(min_length=1,max_length=160)],
        include_cro_contacts: bool=False,
        recommendations: Annotated[list[Recommendation],Field(max_length=30)]=[],
        kind: Kind='cros',
        operation_id: Annotated[str|None,Field(min_length=1,max_length=128,description='Optional identity for an intentionally separate project from the same selection. Reuse it unchanged on retries.')]=None,
    ) -> dict[str, Any]:
        """Store and present finalized research; authentication is optional.

        Storage depends on verified credentials.
        Guests receive a cached seven-day preview; connected owners receive a canonical
        saved project. Existing project revisions use save_project with expected_revision.
        Custom view storage is a separate operation exposed by save_project_custom_view.
        For a connected account, repeating the same selection and publication inputs
        reuses the project. Anonymous calls keep independent private preview capabilities.
        Use a new operation_id only when intentionally creating a separate project
        from that same selection; reuse it on retries. It is not an access token.
        """
        preview_id=None
        if current_oauth_subject():
            identity=payload_key(['publish-v1',current_oauth_subject(),selection_id,title,include_cro_contacts,
                                  [r.model_dump(mode='json') for r in recommendations],operation_id])
            preview_id=str(uuid5(NAMESPACE_URL,'trialagents:publish:'+identity))
        out=await prepare_research_workspace(selection_id,title,include_cro_contacts,recommendations,kind,preview_id=preview_id)
        if not current_oauth_subject() or out.get('storage_status')!='ready':return out
        try:
            return await save_project(PreviewSpec.model_validate(out['draft']))
        except ToolError as error:
            return {**out,'project_save_error':str(error),'save_status':'failed',
                    'recovery':{'retry_tool':'save_project','preview_available':True,'draft_retained':True}}

    @server.tool(meta={**mixed,**app_callable},annotations=read_annotations,structured_output=True)
    async def get_research_workspace(
        project_id:Annotated[str,Field(pattern=r'^[a-f0-9-]{36}$')],
        preview_token:Annotated[str,Field(pattern=r'^[A-Za-z0-9_-]{43}$')]|None=None,
        kind:Kind='cros',offset:Annotated[int,Field(ge=0)]=0,
        revision:Annotated[int,Field(ge=1)]|None=None,
    )->dict[str,Any]:
        """Open/paginate a SAVED project table or read a previous revision under current access.

        Unsaved previews (saved=false, with draft) use prepare_research_workspace, never this tool.

        Model and UI receive the same authorized rows. Free access is ten per table;
        active paid access permits subsequent pages. No arbitrary trial profiles are exposed.
        """
        try:return await read(project_id,preview_token,kind,offset,revision)
        except ControlPlaneError as e:raise ToolError(str(e)) from e

    @server.tool(meta={**mixed,**ui},annotations=read_annotations,structured_output=True)
    async def open_research_workspace(
        project_id:Annotated[str,Field(pattern=r'^[a-f0-9-]{36}$')],
        preview_token:Annotated[str,Field(pattern=r'^[A-Za-z0-9_-]{43}$')]|None=None,
    )->dict[str,Any]:
        """Reopen the shared TrialAgents Intel workspace preview without changing saved data."""
        try:return await read(project_id,preview_token)
        except ControlPlaneError as e:raise ToolError(str(e)) from e

    @server.tool(meta={**mixed,'ui':{'visibility':['app']},'openai/widgetAccessible':True},annotations=overwrite,structured_output=True)
    @workspace_gate(store)
    async def revise_research_workspace(
        project_id:Annotated[str,Field(pattern=r'^[a-f0-9-]{36}$')],
        expected_revision:Annotated[int,Field(ge=1)],
        selection_id:Annotated[str,Field(min_length=40,max_length=64)],
        title:Annotated[str,Field(min_length=1,max_length=160)],
        preview_token:Annotated[str,Field(pattern=r'^[A-Za-z0-9_-]{43}$')]|None=None,
        include_cro_contacts:bool=False,
        recommendations:Annotated[list[Recommendation],Field(max_length=30)]=[],
    )->dict[str,Any]:
        """Save a new revision of the same project after a user-requested cohort/priority change.

        Use search/inspect/refine to select source trials first. Preserve the current project ID.
        Expected revision prevents overwriting intervening changes. On REVISION_CONFLICT,
        reopen current state and reconcile with the user request, never blindly overwrite.
        Recommendations replace this revision's recommendation list; [] clears it.
        """
        try:
            body=workspace_payload(store.get(selection_id),title,include_cro_contacts,recommendations)
            await control_factory().research_workspace({'operation':'revise','projectId':project_id,'previewToken':preview_token,'expectedRevision':expected_revision,'payload':body})
            return await read(project_id,preview_token)
        except (SelectionError,ControlPlaneError) as e:raise ToolError(str(e)) from e

    @server.tool(meta={**mixed,**app_callable,'ui':{'visibility':['app']}},annotations=write,structured_output=True)
    async def create_research_account_handoff(
        project_id:Annotated[str,Field(pattern=r'^[a-f0-9-]{36}$')],
        preview_token:Annotated[str,Field(pattern=r'^[A-Za-z0-9_-]{43}$')]|None=None,
        draft:PreviewSpec|None=None,
    )->dict[str,Any]:
        """On explicit Connect account, save a preview and open login/signup for the chosen account.

        Pass draft from prepare_research_workspace for an unsaved preview. This is the
        first persistent write: it stores the exact search snapshot without rerunning research.

        Legacy model-driven handoff; the embedded Connect button instead opens website login
        immediately and imports after authentication. Does not initiate host OAuth or a
        purchase. The private short-lived URL authorizes saving this exact project;
        open it on the user's click. Never print its token in conversation text.
        Login completes saving and opens the ordinary Projects list. A different
        account may receive an exact copy; the original owner's project stays private.
        """
        try:
            if draft is not None:
                project_id,preview_token=await materialize(draft)
            return await control_factory().research_workspace({'operation':'handoff',
                'projectId':project_id,'previewToken':preview_token})
        except (SelectionError,ControlPlaneError) as e:raise ToolError(str(e)) from e

    @server.tool(meta={**oauth,'ui':{'visibility':['app']},'openai/widgetAccessible':True},annotations=write,structured_output=True)
    async def claim_research_workspace(
        project_id:Annotated[str,Field(pattern=r'^[a-f0-9-]{36}$')],
        preview_token:Annotated[str,Field(pattern=r'^[A-Za-z0-9_-]{43}$')]|None=None,
        draft:PreviewSpec|None=None,
    )->dict[str,Any]:
        """Save a preview to the connected account. Pass draft for unsaved search previews.

        Legacy persisted previews retain their ID; unsaved previews receive a project ID on save.

        Requires the preview owner's authorization. Repeated claims by its owner
        preserve the same research without rerunning its search.
        Connection alone does not activate paid access.
        The preview capability becomes unusable anonymously after claiming. Starts no payment.
        """
        if not current_oauth_subject():return connect_result()
        try:
            if draft is not None:
                project_id,preview_token=await materialize(draft)
            await control_factory().research_workspace({'operation':'claim','projectId':project_id,'previewToken':preview_token})
            out=await read(project_id,None)
            out['saved']=True
            out['projects_url']='https://intel.trialagents.com/projects'
            out['message']='This research is saved in your TrialAgents account and appears in Projects.'
            return out
        except (SelectionError,ControlPlaneError) as e:raise ToolError(str(e)) from e

    return recover_preview
