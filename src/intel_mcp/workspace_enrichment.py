"""Versioned presentation enrichment of frozen research; never changes membership/order."""
from copy import deepcopy
from datetime import date
from .site_ranking import ProfileRanker

def criteria_for(raw):
    def values(key):
        result=[]
        for source in (raw.get('direct') or {},raw.get('base') or {}):
            node=source.get(key) or {}
            for v in (node.get('values') or []) if node.get('operator') not in ('contains_none','not_contains_any','not_in','not_equals') else []:
                if v not in result:result.append(v)
        return result
    return {'countries':raw.get('entity_countries') or [],'strict_identity':True,
            'therapeutic_areas':values('therapeutic_areas'),'disease_terms':values('diseases'),
            'phases':values('phase'),'modalities':values('modalities'),
            'paediatric_relevant':any(((s.get('paediatric_trial') or {}).get('value') is True and (s.get('paediatric_trial') or {}).get('operator','is')=='is') for s in (raw.get('base') or {},raw.get('direct') or {}))}

def enrich(payload,records,raw):
    result=deepcopy(payload);criteria=criteria_for(raw)
    ranker=ProfileRanker(criteria)
    for record in records:
        profile=deepcopy(record['profile'])
        for site in (profile.get('classification_variables') or {}).get('sites') or []:
            for p in site.get('investigators') or []:
                email=str(p.get('email') or '')
                if any(x in email.lower() for x in ('redacted','masked','withheld','xxx','*')):p['email']=''
        ranker.add([{'eu_number':record['trial_id'],'profile':profile}])
    ranked=ranker.result(None,as_of=date.fromisoformat(raw['as_of']))
    profiles={r['trial_id']:r for r in records}
    for section in result['sections']:
        kind=section['entity_type'];out=section['result']
        out['ranking_criteria']=criteria;out['as_of']=raw['as_of'];out['projection_version']='workspace-rich-1'
        out['subgroups']=[{'id':g['id'],'label':g.get('label',g['id'])} for g in raw.get('subgroups',[])]
        lookup={r['id']:r for r in ranked.get(kind,[])}
        for entity in out['entities']:
            if kind in ('sites','pis'):
                native=lookup.get(entity['id'])
                if not native:raise ValueError('FROZEN_ENTITY_IDENTITY_MISMATCH')
                native=deepcopy(native);native['rank']=entity['rank'];native['name']=entity['name']
                entity['workspace_row']=native
                if kind=='sites':entity['contacts']=[native['contact']] if native.get('contact') else []
                entity['subgroup_tags']=sorted({g['id'] for tid in (ranker.sites if kind=='sites' else ranker.people)[entity['id']]['trials'] for g,match in zip(raw.get('subgroups',[]),profiles[tid].get('subgroup_matches',[])) if match})
            elif kind=='trials':
                r=profiles[entity['id']];p=r['profile'];c=p.get('classification_variables') or {};f=p.get('filtering_variables') or {}
                from .workspace_trial import trial_row
                entity['workspace_row']=trial_row(entity['id'],p,['base',*[g['id'] for g,match in zip(raw.get('subgroups',[]),r.get('subgroup_matches',[])) if match]])
    return result
