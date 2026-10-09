const trustedHandoff=/^https:\/\/intel\.trialagents\.com\/auth\?mode=login&connect=1#handoff=[A-Za-z0-9_-]{43}$/;
export class ConnectionError extends Error {
 constructor(public code:'timeout'|'expired'|'handoff'|'navigation'){super(code);}
}
// Bound the wait even if a host implementation ignores SDK request options.
async function bounded<T>(request:Promise<T>,ms:number):Promise<T>{
 let timer:ReturnType<typeof setTimeout>;
 try{return await Promise.race([request,new Promise<never>((_,reject)=>{timer=setTimeout(()=>reject(new ConnectionError('timeout')),ms);})]);}
 finally{clearTimeout(timer!);}
}
export async function openConnection(app:any,url:string,timeout=15000){
 if(!trustedHandoff.test(url))throw new ConnectionError('handoff');
 try{const result=await bounded<any>(app.openLink({url},{timeout}),timeout);
  if(result?.isError)throw new ConnectionError('navigation');
 }catch{throw new ConnectionError('navigation');}
}
// Called only by an explicit user click. Saving stays a write operation.
export async function connectProject(app:any,data:any,onReady:(url:string)=>void=()=>{},timeout=30000){
 if(!/^[a-f0-9-]{36}$/.test(data.project_id))throw new ConnectionError('handoff');
 let result:any;
 try{result=await bounded(app.callServerTool({name:'create_research_account_handoff',arguments:{
  project_id:data.project_id,...(data.draft?{draft:data.draft}:{}),...(data.preview_token?{preview_token:data.preview_token}:{})}},
  {timeout,resetTimeoutOnProgress:false}),timeout);
 }catch(error){if(error instanceof ConnectionError)throw error;throw new ConnectionError('handoff');}
 if(result?.isError){
  const message=(result.content??[]).filter((c:any)=>c.type==='text').map((c:any)=>c.text).join(' ');
  throw new ConnectionError(/SELECTION_EXPIRED|PREVIEW_CHANGED/.test(message)?'expired':'handoff');
 }
 const url=result?.structuredContent?.url;
 if(typeof url!=='string'||!trustedHandoff.test(url))throw new ConnectionError('handoff');
 // Keep this private URL in UI memory so navigation retries never save again.
 onReady(url);
 await openConnection(app,url);
}
