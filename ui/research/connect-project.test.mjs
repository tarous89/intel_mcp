import test from 'node:test';
import assert from 'node:assert/strict';
import {build} from 'esbuild';
const bundle=await build({entryPoints:[new URL('./connect-project.ts',import.meta.url).pathname],bundle:true,write:false,format:'esm',platform:'node'});
const {connectProject}=await import('data:text/javascript;base64,'+Buffer.from(bundle.outputFiles[0].text).toString('base64'));
const data={project_id:'00000000-0000-0000-0000-000000000001',preview_token:'a'.repeat(43)};
test('connect carries the exact existing project into host OAuth and save request',async()=>{
 const calls=[];
 await connectProject({updateModelContext:async p=>calls.push(['context',p]),sendMessage:async p=>{calls.push(['message',p]);return {}; }},data);
 assert.equal(calls[0][0],'context');
 assert.deepEqual(calls[0][1].structuredContent.connect_and_save.arguments,data);
 const text=calls[1][1].content[0].text;
 assert(text.includes('claim_research_workspace'));assert(text.includes(data.project_id));
 assert(!text.includes(data.preview_token));assert(text.includes('only after the tool succeeds'));
});
test('rejected connection or missing capability never reports success',async()=>{
 await assert.rejects(connectProject({updateModelContext:async()=>{},sendMessage:async()=>({isError:true})},data));
 await assert.rejects(connectProject({}, {...data,preview_token:undefined}));
});
