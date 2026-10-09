import test from 'node:test';
import assert from 'node:assert/strict';
import {build} from 'esbuild';
const bundle=await build({entryPoints:[new URL('./connect-project.ts',import.meta.url).pathname],bundle:true,write:false,format:'esm',platform:'node'});
const {connectProject,connectionUrl,openConnection}=await import('data:text/javascript;base64,'+Buffer.from(bundle.outputFiles[0].text).toString('base64'));
const draft={preview_id:'00000000-0000-0000-0000-000000000001',title:'Sites — München',selection_id:'s'.repeat(43),snapshot_key:'a'.repeat(64)};
test('Connect opens sign-in immediately without invoking a write tool',async()=>{
 let opened,ready;const host={callServerTool:()=>assert.fail('No tool before login'),openLink:args=>{opened=args.url;return Promise.resolve({});}};
 const pending=connectProject(host,{draft},url=>ready=url);
 assert.equal(opened,ready,'navigation happens before the first await');await pending;
 const encoded=new URL(opened).hash.slice('#import='.length);
 assert.deepEqual(JSON.parse(Buffer.from(encoded,'base64url').toString()),{draft});
});
test('owned project opens Projects and legacy preview retains its capability',()=>{
 assert.equal(connectionUrl({owned:true}),'https://intel.trialagents.com/projects');
 assert(connectionUrl({project_id:draft.preview_id,preview_token:'a'.repeat(43)}).includes('#import='));
});
test('navigation denial and timeout are visible; external URLs rejected',async()=>{
 await assert.rejects(connectProject({openLink:async()=>({isError:true})},{draft}),e=>e.code==='navigation');
 await assert.rejects(openConnection({openLink:()=>new Promise(()=>{})},connectionUrl({draft}),5),e=>e.code==='navigation');
 await assert.rejects(openConnection({openLink:()=>assert.fail()},'https://evil.invalid'),e=>e.code==='handoff');
});
