import React,{useState} from 'react';
import {createRoot} from 'react-dom/client';
import {App,applyDocumentTheme,applyHostStyleVariables} from '@modelcontextprotocol/ext-apps';
import {OpenAIExtensions} from '@openai/mcp-extensions/app';
import {WorkspaceTables,type WorkspaceKind} from 'intel-shared-workspace';
import {connectProject} from './connect-project';
const app=new App({name:'Intel Agent workspace',version:'0.2.0'},{availableDisplayModes:['fullscreen']});
new OpenAIExtensions(app);
const root=createRoot(document.querySelector('main')!);
let setIncoming:(data:any)=>void=()=>{};
function modelContext(data:any){
 void app.updateModelContext({structuredContent:{project_id:data.project_id,revision:data.revision,table:data.result.entity_type,visible_rows:data.result.entities,access:data.result.access_info,selection:data.result.selection_origin??null}}).catch(()=>{});
}
function externalUrl(data:any,view?:string){
 const id=data.project_id;if(!/^[a-f0-9-]{36}$/.test(id))throw Error('Invalid project');
 const base='https://intel.trialagents.com/share/research/'+id+(view==='dataset'?'?view=dataset':view==='save'||view==='account'?'?save=1':'');
 return !data.owned&&/^[A-Za-z0-9_-]{43}$/.test(data.preview_token)?base+'#preview='+data.preview_token:base;
}
function View({initial}:{initial:any}){
 const [data,setData]=useState(initial),[busy,setBusy]=useState(false),[error,setError]=useState('');
 setIncoming=value=>{setData(value);setError('');};
 async function page(kind:WorkspaceKind,offset:number){setBusy(true);setError('');try{
  const out=await app.callServerTool({name:'get_research_workspace',arguments:{project_id:data.project_id,preview_token:data.preview_token,kind,offset,revision:data.revision}});
  if(out.isError||!out.structuredContent?.result)throw Error();setData(out.structuredContent);modelContext(out.structuredContent);
 }catch{setData(null);setError('Access changed or this preview expired. Reopen the project from the conversation.');}finally{setBusy(false);}}
 async function external(view?:string){try{await app.openLink({url:externalUrl(data,view)});}catch{setError('Open the project using the link below.');}}
 async function connect(){
  setBusy(true);setError('');
  try{await connectProject(app,data);}catch{setError('Account connection could not start. Please retry Connect account.');}finally{setBusy(false);}
 }

 async function access(){try{await app.openLink({url:'https://intel.trialagents.com/dataset-access'});}catch{setError('About dataset access is available on the Intel Agent website.');}}

 if(!data)return <p role="alert">{error}</p>;
 return <><WorkspaceTables data={data} onPage={page} onAccount={connect} onDataset={()=>external('dataset')} onAccess={access} busy={busy} error={error}/>{error&&<p><button onClick={connect} disabled={busy}>Retry account connection</button></p>}</>;
}
let mounted=false;
app.ontoolresult=result=>{const data=result.structuredContent;if(!data?.project_id||!data.result)return;
 modelContext(data);if(mounted)setIncoming(data);else{root.render(<View initial={data}/>);mounted=true;}};
function theme(ctx:any){if(ctx?.theme)applyDocumentTheme(ctx.theme);if(ctx?.styles?.variables)applyHostStyleVariables(ctx.styles.variables);}
app.onhostcontextchanged=theme;
app.connect().then(async()=>{const context=app.getHostContext();theme(context);if(context?.displayMode!=='fullscreen'&&context?.availableDisplayModes?.includes('fullscreen')){try{await app.requestDisplayMode({mode:'fullscreen'});}catch{/* Host placement remains authoritative. */}}}).catch(()=>root.render(<p>Use the project link in the conversation to open Intel Agent.</p>));
