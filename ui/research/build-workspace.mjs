import {createHash} from 'node:crypto';
import {build} from 'esbuild';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {writeFile,readFile} from 'node:fs/promises';
const here=dirname(fileURLToPath(import.meta.url)),appSource=process.argv[2];
if(!appSource)throw Error('Pass the Intel Agent App source checkout used for this release.');
const source=resolve(appSource);
const out=await build({entryPoints:[resolve(here,'workspace.tsx')],bundle:true,write:false,outdir:'out',minify:true,format:'iife',jsx:'automatic',define:{'process.env.NODE_ENV':'"production"'},nodePaths:[resolve(source,'node_modules'),resolve(here,'node_modules')],plugins:[{name:'shared-intel-app',setup(b){b.onResolve({filter:/^intel-shared-workspace$/},()=>({path:resolve(source,'app/research/WorkspaceTables.tsx')}));b.onResolve({filter:/^@\//},args=>({path:resolve(source,args.path.slice(2))+(/\.[a-z]+$/i.test(args.path)?'':args.path.includes('combined-cro-functions')?'.ts':'.tsx')}));}}]});
const js=out.outputFiles.find(f=>f.path.endsWith('.js')).text.replaceAll('</script','<\\/script');
const baseCss=(await readFile(resolve(source,'app/trialagents-theme.css'),'utf8'))+'\n'+(await readFile(resolve(source,'app/globals.css'),'utf8')).replace(/^@import[^;]+;/gm,'');
const css=baseCss+'\n'+(out.outputFiles.find(f=>f.path.endsWith('.css'))?.text??'');
const html='<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><style>body{margin:0}'+css+'</style></head><body><main><p>Opening Intel Agent…</p></main><script>'+js+'</script></body></html>';
await writeFile(resolve(here,'../../src/intel_mcp/ui/workspace-v1.html'),html);
console.log('Built shared workspace:',html.length,'bytes');

const inputs=['app/research/WorkspaceTables.tsx','app/research/workspace.css','app/preview/combined/SharedProjectFrame.tsx','app/components/workspace/workspace-shell.css','app/globals.css','app/trialagents-theme.css','app/_site-agent/SiteResultsTable.tsx','app/_site-agent/SiteAgentWorkspace.module.css','app/preview/combined/CombinedEntityTable.tsx','app/preview/combined/combined-workspace.css','app/components/TrialEvidence.tsx','app/lib/combined-cro-functions.ts','app/app-icon.tsx'];
const hashes={};for(const path of inputs)hashes[path]=createHash('sha256').update(await readFile(resolve(source,path))).digest('hex');
await writeFile(resolve(here,'workspace-source.json'),JSON.stringify({source_repository:'tarous89/intel_agent_app',source_commit:process.argv[3]??null,status:'Draft shared preview; real-host acceptance pending',files:hashes,bundle_sha256:createHash('sha256').update(html).digest('hex')},null,2)+'\n');
