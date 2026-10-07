import {App, applyDocumentTheme, applyHostStyleVariables} from '@modelcontextprotocol/ext-apps';
import {OpenAIExtensions} from '@openai/mcp-extensions/app';
const app = new App({name:'TrialAgents experience',version:'0.1.3'},{availableDisplayModes:['inline']});
new OpenAIExtensions(app);
const root=document.querySelector('main');
const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=String(text);if(cls)n.className=cls;return n;};
function render(data){
 if(!data || !Array.isArray(data.entities))return;
 root.replaceChildren();
 const total=data.cohort?.counts?.base ?? 0;
 root.append(el('p','TRIALAGENTS · RECORDED EXPERIENCE','eyebrow'),el('h2',`${total} trials · ${data.total_entities} matching results`),el('p','Distinct trials in this selected cohort. Recorded participation does not establish current capacity.','muted'));
 const table=el('table'); const caption=el('caption','Partner experience across the full cohort');table.append(caption);
 const head=el('tr');for(const label of ['Partner','Trial experience','Functions / affiliations'])head.append(el('th',label));table.append(el('thead'));table.tHead.append(head);const body=el('tbody');
 const max=Math.max(1,...data.entities.map(e=>e.trial_counts?.total||0));
 for(const e of data.entities){const tr=el('tr');tr.append(el('td',`${e.rank}. ${e.name}`));const td=el('td');td.append(el('span',`${e.trial_counts.total} / ${total}`));const track=el('div',undefined,'track'),bar=el('div',undefined,'bar');bar.style.width=`${Math.max(0,Math.min(100,e.trial_counts.total/max*100))}%`;track.setAttribute('aria-hidden','true');track.append(bar);td.append(track);tr.append(td);
 const roles=[...new Set((e.evidence||[]).flatMap(t=>t.roles||[]))];const details=roles.length?roles.join('; '):(e.affiliations||[]).map(a=>a.name).join('; ')||'No role details recorded';tr.append(el('td',details+' · '+(e.countries||[]).join(', ')));body.append(tr);}
 table.append(body);root.append(table,el('p',data.access_info?.message||'','notice'));
 root.append(el('p','Explore supporting studies, refine by country or trial type, or ask to check existing account access to the full list.','muted'));
}
function theme(ctx){if(ctx?.theme)applyDocumentTheme(ctx.theme);if(ctx?.styles?.variables)applyHostStyleVariables(ctx.styles.variables);}
app.ontoolresult=r=>render(r.structuredContent);
app.onhostcontextchanged=theme;
app.connect().then(()=>theme(app.getHostContext())).catch(()=>{root.replaceChildren(el('p','Use the table in the conversation. This host could not initialize the inline view.'));});
