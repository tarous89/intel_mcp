export class ConnectionError extends Error {
 constructor(public code:'navigation'|'handoff'){super(code);}
}
export function connectionUrl(data:any){
 if(data.owned&&!data.draft)return 'https://intel.trialagents.com/projects';
 const payload=data.draft?{draft:data.draft}:{project_id:data.project_id,preview_token:data.preview_token};
 if(!data.draft&&!data.preview_token)throw new ConnectionError('handoff');
 const encoded=btoa(Array.from(new TextEncoder().encode(JSON.stringify(payload)),byte=>String.fromCharCode(byte)).join('')).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
 if(encoded.length>180000)throw new ConnectionError('handoff');
 return 'https://intel.trialagents.com/auth?mode=login&connect=1#import='+encoded;
}
export async function openConnection(app:any,url:string,timeout=15000){
 if(!/^https:\/\/intel\.trialagents\.com\/(projects|auth\?mode=login&connect=1#import=[A-Za-z0-9_-]+)$/.test(url))throw new ConnectionError('handoff');
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
