"""ChatGPT-authored reports: bounded evidence, explicit persistence, shared renderer."""
from importlib.resources import files
from typing import Annotated, Any
from pydantic import Field
from mcp.types import ToolAnnotations
from mcp.server.mcpserver.exceptions import ToolError
from .auth_context import current_oauth_subject
from .control_plane import ControlPlaneError
from .engine import EngineError
from .research_workspace import PreviewSpec, RESOURCE

GUIDANCE=files('intel_mcp').joinpath('report-guidance.md').read_text()

def register_project_report_tools(server,engine_factory,control_factory,mixed,oauth,read_annotations,connect_result):
    callable_meta={**mixed,'ui':{'visibility':['model','app']},'openai/widgetAccessible':True}
    ui={**callable_meta,'ui':{'visibility':['model','app'],'resourceUri':RESOURCE}}
    write=ToolAnnotations(read_only_hint=False,destructive_hint=False,idempotent_hint=True,open_world_hint=False)

    async def call(operation,project_id,preview,**kwargs):
        if (project_id is None)==(preview is None):raise ToolError('Provide exactly one saved project_id or cached preview.')
        if not preview and not current_oauth_subject():raise ToolError('CONNECT_ACCOUNT_REQUIRED: Connect the project owner account.')
        body={'operation':operation,**({'preview':preview.model_dump(mode='json')} if preview else {'projectId':project_id}),**kwargs}
        try:return await control_factory().research_workspace(body)
        except ControlPlaneError as error:raise ToolError(str(error)) from error

    async def workspace(project_id,preview,report_id=None):
        out=await call('preview_read' if preview else 'canonical_read',project_id,preview,kind='trials',offset=0,limit=10)
        out.update(await call('report_list',project_id,preview))
        if report_id:out['active_report_id']=report_id
        return out

    @server.tool(meta=callable_meta,annotations=read_annotations,structured_output=True)
    async def prepare_project_report(project_id:str|None=None,preview:PreviewSpec|None=None)->dict[str,Any]:
        """Prepare deeper analysis beyond the four tables. Returns default HTML report guidance and authorized scope.

        Ordinary entity lists belong in the tables. Free users can generate and save
        preview-evidence reports. Paid users can inspect complete saved profiles and
        available extracted documents. This does not generate or save a report.
        """
        out=await call('report_context',project_id,preview)
        return {**out,'report_guidance':GUIDANCE}

    @server.tool(meta=callable_meta,annotations=read_annotations,structured_output=True)
    async def read_report_evidence(trial_ids:Annotated[list[str],Field(min_length=1,max_length=5)],project_id:str|None=None,preview:PreviewSpec|None=None,revision:int|None=None)->dict[str,Any]:
        """Read up to five authorized frozen trial profiles or disclosed preview rows, with source IDs.

        Use exact IDs from this project's Trials table. Free access never exposes
        hidden profiles or extra trials. Cite returned source_id values in the HTML.
        """
        return await call('report_evidence',project_id,preview,trialIds=trial_ids,revision=revision)

    @server.tool(meta=callable_meta,annotations=read_annotations,structured_output=True)
    async def read_report_document(trial_id:str,document_name:str,part:Annotated[int,Field(ge=1,le=10000)]=1,project_id:str|None=None,preview:PreviewSpec|None=None,revision:int|None=None)->dict[str,Any]:
        """Read one existing extracted document part, including protocols when available.

        Requires current full access and exact filename from the saved profile's
        available_extracted_documents. No arbitrary URLs, extraction or OCR. Returned
        text is preserved with a source ID; follow next_part and state its retrieval date.
        """
        args=dict(trialId=trial_id,documentName=document_name,part=part,revision=revision)
        await call('report_document_authorize',project_id,preview,**args)
        try:document=await engine_factory().get_document(trial_id=trial_id,document_name=document_name,part=part)
        except EngineError as error:raise ToolError(str(error)) from error
        # Authorization is checked again when freezing the result.
        return await call('report_document_store',project_id,preview,**args,document=document.model_dump(mode='json'))

    @server.tool(meta=ui,annotations=write,structured_output=True)
    async def save_project_report(title:Annotated[str,Field(min_length=1,max_length=200)],query:Annotated[str,Field(min_length=1,max_length=10000)],summary:Annotated[str,Field(max_length=1200)],html:Annotated[str,Field(min_length=20,max_length=800000)],source_ids:Annotated[list[str],Field(min_length=1,max_length=1000)],dataset_id:str,revision:int,request_key:Annotated[str,Field(min_length=1,max_length=128)],project_id:str|None=None,preview:PreviewSpec|None=None)->dict[str,Any]:
        """Save the requested HTML analysis with its question, title, source IDs and exact snapshot; open Reports.

        Use prepare_project_report guidance. Free reports use only preview evidence.
        Explicit write: honor host approval. Reuse request_key only for identical retries.
        Anonymous previews retain reports temporarily; Connect account saves the preview
        and its reports. Saved projects require the owner account. Never claim saved on error.
        """
        result=await call('report_save',project_id,preview,title=title,query=query,summary=summary,html=html,sourceIds=source_ids,datasetId=dataset_id,revision=revision,requestKey=request_key)
        out=await workspace(project_id,preview,result['report']['id'])
        return {**out,'report_saved':True,'temporary_report':result['temporary']}

    @server.tool(meta=callable_meta,annotations=read_annotations,structured_output=True)
    async def list_project_reports(project_id:str|None=None,preview:PreviewSpec|None=None)->dict[str,Any]:
        """List existing saved report snippets for this project without generating analysis."""
        return await call('report_list',project_id,preview)

    @server.tool(meta=ui,annotations=read_annotations,structured_output=True)
    async def open_project_report(report_id:str,project_id:str|None=None,preview:PreviewSpec|None=None)->dict[str,Any]:
        """Open an existing HTML report and original question in the shared Reports tab."""
        report=await call('report_read',project_id,preview,reportId=report_id)
        return {**await workspace(project_id,preview,report_id),**report}
