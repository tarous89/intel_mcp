import React,{useState} from 'react';
import {createRoot} from 'react-dom/client';
import {App,applyDocumentTheme,applyHostStyleVariables} from '@modelcontextprotocol/ext-apps';
import {OpenAIExtensions} from '@openai/mcp-extensions/app';
import {WorkspaceTables,type WorkspaceKind} from 'intel-shared-workspace';
const app=new App({name:'Intel Agent workspace',version:'0.2.0'},{availableDisplayModes:['inline','fullscreen']});
new OpenAIExtensions(app);
const root=createRoot(document.querySelector('main')!);
let setIncoming:(data:any)=>void=()=>{};
function modelContext(data:any){
 void app.updateModelContext({structuredContent:{project_id:data.project_id,revision:data.revision,table:data.result.entity_type,visible_rows:data.result.entities,access:data.result.access_info,selection:data.result.selection_origin??null}}).catch(()=>{});
}
function externalUrl(data:any){
 const id=data.project_id;if(!/^[a-f0-9-]{36}$/.test(id))throw Error('Invalid project');
 const base='https://intel.trialagents.com/research/workspaces/'+id;
 return !data.owned&&/^[A-Za-z0-9_-]{43}$/.test(data.preview_token)?base+'#preview='+data.preview_token:base;
}
function View({initial}:{initial:any}){
 const [data,setData]=useState(initial),[busy,setBusy]=useState(false),[error,setError]=useState('');
 setIncoming=value=>{setData(value);setError('');};
 async function page(kind:WorkspaceKind,offset:number){setBusy(true);setError('');try{
  const out=await app.callServerTool({name:'get_research_workspace',arguments:{project_id:data.project_id,preview_token:data.preview_token,kind,offset,revision:data.revision}});
  if(out.isError||!out.structuredContent?.result)throw Error();setData(out.structuredContent);modelContext(out.structuredContent);
 }catch{setData(null);setError('Access changed or this preview expired. Reopen the project from the conversation.');}finally{setBusy(false);}}
 async function external(){try{await app.openLink({url:externalUrl(data)});}catch{setError('Open the project using the link below.');}}
 async function expand(){if(app.getHostContext()?.availableDisplayModes?.includes('fullscreen')){try{const mode=await app.requestDisplayMode({mode:'fullscreen'});if(mode.mode==='fullscreen')return;}catch{}}await external();}
 async function claim(){try{await app.sendMessage({role:'user',content:[{type:'text',text:`Save research workspace ${data.project_id} to my connected TrialAgents account using claim_research_workspace and the preview token already returned. Preserve this project and use my existing access.`}]});}catch{setError('Ask in chat to save this research workspace to your account.');}}
 if(!data)return <p role="alert">{error}</p>;
 return <><WorkspaceTables data={data} onPage={page} onClaim={claim} onExpand={expand} onExternal={external} busy={busy} error={error}/>{error&&<p><a href={externalUrl(data)} target="_blank" rel="noopener noreferrer">Open in Intel Agent</a></p>}</>;
}
let mounted=false;
app.ontoolresult=result=>{const data=result.structuredContent;if(!data?.project_id||!data.result)return;
 modelContext(data);if(mounted)setIncoming(data);else{root.render(<View initial={data}/>);mounted=true;}};
function theme(ctx:any){if(ctx?.theme)applyDocumentTheme(ctx.theme);if(ctx?.styles?.variables)applyHostStyleVariables(ctx.styles.variables);}
app.onhostcontextchanged=theme;
app.connect().then(()=>theme(app.getHostContext())).catch(()=>root.render(<p>Use the project link in the conversation to open Intel Agent.</p>));
