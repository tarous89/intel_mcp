import test from 'node:test';
import assert from 'node:assert/strict';
import {build} from 'esbuild';
const bundle=await build({entryPoints:[new URL('./connect-project.ts',import.meta.url).pathname],bundle:true,write:false,format:'esm',platform:'node'});
const {connectProject}=await import('data:text/javascript;base64,'+Buffer.from(bundle.outputFiles[0].text).toString('base64'));
const data={project_id:'00000000-0000-0000-0000-000000000001',preview_token:'a'.repeat(43)};
const url='https://intel.trialagents.com/auth?mode=login&connect=1#handoff='+'b'.repeat(43);
for(const owned of [false,true])test(`connect opens website auth directly (owned=${owned})`,async()=>{
 const calls=[];
 await connectProject({callServerTool:async p=>{calls.push(['tool',p]);return {structuredContent:{url}};},openLink:async p=>calls.push(['open',p])},{...data,owned,...(owned?{preview_token:undefined}:{})});
 assert.equal(calls[0][1].name,'create_research_account_handoff');assert.equal(calls[0][1].arguments.project_id,data.project_id);
 assert.deepEqual(calls[1],['open',{url}]);assert.equal(calls.length,2);
});
test('failed or untrusted handoff never opens a URL',async()=>{
 for(const result of [{isError:true},{structuredContent:{url:'https://evil.invalid/'}},{structuredContent:{url:url+'&extra=1'}}]){
  await assert.rejects(connectProject({callServerTool:async()=>result,openLink:()=>assert.fail('must not open')},data));
 }
});

test('unsaved preview is passed only on the explicit Connect action',async()=>{
 const draft={selection_id:'s'.repeat(43),title:'Same results',snapshot_key:'a'.repeat(64)};
 let request;
 await connectProject({callServerTool:async p=>{request=p;return {structuredContent:{url}};},openLink:async()=>{}},{project_id:data.project_id,draft});
 assert.deepEqual(request.arguments,{project_id:data.project_id,draft});
});

test('host navigation refusal is reported and private handoff retained for retry',async()=>{
 let ready;
 await assert.rejects(connectProject({callServerTool:async()=>({structuredContent:{url}}),openLink:async()=>({isError:true})},data,value=>ready=value),error=>error.code==='navigation');
 assert.equal(ready,url);
});
test('stalled tool times out without opening or accepting a late handoff',async()=>{
 let resolve;
 const pending=new Promise(r=>resolve=r);
 await assert.rejects(connectProject({callServerTool:()=>pending,openLink:()=>assert.fail('must not open')},data,()=>assert.fail('late URL'),5),error=>error.code==='timeout');
 resolve({structuredContent:{url}});
 await new Promise(r=>setTimeout(r,0));
});
test('expired source is distinguished from tool rejection',async()=>{
 await assert.rejects(connectProject({callServerTool:async()=>({isError:true,content:[{type:'text',text:'SELECTION_EXPIRED'}]})},data),error=>error.code==='expired');
});
