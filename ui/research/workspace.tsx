import React,{useState,useRef,useEffect} from 'react';
import {flushSync} from 'react-dom';
import {createRoot} from 'react-dom/client';
import {App,applyDocumentTheme,applyHostStyleVariables} from '@modelcontextprotocol/ext-apps';
import {OpenAIExtensions} from '@openai/mcp-extensions/app';
import {WorkspaceTables,CustomViewRecovery,type WorkspaceKind} from 'intel-shared-workspace';
import {connectProject,openConnection,ConnectionError} from './connect-project';
const app=new App({name:'Intel Agent workspace',version:'0.2.0'},{availableDisplayModes:['fullscreen']});
new OpenAIExtensions(app);
const root=createRoot(document.querySelector('main')!);
// Keep host activity separate from the React workspace: pending calls never discard results.
const activity=document.createElement('section');
activity.className='workspace-activity';activity.hidden=true;
activity.setAttribute('role','status');activity.setAttribute('aria-live','polite');
document.querySelector('main')!.before(activity);
let activityTimer:ReturnType<typeof setTimeout>|undefined;
function showActivity(message:string,running=false){
 clearTimeout(activityTimer);activity.replaceChildren();activity.hidden=!message;
 if(!message)return;
 const text=document.createElement('p');text.textContent=message;activity.append(text);
 if(running){
  const track=document.createElement('div');track.className='workspace-loading-track';track.setAttribute('aria-hidden','true');track.append(document.createElement('span'));activity.append(track);
  activityTimer=setTimeout(()=>showActivity('Still waiting for a workspace update. Check the conversation for progress or a pending approval.'),90000);
 }
}
function clearStartup(){if(!mounted)root.render(null);}

let setIncoming:(data:any)=>void=()=>{};
function reportPreview(d:any){return d?{preview_id:d.preview_id,snapshot_key:d.snapshot_key,cache_token:d.cache_token}:undefined;}
function SaveNotice({data}:{data:any}){
 const [busy,setBusy]=useState(false),[error,setError]=useState('');
 const storage=data.storage_status==='unavailable',project=!!data.project_save_error;
 if(data.report_saved===false||(!storage&&!project))return null;
 async function retry(){setBusy(true);setError('');try{
  const call=storage?(data.account?.connected?{name:'save_project',arguments:{preview:data.draft}}:{name:'recover_research_preview',arguments:{preview:data.draft,kind:data.result?.entity_type??'cros'}}):
   project?{name:'save_project',arguments:{preview:data.draft}}:{name:'retry_project_report',arguments:{retry_id:data.retry_id}};
  const out=await app.callServerTool(call);
  if(out.isError)throw Error('The retry could not complete. Your existing research and visualization have not been replaced.');
  receive(out.structuredContent);
 }catch(cause){setError(cause instanceof Error?cause.message:'The retry could not complete.');}finally{setBusy(false);}}
 return <section role="alert" style={{padding:'12px 20px',background:'#fff5e9',color:'#573a16',borderBottom:'1px solid #e6d5be'}}>
  <p style={{margin:'0 0 8px'}}>{storage?'Your results are visible, but preview storage was interrupted. Retry storage before saving or creating a report.':project?'Your preview is ready, but we could not confirm the project save. Retry to verify it without creating another copy.':data.save_status==='unverified'?'The report save could not be verified. Retry the same save to check it without creating another copy.':'The visualization could not be saved. Your existing results have not been replaced.'}</p>
  {(storage||project||data.retry_id)&&<button disabled={busy} onClick={retry}>{busy?'Retrying…':storage?(data.account?.connected?'Retry storage and save':'Retry storage'):project?'Retry project save':'Retry report save'}</button>}
  {error&&<p>{error}</p>}
 </section>;
}
function modelContext(data:any){
 // Context synchronization is optional host support, not a table-load dependency.
 try{void Promise.resolve(app.updateModelContext({structuredContent:{project_id:data.project_id,saved:!data.draft,draft:data.draft,revision:data.revision,table:data.result.entity_type,applied_view:data.view??null,matching_count:data.result.total_entities,visible_count:data.result.returned,view_scope:data.account?.fullAccess?'full_dataset':'accessible_preview',visible_rows:data.result.entities,access:data.result.access_info,selection:data.result.selection_origin??null,reports:data.reports??[],visualization_save_offer:data.visualization_save_offer??null,active_report_id:data.active_report_id??null,workspace_destinations:{tables:{tabs:['sites','pis','cros','trials'],uses:['new searches','query revisions','ranking','sorting','filtering','paging','record details']},custom:{label:'Custom views',uses:['visual analyses','alternative presentations','comparisons','charts','forms','trackers','reusable coded outputs'],save_tool:'save_project_report',open_tool:'open_project_report',active:data.active_tab==='custom'},chat:{uses:['ordinary explanations']}}}})).catch(()=>{});}catch{/* Keep rendered results usable if the host does not support context updates. */}
}
function preserveCustomRecovery(previous:any,next:any){
 if(previous.project_id!==next.project_id||!previous.visualization_save_offer||next.report_saved===true)return next;
 const retained=Object.fromEntries(['visualization_save_offer','pending_custom_view','report_saved','retry_id','save_status','save_error','recovery'].filter(key=>!(key in next)).map(key=>[key,previous[key]]));
 return {...retained,...next};
}
function View({initial}:{initial:any}){
 const [reportsView,setReportsView]=useState(initial.active_tab==='custom'||!!initial.active_report_id),[activeReport,setActiveReport]=useState<string|undefined>(initial.active_report_id);
 const [data,setData]=useState(initial),[dataset,setDataset]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(''),[retryPage,setRetryPage]=useState<{kind:WorkspaceKind;offset:number}|null>(null),[connectionError,setConnectionError]=useState(false);
 const [connectionStatus,setConnectionStatus]=useState('');
 const pageCache=useRef(new Map<string,{at:number;data:any}>());
 const requestSerial=useRef(0),activeControls=useRef<any>({});
 const connecting=useRef(false),handoff=useRef<{url:string;expires:number;project:string}|null>(null);
 setIncoming=value=>{if(!value?.result){setData((old:any)=>({...old,...value}));if(value?.active_tab==='custom'){setReportsView(true);setDataset(false);}return;}pageCache.current.clear();requestSerial.current++;setBusy(false);setConnectionStatus('');handoff.current=null;setData(value);setReportsView(value.active_tab==='custom'||!!value.active_report_id);setActiveReport(value.active_report_id);setDataset(false);setError('');setRetryPage(null);setConnectionError(false);};
 async function page(kind:WorkspaceKind,offset:number,controls:any=undefined,preserveView=false){activeControls.current=controls;const serial=++requestSerial.current;if(!preserveView){setDataset(false);setReportsView(false);}setError('');setRetryPage(null);setConnectionError(false);
  if(!preserveView&&!data.canonical&&offset===0&&!Object.values(controls??{}).some(Boolean)&&data.preview_tables?.[kind]){const next={...data,result:data.preview_tables[kind],view:{table:kind,controls:{},version:0,source:'preview'}};setBusy(false);setData(next);modelContext(next);return;}
  const cacheKey=JSON.stringify([data.project_id,data.revision,kind,offset,controls??null,data.account?.fullAccess]);
  const cached=pageCache.current.get(cacheKey);
  if(!preserveView&&cached&&Date.now()-cached.at<30000){setBusy(false);setData((old:any)=>preserveCustomRecovery(old,cached.data));modelContext(cached.data);return;}
  setBusy(true);setError('');try{
  const {snapshot_key,cache_token,...previewArgs}=data.draft??{};
  const out=await app.callServerTool(data.draft?(cache_token?{name:'read_project_preview',arguments:{preview:data.draft,kind,offset,controls}}:{name:'prepare_research_workspace',arguments:{...previewArgs,kind,offset}}):data.canonical?{name:'open_project',arguments:{project_id:data.project_id,kind,offset,controls}}:{name:'get_research_workspace',arguments:{project_id:data.project_id,preview_token:data.preview_token,kind,offset}});
  if(serial!==requestSerial.current)return;
  if(out.isError||!out.structuredContent?.result)throw Error();
  if(data.canonical&&offset&&data.view?.version!==undefined&&out.structuredContent.view?.version!==data.view.version){void page(kind,0,undefined,preserveView);return;}
  if(pageCache.current.size>=12)pageCache.current.delete(pageCache.current.keys().next().value!);
  pageCache.current.set(cacheKey,{at:Date.now(),data:out.structuredContent});
  setData((old:any)=>preserveCustomRecovery(old,out.structuredContent));modelContext(out.structuredContent);
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
    if(serial===requestSerial.current&&!out.isError&&out.structuredContent?.result){setData((old:any)=>preserveCustomRecovery(old,out.structuredContent));modelContext(out.structuredContent);}
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
  const out=await app.callServerTool({name:'save_visualization_state',arguments:{report_id:id,expected_version:version,state,...(data.draft?{preview:reportPreview(data.draft)}:{project_id:data.project_id})}});
  if(out.isError||!out.structuredContent?.saved)throw Error();
  const result=out.structuredContent;setData((current:any)=>({...current,report:result.report,reports:current.reports.map((r:any)=>r.id===id?{...r,version:result.report.version,updated_at:result.report.updated_at}:r)}));return result;
 }
 const savingCustom=useRef(false);
 async function requestSave(){
  if(savingCustom.current)return;savingCustom.current=true;setError('');
  try{
   let value=data;
   if(data.retry_id){
    const out=await app.callServerTool({name:'retry_project_report',arguments:{retry_id:data.retry_id}});
    if(out.isError)throw Error('The retained custom view could not be saved. Please retry.');
    value=out.structuredContent;receive(value);
    if(value?.recovery?.action!=='reconcile')return;
   }
   try{await app.updateModelContext({structuredContent:{project_id:data.project_id,preview:data.draft??null,retry_id:value.retry_id,current_context:value.current_context,visualization_save_offer:value.visualization_save_offer}});}catch{/* Optional host context; the explicit message still carries the request. */}
   const reconcile=value.recovery?.action==='reconcile';
   const result=await app.sendMessage({role:'user',content:[{type:'text',text:reconcile?'Reconcile the retained custom view with the current project and latest saved view, then save it in Custom views. Preserve its intended content and check evidence and version changes.':'Save the custom view “'+data.visualization_save_offer?.title+'” in this TrialAgents project using the existing content.'}]});
   if(result.isError)throw Error('Could not send the save request. Ask ChatGPT to save this custom view again.');
  }catch(cause){setError(cause instanceof Error?cause.message:'The save request could not complete.');}finally{savingCustom.current=false;}
 }
 async function createCustom(){
  const prompt='Create a useful custom view for this TrialAgents project using our current question and available data, such as a comparison, visualization, tracker or form. Save it and open it in Custom views.';
  const result=await app.sendMessage({role:'user',content:[{type:'text',text:prompt+' Project: '+data.title+' ('+data.project_id+').'}]});
  if(result.isError)throw Error('Could not confirm delivery');
 }
 async function readReport(id:string){if(data.report?.id===id&&(!data.reports?.find((r:any)=>r.id===id)?.version||data.reports.find((r:any)=>r.id===id).version===data.report.version))return {report:data.report};const out=await app.callServerTool({name:'read_project_report',arguments:{report_id:id,...(data.draft?{preview:reportPreview(data.draft)}:{project_id:data.project_id})}});if(out.isError||!out.structuredContent?.report)throw Error();modelContext({...data,active_report_id:id});return out.structuredContent;}

 if(!data)return <p role="alert">{error}</p>;
 return <><SaveNotice data={data}/>{connectionStatus&&<section aria-label="Account connection" style={{padding:'12px 16px',borderBottom:'1px solid currentColor'}}><p role={connectionError?'alert':'status'}>{connectionStatus}</p>{!busy&&<button onClick={connect}>{handoff.current?'Open account connection':'Retry account connection'}</button>}</section>}<WorkspaceTables surface="extension" data={data} reportsView={reportsView} activeReportId={activeReport} onReports={()=>{setReportsView(true);setDataset(false);}} onCreateCustom={createCustom} onReportRead={readReport} onReportStateSave={saveState} onSaveVisualization={requestSave} onPage={page} onApply={applyView} onRead={readPage} onProfile={profile} onDownload={download} onAccount={connect} onDataset={()=>{setDataset(true);setReportsView(false);}} dataset={dataset} onAccess={access} busy={busy} error={error}/>{retryPage&&<p><button onClick={()=>page(retryPage.kind,retryPage.offset)} disabled={busy}>Retry loading table</button></p>}</>;
}
class WorkspaceBoundary extends React.Component<{children:React.ReactNode},{failed:boolean}>{
 state={failed:false};
 static getDerivedStateFromError(){return {failed:true};}
 render(){return this.state.failed?<section role="alert" style={{padding:24,color:'#182628',background:'#fff',fontFamily:'system-ui'}}><h1>Workspace could not be displayed</h1><p>Please reopen the workspace from the conversation. Your research has not been changed.</p></section>:this.props.children;}
}
let mounted=false;
function receive(data:any){
 if(!data)return;
 if(!data.project_id||!data.result){
  if(data.report_saved===false||data.storage_status==='unavailable'||data.project_save_error){
   if(mounted)setIncoming(data);else if(data.report_saved===false)root.render(<section style={{padding:24}}><h2>Custom views</h2><CustomViewRecovery data={data} onSave={async()=>{const out=await app.callServerTool({name:'retry_project_report',arguments:{retry_id:data.retry_id}});if(out.isError)throw Error();receive(out.structuredContent);if(out.structuredContent?.recovery?.action==='reconcile'){const sent=await app.sendMessage({role:'user',content:[{type:'text',text:'Reconcile and save the retained custom view using the current project and latest version.'}]});if(sent.isError)throw Error();}}}/></section>);else root.render(<SaveNotice data={data}/>);
  }return;
 }
 modelContext(data);if(mounted)setIncoming(data);else{flushSync(()=>root.render(<WorkspaceBoundary><View initial={data}/></WorkspaceBoundary>));mounted=true;}
}
app.ontoolinput=()=>{
 clearStartup();showActivity(mounted?'Updating your workspace…':'Preparing your research…',true);
};
app.ontoolcancelled=()=>{
 clearStartup();showActivity('Operation cancelled. Existing research is unchanged.');
};
app.ontoolresult=result=>{
 clearStartup();const data=result.structuredContent as any;
 if(result.isError){showActivity('This operation could not complete. Check the conversation for details.');return;}
 if(data?.selection_id&&data?.presentation?.tool==='publish_research_workspace'){
  showActivity(data.total_entities===0?'No matching results for this search.':'Search complete. ChatGPT can now review the selection and prepare the tables.');
  return;
 }
 showActivity('');receive(data);
};
let displayRequested=false,displayPending=false;
async function requestWorkspace(ctx:any){
 if(displayRequested||displayPending||ctx?.displayMode==='fullscreen'||!ctx?.availableDisplayModes?.includes('fullscreen'))return;
 displayPending=true;try{await app.requestDisplayMode({mode:'fullscreen'});displayRequested=true;}catch{/* Retry on the next host capability notification. */}finally{displayPending=false;}
}
function theme(ctx:any){if(ctx?.theme)applyDocumentTheme(ctx.theme);if(ctx?.styles?.variables)applyHostStyleVariables(ctx.styles.variables);void requestWorkspace(ctx);}
app.onhostcontextchanged=theme;
async function connectHost(){
 try{await app.connect();theme(app.getHostContext());}
 catch{if(!mounted)root.render(<section className="workspace-loading" role="alert"><strong>TrialAgents</strong><p>The workspace connection was interrupted.</p><button onClick={()=>void connectHost()}>Retry opening workspace</button></section>);}
}
void connectHost();
