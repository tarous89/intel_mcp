"""Host-readable criteria, honest discovery scope and public access disclosure."""
from copy import deepcopy
import json

import pytest
from jsonschema import Draft202012Validator, ValidationError
from intel_mcp.research_presentation import inline_schema, public_cohort, discovery_guidance, access_info
from intel_mcp.selection import SelectionCriteria, SelectionDataset
from test_selection import criteria, record


def test_inline_criteria_retains_validation_and_all_supported_filters():
    original = SelectionCriteria.model_json_schema()
    before = deepcopy(original)
    published = inline_schema(original)
    assert original == before
    assert '"$ref"' not in json.dumps(published)
    assert '"$defs"' not in json.dumps(published)
    Draft202012Validator.check_schema(published)
    validator = Draft202012Validator(published)
    request = {
        'base': {}, 'base_text': {'fields': ['title', 'diseases'], 'terms': ['prostate']},
        'entity_type': 'cros', 'as_of': '2026-10-07', 'include_broader': True,
        'subgroups': [{'id': 'phase3', 'label': 'Phase III candidates', 'bucket': 'direct',
                      'filters': {'phase': {'values': [3]}}, 'phase_title_fallback': True}],
    }
    validator.validate(request)
    SelectionCriteria.model_validate(request)
    for invalid in ({**request, 'entity_type': 'unknown'},
                    {**request, 'base_text': {'fields': ['raw_sql'], 'terms': ['prostate']}},
                    {key: value for key, value in request.items() if key != 'as_of'},
                    {**request, 'unexpected': True}):
        with pytest.raises(ValidationError):
            validator.validate(invalid)
    # Private contract still owns the complete filter inventory; none are hidden.
    assert set(published['properties']['base']['properties']) == set(original['$defs']['TrialFilters']['properties'])


def test_schema_rejects_external_and_recursive_refs():
    for schema in ({'$ref': 'https://untrusted.invalid/schema'},
                   {'$defs': {'x': {'$ref': '#/$defs/x'}}, '$ref': '#/$defs/x'}):
        with pytest.raises(ValueError):
            inline_schema(schema)


def test_public_coverage_does_not_change_private_contract_or_hide_real_limits():
    original = SelectionDataset(criteria(), [record()]).summary().model_dump(mode='json')
    before = deepcopy(original)
    result = public_cohort(original)
    assert original == before
    assert result['coverage'] == 'complete_available_profile_selection'
    assert result['counts'] == original['counts']
    assert 'migration 047' not in str(result)
    assert any('Identity aliases' in item for item in result['limitations'])
    assert 'not a worldwide or all-CTIS census' in result['source_scope']


@pytest.mark.parametrize('count,status', [(0, 'below_target'), (6, 'below_target'),
                                        (99, 'below_target'), (100, 'within_target'),
                                        (192, 'within_target'), (500, 'within_target')])
def test_landscape_guidance_never_pads_counts_or_relaxes_hard_constraints(count, status):
    result = discovery_guidance(count)
    assert result['actual_trials'] == count and result['status'] == status
    if count < 100:
        assert 'Preserve explicit mandatory constraints' in result['next_step']
        assert 'report the actual count' in result['next_step']


def test_access_notice_does_not_equate_login_with_entitlement_or_invent_more_results():
    small = access_info(6, 6)
    assert not small['has_more'] and '6 of 6' in small['message']
    free = access_info(272, 10)
    assert free['has_more'] and '10 of 272' in free['message']
    assert not free['connection_required_for_initial_research']
    assert 'connecting alone does not unlock' in free['message']
    full = access_info(25, 15, full=True, offset=10)
    assert full['mode'] == 'full' and not full['has_more']
