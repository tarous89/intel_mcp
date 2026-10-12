import React,{useState,useRef,useEffect} from 'react';
import {createRoot} from 'react-dom/client';
import {App,applyDocumentTheme,applyHostStyleVariables} from '@modelcontextprotocol/ext-apps';
import {OpenAIExtensions} from '@openai/mcp-extensions/app';
import {WorkspaceTables,type WorkspaceKind} from 'intel-shared-workspace';
import {connectProject,openConnection,ConnectionError} from './connect-project';
const app=new App({name:'Intel Agent workspace',version:'0.2.0'},{availableDisplayModes:['fullscreen']});
new OpenAIExtensions(app);
const root=createRoot(document.querySelector('main')!);
let setIncoming:(data:any)=>void=()=>{};
function modelContext(data:any){
 // Context synchronization is optional host support, not a table-load dependency.
 try{void Promise.resolve(app.updateModelContext({structuredContent:{project_id:data.project_id,saved:!data.draft,draft:data.draft,revision:data.revision,table:data.result.entity_type,applied_view:data.view??null,matching_count:data.result.total_entities,visible_count:data.result.returned,view_scope:data.account?.fullAccess?'full_dataset':'accessible_preview',visible_rows:data.result.entities,access:data.result.access_info,selection:data.result.selection_origin??null,reports:data.reports??[],visualization_save_offer:data.visualization_save_offer??null,active_report_id:data.active_report_id??null}})).catch(()=>{});}catch{/* Keep rendered results usable if the host does not support context updates. */}
}
function View({initial}:{initial:any}){
 const [reportsView,setReportsView]=useState(!!initial.active_report_id),[activeReport,setActiveReport]=useState<string|undefined>(initial.active_report_id);
 const [data,setData]=useState(initial),[dataset,setDataset]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(''),[retryPage,setRetryPage]=useState<{kind:WorkspaceKind;offset:number}|null>(null),[connectionError,setConnectionError]=useState(false);
 const [connectionStatus,setConnectionStatus]=useState('');
 const pageCache=useRef(new Map<string,{at:number;data:any}>());
 const requestSerial=useRef(0),activeControls=useRef<any>({});
 const connecting=useRef(false),handoff=useRef<{url:string;expires:number;project:string}|null>(null);
 setIncoming=value=>{pageCache.current.clear();requestSerial.current++;setBusy(false);setConnectionStatus('');handoff.current=null;setData(value);setReportsView(!!value.active_report_id);setActiveReport(value.active_report_id);setDataset(false);setError('');setRetryPage(null);setConnectionError(false);};
 async function page(kind:WorkspaceKind,offset:number,controls:any=undefined,preserveView=false){activeControls.current=controls;const serial=++requestSerial.current;if(!preserveView){setDataset(false);setReportsView(false);}setError('');setRetryPage(null);setConnectionError(false);
  if(!preserveView&&!data.canonical&&offset===0&&!Object.values(controls??{}).some(Boolean)&&data.preview_tables?.[kind]){const next={...data,result:data.preview_tables[kind],view:{table:kind,controls:{},version:0,source:'preview'}};setBusy(false);setData(next);modelContext(next);return;}
  const cacheKey=JSON.stringify([data.project_id,data.revision,kind,offset,controls??null,data.account?.fullAccess]);
  const cached=pageCache.current.get(cacheKey);
  if(!preserveView&&cached&&Date.now()-cached.at<30000){setBusy(false);setData(cached.data);modelContext(cached.data);return;}
  setBusy(true);setError('');try{
  const {snapshot_key,cache_token,...previewArgs}=data.draft??{};
  const out=await app.callServerTool(data.draft?(cache_token?{name:'read_project_preview',arguments:{preview:data.draft,kind,offset,controls}}:{name:'prepare_research_workspace',arguments:{...previewArgs,kind,offset}}):data.canonical?{name:'open_project',arguments:{project_id:data.project_id,kind,offset,controls}}:{name:'get_research_workspace',arguments:{project_id:data.project_id,preview_token:data.preview_token,kind,offset}});
  if(serial!==requestSerial.current)return;
  if(out.isError||!out.structuredContent?.result)throw Error();
  if(data.canonical&&offset&&data.view?.version!==undefined&&out.structuredContent.view?.version!==data.view.version){void page(kind,0,undefined,preserveView);return;}
  if(pageCache.current.size>=12)pageCache.current.delete(pageCache.current.keys().next().value!);
  pageCache.current.set(cacheKey,{at:Date.now(),data:out.structuredContent});
  setData(out.structuredContent);modelContext(out.structuredContent);
 }catch{if(serial!==requestSerial.current)return;setRetryPage({kind,offset});setError('This table could not be loaded. Your current results are still shown. Retry, or reopen the preview from the conversation if it has expired.');}finally{if(serial===requestSerial.current)setBusy(false);}}
 // Recheck account/project state only on return to this workspace. Do not poll
 // immutable datasets or block controls while the user is inspecting a table.
 const current=useRef(data);current.current=data;
 const refreshing=useRef(false);
 useEffect(()=>{
  const refresh=async()=>{
   const value=current.current;if(document.hidden||refreshing.current||(!value.canonical&&!value.draft?.cache_token))return;
   pageCache.current.clear();refreshing.current=true;const serial=requestSerial.current;
   try{const out=await app.callServerTool(value.draft?{name:'read_project_preview',arguments:{preview:value.draft,kind:value.result.entity_type,offset:value.result.access_info.offset??0,controls:activeControls.current}}:{name:'open_project',arguments:{project_id:value.project_id,kind:value.result.entity_type,offset:value.result.access_info.offset??0}});
    if(serial===requestSerial.current&&!out.isError&&out.structuredContent?.result){setData(out.structuredContent);modelContext(out.structuredContent);}
   }catch{/* Retain the visible snapshot; interactive reads surface retry errors. */}finally{refreshing.current=false;}
  };
  window.addEventListener('focus',refresh);return()=>window.removeEventListener('focus',refresh);
 },[]);
 async function applyView(controls:any){
  pageCache.current.clear();
  if(!data.canonical){await page(data.result.entity_type,0,controls);return;}
  if(busy)return;setBusy(true);setError('');
  try{
   const out=await app.callServerTool({name:'save_project_view',arguments:{project_id:data.project_id,kind:data.result.entity_type,controls,expected_version:data.view?.version??0,expected_revision:data.revision}});
   if(out.isError||!out.structuredContent?.view)throw Error();
   await page(data.result.entity_type,0);
  }catch{setError('Your filters could not be saved. Reopen the project to check the latest settings, then retry.');}
  finally{setBusy(false);}
 }
 async function readPage(kind:WorkspaceKind,offset:number,controls:any=undefined){
  const out=await app.callServerTool(data.draft?{name:'read_project_preview',arguments:{preview:data.draft,kind,offset,controls}}:{name:'open_project',arguments:{project_id:data.project_id,kind,offset,controls}});
  if(out.isError||!out.structuredContent?.result)throw Error();return out.structuredContent;
 }
 async function profile(id:string){const out=await app.callServerTool({name:'read_workspace_trial',arguments:{trial_id:id,...(data.draft?{preview:data.draft}:{project_id:data.project_id,revision:data.revision})}});if(out.isError||!out.structuredContent?.profile)throw Error();return out.structuredContent;}
 async function download(bytes:Uint8Array,name:string){let binary='';for(let i=0;i<bytes.length;i+=8192)binary+=String.fromCharCode(...bytes.subarray(i,i+8192));const out=await app.downloadFile({contents:[{type:'resource',resource:{uri:'file:///'+name,mimeType:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',blob:btoa(binary)}}]});if(out.isError)throw Error();}
 async function connect(){
  if(connecting.current)return;
  connecting.current=true;setBusy(true);setError('');setRetryPage(null);setConnectionError(false);
  const cached=handoff.current;
  setConnectionStatus('Opening TrialAgents…');
  try{
   if(cached&&cached.project===data.project_id&&cached.expires>Date.now())await openConnection(app,cached.url);
   else await connectProject(app,data,url=>{handoff.current={url,expires:Date.now()+14*60*1000,project:data.project_id};setConnectionStatus('Opening TrialAgents…');});
   setConnectionStatus('');
  }catch(cause){
   const code=cause instanceof ConnectionError?cause.code:'handoff';
   setConnectionError(true);
   setConnectionStatus(code==='navigation'?'TrialAgents could not be opened. Try Open account connection again.':'This connection link could not be prepared. Reopen the preview and try again.');
  }finally{connecting.current=false;setBusy(false);}
 }

 async function access(){try{await app.openLink({url:'https://intel.trialagents.com/dataset-access'});}catch{setError('About dataset access is available on the Intel Agent website.');}}

 async function saveState(id:string,version:number,state:any){
  const out=await app.callServerTool({name:'save_visualization_state',arguments:{report_id:id,expected_version:version,state,...(data.draft?{preview:data.draft}:{project_id:data.project_id})}});
  if(out.isError||!out.structuredContent?.saved)throw Error();
  const result=out.structuredContent;setData((current:any)=>({...current,report:result.report,reports:current.reports.map((r:any)=>r.id===id?{...r,version:result.report.version,updated_at:result.report.updated_at}:r)}));return result;
 }
 async function requestSave(){
  try{await app.updateModelContext({structuredContent:{project_id:data.project_id,preview:data.draft??null,visualization_save_offer:data.visualization_save_offer}});
   const result=await app.sendMessage({role:'user',content:[{type:'text',text:(data.visualization_save_offer?.retry?'Retry saving':'Save')+' the visualization “'+data.visualization_save_offer?.title+'” in this TrialAgents project. Use the existing content; verify the saved result.'}]});if(result.isError)throw Error();
  }catch{setError('Could not send the save request. Ask ChatGPT to save this visualization again.');}
 }
 async function readReport(id:string){if(data.report?.id===id&&(!data.reports?.find((r:any)=>r.id===id)?.version||data.reports.find((r:any)=>r.id===id).version===data.report.version))return {report:data.report};const out=await app.callServerTool({name:'read_project_report',arguments:{report_id:id,...(data.draft?{preview:data.draft}:{project_id:data.project_id})}});if(out.isError||!out.structuredContent?.report)throw Error();modelContext({...data,active_report_id:id});return out.structuredContent;}

 if(!data)return <p role="alert">{error}</p>;
 return <>{connectionStatus&&<section aria-label="Account connection" style={{padding:'12px 16px',borderBottom:'1px solid currentColor'}}><p role={connectionError?'alert':'status'}>{connectionStatus}</p>{!busy&&<button onClick={connect}>{handoff.current?'Open account connection':'Retry account connection'}</button>}</section>}<WorkspaceTables surface="extension" data={data} reportsView={reportsView} activeReportId={activeReport} onReports={()=>{setReportsView(true);setDataset(false);}} onReportRead={readReport} onReportStateSave={saveState} onSaveVisualization={requestSave} onPage={page} onApply={applyView} onRead={readPage} onProfile={profile} onDownload={download} onAccount={connect} onDataset={()=>{setDataset(true);setReportsView(false);}} dataset={dataset} onAccess={access} busy={busy} error={error}/>{retryPage&&<p><button onClick={()=>page(retryPage.kind,retryPage.offset)} disabled={busy}>Retry loading table</button></p>}</>;
}
class WorkspaceBoundary extends React.Component<{children:React.ReactNode},{failed:boolean}>{
 state={failed:false};
 static getDerivedStateFromError(){return {failed:true};}
 render(){return this.state.failed?<section role="alert" style={{padding:24,color:'#182628',background:'#fff',fontFamily:'system-ui'}}><h1>Workspace could not be displayed</h1><p>Please reopen the workspace from the conversation. Your research has not been changed.</p></section>:this.props.children;}
}
let mounted=false;
app.ontoolresult=result=>{const data=result.structuredContent;if(!data?.project_id||!data.result)return;
 modelContext(data);if(mounted)setIncoming(data);else{root.render(<WorkspaceBoundary><View initial={data}/></WorkspaceBoundary>);mounted=true;}};
function theme(ctx:any){if(ctx?.theme)applyDocumentTheme(ctx.theme);if(ctx?.styles?.variables)applyHostStyleVariables(ctx.styles.variables);}
app.onhostcontextchanged=theme;
app.connect().then(async()=>{const context=app.getHostContext();theme(context);if(context?.displayMode!=='fullscreen'&&context?.availableDisplayModes?.includes('fullscreen')){try{await app.requestDisplayMode({mode:'fullscreen'});}catch{/* Host placement remains authoritative. */}}}).catch(()=>root.render(<p>Use the project link in the conversation to open Intel Agent.</p>));
