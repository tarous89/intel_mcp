import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {JSDOM,VirtualConsole} from 'jsdom';
// Execute the shipped artifact; only the host transport is simulated.
test('shipped workspace renders all tables after the host handshake',async t=>{
 const errors=[],vc=new VirtualConsole();
 vc.on('jsdomError',e=>{if(e.type!=='css parsing')errors.push(e.message);});vc.on('error',e=>errors.push(String(e)));
 const html=await readFile(new URL('../../src/intel_mcp/ui/workspace-v1.html',import.meta.url),'utf8');
 const pages=Object.fromEntries(['sites','pis','cros','trials'].map(kind=>[kind,{entity_type:kind,entities:[],returned:0,total_entities:0,next_offset:null,access_info:{offset:0},cohort:{counts:{base:1},source_scope:'Synthetic regression fixture'}}]));
 const data={project_id:'00000000-0000-4000-8000-000000000001',title:'Bundle rendering regression',draft:{cache_token:'synthetic'},tables:Object.keys(pages).map(kind=>({kind,total:0})),preview_tables:pages,result:pages.pis};
 const dom=new JSDOM(html,{url:'https://synthetic.invalid',runScripts:'dangerously',pretendToBeVisual:true,virtualConsole:vc,beforeParse(w){
  w.TextEncoder=TextEncoder;w.TextDecoder=TextDecoder;
  w.ResizeObserver=class{observe(){}disconnect(){}};
  w.postMessage=msg=>{if(msg.method==='ui/initialize')setTimeout(()=>w.dispatchEvent(new w.MessageEvent('message',{source:w,data:{jsonrpc:'2.0',id:msg.id,result:{protocolVersion:'2026-01-26',hostInfo:{name:'Regression host',version:'1'},hostCapabilities:{},hostContext:{theme:'light',displayMode:'fullscreen'}}}})),0);
   else if(msg.method==='ui/notifications/initialized')setTimeout(()=>w.dispatchEvent(new w.MessageEvent('message',{source:w,data:{jsonrpc:'2.0',method:'ui/notifications/tool-result',params:{structuredContent:data}}})),0);
   else if(msg.id!==undefined)setTimeout(()=>w.dispatchEvent(new w.MessageEvent('message',{source:w,data:{jsonrpc:'2.0',id:msg.id,result:{}}})),0);
  };
 }});
 t.after(()=>dom.window.close());await new Promise(r=>setTimeout(r,250));
 assert.deepEqual(errors,[],'the shipped bundle must not crash');
 assert.match(dom.window.document.querySelector('main').textContent,/Bundle rendering regression/);
 for(const label of ['Sites','PIs','CROs','Trials']){
  const button=[...dom.window.document.querySelectorAll('nav button')].find(b=>b.textContent.startsWith(label));
  assert(button,`${label} tab renders`);button.click();await new Promise(r=>setTimeout(r,30));assert.match(dom.window.document.querySelector('main').textContent,/Filters/);
 }
 assert.deepEqual(errors,[]);
});
