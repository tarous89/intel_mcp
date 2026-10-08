"""Public selection disclosure policy. The private App-lease tools are not exposed here."""
from __future__ import annotations
import asyncio
import secrets
import time
from collections import OrderedDict
from .selection import SelectionDataset, SelectionError, digest
from .research_cohort import refine_cohort

class ResearchStore:
    """Bounded, short-lived public-data snapshots; restart/eviction requires a new search."""
    def __init__(self, engine_factory, ttl=900, max_bytes=64*1024*1024):
        self.engine_factory = engine_factory
        self.ttl, self.max_bytes = ttl, max_bytes
        self.entries = OrderedDict()
        self.lock = asyncio.Lock()

    async def search(self, criteria):
        # Serialize construction to bound simultaneous DB reads/memory, coalesce retries.
        if self.lock.locked():
            raise SelectionError('RESEARCH_BUSY: Another selection is being prepared; retry shortly.')
        async with self.lock:
            now=time.monotonic()
            for token in list(self.entries):
                if self.entries[token]['expires'] <= now:
                    del self.entries[token]
            key=digest(criteria.model_dump(mode='json'))
            for token, entry in self.entries.items():
                if entry['key']==key:
                    return token, entry['dataset']
            engine=self.engine_factory()
            if not hasattr(engine, 'selection'):
                raise SelectionError('SELECTION_DATABASE_REQUIRED: Configure the restricted database reader.')
            dataset=await engine.selection(criteria)
            return self._put(dataset, key)

    def _put(self, dataset, key):
        import json
        size=len(json.dumps(dataset.records, ensure_ascii=False).encode())
        if size>self.max_bytes:
            raise SelectionError('SELECTION_TOO_LARGE: Narrow the selection.')
        while self.entries and (len(self.entries)>=8 or sum(e['bytes'] for e in self.entries.values())+size>self.max_bytes):
            self.entries.popitem(last=False)
        token=secrets.token_urlsafe(32)
        self.entries[token]={'dataset':dataset,'expires':time.monotonic()+self.ttl,'key':key,'bytes':size}
        return token,dataset

    async def refine(self, token, request):
        if self.lock.locked():
            raise SelectionError('RESEARCH_BUSY: Another selection is being prepared; retry shortly.')
        async with self.lock:
            dataset=refine_cohort(self.get(token),request)
            key='refined:'+dataset.snapshot
            for cached, entry in self.entries.items():
                if entry['key']==key and entry['expires']>time.monotonic():
                    return cached,entry['dataset']
            return self._put(dataset,key)

    def remaining_seconds(self, token):
        self.get(token)
        return max(0, int(self.entries[token]["expires"] - time.monotonic()))

    def get(self, token):
        entry=self.entries.get(token)
        if not entry or entry['expires']<=time.monotonic():
            self.entries.pop(token,None)
            raise SelectionError('SELECTION_EXPIRED: Repeat the search; no partial result was returned.')
        return entry['dataset']


def public_ranking(dataset, *, offset=0, limit=10, full_access=False, include_cro_contacts=False):
    if offset<0 or limit<1 or limit>100:
        raise SelectionError('INVALID_PAGE')
    if not full_access and (offset!=0 or limit>10):
        raise SelectionError('ACCOUNT_ACCESS_REQUIRED: Current access includes the top ten. Connect your TrialAgents account to check full-list access.')
    ranked=dataset.rank(limit=offset+limit, full_cohort=True)
    ranked.entities=ranked.entities[offset:offset+limit]
    ranked.returned=len(ranked.entities)
    if dataset.criteria.entity_type == 'cros':
        for entity in ranked.entities:
            if not include_cro_contacts:
                entity.contacts = [c for c in entity.contacts if 'email' not in c]
            else:
                entity.contacts = [{**c, 'contact_caveat': 'Recorded trial/regulatory source contact; suitability for commercial outreach is unverified.'} if 'email' in c else c for c in entity.contacts]
    if not full_access:
        for entity in ranked.entities:
            for trial in entity.evidence:
                trial.pop('discovery_evidence',None)
                trial.pop('operational_findings',None)
    # No unbounded profile or entity lookup is exposed by this public surface.
    return ranked


def public_evidence(dataset, entity_id, *, offset=0, full_access=False):
    allowed={e.id for e in dataset.rank(limit=10, full_cohort=True).entities}
    if not full_access and entity_id not in allowed:
        raise SelectionError('ENTITY_ACCESS_REQUIRED: Evidence is available for the displayed top ten.')
    result=dataset.evidence(entity_id,offset=offset,limit=10,full_cohort=True)
    # Source narratives/sections may enumerate unrelated entities. Public evidence
    # returns explicit trial and role links; unrestricted sections stay private.
    if not full_access:
        for trial in result.trials:
            trial.pop('discovery_evidence',None)
            trial.pop('operational_findings',None)
    return result
