"""Isolated mixed-auth MCP: public top-ten research and project-bound full access."""
import json
from importlib.resources import files
from mcp.server.apps import Apps, APP_MIME_TYPE
from mcp.server.mcpserver.resources import TextResource
from typing import Annotated, Any
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations, CallToolResult, TextContent
from pydantic import Field
from starlette.responses import JSONResponse
from .auth_context import current_oauth_subject, set_oauth_subject, reset_oauth_subject
from .selection import SelectionCriteria, SelectionError
from .research_access import ResearchStore, public_ranking, public_evidence
from .control_plane import ControlPlaneError
from .engine import EngineError
from .research_presentation import RESEARCH_WORKFLOW, inline_schema, public_cohort, discovery_guidance, access_info, RESEARCH_CAPABILITIES

ANNOTATIONS=ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)
MIXED={"securitySchemes":[{"type":"noauth"},{"type":"oauth2","scopes":["mcp:tools"]}]}
OAUTH={"securitySchemes":[{"type":"oauth2","scopes":["mcp:tools"]}]}


async def research_tool_security_schemes(ctx, call_next):
    """Preserve ChatGPT auth declarations after the SDK's protocol serialization."""
    result = await call_next(ctx)
    if ctx.method == 'tools/list':
        # SDK 2.x sieves non-standard Tool fields during protocol serialization.
        # Its public middleware API runs after that sieve on the response path.
        return {**result, 'tools': [
            {**tool, 'securitySchemes': tool['_meta']['securitySchemes'],
             'inputSchema': inline_schema(tool['inputSchema'])}
            for tool in result['tools']
        ]}
    return result


def create_research_server(settings, engine_factory, control_factory):
    store=ResearchStore(engine_factory)
    resource=settings.mcp_public_resource_url.removesuffix('/mcp')+'/research/mcp'
    metadata_url=settings.mcp_public_resource_url.removesuffix('/mcp')+'/research/.well-known/oauth-protected-resource'
    issuer=settings.oauth_authorization_server_url.rstrip('/')+'/oauth/intel'
    challenge=f'Bearer resource_metadata="{metadata_url}", scope="mcp:tools"'
    apps = Apps()
    apps.add_resource(TextResource(uri="ui://trialagents/research-v014", name="Trial experience",
        mime_type=APP_MIME_TYPE, text=files("intel_mcp").joinpath("ui/research-v014.html").read_text(),
        meta={"ui": {"csp": {"connectDomains": [], "resourceDomains": []}},
              "openai/ui": {"preferredDisplayMode": "inline", "availableDisplayModes": ["inline"]}}))
    server=MCPServer('TrialAgents clinical research', extensions=[apps], middleware=[research_tool_security_schemes],
                     instructions=RESEARCH_WORKFLOW)

    async def full_access(dataset, project_id):
        if project_id is None:
            return False
        if not current_oauth_subject():
            raise SelectionError('CONNECT_ACCOUNT_REQUIRED: Connect your TrialAgents account to check project access.')
        result=await control_factory().research_access(project_id,list(dataset.records))
        if result.get('fullAccess') is not True:
            raise SelectionError('PROJECT_ACCESS_REQUIRED: This selection is not covered by the connected project entitlement.')
        return True

    @server.tool(meta=MIXED,annotations=ANNOTATIONS,structured_output=True)
    async def search_research_trials(criteria:Annotated[SelectionCriteria, Field(description=(
        "Required: base (hard structured filters), entity_type (cros/sites/pis), as_of (today YYYY-MM-DD). "
        "Also supply base_text or positive base.therapeutic_areas. For exploratory discovery use a broad "
        "disease-family base, named subgroups for population/phase, and include_broader=true. "
        "Preserve explicit mandatory constraints in base."))])->dict[str, Any]:
        """Start anonymous clinical-partner research; returns cohort counts and a selection ID.

        Required criteria keys: base, entity_type (cros/sites/pis), as_of (today YYYY-MM-DD).
        Minimal example (replace date with today):
        {"base":{},"base_text":{"fields":["title","diseases"],"terms":["prostate"]},
         "entity_type":"cros","as_of":"2026-10-07","include_broader":true}

        For first exploratory discovery target 200–500 relevant disease-family trials.
        Do not restrict the base to exact population/phase preferences: use ordered
        subgroups [{id,label,bucket,filters,text}] for direct/related candidates.
        A phase subgroup uses filters={"phase":{"values":[3]}} and optional
        phase_title_fallback=true. Text uses fields plus terms (operator any/all).
        Preserve explicit only/must constraints in base. Explain broadening.
        If fewer than 200 trials, follow discovery_guidance before finalizing.
        Do not invent a minimum or broaden mandatory constraints. Over 500 fails
        without sampling: narrow explicitly. Run entity categories sequentially.

        Next call rank_research_entities. Show concise scope and cohort size,
        total/visible entities and access_info.message in the initial report.
        No sign-in needed. Full access requires an entitled connected project.
        """
        try:
            token,dataset=await store.search(criteria)
            rank=dataset.rank(limit=10, full_cohort=True)
            return {'selection_id':token,'expires_in_seconds':store.remaining_seconds(token),
                    'cohort':public_cohort(dataset.summary().model_dump(mode='json')),
                    'discovery_guidance':discovery_guidance(len(dataset.records)),
                    'access_info':access_info(rank.total_entities,rank.returned),
                    'capabilities':RESEARCH_CAPABILITIES,
                    'entity_type':criteria.entity_type,'total_entities':rank.total_entities,
                    'visible_entities':rank.returned,'access':'top_ten','limit':10}
        except (SelectionError,EngineError) as e:
            raise ToolError(str(e)) from e

    @server.tool(meta={**MIXED, "ui": {"resourceUri": "ui://trialagents/research-v014"}},annotations=ANNOTATIONS,structured_output=True)
    async def rank_research_entities(
        selection_id:Annotated[str,Field(min_length=40,max_length=64)],
        show_followups:Annotated[bool,Field(description="True only for the final requested entity category; show supported next-action buttons once.")]=True,
        show_access_notice:Annotated[bool,Field(description="Show access notice once, in the final requested category chart.")]=True,
        offset:Annotated[int,Field(ge=0)]=0,
        limit:Annotated[int,Field(ge=1,le=100)]=10,
        include_cro_contacts:Annotated[bool,Field(description="Set true only when the user explicitly requests CRO/provider contacts. Source contacts are not verified commercial contacts.")]=False,
        project_id:Annotated[str,Field(pattern=r'^[a-fA-F0-9-]{36}$')]|None=None,
    )->dict[str, Any]:
        """Return top ten across the whole cohort by distinct trials, with total counts.

        Free access has no pagination past ten. An eligible connected project grants
        full pagination only for selections wholly within its licensed trial population.
        Always present returned/total counts and access_info.message once in the initial report.
        Preserve server order. Hide match breakdown unless asked. CRO emails require explicit contact request.
        """
        try:
            dataset=store.get(selection_id)
            full=await full_access(dataset,project_id)
            result=public_ranking(dataset,offset=offset,limit=limit,full_access=full,include_cro_contacts=include_cro_contacts)
            # Recheck after computing output: expired/revoked access releases no result.
            if full: await full_access(dataset,project_id)
            return {**result.model_dump(mode='json'),
                    'entity_type':dataset.criteria.entity_type,
                    'show_followups':show_followups,'show_access_notice':show_access_notice,
                    'cohort':public_cohort(result.cohort.model_dump(mode='json')),
                    'access_info':access_info(result.total_entities,result.returned,full=full,offset=offset),
                    'access':'full' if full else 'top_ten',
                    'next_offset':offset+result.returned if full and offset+result.returned<result.total_entities else None}
        except (SelectionError,ControlPlaneError) as e:
            raise ToolError(str(e)) from e

    @server.tool(meta=MIXED,annotations=ANNOTATIONS,structured_output=True)
    async def get_research_entity_evidence(
        selection_id:Annotated[str,Field(min_length=40,max_length=64)],
        entity_id:Annotated[str,Field(pattern=r'^[a-f0-9]{24}$')],
        offset:Annotated[int,Field(ge=0,le=500)]=0,
        project_id:Annotated[str,Field(pattern=r'^[a-fA-F0-9-]{36}$')]|None=None,
    )->dict[str, Any]:
        """Inspect supporting trial links/roles for an accessible entity; no raw profile sections.

        Free requests must name one of this selection's top ten entity IDs. Contact
        details appear in ranking results and are limited to accessible entities.
        """
        try:
            dataset=store.get(selection_id)
            full=await full_access(dataset,project_id)
            result=public_evidence(dataset,entity_id,offset=offset,full_access=full)
            if full: await full_access(dataset,project_id)
            return result.model_dump(mode='json')
        except (SelectionError,ControlPlaneError) as e:
            raise ToolError(str(e)) from e

    @server.tool(meta=OAUTH,annotations=ANNOTATIONS)
    async def list_research_projects() -> CallToolResult:
        """List your connected TrialAgents projects and existing full-access status. No purchases."""
        if not current_oauth_subject():
            return CallToolResult(is_error=True,content=[TextContent(type='text',text='Free research includes the top ten. Connect your TrialAgents account to check whether an existing project covers the full matching list. Connecting alone does not grant full access.')],
                _meta={'mcp/www_authenticate':[challenge]})
        try:
            result = await control_factory().research_access(None,[])
            result = {**result, 'account_message': (
                'Account connected. Select an eligible project to check complete-cohort access; connection alone does not grant it.'
                if any(p.get('fullAccess') is True for p in result.get('projects', []) if isinstance(p, dict)) else
                'Account connected, but no eligible project access was found. You can continue free top-ten research, refinements and evidence; creating an account does not purchase full-list access.')}
            return CallToolResult(content=[TextContent(type="text", text=json.dumps(result))], structured_content=result)
        except ControlPlaneError as e:
            raise ToolError(str(e)) from e

    @server.custom_route('/.well-known/oauth-protected-resource',methods=['GET'])
    async def metadata(request):
        return JSONResponse({'resource':resource,'authorization_servers':[issuer],'scopes_supported':['mcp:tools']})

    return server,ResearchAuth,store,resource,challenge


class ResearchAuth:
    def __init__(self,app,control_factory,resource,challenge):
        self.app,self.control_factory,self.resource,self.challenge=app,control_factory,resource,challenge
    async def __call__(self,scope,receive,send):
        if scope['type']!='http':
            return await self.app(scope,receive,send)
        authorization=dict(scope.get('headers',[])).get(b'authorization',b'').decode('latin-1')
        if not authorization:
            token=set_oauth_subject(None)
            try: return await self.app(scope,receive,send)
            finally: reset_oauth_subject(token)
        scheme,_,value=authorization.partition(' ')
        try:
            info=await self.control_factory().introspect_access_token(value) if scheme.lower()=='bearer' and value else {}
        except (ControlPlaneError,RuntimeError):
            return await JSONResponse({'error':'AUTH_UNAVAILABLE'},status_code=503)(scope,receive,send)
        if not (info.get('active') is True and isinstance(info.get('sub'),str) and info['sub'] and
                info.get('resource')==self.resource and 'mcp:tools' in str(info.get('scope','')).split()):
            return await JSONResponse({'error':'INVALID_TOKEN'},status_code=401,
                headers={'WWW-Authenticate':self.challenge})(scope,receive,send)
        token=set_oauth_subject(info['sub'])
        try: return await self.app(scope,receive,send)
        finally: reset_oauth_subject(token)
