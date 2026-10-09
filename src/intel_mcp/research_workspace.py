"""One persisted cohort for the shared Intel Agent workspace; no model jobs."""
from copy import deepcopy
import secrets
from typing import Annotated, Any, Literal
from pydantic import Field
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from .auth_context import current_oauth_subject
from .selection import Contract, SelectionCriteria, SelectionDataset, SelectionError
from .research_cohort import candidate_trials
from .research_presentation import public_cohort
from .control_plane import ControlPlaneError

RESOURCE='ui://trialagents/workspace-v1'
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

    @server.tool(meta={**mixed,**ui},annotations=write,structured_output=True)
    async def prepare_research_workspace(
        selection_id:Annotated[str,Field(min_length=40,max_length=64)],
        title:Annotated[str,Field(min_length=1,max_length=160)],
        include_cro_contacts:bool=False,
        recommendations:Annotated[list[Recommendation],Field(max_length=30)]=[],
    )->dict[str,Any]:
        """DEFAULT initial results: open the Intel Agent workspace with one final broadest relevant cohort.

        Call after broadening is complete, before the final chat answer. Use the single
        final selection_id; do not call once per intermediate cohort or subgroup.
        Creates one project preview with four table tabs and up to ten rows per table.
        Keep supporting-trial lists out of chat unless explicitly requested by the user.

        This writes a project, not a paid analysis. Anonymous previews expire in one week;
        connected users get a private owned project. Use after selecting trials for the user's
        requested research. Keep chat to a concise summary, scope and evidence-based insights;
        do not duplicate rendered tables. CRO emails require an explicit user request.
        Recommendations must cite evidence for entities within the user's current access.
        Preserve project_id, revision and preview_token for follow-up tools; tokens are private.
        """
        try:
            dataset=store.get(selection_id)
            token=store.entries[selection_id].setdefault('workspace_token',secrets.token_urlsafe(32))
            body=workspace_payload(dataset,title,include_cro_contacts,recommendations)
            out=await control_factory().research_workspace({'operation':'create','previewToken':token,'payload':body})
            return await read(out['project_id'],token)
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

    @server.tool(meta={**oauth,**ui},annotations=write,structured_output=True)
    async def claim_research_workspace(
        project_id:Annotated[str,Field(pattern=r'^[a-f0-9-]{36}$')],
        preview_token:Annotated[str,Field(pattern=r'^[A-Za-z0-9_-]{43}$')],
    )->dict[str,Any]:
        """Save the user's anonymous preview to their connected account, preserving its project ID.

        Use when the user connects their account from a research workspace: saving that
        current research is part of connection, not a separate optional step. If authentication
        is required, complete OAuth then retry this same claim with the same arguments.
        Never recreate the project or rerun the search. Repeated claims by its owner are safe.
        Connection alone does not activate paid access.
        The preview capability becomes unusable anonymously after claiming. Starts no payment.
        """
        if not current_oauth_subject():return connect_result()
        try:
            await control_factory().research_workspace({'operation':'claim','projectId':project_id,'previewToken':preview_token})
            out=await read(project_id,None)
            out['saved']=True
            out['projects_url']='https://intel.trialagents.com/research'
            out['message']='This research is saved in your TrialAgents account and appears in Projects.'
            return out
        except ControlPlaneError as e:raise ToolError(str(e)) from e
