// Keep the project capability out of visible chat text and external URLs.
// A model-initiated tool call is the portable way to start host OAuth linking.
export async function connectProject(app:any,data:any){
 if(!/^[a-f0-9-]{36}$/.test(data.project_id)||!/^[A-Za-z0-9_-]{43}$/.test(data.preview_token))throw Error('Missing project capability');
 await app.updateModelContext({structuredContent:{
  project_id:data.project_id,
  connect_and_save:{tool:'claim_research_workspace',arguments:{project_id:data.project_id,preview_token:data.preview_token}},
 }});
 const result=await app.sendMessage({role:'user',content:[{type:'text',text:
  `Connect my TrialAgents account and automatically save the current research project ${data.project_id} to that account. Call claim_research_workspace with the project ID and private preview token from the workspace context. Complete account authorization if needed, then finish the same claim. Preserve this project and its results; do not create a duplicate or start a new search. Confirm saving only after the tool succeeds and give me the Projects link.`}]});
 if(result.isError)throw Error('Connection request was not accepted');
}
