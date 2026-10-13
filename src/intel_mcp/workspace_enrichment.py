"""Versioned presentation enrichment of frozen research; never changes membership/order."""
from copy import deepcopy
from datetime import date
from .site_ranking import selection_identity_profile, ProfileRanker

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


def visible_email(value):
    return bool(value) and not any(x in str(value).lower() for x in ('redacted','masked','withheld','xxx','*'))

def hide_contact_placeholders(ranker):
    # Clean contact display after IDs and membership have been established.
    for site in ranker.sites.values():
        for contact in list(site['contacts']):
            if not visible_email(contact[1]):del site['contacts'][contact]
    for person in ranker.people.values():
        mappings=[person['emails'],person['email_recency'],*person['site_emails'].values(),*person['site_email_recency'].values()]
        for mapping in mappings:
            for email in list(mapping):
                if not visible_email(email):del mapping[email]

def enrich(payload,records,raw,*,in_place=False):
    # Only fresh, privately owned workspace payloads opt into mutation.
    result=payload if in_place else deepcopy(payload);criteria=criteria_for(raw)
    ranker=ProfileRanker(criteria)
    for record in records:
        profile=selection_identity_profile(record['profile'])
        ranker.add([{'eu_number':record['trial_id'],'profile':profile}])
    hide_contact_placeholders(ranker)
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
                # ranker.result is private to this invocation; transfer its row.
                native['rank']=entity['rank'];native['name']=entity['name']
                entity['workspace_row']=native
                entity['contacts']=[c for c in entity.get('contacts',[]) if visible_email(c.get('email'))]
                if kind=='sites':entity['contacts']=[native['contact']] if native.get('contact') else []
                entity['subgroup_tags']=sorted({g['id'] for tid in (ranker.sites if kind=='sites' else ranker.people)[entity['id']]['trials'] for g,match in zip(raw.get('subgroups',[]),profiles[tid].get('subgroup_matches',[])) if match})
            elif kind=='trials':
                r=profiles[entity['id']];p=r['profile'];c=p.get('classification_variables') or {};f=p.get('filtering_variables') or {}
                from .workspace_trial import trial_row
                entity['workspace_row']=trial_row(entity['id'],p,['base',*[g['id'] for g,match in zip(raw.get('subgroups',[]),r.get('subgroup_matches',[])) if match]])
    return result
