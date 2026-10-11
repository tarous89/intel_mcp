import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,mkdir} from 'node:fs/promises';
import {chromium} from 'playwright';
const metrics={therapeuticAreaTrials:12,recentActivityTrials:3,sponsors:[{name:'Example sponsor',trials:2}],evidence:[]};
const rows={sites:{id:'site',rank:1,name:'Example hospital',country:'DE',contact:{name:'Example contact',email:'contact@example.test'},metrics},pis:{id:'pi',rank:1,name:'Example investigator',department:'Oncology department',email:'pi@example.test',sites:[{id:'site',name:'Example hospital',country:'DE',trials:12}],metrics},cros:{id:'cro',rank:1,name:'Example CRO',country:'DE',trialCount:12,functionCounts:{1:3},organisationTypes:[],sourceNames:[],unresolvedFunctions:[]},trials:{id:'2026-000001-00-00',title:'Example trial',phase:[3],status:'Recruiting',countries:['DE'],subgroups:[],listedSiteCount:4}};
const pages=Object.fromEntries(Object.entries(rows).map(([kind,row])=>[kind,{entity_type:kind,entities:[{...row,workspace_row:row}],returned:1,total_entities:50,next_offset:null,access_info:{offset:0},cohort:{counts:{base:12}},ranking_criteria:{therapeutic_areas:[],disease_terms:[],countries:[]}}]));
const data={project_id:'synthetic-project',title:'Research workspace',draft:{cache_token:'synthetic'},tables:Object.keys(pages).map(kind=>({kind,total:50})),preview_tables:pages,result:pages.pis,reports:[{id:'report-1',title:'Protocol comparison',summary:'Evidence comparison from the accessible preview.',access_scope:'preview',created_at:'2026-10-11T12:00:00Z'}]};
test('shipped workspace has compact controls and reachable rightmost columns',async()=>{
 await mkdir('/tmp/workspace-design',{recursive:true});
 const browser=await chromium.launch({headless:true});
 try{
 const html=await readFile(new URL('../../src/intel_mcp/ui/workspace-v1.html',import.meta.url),'utf8');
 for(const width of [1280,760,420]){
  const page=await browser.newPage({viewport:{width,height:900}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(data=>{
   window.postMessage=msg=>{let result;if(msg.method==='ui/initialize')result={protocolVersion:'2026-01-26',hostInfo:{name:'Browser fixture',version:'1'},hostCapabilities:{},hostContext:{theme:'light',displayMode:'fullscreen'}};else if(msg.method==='ui/notifications/initialized'){setTimeout(()=>window.dispatchEvent(new MessageEvent('message',{source:window,data:{jsonrpc:'2.0',method:'ui/notifications/tool-result',params:{structuredContent:data}}})),0);return;}else if(msg.method==='tools/call'&&msg.params.name==='open_project_report')result={structuredContent:{report:{id:'report-1',title:'Protocol comparison',query:'How do endpoints differ?',access_scope:'preview',revision:1,created_at:'2026-10-11T12:00:00Z',html:'<h1>Evidence comparison</h1><p>Accessible preview evidence.</p>'}}};else if(msg.id!==undefined)result={};else return;setTimeout(()=>window.dispatchEvent(new MessageEvent('message',{source:window,data:{jsonrpc:'2.0',id:msg.id,result}})),0);};
  },data);
  await page.route('https://synthetic.invalid/',r=>r.fulfill({contentType:'text/html',body:html}));await page.goto('https://synthetic.invalid/');
  await page.getByRole('button',{name:'Connect account',exact:true}).waitFor();
  assert(await page.locator('.workspace-brand img').evaluate(img=>img.complete&&img.naturalWidth>0),'Embedded brand mark must render without a network request');
  assert.equal(await page.getByRole('button',{name:'Export Excel',exact:true}).count(),0);
  assert.equal(await page.getByRole('button',{name:/Dataset/}).count(),0);
  assert.equal(await page.getByRole('button',{name:/^(Previous|Next)$/}).count(),0);
  for(const label of ['Sites','PIs','CROs','Trials']){
   await page.locator('nav[aria-label="Project tables"] button').filter({hasText:label}).click();
   await page.locator('[class*="tableViewport"]').waitFor();
   await page.locator('[class*="tableViewport"]').evaluate(v=>v.scrollLeft=0);
   await page.screenshot({path:`/tmp/workspace-design/${width}-${label}.png`,fullPage:true});
   const headers=await page.locator('[class*="listHeader"]').innerText();assert(!headers.includes('Recent activity'));assert(!headers.includes('Department'));
   const footer=await page.locator('.workspace-access').boundingBox();assert(footer.y>=0&&footer.y+footer.height<=900,`${width}/${label}: access banner outside viewport`);
   const dims=await page.locator('[class*="tableViewport"]').evaluate(v=>{v.scrollLeft=v.scrollWidth;const b=v.querySelector('article button:last-child');return {edge:b.getBoundingClientRect().right,viewport:v.getBoundingClientRect().right,body:document.documentElement.scrollWidth,width:innerWidth};});
   assert(dims.edge<=dims.viewport+2,`${width}/${label}: rightmost button clipped ${JSON.stringify(dims)}`);assert(dims.body<=dims.width+2,`${width}/${label}: page overflow`);
  }
  await page.locator('nav button').filter({hasText:'PIs'}).click();await page.getByRole('button',{name:'Insights',exact:true}).click();assert(await page.getByText('Department: Oncology department').isVisible());assert(await page.getByText('Recent activity',{exact:true}).isVisible());
  await page.getByRole('button',{name:'Filters',exact:true}).click();assert(await page.getByLabel('Rank by').isVisible());
  if(width===1280)await page.screenshot({path:process.env.UX_SCREENSHOT??'/tmp/workspace-ux.png',fullPage:true});
  await page.locator('nav button').filter({hasText:'Reports'}).click();
  await page.getByRole('button',{name:/Protocol comparison/}).click();
  await page.frameLocator('iframe[title="Protocol comparison"]').getByRole('heading',{name:'Evidence comparison'}).waitFor();
  assert(await page.getByText('How do endpoints differ?',{exact:false}).isVisible());
  assert.equal(await page.locator('iframe').getAttribute('sandbox'),'');
  assert(await page.locator('.workspace-access').isVisible());
  const footer=await page.locator('.workspace-access').boundingBox();assert(footer.y>=0&&footer.y+footer.height<=900,`${width}/Reports: banner outside viewport`);
  assert.equal(await page.locator('nav[aria-label="Project tables"] button').count(),5);
  await page.screenshot({path:`/tmp/workspace-design/${width}-reports.png`,fullPage:true});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));
  assert.deepEqual(errors,[]);await page.close();
 }
 }finally{await browser.close();}
});
