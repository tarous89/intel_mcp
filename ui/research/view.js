import {App, applyDocumentTheme, applyHostStyleVariables} from '@modelcontextprotocol/ext-apps';
import {OpenAIExtensions} from '@openai/mcp-extensions/app';
const app=new App({name:'TrialAgents research',version:'0.1.5'},{availableDisplayModes:['inline']});
new OpenAIExtensions(app);
const root=document.querySelector('main');
const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=String(text);if(cls)n.className=cls;return n;};
function safeProjectLink(raw){try{const u=new URL(raw);return u.origin==='https://intel.trialagents.com'&&/^\/research\/projects\/[a-f0-9-]{36}$/i.test(u.pathname)&&!u.search&&!u.hash?u.href:null;}catch{return null;}}
function render(data){
 const view=data?.view;if(!view||!Array.isArray(view.rows)||!Array.isArray(view.columns))return;
 root.replaceChildren();root.append(el('p','TrialAgents · Intel Agent','brand'),el('h2',view.title),el('p',view.summary));
 const table=el('table');table.setAttribute('aria-label',view.title);
 const head=el('thead'),hr=el('tr');view.columns.forEach(label=>hr.append(el('th',label)));head.append(hr);table.append(head);
 const body=el('tbody');
 for(const row of view.rows){const tr=el('tr');row.cells.forEach((value,index)=>{
  const td=el('td');td.append(el('p',value));
  if(row.bar?.column===index){const track=el('div',undefined,'track'),bar=el('div',undefined,'bar');track.setAttribute('aria-hidden','true');bar.style.width=`${Math.max(0,Math.min(100,100*row.bar.value/Math.max(1,row.bar.maximum)))}%`;track.append(bar);td.append(track);}
  if(index===row.cells.length-1&&row.details){const details=el('details');details.append(el('summary',row.details.label),el('p',row.details.text));td.append(details);}
  tr.append(td);
 });body.append(tr);}
 table.append(body);root.append(table);if(!view.rows.length)root.append(el('p','No matching records.'));
 if(view.notice)root.append(el('p',view.notice,'notice'));
 const actions=(view.actions||[]).slice(0,3);
 if(actions.length){root.append(el('h3','Explore more data'));const group=el('div',undefined,'actions'),status=el('p');status.setAttribute('role','status');
  for(const a of actions){const url=a.url?safeProjectLink(a.url):null;if(a.url&&!url)continue;
   const button=el('button',a.label);button.type='button';button.onclick=async()=>{button.disabled=true;status.textContent='';try{
    const response=url?await app.openLink({url}):await app.sendMessage({role:'user',content:[{type:'text',text:a.prompt}]});
    if(response?.isError)throw Error('Host action unavailable');
   }catch{if(url){status.replaceChildren(el('span','Open your saved project: '));const link=el('a',url);link.href=url;link.target='_blank';link.rel='noopener noreferrer';status.append(link);}else status.textContent='Ask in chat: '+a.prompt;}finally{button.disabled=false;}};group.append(button);
  }root.append(group,status);
 }
}
function theme(ctx){if(ctx?.theme)applyDocumentTheme(ctx.theme);if(ctx?.styles?.variables)applyHostStyleVariables(ctx.styles.variables);}
app.ontoolresult=r=>render(r.structuredContent);app.onhostcontextchanged=theme;
app.connect().then(()=>theme(app.getHostContext())).catch(()=>root.replaceChildren(el('p','This host could not initialize the branded view. Use one table in the conversation.')));
