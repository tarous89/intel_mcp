"""Public Custom view vocabulary; legacy storage keys remain private to the backend.

Only envelope keys are translated. Never rewrite clinical evidence, HTML, titles,
user state, identifiers or source documents.
"""
import json

KEYS = {
    'report': 'custom_view', 'reports': 'custom_views',
    'report_id': 'custom_view_id', 'active_report_id': 'active_custom_view_id',
    'report_saved': 'custom_view_saved', 'temporary_report': 'temporary_custom_view',
    'report_preview': 'custom_view_preview', 'report_guidance': 'custom_view_guidance',
    'report_html_example': 'custom_view_html_example',
}
ENVELOPES = {'presentation_recovery', 'recovery', 'current_context'}

def custom_view_envelope(value):
    if not isinstance(value, dict):
        return value
    return {KEYS.get(key, key): custom_view_envelope(item) if key in ENVELOPES else item
            for key, item in value.items()}

async def custom_view_contract(ctx, call_next):
    result = await call_next(ctx)
    if ctx.method != 'tools/call' or not isinstance(result, dict):
        return result
    out = dict(result)
    if 'structuredContent' in out:
        out['structuredContent'] = custom_view_envelope(out['structuredContent'])
    content = []
    for block in out.get('content', []):
        if block.get('type') == 'text':
            try:
                parsed = json.loads(block['text'])
            except (ValueError, TypeError, KeyError):
                pass
            else:
                if isinstance(parsed, dict):
                    block = {**block, 'text': json.dumps(custom_view_envelope(parsed), ensure_ascii=False)}
        content.append(block)
    if 'content' in out:
        out['content'] = content
    return out
