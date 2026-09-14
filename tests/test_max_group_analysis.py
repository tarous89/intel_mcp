import copy
import json

import httpx
import pytest

from intel_mcp.max_group_analysis import examined_groups, check_group_assessments, group_accounting_complete
from intel_mcp.max_report import (
    AnalysisSpecification, MaxGroupAssessment, MaxReportError, TerraMaxReportRunner,
    objective_schema, summarize_dataset,
)
from intel_mcp.max_report_quality import filter_objective, public_section
from test_max_report import _settings
from test_max_report_quality import sample


def group_fixture():
    result, rows, definitions = sample(6)
    for row in rows:
        row['segment_keys'].append('prostate')
    metadata = [{'key': 'mcrpc', 'label': 'CRPC'}, {'key': 'prostate', 'label': 'Prostate cancer'},
                {'key': 'empty', 'label': 'Narrow population'}]
    finding = result.sub_analyses[0]
    finding.visual.supports.append(finding.visual.supports[0].model_copy(update={'segment_key': 'prostate'}))
    result.group_assessments = [MaxGroupAssessment(
        segment_key=key, status='reported', reason='', trial_ids=[row['alias'] for row in rows],
        finding_titles=[finding.title],
    ) for key in ['mcrpc', 'prostate']]
    return result, rows, definitions, metadata


def test_overlapping_groups_are_accounted_for_without_summing_them():
    result, rows, definitions, metadata = group_fixture()
    groups = examined_groups(rows, metadata)
    assert [group['key'] for group in groups] == ['mcrpc', 'prostate']
    assert len(set(i for group in groups for i in group['trial_ids'])) == 6
    result = filter_objective(result, rows, definitions)
    audit = check_group_assessments(result, groups)
    assert group_accounting_complete(result)
    assert all(item['valid'] for item in audit)
    assert 'group_assessments' not in public_section(result)
    assert 'supports' not in public_section(result)['sub_analyses'][0]['visual']


@pytest.mark.parametrize('problem', ['omitted', 'duplicate', 'duplicate_titles', 'pooled_only', 'pruned', 'wrong_ids', 'vague_reason'])
def test_group_accounting_cannot_be_satisfied_by_a_pooled_total_or_stale_finding(problem):
    result, rows, definitions, metadata = group_fixture()
    if problem == 'omitted': result.group_assessments.pop()
    if problem == 'duplicate': result.group_assessments[1] = result.group_assessments[0]
    if problem == 'duplicate_titles': result.sub_analyses.append(result.sub_analyses[0].model_copy(deep=True))
    if problem == 'pooled_only': result.sub_analyses[0].visual.supports[1].segment_key = None
    if problem == 'pruned': result.sub_analyses = []
    if problem == 'wrong_ids': result.group_assessments[1].trial_ids = ['T999']
    if problem == 'vague_reason':
        result.group_assessments[1] = MaxGroupAssessment(segment_key='prostate', status='not_applicable',
                                                       reason='Not relevant.', trial_ids=[], finding_titles=[])
    check_group_assessments(result, examined_groups(rows, metadata))
    assert not group_accounting_complete(result)


def test_unassigned_trials_remain_in_scope_and_empty_groups_never_need_public_filler():
    result, rows, definitions, metadata = group_fixture()
    rows.append({'alias': 'T007', 'segment_keys': [], 'values': {'endpoint': None}})
    groups = examined_groups(rows, metadata)
    assert groups[-1]['key'] == 'unassigned_trials'
    result.group_assessments.append(MaxGroupAssessment(
        segment_key='unassigned_trials', status='insufficient_evidence', trial_ids=[], finding_titles=[],
        reason='The adjacent diagnostic study does not establish a treatment response endpoint for this comparison.',
    ))
    check_group_assessments(result, groups)
    assert group_accounting_complete(result)
    assert 'diagnostic' not in json.dumps(public_section(result))


def test_schema_requires_one_assessment_per_nonempty_group():
    schema = objective_schema(['T001'], ['broader', 'narrower'])
    assessments = schema['properties']['group_assessments']
    assert assessments['minItems'] == assessments['maxItems'] == 2
    assert assessments['items']['properties']['segment_key']['enum'] == ['broader', 'narrower']
    assert assessments['items']['properties']['trial_ids']['items']['enum'] == ['T001']
    assert schema['properties']['sub_analyses']['maxItems'] == 8


def test_group_statistics_count_trials_not_repeated_tags_and_omit_empty_groups():
    summary = summarize_dataset([
        {'segment_keys': ['broad'], 'values': {'endpoints': ['ORR', 'ORR', 'PFS']}},
        {'segment_keys': ['broad'], 'values': {'endpoints': ['ORR']}},
    ], {'endpoints': {'kind': 'categorical'}}, [{'key': 'broad', 'label': 'Broad'}, {'key': 'empty', 'label': 'Empty'}])
    assert [group['segment_key'] for group in summary['segments']] == ['all_trials', 'broad']
    assert summary['segments'][1]['variables'][0]['summary']['top_values'] == [
        {'value': 'ORR', 'count': 2}, {'value': 'PFS', 'count': 1}]


@pytest.mark.anyio
@pytest.mark.parametrize('repair', [True, False])
async def test_all_group_enforcement_uses_only_one_correction_and_never_publishes_unaccounted_groups(repair):
    result, rows, definitions, metadata = group_fixture()
    draft = result.model_dump(mode='json')
    draft['group_assessments'] = [item.model_dump() for item in result.group_assessments]
    calls = []

    def handler(request):
        payload = json.loads(request.content)
        body = json.loads(payload['input'][1]['content'][0]['text'])
        assert [group['key'] for group in body['examined_groups']] == ['mcrpc', 'prostate']
        assert len(body['evidence_rows']) == 6
        assert payload['max_output_tokens'] == 12000
        calls.append(payload)
        output = copy.deepcopy(draft)
        if len(calls) == 1 or not repair:
            output['group_assessments'] = output['group_assessments'][:1]
        return httpx.Response(200, json={'status': 'completed', 'output': [
            {'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(output)}]}]})

    runner = TerraMaxReportRunner(_settings(), transport=httpx.MockTransport(handler))
    kwargs = dict(context='Endpoint choices', pair={'maxAnalysis': {'title': result.title}},
                  specification=AnalysisSpecification(analysis_index=0, purpose='Endpoint choices', methods=['Count', 'Compare'],
                                                      variable_names=['endpoint'], segment_keys=['mcrpc']),
                  rows=[{**row, 'trial_id': 'trial-' + row['alias']} for row in rows],
                  definitions=definitions, segment_metadata=metadata)
    if repair:
        completed = await runner.analyze_objective(**kwargs)
        assert len(completed.analysis_audit['groupAssessments']) == 2
        assert completed.analysis_audit['emptyGroupsOmitted'] == ['empty']
        assert completed.analysis_audit['groupAssessments'][0]['trial_ids'][0] == 'trial-T001'
        assert 'group_assessments' not in public_section(completed)
    else:
        with pytest.raises(MaxReportError) as caught:
            await runner.analyze_objective(**kwargs)
        assert caught.value.code == 'MAX_REPORT_GROUP_ANALYSIS_INCOMPLETE'
    assert len(calls) == 2
