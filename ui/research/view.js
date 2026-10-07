import {App, applyDocumentTheme, applyHostStyleVariables} from '@modelcontextprotocol/ext-apps';
import {OpenAIExtensions} from '@openai/mcp-extensions/app';
const app = new App({name:'TrialAgents experience',version:'0.1.4'},{availableDisplayModes:['inline']});
new OpenAIExtensions(app);
const root=document.querySelector('main');
const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=String(text);if(cls)n.className=cls;return n;};
function render(data){
 if(!data || !Array.isArray(data.entities))return;
 root.replaceChildren();
 const total=data.cohort?.counts?.base ?? 0;
 const label={cros:'CROs and providers',sites:'Trial sites',pis:'Principal investigators'}[data.entity_type]||'Trial partners';
 root.append(el('h2',label));
 const first=data.entities[0];
 const summary=first ? `Showing ${data.returned} of ${data.total_entities} matching results. ${first.name} has the most recorded experience in this selection, with ${first.trial_counts.total} distinct trials.` : 'No matching entities were recorded in this selection.';
 root.append(el('p',summary));
 const table=el('table'); table.setAttribute('aria-label',label+' trial experience');
 const head=el('tr');for(const label of ['Partner','Trial experience','Functions / affiliations'])head.append(el('th',label));table.append(el('thead'));table.tHead.append(head);const body=el('tbody');
 const max=Math.max(1,...data.entities.map(e=>e.trial_counts?.total||0));
 for(const e of data.entities){const tr=el('tr');tr.append(el('td',`${e.rank}. ${e.name}`));const td=el('td');td.append(el('span',`${e.trial_counts.total} / ${total}`));const track=el('div',undefined,'track'),bar=el('div',undefined,'bar');bar.style.width=`${Math.max(0,Math.min(100,e.trial_counts.total/max*100))}%`;track.setAttribute('aria-hidden','true');track.append(bar);td.append(track);tr.append(td);
 const roles=[...new Set((e.evidence||[]).flatMap(t=>t.roles||[]))];const details=roles.length?roles.join('; '):(e.affiliations||[]).map(a=>a.name).join('; ')||'No role details recorded';tr.append(el('td',details+' · '+(e.countries||[]).join(', ')));body.append(tr);}
 table.append(body);root.append(table);
 if(data.show_access_notice!==false)root.append(el('p',data.access_info?.message||'','notice'));
 if(data.show_followups!==false){
  root.append(el('h3','Explore further'));
  const actions=el('div',undefined,'actions');
  const add=(label,prompt)=>{const button=el('button',label);button.type='button';button.onclick=async()=>{button.disabled=true;try{const result=await app.sendMessage({role:'user',content:[{type:'text',text:prompt}]});if(result?.isError)throw new Error('Message unavailable');}catch{status.textContent='Ask in chat: '+prompt;}finally{button.disabled=false;}};actions.append(button);};
  const status=el('p');status.setAttribute('role','status');
  if(first)add('Supporting studies',`Show the recorded supporting studies and roles for entity ID ${first.id} in the current ${label.toLowerCase()} selection.`);
  add('Refine by country',`Help me refine this ${label.toLowerCase()} selection by country. Ask which country I want, then keep the same clinical criteria.`);
  if(data.access_info?.has_more)add('Check full-list access',`Check whether my connected TrialAgents account has an existing eligible project covering this cohort for the full ${label.toLowerCase()} list. Explain the access requirement before connecting.`);
  root.append(actions,status);
 }

}
function theme(ctx){if(ctx?.theme)applyDocumentTheme(ctx.theme);if(ctx?.styles?.variables)applyHostStyleVariables(ctx.styles.variables);}
app.ontoolresult=r=>render(r.structuredContent);
app.onhostcontextchanged=theme;
app.connect().then(()=>theme(app.getHostContext())).catch(()=>{root.replaceChildren(el('p','Use the table in the conversation. This host could not initialize the inline view.'));});
