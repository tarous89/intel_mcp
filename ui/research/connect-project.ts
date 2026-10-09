// Open website authentication directly. Host OAuth remains a separate operation
// for authorizing ChatGPT reads; it must not block website saving/account choice.
export async function connectProject(app:any,data:any){
 if(!/^[a-f0-9-]{36}$/.test(data.project_id))throw Error('Missing project');
 const result=await app.callServerTool({name:'create_research_account_handoff',arguments:{
  project_id:data.project_id,...(data.preview_token?{preview_token:data.preview_token}:{})}});
 const url=result.structuredContent?.url;
 if(result.isError||typeof url!=='string'||!/^https:\/\/intel\.trialagents\.com\/auth\?mode=login&connect=1#handoff=[A-Za-z0-9_-]{43}$/.test(url))throw Error('Connection request was not accepted');
 await app.openLink({url});
}
