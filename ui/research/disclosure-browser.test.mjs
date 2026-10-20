import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,mkdir} from 'node:fs/promises';
import {chromium} from 'playwright';

test('unloaded tabs request nothing until Load; contacts require a second explicit click',async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  for(const width of [1280,420]){
   const page=await browser.newPage({viewport:{width,height:900}}),errors=[];
   page.on('pageerror',e=>errors.push(e.message));
   await page.addInitScript(()=>{
    window.calls=[];
    const make=(kind,contacts=false)=>{
     const native=kind==='cros'?{id:'cro',name:'Example CRO',country:'DE',trialCount:2,functionCounts:{},organisationTypes:[],sourceNames:[],unresolvedFunctions:[]}:
      {id:'pi',name:'Dr Example Investigator',email:contacts?'pi@example.invalid':'***',department:'Oncology',sites:[],metrics:{therapeuticAreaTrials:2,recentActivityTrials:0,sponsors:[],evidence:[]}};
     return {project_id:'synthetic-project',title:'Disclosure test',draft:{cache_token:'synthetic'},revision:1,account:{connected:false,fullAccess:false},
      tables:['cros','sites','pis','trials'].map(kind=>({kind,total:2})),disclosure:{category:kind,contacts_included:contacts,other_categories:'load_on_request'},
      result:{entity_type:kind,entities:[{id:native.id,workspace_row:native}],returned:1,total_entities:2,access_info:{offset:0},cohort:{counts:{base:2}},ranking_criteria:{therapeutic_areas:[],disease_terms:[],countries:[]}}};
    };
    window.postMessage=msg=>{
     let result;
     if(msg.method==='ui/initialize')result={protocolVersion:'2026-01-26',hostInfo:{name:'Fixture',version:'1'},hostCapabilities:{},hostContext:{theme:'light',displayMode:'fullscreen'}};
     else if(msg.method==='ui/notifications/initialized'){setTimeout(()=>window.dispatchEvent(new MessageEvent('message',{source:window,data:{jsonrpc:'2.0',method:'ui/notifications/tool-result',params:{structuredContent:make('cros')}}})),0);return;}
     else if(msg.method==='tools/call'){window.calls.push(msg.params);result={structuredContent:make(msg.params.arguments.kind,msg.params.arguments.include_contacts===true)};}
     else if(msg.id!==undefined)result={};else return;
     setTimeout(()=>window.dispatchEvent(new MessageEvent('message',{source:window,data:{jsonrpc:'2.0',id:msg.id,result}})),0);
    };
   });
   const html=await readFile(new URL('../../src/intel_mcp/ui/workspace-v1.html',import.meta.url),'utf8');
   await page.route('https://synthetic.invalid/',r=>r.fulfill({contentType:'text/html',body:html}));await page.goto('https://synthetic.invalid/');
   await page.getByRole('heading',{name:'Contract research organizations'}).waitFor();
   await page.getByRole('button',{name:/^PIs /}).click();
   await page.getByRole('button',{name:'Load investigators',exact:true}).waitFor();
   assert.equal(await page.evaluate(()=>window.calls.length),0);
   assert.equal(await page.getByText('Dr Example Investigator',{exact:true}).count(),0);
   await mkdir('/tmp/workspace-design',{recursive:true});
   await page.screenshot({path:`/tmp/workspace-design/${width}-load-investigators.png`});
   await page.getByRole('button',{name:'Load investigators',exact:true}).click();
   await page.getByText('Dr Example Investigator',{exact:true}).waitFor();
   assert.equal(await page.getByText('pi@example.invalid',{exact:true}).count(),0);
   const first=await page.evaluate(()=>window.calls[0]);assert.equal(first.name,'read_project_preview');assert.equal(first.arguments.kind,'pis');assert.equal(first.arguments.include_contacts,false);
   await page.getByRole('button',{name:'Show contact details',exact:true}).click();
   await page.getByText('pi@example.invalid',{exact:true}).waitFor();
   assert.equal(await page.evaluate(()=>window.calls.at(-1).arguments.include_contacts),true);
   assert.equal(await page.getByRole('button',{name:'Show contact details',exact:true}).count(),0);
   assert.deepEqual(errors,[]);await page.close();
  }
 }finally{await browser.close();}
});
