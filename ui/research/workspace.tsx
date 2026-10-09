import React,{useState,useRef} from 'react';
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
 try{void Promise.resolve(app.updateModelContext({structuredContent:{project_id:data.project_id,saved:!data.draft,draft:data.draft,revision:data.revision,table:data.result.entity_type,visible_rows:data.result.entities,access:data.result.access_info,selection:data.result.selection_origin??null}})).catch(()=>{});}catch{/* Keep rendered results usable if the host does not support context updates. */}
}
function View({initial}:{initial:any}){
 const [data,setData]=useState(initial),[dataset,setDataset]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(''),[retryPage,setRetryPage]=useState<{kind:WorkspaceKind;offset:number}|null>(null),[connectionError,setConnectionError]=useState(false);
 const [connectionStatus,setConnectionStatus]=useState('');
 const connecting=useRef(false),handoff=useRef<{url:string;expires:number;project:string}|null>(null);
 setIncoming=value=>{setConnectionStatus('');handoff.current=null;setData(value);setDataset(false);setError('');setRetryPage(null);setConnectionError(false);};
 async function page(kind:WorkspaceKind,offset:number){setDataset(false);setError('');setRetryPage(null);setConnectionError(false);
  if(offset===0&&data.preview_tables?.[kind]){const next={...data,result:data.preview_tables[kind]};setData(next);modelContext(next);return;}
  setBusy(true);setError('');try{
  const {snapshot_key,...previewArgs}=data.draft??{};
  const out=await app.callServerTool(data.draft?{name:'prepare_research_workspace',arguments:{...previewArgs,kind,offset}}:{name:'get_research_workspace',arguments:{project_id:data.project_id,preview_token:data.preview_token,kind,offset,revision:data.revision}});
  if(out.isError||!out.structuredContent?.result)throw Error();setData(out.structuredContent);modelContext(out.structuredContent);
 }catch{setRetryPage({kind,offset});setError('This table could not be loaded. Your current results are still shown. Retry, or reopen the preview from the conversation if it has expired.');}finally{setBusy(false);}}
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

 if(!data)return <p role="alert">{error}</p>;
 return <>{connectionStatus&&<section aria-label="Account connection" style={{padding:'12px 16px',borderBottom:'1px solid currentColor'}}><p role={connectionError?'alert':'status'}>{connectionStatus}</p>{!busy&&<button onClick={connect}>{handoff.current?'Open account connection':'Retry account connection'}</button>}</section>}<WorkspaceTables data={data} onPage={page} onAccount={connect} onDataset={()=>setDataset(true)} dataset={dataset} onAccess={access} busy={busy} error={error}/>{retryPage&&<p><button onClick={()=>page(retryPage.kind,retryPage.offset)} disabled={busy}>Retry loading table</button></p>}</>;
}
let mounted=false;
app.ontoolresult=result=>{const data=result.structuredContent;if(!data?.project_id||!data.result)return;
 modelContext(data);if(mounted)setIncoming(data);else{root.render(<View initial={data}/>);mounted=true;}};
function theme(ctx:any){if(ctx?.theme)applyDocumentTheme(ctx.theme);if(ctx?.styles?.variables)applyHostStyleVariables(ctx.styles.variables);}
app.onhostcontextchanged=theme;
app.connect().then(async()=>{const context=app.getHostContext();theme(context);if(context?.displayMode!=='fullscreen'&&context?.availableDisplayModes?.includes('fullscreen')){try{await app.requestDisplayMode({mode:'fullscreen'});}catch{/* Host placement remains authoritative. */}}}).catch(()=>root.render(<p>Use the project link in the conversation to open Intel Agent.</p>));
