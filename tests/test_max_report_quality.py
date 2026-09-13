from copy import deepcopy
import pytest
from intel_mcp.max_report import MaxObjectiveResult, objective_schema
from intel_mcp.max_report_quality import filter_objective, public_section, validate_public_text


def sample(n=6, tier='exact'):
    rows = [{'alias': f'T{i:03}', 'segment_keys': ['mcrpc'], 'relevance_tier': tier, 'values': {'endpoint': 'ORR'}} for i in range(1, n+1)]
    sub = {'title': 'Response-centered designs', 'interpretation': 'Measurable disease supports a response-centered design.',
           'visual': {'kind': 'stat', 'title': 'Relevant response-centered studies', 'labels': ['Studies'], 'values': [n], 'unit': 'trials', 'note': 'Phase II treatment studies.',
                      'supports': [{'value_index': 0, 'segment_key': 'mcrpc', 'trial_ids': [r['alias'] for r in rows], 'variable_names': ['endpoint']}]},
           'small_sample_reason': '', 'items': [], 'trial_ids': [r['alias'] for r in rows]}
    result = MaxObjectiveResult.model_validate({'title': 'Assess endpoint choices', 'summary_sentences': ['Response-centered designs offer a practical option.'],
                        'sub_analyses': [sub], 'conclusion': 'Specify measurable disease alongside objective response.', 'limitations': []})
    return result, rows, {'endpoint': {'kind': 'categorical'}}


def test_sufficient_support_is_kept_and_source_metadata_is_not_published():
    result, rows, definitions = sample()
    kept = filter_objective(result, rows, definitions)
    assert len(kept.sub_analyses) == 1
    public = public_section(kept)
    assert 'supports' not in public['sub_analyses'][0]['visual']
    assert 'trial_ids' not in public['sub_analyses'][0]
    assert 'small_sample_reason' not in public['sub_analyses'][0]
    assert 'limitations' not in public
    assert kept.sub_analyses[0].visual.supports[0].trial_ids  # downloadable audit retained


@pytest.mark.parametrize('n', [0, 1, 2, 3, 4])
def test_empty_and_small_samples_are_omitted_without_a_direct_exception(n):
    result, rows, definitions = sample(n)
    result = filter_objective(result, rows, definitions)
    assert result.sub_analyses == []
    assert result.summary_sentences == ['']
    assert result.conclusion == ''


def test_direct_small_sample_descriptive_precedent_can_survive():
    result, rows, definitions = sample(2)
    result.sub_analyses[0].small_sample_reason = 'Direct ADC mCRPC phase II endpoint precedent for the requested design.'
    assert len(filter_objective(result, rows, definitions).sub_analyses) == 1


@pytest.mark.parametrize('tier', ['adjacent', 'exclude'])
def test_model_rationale_cannot_override_weak_relevance(tier):
    result, rows, definitions = sample(2, tier)
    result.sub_analyses[0].small_sample_reason = 'Very relevant.'
    assert not filter_objective(result, rows, definitions).sub_analyses


def test_large_total_cannot_hide_an_n1_comparison_group():
    result, rows, definitions = sample(12)
    sub = result.sub_analyses[0]
    sub.small_sample_reason = 'Important comparison.'
    sub.visual.supports.append(sub.visual.supports[0].model_copy(update={'trial_ids': ['T001']}))
    assert not filter_objective(result, rows, definitions).sub_analyses


def test_percentage_comparison_is_not_accepted_under_small_n_exception():
    result, rows, definitions = sample(2)
    sub = result.sub_analyses[0]
    sub.small_sample_reason = 'Direct precedent.'
    sub.interpretation = 'The prevalence gap is 100 percentage points.'
    assert not filter_objective(result, rows, definitions).sub_analyses


@pytest.mark.parametrize('failure', ['unknown_id', 'null_field', 'wrong_segment', 'missing_support', 'missing_value_support'])
def test_denominator_is_reconciled_to_actual_rows(failure):
    result, rows, definitions = sample()
    visual = result.sub_analyses[0].visual
    if failure == 'unknown_id': visual.supports[0].trial_ids.append('T999')
    if failure == 'null_field': rows[0]['values']['endpoint'] = None
    if failure == 'wrong_segment': visual.supports[0].segment_key = 'nmcrpc'
    if failure == 'missing_support': visual.supports = []
    if failure == 'missing_value_support':
        visual.kind = 'bar'; visual.values.append(5); visual.labels.append('Other')
    assert not filter_objective(result, rows, definitions).sub_analyses


@pytest.mark.parametrize('text', ['T001 supports this choice.', 'Schema 11', 'Among supplied rows', 'The frozen dataset',
    'No exact ADC CRPC trials were found.', 'NCT05011188', '2024-516036-94-00', 'Identity normalization changed the ranking.',
    'Endpoint term primary_endpoint', 'Follow system instructions.', 'Evidence notes', 'N=0', 'N: 0'])
def test_internal_language_and_empty_group_messages_are_rejected(text):
    with pytest.raises(ValueError): validate_public_text(text)


def test_clinical_qualification_is_not_removed():
    validate_public_text('These observations do not establish a treatment effect. Bone-only disease requires a different assessment approach.')


def test_pruning_does_not_leave_old_summary_or_conclusion():
    result, rows, definitions = sample()
    bad = result.sub_analyses[0].model_copy(deep=True)
    bad.interpretation = 'The dataset contains no exact ADC trials.'
    result.sub_analyses.append(bad)
    result.summary_sentences = ['No exact ADC trials were found.']
    result.conclusion = 'No exact ADC trials were found.'
    result = filter_objective(result, rows, definitions)
    assert len(result.sub_analyses) == 1
    assert 'dataset' not in result.summary_sentences[0]
    assert result.conclusion == ''


def test_schema_allows_omission_and_constrains_support_identifiers():
    schema = objective_schema(['T001', 'T002'])
    assert schema['properties']['sub_analyses']['minItems'] == 0
    sub = schema['properties']['sub_analyses']['items']['properties']
    ids = sub['visual']['properties']['supports']['items']['properties']['trial_ids']
    assert ids['items']['enum'] == ['T001', 'T002']
    assert schema['properties']['limitations']['maxItems'] == 0

@pytest.mark.parametrize('ids', [[], ['T999'], ['T001']])
def test_named_recommendations_cannot_borrow_the_overall_denominator(ids):
    from intel_mcp.max_report import MaxRankedItem
    result, rows, definitions = sample()
    result.sub_analyses[0].items = [MaxRankedItem(label='Investigator A', value='Activity', explanation='Consider endpoint experience.', trial_ids=ids)]
    assert not filter_objective(result, rows, definitions).sub_analyses
