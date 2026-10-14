"""Public research metadata and presentation; no DB reads or model calls."""
from copy import deepcopy
from importlib.resources import files



RESEARCH_WORKFLOW = "\n\n".join(files("intel_mcp").joinpath(name).read_text() for name in (
    "presentation-standard.md", "access-and-evidence.md", "research-workflow.md"))


def inline_schema(schema):
    """Expose nested criteria to clients that do not resolve local $defs references.

    Only tool input metadata is transformed. Pydantic runtime validation is unchanged.
    Fail explicitly on unexpected external/cyclic refs rather than publish an untyped input.
    """
    def expand(value, stack=()):
        if isinstance(value, list):
            return [expand(item, stack) for item in value]
        if not isinstance(value, dict):
            return value
        if '$ref' in value:
            ref = value['$ref']
            if not ref.startswith('#/') or ref in stack:
                raise ValueError('Research schema requires nonrecursive local references')
            target = schema
            for part in ref[2:].split('/'):
                target = target[part.replace('~1', '/').replace('~0', '~')]
            return {**expand(target, (*stack, ref)),
                    **expand({key: item for key, item in value.items() if key != '$ref'}, stack)}
        return {key: expand(item, stack) for key, item in value.items() if key != '$defs'}
    return expand(schema)


def public_cohort(summary, selection_origin=None):
    """Describe a successful bounded read without legacy deployment warnings.

    Does not assert that the database contains every CTIS study. Legacy private
    contract labels remain unchanged for existing App consumers.
    """
    result = deepcopy(summary)
    result['coverage'] = 'complete_available_profile_selection'
    result['source_scope'] = (
        'Matching current available TrialAgents profiles within the stated criteria. '
        'This is not a worldwide or all-CTIS census. A successful selection is not sampled; '
        'over-limit or unsupported-profile reads fail instead of returning a partial ranking.'
    )
    result['limitations'] = [
        'Individual recorded fields may be absent; missing information is not evidence of no experience.',
        *[item for item in result['limitations']
          if not item.startswith('Current serving profiles; full study coverage requires Engine availability migration 047.')],
    ]
    if selection_origin:
        result['coverage'] = 'model_selected_source_subset'
        result['source_scope'] = (
            'Explicit trial IDs selected from a bounded source cohort. Original search criteria '
            'describe retrieval, not proof that every matching trial remains in this selection. '
            'Selection rationale is model interpretation; source facts and counts remain deterministic.'
        )
    return result


def discovery_guidance(trial_count):
    return {
        'target_trials': {'minimum': 100, 'maximum': 500},
        'actual_trials': trial_count,
        'status': 'below_target' if trial_count < 100 else 'within_target',
        'next_step': (
            'For initial exploratory discovery, broaden through a relevant therapeutic area, phase or modality '
            'before finalizing; retain requested population/phase as named subgroups. Preserve explicit '
            'mandatory constraints. If no relevant broadening is possible, report the actual count and why.'
            if trial_count < 100 else
            'Discovery is ready. Call publish_research_workspace once with this final broadest relevant selection_id. Return one top-ten list per requested category in the workspace, not separate cohort lists or chat tables.'
        ),
        'presentation': 'After broadening finishes, use only the final broadest relevant selection_id with publish_research_workspace. Do not rank or display intermediate cohorts.',
        'ranking_priority': 'Distinct trial count across the whole selected cohort, then name and ID for stable ties.',
    }


def access_info(total, returned, *, full=False, offset=0):
    if full:
        message = (f'Showing {returned} of {total} matching results in this page. '
                   'Your account includes full-list access across research selections.')
    else:
        message = (f'Showing {returned} of {total} matching results. Free research includes up to ten '
                   'results per category without login. Full lists require active paid TrialAgents '
                   'account access. Connect to use existing access; connecting alone does not unlock full lists.')
    return {
        'mode': 'full' if full else 'top_ten',
        'total_matching': total,
        'returned': returned,
        'offset': offset,
        'anonymous_limit': 10,
        'has_more': offset + returned < total,
        'connection_required_for_initial_research': False,
        'full_access_requirements': ['connected_account', 'active_paid_account_access'],
        'message': message,
    }


RESEARCH_CAPABILITIES = {
    'anonymous': ['Top-ten CRO/provider, site or PI ranking across a bounded cohort',
                  'Title/disease/profile-text discovery and structured country, phase, modality and therapeutic-area filters',
                  'Recorded supporting trial titles, IDs, source links and entity roles for displayed entities',
                  'Function-specific CRO experience, recorded sponsor co-occurrence and PI affiliations',
                  'Explicit-request recorded CRO contacts; PI contacts where available',
                  'Complete frozen profiles, one or combined sections, and all available extracted document text for the fixed eligible ten trials',
                  'describe_trial_profile_schema exposes the exact section vocabulary, field types and nesting',
                  'Recorded operational findings within eligible trial profiles, without attributing entity performance'],
    'existing_entitlement': ['Full entity lists across research selections with active paid account access',
                             'Expanded complete trial content beyond the eligible free trial set'],
    'connected_account': ['Save private research projects and reopen them in ChatGPT or Intel Agent without new analysis'],
    'reports': ['HTML analysis saved to a project and visible in both interfaces', 'Complete profiles/sections and extracted documents for eligible ten free trials; all authorized trials with paid access'],
    'not_exposed': ['Unavailable or unextracted documents', 'Patient-level data',
                    'Complete EU regulatory history', 'Unavailable clinical-study datasets', 'Outreach or response tracking'],
}
