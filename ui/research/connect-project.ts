export class ConnectionError extends Error {
 constructor(public code:'navigation'|'handoff'){super(code);}
}
export function connectionUrl(data:any){
 const connected=data.account?.connected===true||data.owned===true;
 const payload=data.draft?{draft:data.draft,account_email:data.account?.email??null}:connected?{project_id:data.project_id,account_email:data.account?.email??null,account_project:true}:{project_id:data.project_id,preview_token:data.preview_token};
 if(!data.draft&&!data.preview_token&&!connected)throw new ConnectionError('handoff');
 const encoded=btoa(Array.from(new TextEncoder().encode(JSON.stringify(payload)),byte=>String.fromCharCode(byte)).join('')).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
 if(encoded.length>180000)throw new ConnectionError('handoff');
 return 'https://intel.trialagents.com/auth?mode=login&connect=1#import='+encoded;
}
export async function openConnection(app:any,url:string,timeout=15000){
 if(!/^https:\/\/intel\.trialagents\.com\/(projects(?:\/settings)?|auth\?mode=login&connect=1#import=[A-Za-z0-9_-]+)$/.test(url))throw new ConnectionError('handoff');
 let timer:ReturnType<typeof setTimeout>;
 try{
  const result:any=await Promise.race([app.openLink({url},{timeout}),new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error('timeout')),timeout);})]);
  if(result?.isError)throw new Error('navigation');
 }catch{throw new ConnectionError('navigation');}finally{clearTimeout(timer!);}
}
// No network/tool call before opening login. Authenticated website imports results.
export async function connectProject(app:any,data:any,onReady:(url:string)=>void=()=>{}){
 const url=connectionUrl(data);onReady(url);await openConnection(app,url);
}

// Invoked only by an explicit Connect click. The host owns OAuth and consent.
export async function connectPreviewAccount(app:any,data:any){
 if(!data.draft?.cache_token)return {status:'website' as const};
 try{
  const out=await app.callServerTool({name:'save_project',arguments:{preview:data.draft}});
  const saved=out.structuredContent;
  if(!out.isError&&saved?.canonical&&saved?.result)return {status:'saved' as const,data:saved};
 }catch{/* Host authorization can be unavailable/cancelled; retain the preview. */}
 return {status:'pending' as const};
}
export async function continueAccountConnection(app:any,data:any){
 // Only the public preview identity enters chat, never cache/preview capabilities.
 const id=data.draft?.preview_id;
 if(typeof id!=='string'||!/^[a-f0-9-]{36}$/i.test(id))throw new ConnectionError('handoff');
 const result=await app.sendMessage({role:'user',content:[{type:'text',text:
  'Connect my TrialAgents account and save the existing preview '+id+' and its Custom views to it. Use the retained preview from this conversation, then reopen the saved workspace with my account access.'}]});
 if(result?.isError)throw new ConnectionError('handoff');
}
