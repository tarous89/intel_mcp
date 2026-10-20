"""Public research response projection. Never alter stored snapshots or documents."""
import json

ACCOUNT_FIELDS = {'connected', 'fullAccess', 'accessScope', 'reason', 'account_message',
                  'capabilities', 'limits', 'projects', 'truncated', 'view'}
PERSON_GROUPS = {'contact', 'contacts', 'investigators', 'matchedPIs',
                 'trial_management_contact', 'trial_scientific_contact',
                 'trial_recruitment_contact', 'trial_public_ctis_contact'}
CONTACT_FIELDS = {'email', 'emails', 'phone', 'telephone', 'phone_number', 'phoneNumber',
                  'contact_first_name', 'contact_last_name', 'contact_name', 'contactName',
                  'first_name', 'last_name'}
PERSON_FIELDS = {'name', 'firstName', 'lastName', 'profile_url', 'profileUrl'}


def mask_contacts(value, *, reveal=False, person=False):
    """Mask structured fields only; preserve institutions and arbitrary prose/HTML."""
    if isinstance(value, list):
        return [mask_contacts(v, reveal=reveal, person=person) for v in value]
    if not isinstance(value, dict):
        return value
    out = {}
    for key, item in value.items():
        if not reveal and (key in CONTACT_FIELDS or (person and key in PERSON_FIELDS)):
            out[key] = '***' if item else item
        else:
            out[key] = mask_contacts(item, reveal=reveal, person=person or key in PERSON_GROUPS)
    return out


def project_response(value, *, reveal=False, account=False):
    if isinstance(value, list):
        return [project_response(v, reveal=reveal) for v in value]
    if not isinstance(value, dict):
        return value
    if account:
        # Explicit allowlist: backend identity additions cannot silently become public.
        value = {k: v for k, v in value.items() if k in ACCOUNT_FIELDS}
    out = {}
    for key, item in value.items():
        if key in ('account_email', 'accountEmail', 'user_email', 'userEmail'):
            continue
        if key == 'preview_tables':
            # The full project remains stored; only the selected table travels to the host.
            kind = value.get('result', {}).get('entity_type')
            out[key] = {kind: project_response(item[kind], reveal=reveal)} if kind in item else {}
        elif key == 'account':
            out[key] = project_response(item, account=True)
        elif key == 'profile':
            out[key] = mask_contacts(item)
        elif key in ('html', 'state', 'profile_json_part'):
            out[key] = item
        else:
            out[key] = project_response(item, reveal=reveal)
    # Legacy tables serialize the structured contact field into a known column.
    # Mask that column too; never search/replace arbitrary prose or Custom HTML.
    if not reveal and 'Recorded contacts' in out.get('columns', []):
        column = out['columns'].index('Recorded contacts')
        for row in out.get('rows', []):
            cells = row.get('cells', [])
            if len(cells) > column and cells[column] not in ('', 'Not included', 'Not recorded'):
                cells[column] = '***'
    if 'entity_type' in out and ('entities' in out or 'native_rows' in out):
        out = mask_contacts(out, reveal=reveal and out['entity_type'] != 'trials')
    if isinstance(out.get('result'), dict) and 'entity_type' in out['result']:
        out['disclosure'] = {'category': out['result']['entity_type'], 'contacts_included': reveal,
                             'other_categories': 'load_on_request'}
    return out


async def disclosure_boundary(ctx, call_next):
    result = await call_next(ctx)
    if ctx.method != 'tools/call' or not isinstance(result, dict):
        return result
    params = ctx.params or {}
    name, args = params.get('name'), params.get('arguments') or {}
    if name in ('read_trial_document', 'read_custom_view_document', 'describe_trial_profile_schema'):
        return result
    reveal = args.get('include_contacts') is True or (name == 'rank_research_entities' and args.get('include_cro_contacts') is True)
    def project(v):
        return project_response(v, reveal=reveal, account=name == 'get_account_access')
    out = dict(result)
    if 'structuredContent' in out:
        out['structuredContent'] = project(out['structuredContent'])
    blocks = []
    for block in out.get('content', []):
        if block.get('type') == 'text':
            try:
                parsed = json.loads(block['text'])
            except (ValueError, TypeError, KeyError):
                pass
            else:
                if isinstance(parsed, (dict, list)):
                    block = {**block, 'text': json.dumps(project(parsed), ensure_ascii=False)}
        blocks.append(block)
    if 'content' in out:
        out['content'] = blocks
    return out
