"""One persisted cohort for the shared Intel Agent workspace; no model jobs."""
from copy import deepcopy
import secrets
import hashlib
import json
import base64
from uuid import uuid4
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

# A bundle change must change the resource identity: hosts can cache UI by URI.
WORKSPACE_HTML=files('intel_mcp').joinpath('ui/workspace-v1.html').read_text()
RESOURCE='ui://trialagents/workspace-'+hashlib.sha256(WORKSPACE_HTML.encode()).hexdigest()[:16]
LEGACY_RESOURCE='ui://trialagents/workspace-v1'
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


def payload_key(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def preview_page(payload, kind, offset, full):
    if not full and offset:
        raise SelectionError('PAID_ACCOUNT_REQUIRED')
    section = next(s for s in payload['sections'] if s['entity_type'] == kind)
    result = deepcopy(section['result'])
    result['entities'] = result['entities'][offset:offset+10]
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
        child=SelectionDataset(SelectionCriteria.model_validate(criteria),deepcopy(list(dataset.records.values())))
        result=child.rank(limit=50000,full_cohort=True).model_dump(mode='json')
        if result['returned']!=result['total_entities']:raise SelectionError('SNAPSHOT_TOO_LARGE')
        origin=getattr(dataset,'selection_origin',None)
        result['cohort']=public_cohort(result['cohort'],origin)
        result['entity_type']=kind
        if origin:result['selection_origin']=origin
        if kind=='cros' and not include_cro_contacts:
            for e in result['entities']:e['contacts']=[c for c in e['contacts'] if 'email' not in c]
        sections.append({'entity_type':kind,'snapshot':child.snapshot,'trial_ids':sorted(dataset.records),'result':result})
    trials=[]
    for offset in range(0,len(dataset.records),100):
        trials.extend({'id':t['trial_id'],**t} for t in candidate_trials(dataset,offset=offset,limit=100)['trials'])
    cohort=public_cohort(dataset.summary().model_dump(mode='json'),getattr(dataset,'selection_origin',None))
    result={'entity_type':'trials','entities':trials,'total_entities':len(trials),'returned':len(trials),'cohort':cohort}
    if hasattr(dataset,'selection_origin'):result['selection_origin']=dataset.selection_origin
    sections.append({'entity_type':'trials','snapshot':dataset.snapshot,'trial_ids':sorted(dataset.records),'result':result})
    shared=compact_workspace_evidence(sections)
    return {'title':title,'sections':sections,'shared_evidence':shared,
            'recommendations':[r.model_dump(mode='json') for r in recommendations]}


def register_workspace_tools(server,store,control_factory,mixed,oauth,read_annotations,connect_result):
    write=ToolAnnotations(read_only_hint=False,destructive_hint=False,idempotent_hint=True,open_world_hint=False)
    ui={'ui':{'resourceUri':RESOURCE}}
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
            return {'fullAccess': False}
        return await control_factory().research_access(None, [])

    def preview_payload(spec):
        payload = workspace_payload(store.get(spec.selection_id), spec.title,
                                    spec.include_cro_contacts, spec.recommendations)
        if payload_key(payload) != spec.snapshot_key:
            raise SelectionError('PREVIEW_CHANGED: Reopen the current preview before connecting.')
        return payload

    async def materialize(spec):
        # Only explicit connection/save tools call this writer. Preview rendering never does.
        payload = preview_payload(spec)
        token = base64.urlsafe_b64encode(hashlib.sha256(
            (spec.preview_id + ':' + spec.selection_id + ':' + spec.snapshot_key + ':' + (current_oauth_subject() or '')).encode()).digest()).decode().rstrip('=')
        out = await control_factory().research_workspace(
            {'operation': 'create', 'previewToken': token, 'payload': payload})
        return out['project_id'], token

    @server.tool(meta={**mixed,**ui},annotations=read_annotations,structured_output=True)
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
        account change, job or durable artifact is created, even for connected users.
        Reuse this tool with updated selection/title/recommendations to refine an unsaved preview.
        Saved projects alone use revise_research_workspace. Keep chat to concise insights.
        Four tables are available immediately. Account access controls pagination and evidence.
        Connect account in the UI explicitly starts saving the exact preview and opens login/signup.
        The preview expires with the search; never claim it has already been saved.
        """
        try:
            payload=workspace_payload(store.get(selection_id),title,include_cro_contacts,recommendations)
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
            return {'project_id':spec.preview_id,
                'title':title,'revision':1,'current_revision':1,'owned':False,'saved':False,
                'draft':spec.model_dump(mode='json'),'preview_tables':pages,
                'expires_in_seconds':store.remaining_seconds(selection_id),'account':access,
                'result':result,'recommendations':[r.model_dump(mode='json') for r in recommendations
                    if r.entity_type==kind and r.entity_id in visible],
                'tables':[{'kind':s['entity_type'],'total':s['result']['total_entities']} for s in payload['sections']],
                'presentation':{'supporting_trials':'only_on_explicit_request',
                    'instruction':'Show the interactive preview. It is not saved yet. Connect account starts saving; no account is needed to view.'}}
        except (SelectionError,ControlPlaneError) as e:raise ToolError(str(e)) from e

    @server.tool(meta=mixed,annotations=read_annotations,structured_output=True)
    async def get_research_workspace(
        project_id:Annotated[str,Field(pattern=r'^[a-f0-9-]{36}$')],
        preview_token:Annotated[str,Field(pattern=r'^[A-Za-z0-9_-]{43}$')]|None=None,
        kind:Kind='cros',offset:Annotated[int,Field(ge=0)]=0,
        revision:Annotated[int,Field(ge=1)]|None=None,
    )->dict[str,Any]:
        """Open/paginate one project table or read a previous revision under current access.

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
        """Reopen the shared Intel Agent workspace preview without changing saved data."""
        try:return await read(project_id,preview_token)
        except ControlPlaneError as e:raise ToolError(str(e)) from e

    @server.tool(meta={**mixed,**ui},annotations=write,structured_output=True)
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

    @server.tool(meta=mixed,annotations=write,structured_output=True)
    async def create_research_account_handoff(
        project_id:Annotated[str,Field(pattern=r'^[a-f0-9-]{36}$')],
        preview_token:Annotated[str,Field(pattern=r'^[A-Za-z0-9_-]{43}$')]|None=None,
        draft:PreviewSpec|None=None,
    )->dict[str,Any]:
        """On explicit Connect account, save a preview and open login/signup for the chosen account.

        Pass draft from prepare_research_workspace for an unsaved preview. This is the
        first persistent write: it stores the exact search snapshot without rerunning research.

        Used by Connect account in the workspace. Does not initiate host OAuth or a
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

    @server.tool(meta={**oauth,**ui},annotations=write,structured_output=True)
    async def claim_research_workspace(
        project_id:Annotated[str,Field(pattern=r'^[a-f0-9-]{36}$')],
        preview_token:Annotated[str,Field(pattern=r'^[A-Za-z0-9_-]{43}$')]|None=None,
        draft:PreviewSpec|None=None,
    )->dict[str,Any]:
        """Save a preview to the connected account. Pass draft for unsaved search previews.

        Legacy persisted previews retain their ID; unsaved previews receive a project ID on save.

        Use when the user connects their account from a research workspace: saving that
        current research is part of connection, not a separate optional step. If authentication
        is required, complete OAuth then retry this same claim with the same arguments.
        Never rerun the search. Materialize unsaved previews only on this explicit save request. Repeated claims by its owner are safe.
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
