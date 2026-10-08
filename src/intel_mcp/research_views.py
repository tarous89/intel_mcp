"""Deterministic branded tables for all research data; no model or database calls."""
import json

LABELS={'cros':'CROs and providers','sites':'Trial sites','pis':'Principal investigators'}

def text(value):
    if value is None: return ''
    if isinstance(value,list): return '\n'.join(filter(None,(text(v) for v in value)))
    if isinstance(value,dict): return '\n'.join(f'{k.replace("_"," ")}: {text(v)}' for k,v in value.items() if v is not None)
    return str(value)

def action(label,prompt): return {'label':label,'prompt':prompt}

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
        if selection_id:
            first=data['entities'][0] if data['entities'] else None
            if first:
                view['actions'].append(action('Supporting studies',f"Show supporting studies for entity {first['id']} in selection {selection_id} in one branded evidence table."))
                view['actions'].append(action('Recorded contacts',f"Show recorded contacts for the displayed {label.lower()} in selection {selection_id}, including CRO emails if applicable. Use one branded table; explain source contact limitations."))
            else:
                view['actions'] += [action('Trial coverage','Show the available trial counts and search criteria for this research.'),action('Available evidence','Explain the recorded evidence available for this research without inventing results.')]
            if data['access_info']['has_more']:
                view['actions'].append(action('Access full list',f"Show more {label.lower()} from selection {selection_id}. Full lists require active paid TrialAgents account access. If needed, offer account connection to use existing access; do not initiate a subscription or purchase."))
            else:
                view['actions'].append(action('Open in Intel Agent',f"Save selection {selection_id} as my private research project and give me its Intel Agent link. Reuse the current snapshot without starting analysis or payment."))
        else:
            view['actions']=[action('More results','Show the next available page of this saved research project, subject to my current account access.'),
                action('Recorded evidence','Show the supporting studies and roles recorded in this saved project.'),
                action('Open in Intel Agent','Give me the link to this saved Intel Agent project.')]
    return view

def evidence_view(data,selection_id,entity_id):
    rows=[]
    for t in data['trials']:
        rows.append({'cells':[t.get('trial_id',''),t.get('title','') or 'Title not recorded',text(t.get('roles',[])) or 'Not recorded',
             text(t.get('sponsor')) or 'Not recorded',text(t.get('operational_findings')) or 'Not included / not recorded'],
             'details':{'label':'Recorded source details','text':text(trial_display(t))}})
    actions=[action('Recorded contacts',f"Show recorded contacts for entity {entity_id} in selection {selection_id}; CRO email contacts are explicitly requested."),
             action('Partner experience',f"Show the partner experience table for selection {selection_id}, including functions and recorded collaborations."),
             action('More supporting studies',f"Show the next supporting-study page for entity {entity_id}, selection {selection_id}, offset {data['next_offset']}.") if data.get('next_offset') is not None else
             action('Open in Intel Agent',f"Save selection {selection_id} as my private Intel Agent research project; reuse the snapshot without analysis or payment.")]
    return {'title':'Supporting studies','summary':f"Showing {len(rows)} of {data['total_trials']} recorded supporting trials.",
            'columns':['Trial','Title','Recorded roles','Sponsor','Recorded trial findings'],'rows':rows,
            'notice':'Trial-level findings are not a provider performance rating or proof of responsibility.','actions':actions}

def account_view(data):
    full=data.get('fullAccess') is True
    return {'title':'Your TrialAgents account','summary':data['account_message'],
        'columns':['Capability','Included access'],'rows':[{'cells':[k,v]} for k,v in [
            ('Research','Full matching lists' if full else 'Top ten per category'),('Supporting studies','Included for accessible entities'),
            ('Private saved projects','Included'),('Trial findings','Included where recorded' if full else 'Requires active paid access')]],
        'notice':'Up to 500 trials per selection. Connecting an account does not start a subscription.',
        'actions':[action('Continue research','Continue with the results available under my current account access.'),
                   action('Supporting studies','Show supporting studies for the displayed partners.'),
                   action('Open in Intel Agent','Save my current research as a private Intel Agent project and give me its link.')]}
