"""Deterministic branded tables for all research data; no model or database calls."""
import json

LABELS={'cros':'CROs and providers','sites':'Trial sites','pis':'Principal investigators'}

def text(value):
    if value is None: return ''
    if isinstance(value,list): return '\n'.join(filter(None,(text(v) for v in value)))
    if isinstance(value,dict): return '\n'.join(f'{k.replace("_"," ")}: {text(v)}' for k,v in value.items() if v is not None)
    return str(value)

def action(label,prompt): return {'label':label,'prompt':prompt}


def investigation_actions(kind):
    questions={
        'cros': ['Which services are most often recorded for these CROs?', 'How does their trial coverage differ by country and subgroup?', 'What operational findings are recorded in trials involving these CROs?'],
        'sites': ['Which other relevant trials involve these sites?', 'How do their trial populations and protocols differ?', 'What recruitment timelines and operational findings are available for their trials?'],
        'pis': ['Which sponsors co-occur in these investigators’ trial records?', 'Where is their phase and subgroup experience concentrated?', 'Which endpoints and protocol designs appear in their trials?'],
    }.get(kind,['How do available protocols and eligibility criteria differ?', 'What timelines are recorded across the authorized cohort?', 'What results and operational findings are available for these trials?'])
    return [action(question,question) for question in questions]

def trial_display(trial):
    return {k:trial[k] for k in ('trial_id','title','url','roles','sponsor','operational_findings') if trial.get(k)}

def result_view(data,selection_id=None):
    label=LABELS.get(data.get('entity_type'),'Trial partners')
    rows=[]
    total=data['cohort']['counts']['base']
    for e in data['entities']:
        roles=sorted({r for t in e.get('evidence',[]) for r in t.get('roles',[])})
        rows.append({'cells':[f"{e['rank']}. {e['name']}",f"{e['trial_counts']['total']} / {total} trials",
            text(roles) or text(e.get('affiliations')) or 'Not recorded',text(e.get('countries')) or 'Not recorded',
            text(e.get('contacts')) or 'Not included',e['rationale']],
            'bar':{'column':1,'value':e['trial_counts']['total'],'maximum':max(1,total)},
            'details':{'label':'Supporting studies, functions and collaborations',
                'text':text({'studies':[trial_display(t) for t in e.get('evidence',[])],'function_trial_counts':e.get('function_counts',{}),
                             'recorded_sponsor_cooccurrence':e.get('sponsors',[]),'identity_basis':e.get('identity_basis')})}})
    view={'title':label,'summary':f"Showing {data['returned']} of {data['total_entities']} matching results across {total} trials.",
          'columns':['Partner','Trial experience','Functions / affiliations','Countries','Recorded contacts','Selection basis'],
          'rows':rows,'notice':data['access_info']['message'] if data.get('show_access_notice',True) else '', 'actions':[]}
    if data.get('show_followups',True):
        view['actions']=investigation_actions(data.get('entity_type'))
    return view

def evidence_view(data,selection_id,entity_id):
    rows=[]
    for t in data['trials']:
        rows.append({'cells':[t.get('trial_id',''),t.get('title','') or 'Title not recorded',text(t.get('roles',[])) or 'Not recorded',
             text(t.get('sponsor')) or 'Not recorded',text(t.get('operational_findings')) or 'Not included / not recorded'],
             'details':{'label':'Recorded source details','text':text(trial_display(t))}})
    actions=investigation_actions('trials')
    return {'title':'Supporting studies','summary':f"Showing {len(rows)} of {data['total_trials']} recorded supporting trials.",
            'columns':['Trial','Title','Recorded roles','Sponsor','Recorded trial findings'],'rows':rows,
            'notice':'Trial-level findings are not a provider performance rating or proof of responsibility.','actions':actions}

def account_view(data):
    full=data.get('fullAccess') is True
    return {'title':'Your TrialAgents account','summary':data['account_message'],
        'columns':['Capability','Included access'],'rows':[{'cells':[k,v]} for k,v in [
            ('Research','Full matching lists' if full else 'Top ten per category'),('Supporting studies','Included for accessible entities'),
            ('Private saved projects','Included'),('Trial findings','Included where recorded within authorized trials')]],
        'notice':'Up to 1000 trials per selection. Connecting an account does not start a subscription.',
        'actions':[action('Continue research','Continue with the results available under my current account access.'),
                   action('Supporting studies','Show supporting studies for the displayed partners.'),
                   action('Open in TrialAgents Intel','Save my current research as a private TrialAgents project and open its workspace.')]}
