"""Inert question suggestions: verified scope, no evidence expansion or persistence."""
from importlib.resources import files
from hashlib import sha256
from mcp.server.mcpserver.exceptions import ToolError
HTML=files('intel_mcp').joinpath('ui/followups.html').read_text()
RESOURCE='ui://trialagents/followups-'+sha256(HTML.encode()).hexdigest()[:12]

def followup_payload(questions,scope,context,connected=False):
    cleaned=[q.strip() for q in questions]
    if len(cleaned)!=3 or len(set(q.casefold() for q in cleaned))!=3 or any(len(q)<10 or len(q)>260 or not q.endswith('?') for q in cleaned):
        raise ToolError('Provide exactly three distinct, concise investigation questions ending in a question mark.')
    full=scope.get('access_scope')=='full'
    count=min(10,max(0,int(scope.get('available_trials',10))))
    if full:
        notice='Your connected account has full access to this selection.'
    elif count==0:
        notice='No trials are available in this preview.'
    elif connected:
        notice=f'Preview: {count} accessible trials; full-cohort analysis requires full account access.'
    elif count==10:
        notice='Preview: up to 10 trials; connect your account to use existing full access.'
    else:
        notice=f'Preview: {count} available trial'+('s' if count!=1 else '')+'; connect your account to use existing full access.'
    return {'questions':cleaned,'access_notice':notice,'access_scope':'full' if full else 'preview',
            'context':context,'presentation':'Show these three questions and this single access sentence at the end; if the card renders, do not duplicate them in prose. Suggestions do not grant access or imply the analysis was performed.'}
