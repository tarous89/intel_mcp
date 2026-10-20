import test from 'node:test';
import assert from 'node:assert/strict';
import {build} from 'esbuild';
const bundle=await build({entryPoints:[new URL('./connect-project.ts',import.meta.url).pathname],bundle:true,write:false,format:'esm',platform:'node'});
const {projectsUrl,connectProject,connectionUrl,openConnection,connectPreviewAccount,continueAccountConnection}=await import('data:text/javascript;base64,'+Buffer.from(bundle.outputFiles[0].text).toString('base64'));
const draft={preview_id:'00000000-0000-0000-0000-000000000001',title:'Sites — München',selection_id:'s'.repeat(43),snapshot_key:'a'.repeat(64)};
test('Connect opens sign-in immediately without invoking a write tool',async()=>{
 let opened,ready;const host={callServerTool:()=>assert.fail('No tool before login'),openLink:args=>{opened=args.url;return Promise.resolve({});}};
 const pending=connectProject(host,{draft},url=>ready=url);
 assert.equal(opened,ready,'navigation happens before the first await');await pending;
 const encoded=new URL(opened).hash.slice('#import='.length);
 assert.deepEqual(JSON.parse(Buffer.from(encoded,'base64url').toString()),{draft,account_email:null});
});
test('saved account opens Projects; connected unsaved preview imports before opening Projects',()=>{
 const url=connectionUrl({owned:true,project_id:draft.preview_id,account:{email:'owner@example.test'}});
 assert.deepEqual(JSON.parse(Buffer.from(new URL(url).hash.slice(8),'base64url').toString()),{project_id:draft.preview_id,account_email:'owner@example.test',account_project:true});
 assert(connectionUrl({draft,account:{connected:true,fullAccess:false}}).includes('#import='));
 assert(connectionUrl({project_id:draft.preview_id,preview_token:'a'.repeat(43)}).includes('#import='));
});
test('navigation denial and timeout are visible; external URLs rejected',async()=>{
 await assert.rejects(connectProject({openLink:async()=>({isError:true})},{draft}),e=>e.code==='navigation');
 await assert.rejects(openConnection({openLink:()=>new Promise(()=>{})},connectionUrl({draft}),5),e=>e.code==='navigation');
 await assert.rejects(openConnection({openLink:()=>assert.fail()},'https://evil.invalid'),e=>e.code==='handoff');
});

test('explicit connection saves exact preview and accepts only verified workspace state',async()=>{
 const data={draft:{...draft,cache_token:'sensitive-capability',snapshot_key:'a'.repeat(64)}};
 const before=JSON.stringify(data);let call;
 const saved={canonical:true,result:{entities:[]},project_id:draft.preview_id};
 assert.deepEqual(await connectPreviewAccount({callServerTool:async x=>{call=x;return {structuredContent:saved}}},data),{status:'saved',data:saved});
 assert.deepEqual(call,{name:'save_project',arguments:{preview:data.draft,kind:'cros'}});
 assert.equal(JSON.stringify(data),before);
 for(const host of [{callServerTool:async()=>({isError:true})},{callServerTool:async()=>{throw Error('cancelled')}},{callServerTool:async()=>({structuredContent:{saved:true}})}]){
  assert.deepEqual(await connectPreviewAccount(host,data),{status:'pending'});
 }
 assert.deepEqual(await connectPreviewAccount({callServerTool:()=>assert.fail()},{}),{status:'website'});
});
test('chat continuation contains identity only and never preview capabilities',async()=>{
 let message;const data={draft:{...draft,cache_token:'SECRET',preview_token:'SECRET2'}};
 await continueAccountConnection({sendMessage:async m=>{message=m;return {}}},data);
 const text=JSON.stringify(message);assert(text.includes(draft.preview_id));assert(!text.includes('SECRET'));assert(!text.includes(draft.selection_id));
 await assert.rejects(continueAccountConnection({sendMessage:async()=>({isError:true})},data));
});

test('saved connection carries only an editable email hint in the URL fragment',async()=>{
 const email='linked+trial@example.test';
 const url=projectsUrl({account:{connected:true,email}});
 assert.equal(url,'https://intel.trialagents.com/projects#account_email=linked%2Btrial%40example.test');
 assert.equal(new URL(url).search,'');
 let opened;await openConnection({openLink:async value=>{opened=value.url;}},url);assert.equal(opened,url);
 for(const data of [{},{account:{}},{account:{email:'not an email'}},{account:{email:'a'.repeat(255)+'@example.test'}}])assert.equal(projectsUrl(data),'https://intel.trialagents.com/projects');
 for(const bad of [url+'&redirect=https://evil.invalid',url+'/anything','https://intel.trialagents.com.evil.invalid/projects'])await assert.rejects(openConnection({openLink:()=>assert.fail()},bad));
});
