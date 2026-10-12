"""Bounded private snapshot transport. Never exposed as a model/tool result."""
import base64
import gzip
import hashlib
import json
from .selection import SelectionError

MAX_CHUNK = 1024 * 1024
MAX_TOTAL = 64 * 1024 * 1024


def snapshot_chunks(token, snapshot_key, payload, prepared):
    metadata = {k: v for k, v in prepared.items() if k != 'records'}
    sections = []
    for section in payload['sections']:
        result = section['result']
        sections.append({**section, 'result': {**result, 'entities': [{'id': e['id']} for e in result['entities'][:10]]}})
    header = {'type': 'header', 'version': 1, 'token': token, 'snapshot_key': snapshot_key,
              'title': payload['title'], 'sections': sections, 'recommendations': payload.get('recommendations', []),
              'metadata': metadata, 'profiles': [{k: v for k, v in r.items() if k != 'json'} for r in prepared['records']]}
    # Stable source identity across interrupted attempts; no source text is returned to the host.
    source = hashlib.sha256()
    total = 0
    def line(value):
        nonlocal total
        raw = json.dumps(value, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()
        if len(raw) > MAX_CHUNK:
            raise SelectionError('SNAPSHOT_CHUNK_TOO_LARGE: One snapshot item exceeds the safe storage bound.')
        total += len(raw)
        if total > MAX_TOTAL:
            raise SelectionError('SNAPSHOT_TOO_LARGE')
        source.update(raw + b'\n')
        return json.dumps({'gzip': base64.b64encode(gzip.compress(raw, compresslevel=1)).decode()}, separators=(',', ':')).encode() + b'\n'
    yield line(header)
    for section in payload['sections']:
        rows = section['result']['entities']
        for start in range(0, len(rows), 10):
            yield line({'type': 'page', 'kind': section['entity_type'], 'page': start // 10, 'rows': rows[start:start + 10]})
    for trial_id, evidence in payload.get('shared_evidence', {}).items():
        yield line({'type': 'evidence', 'trial_id': trial_id, 'value': evidence})
    for ordinal, row in enumerate(prepared['records']):
        yield line({'type': 'profile', 'ordinal': ordinal, 'row': row})
    yield json.dumps({'finish': source.hexdigest()}, separators=(',', ':')).encode() + b'\n'
