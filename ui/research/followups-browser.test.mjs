import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {chromium} from 'playwright';
const questions=['Which services are most often recorded for these CROs?','How does country coverage differ across the broader cohort?','What operational findings occur in their associated trials?'];
const html=await readFile(new URL('../../src/intel_mcp/ui/followups.html',import.meta.url),'utf8');
for(const mode of ['success','denied','missing-context'])test('follow-up buttons: '+mode,async()=>{
 const browser=await chromium.launch({headless:true});
 try{for(const width of [1280,420]){
 const page=await browser.newPage({viewport:{width,height:650}});
 await page.addInitScript(({mode,questions})=>{
  window.__sent=[];window.__contexts=[];
  window.postMessage=msg=>{
   let result={};
   if(msg.method==='ui/initialize')result={protocolVersion:'2026-01-26',hostInfo:{name:'Fixture',version:'1'},hostCapabilities:{},hostContext:{theme:'light',displayMode:'inline'}};
   else if(msg.method==='ui/notifications/initialized'){setTimeout(()=>window.dispatchEvent(new MessageEvent('message',{source:window,data:{jsonrpc:'2.0',method:'ui/notifications/tool-result',params:{structuredContent:{questions,context:{project_id:'original-project',revision:2},access_scope:'preview',access_notice:'Preview: up to 10 trials; connect your account to use existing full access.'}}}})),0);return;}
   else if(msg.method==='ui/update-model-context'){window.__contexts.push(msg.params);if(mode==='missing-context'){setTimeout(()=>window.dispatchEvent(new MessageEvent('message',{source:window,data:{jsonrpc:'2.0',id:msg.id,error:{code:-32601,message:'Unsupported'}}})),0);return;}}
   else if(msg.method==='ui/message'){window.__sent.push(msg.params);result={isError:mode==='denied'};}
   else if(msg.id===undefined)return;
   setTimeout(()=>window.dispatchEvent(new MessageEvent('message',{source:window,data:{jsonrpc:'2.0',id:msg.id,result}})),0);
  };
 },{mode,questions});
 await page.route('https://test.invalid/',r=>r.fulfill({contentType:'text/html',body:html}));await page.goto('https://test.invalid/');
 await page.getByRole('button',{name:questions[0],exact:true}).waitFor();
 assert.equal(await page.getByRole('button').count(),3);
 assert.deepEqual(await page.evaluate(()=>window.__sent),[]);
 await page.getByRole('button',{name:questions[1],exact:true}).click();
 if(mode==='success'){
  await page.getByRole('status').filter({hasText:'Question sent'}).waitFor();
  assert.equal((await page.evaluate(()=>window.__sent)).length,1);
  assert.equal(await page.evaluate(()=>window.__sent[0].content[0].text),questions[1]);
  assert.equal(await page.evaluate(()=>window.__contexts[0].structuredContent.research_context.project_id),'original-project');
  assert(await page.getByRole('button',{name:questions[1],exact:true}).isDisabled());
 }else{
  await page.getByRole('status').filter({hasText:'copy a question'}).waitFor();
  assert.equal((await page.evaluate(()=>window.__sent)).length,mode==='denied'?1:0);
  assert(!(await page.getByRole('button',{name:questions[1],exact:true}).isDisabled()));
 }
 assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 await page.close();
 }}finally{await browser.close();}
});
