import {App,applyDocumentTheme,applyHostStyleVariables} from '@modelcontextprotocol/ext-apps';
const app=new App({name:'TrialAgents next questions',version:'0.5.0'},{availableDisplayModes:['inline']});
const root=document.querySelector('main')!;
let serial=0;
app.ontoolresult=result=>{
 const data=result.structuredContent;if(!data?.questions||data.questions.length!==3)return;
 const current=++serial;root.replaceChildren();
 const title=document.createElement('h2');title.textContent='Explore further';root.append(title);
 const group=document.createElement('div');group.className='questions';group.setAttribute('role','group');group.setAttribute('aria-label','Further investigations');
 const buttons:HTMLButtonElement[]=[];
 const status=document.createElement('p');status.className='status';status.setAttribute('role','status');
 let pending=false;
 for(const question of data.questions){
  const button=document.createElement('button');button.type='button';button.textContent=question;buttons.push(button);
  button.onclick=async()=>{
   if(pending||current!==serial)return;pending=true;buttons.forEach(b=>b.disabled=true);status.textContent='Sending question…';
   try{
    // Keep an older card bound to its original project/preview before requesting analysis.
    await app.updateModelContext({structuredContent:{research_context:data.context,access_scope:data.access_scope}});
    const result=await app.sendMessage({role:'user',content:[{type:'text',text:question}]});
    if(result.isError)throw Error('Host rejected message');
    if(current===serial)status.textContent='Question sent';
   }catch{
    if(current===serial){pending=false;buttons.forEach(b=>b.disabled=false);status.textContent='Could not confirm delivery; check the conversation, or copy a question above into chat.';}
   }
  };
  group.append(button);
 }
 root.append(group);
 const notice=document.createElement('p');notice.className='access-notice';notice.textContent=data.access_notice;root.append(notice,status);
};
function theme(ctx:any){if(ctx?.theme)applyDocumentTheme(ctx.theme);if(ctx?.styles?.variables)applyHostStyleVariables(ctx.styles.variables);}
app.onhostcontextchanged=theme;
app.connect().then(()=>theme(app.getHostContext())).catch(()=>{root.textContent='Ask for three suggested investigations in the conversation.';});
