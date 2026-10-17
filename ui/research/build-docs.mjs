// The App owns shared public chrome and the MCP documentation. Run after changing either.
import {build} from 'esbuild';
import {resolve,dirname} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {mkdtemp,writeFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
const here=dirname(fileURLToPath(import.meta.url));
if(!process.argv[2])throw Error('Pass the TrialAgents Intel App source checkout.');
const dir=await mkdtemp(resolve(tmpdir(),'trialagents-docs-'));
try{
 const out=resolve(dir,'docs.mjs');
 await build({entryPoints:[resolve(process.argv[2],'app/lib/mcp-documentation.ts')],bundle:true,platform:'node',format:'esm',outfile:out});
 const {mcpDocumentationHtml}=await import(pathToFileURL(out).href);
 const html=mcpDocumentationHtml();
 if(/ctis/i.test(html))throw Error('MCP copy and metadata must not mention CTIS.');
 await writeFile(resolve(here,'../../src/intel_mcp/ui/mcp-documentation.html'),html);
 console.log('Built shared MCP documentation:',html.length,'bytes');
}finally{await rm(dir,{recursive:true,force:true});}
