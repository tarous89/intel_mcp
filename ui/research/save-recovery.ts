// Storage recovery updates status without navigating away from the user's work.
export function saveNotice(data:any):string {
 if(data.report_saved===false)return 'Your Custom view is not saved yet; save it to the TrialAgents app to access it at any time.';
 if(data.recovery?.arguments?.project_id)return 'Your project changes are not saved yet; save them to the TrialAgents app to access them at any time.';
 const seconds=Number(data.expires_in_seconds);
 if(data.storage_status==='ready'&&Number.isFinite(seconds)&&seconds>0){
  const unit=seconds>=86400?'day':seconds>=3600?'hour':'minute';
  const count=Math.max(1,Math.floor(seconds/(unit==='day'?86400:unit==='hour'?3600:60)));
  return `Your project is available for up to ${count} ${unit}${count===1?'':'s'}; save it to the TrialAgents app to access it at any time.`;
 }
 return 'Your project is available only in this session; save it to the TrialAgents app to access it at any time.';
}

export function recoveryRequest(data:any){
 if(data.retry_id)return {name:'retry_project_custom_view',arguments:{retry_id:data.retry_id}};
 if(data.recovery?.arguments)return {name:data.recovery.retry_tool,arguments:data.recovery.arguments};
 const name=data.recovery?.retry_tool??data.recovery_tool??(data.account?.connected?'save_project':'recover_research_preview');
 return {name,arguments:{preview:data.draft,...(name==='recover_research_preview'?{kind:data.result?.entity_type??'cros'}:{})}};
}

export function sameRecoveryTarget(a:any,b:any){
 return a.project_id===b.project_id&&a.revision===b.revision&&a.draft?.snapshot_key===b.draft?.snapshot_key;
}

export function mergeRecoveryResult(current:any,next:any){
 // An explicitly requested cohort revision must show its new rows, never label
 // the previous cohort as the newly saved revision.
 if(next.saved===true&&next.canonical&&current.recovery?.arguments?.project_id&&next.revision!==current.revision)return next;
 // A saved identity may replace its preview identity, but rows, controls, scroll,
 // the selected Custom view and any newer report state stay where the user left them.
 const {result,view,preview_tables,active_tab,active_report_id,reports,report,...status}=next;
 const merged={...current,...status};
 if(next.saved===true&&next.canonical){
  delete merged.draft;delete merged.preview_tables;
  delete merged.project_save_error;delete merged.storage_error;delete merged.recovery_tool;
  merged.storage_status='ready';
 }
 if(reports){
  const byId=new Map((current.reports??[]).map((r:any)=>[r.id,r]));
  for(const r of reports){const old:any=byId.get(r.id);if(!old||(r.version??0)>=(old.version??0))byId.set(r.id,r);}
  merged.reports=[...byId.values()];
 }
 if(report&&(!current.report||current.report.id!==report.id||report.version>=current.report.version))merged.report=report;
 if(next.report_saved===true){
  merged.visualization_save_offer=null;merged.retry_id=null;merged.pending_custom_view=null;
  delete merged.save_error;delete merged.save_status;delete merged.recovery;
 }
 return merged;
}
