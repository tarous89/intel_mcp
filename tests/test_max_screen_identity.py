"""Regression for the 2026-09-14 candidate-screen identity failure."""
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace

import httpx
import jsonschema
import pytest

from intel_mcp.max_candidate_screening import candidate_screen_schema, validate_candidate_screen
from intel_mcp.max_report import AnalysisSpecification, TerraMaxReportRunner, MaxReportError
from intel_mcp.max_report_execution import MaxReportExecutor
from intel_mcp.server import settings

@pytest.fixture
def anyio_backend():
    return 'asyncio'


def assessment(tier='adjacent'):
    return {'tier': tier, 'relevance_score': 70, 'segment_keys': [],
            'uncertain_segment_keys': [], 'rationale': 'Transferable clinical experience.'}


@pytest.mark.parametrize('form', ['keyed', 'legacy'])
@pytest.mark.parametrize('failure', ['missing', 'unknown', 'duplicate'])
def test_identity_errors_remain_rejected(form, failure):
    records = [{'trial_id': 'T1', **assessment('exact')}, {'trial_id': 'T2', **assessment()}]
    if failure == 'missing': records.pop()
    elif failure == 'unknown': records[1]['trial_id'] = 'UNKNOWN'
    else: records[1]['trial_id'] = 'T1'
    payload = {'assessments': records if form == 'legacy' else {
        row['trial_id']: {k: v for k, v in row.items() if k != 'trial_id'} for row in records
    }}
    with pytest.raises(ValueError):
        validate_candidate_screen(payload, trial_ids=['T1', 'T2'], segment_keys=['primary'])


def test_strict_schema_requires_exact_trial_keys_and_accepts_any_order():
    schema = candidate_screen_schema(['T1', 'T2'], ['primary'])
    payload = {'assessments': {'T2': assessment(), 'T1': assessment('exact')}}
    jsonschema.validate(payload, schema)
    result = validate_candidate_screen(payload, trial_ids=['T1', 'T2'], segment_keys=['primary'])
    assert [(item.trial_id, item.tier) for item in result] == [('T1', 'exact'), ('T2', 'adjacent')]
    for invalid in ({'T1': assessment()}, {**payload['assessments'], 'UNKNOWN': assessment()}):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate({'assessments': invalid}, schema)
    invalid = deepcopy(payload)
    invalid['assessments']['T1']['rationale'] = 'x' * 501
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(invalid, schema)


def test_nine_planned_segments_fit_both_schema_and_runtime():
    segments = [f'segment_{i}' for i in range(9)]
    payload = {'assessments': {'T1': {**assessment(), 'segment_keys': segments}}}
    jsonschema.validate(payload, candidate_screen_schema(['T1'], segments))
    result = validate_candidate_screen(payload, trial_ids=['T1'], segment_keys=segments)
    assert result[0].segment_keys == segments
    assert AnalysisSpecification(analysis_index=0, purpose='Compare designs', methods=['Count', 'Compare'],
        variable_names=['phase'], segment_keys=segments).segment_keys == segments


@pytest.mark.parametrize('failure', ['unknown_segment', 'contradictory_segment', 'duplicate_segment', 'conflicting_id'])
def test_keyed_contract_preserves_scientific_validation(failure):
    row = assessment()
    if failure == 'unknown_segment': row['segment_keys'] = ['invented']
    elif failure == 'contradictory_segment': row.update(segment_keys=['primary'], uncertain_segment_keys=['primary'])
    elif failure == 'duplicate_segment': row['segment_keys'] = ['primary', 'primary']
    else: row['trial_id'] = 'ANOTHER'
    with pytest.raises(ValueError):
        validate_candidate_screen({'assessments': {'T1': row}}, trial_ids=['T1'], segment_keys=['primary'])


@pytest.mark.anyio
async def test_reversed_batches_keep_all_candidates_with_no_extra_model_calls():
    calls, reservations = [], []
    async def handler(request):
        body = json.loads(request.content)
        calls.append(body)
        assert body['model'] == 'gpt-5.6-sol'
        assert body['max_output_tokens'] == 10000
        assert body['text']['format']['name'] == 'intel_max_candidate_screen_v2'
        data = json.loads(body['input'][1]['content'][0]['text'])
        ids = [row['trial_id'] for row in data['candidate_profiles']]
        response = {'assessments': {trial_id: assessment('exact' if trial_id == 'T000' else 'adjacent') for trial_id in reversed(ids)}}
        jsonschema.validate(response, body['text']['format']['schema'])
        return httpx.Response(200, json={'status': 'completed', 'output': [{'type': 'message',
            'content': [{'type': 'output_text', 'text': json.dumps(response)}]}]})
    class Control:
        async def authorize_classifications(self, analysis_id, keys, operation):
            reservations.append((operation, tuple(keys)))
            return SimpleNamespace(access=SimpleNamespace(allowed_classification_keys=keys))
    executor = object.__new__(MaxReportExecutor)
    executor._analysis_control = Control()
    executor._runner = TerraMaxReportRunner(replace(settings, openai_api_key='test-key'), transport=httpx.MockTransport(handler))
    candidates = [{'trial_id': f'T{i:03d}', 'profile': {}} for i in range(100)]
    result = await executor._screen_candidates(analysis_id='test-analysis', context='Clinical experience', insights='Designs',
        approved_plan={}, segment_metadata=[{'key':'primary','label':'Clinical studies','cohort_index':0,
            'cohort_title':'Clinical studies','inclusion_criteria':[],'exclusion_criteria':[]}], candidates=candidates)
    assert len(calls) == 4  # same four batches, no correction or repeated screening
    assert [item.trial_id for item in result] == [item['trial_id'] for item in candidates]
    assert result[0].tier == 'exact' and all(item.tier == 'adjacent' for item in result[1:])
    assert sorted(keys for operation, keys in reservations if operation == 'reserve') == sorted(keys for operation, keys in reservations if operation == 'commit')
    assert not any(operation == 'release' for operation, _ in reservations)


@pytest.mark.anyio
async def test_invalid_screen_logs_a_safe_specific_reason_without_trial_content(caplog):
    async def handler(request):
        return httpx.Response(200, json={'status':'completed', 'output':[{'type':'message','content':[
            {'type':'output_text','text':json.dumps({'assessments': {'PRIVATE_TRIAL': assessment()}})}]}]})
    runner = TerraMaxReportRunner(replace(settings, openai_api_key='test-key'), transport=httpx.MockTransport(handler))
    with pytest.raises(MaxReportError) as caught:
        await runner.screen_candidate_batch(context='Test', insights='Test', approved_plan={},
            segment_metadata=[{'key':'primary'}], candidates=[{'trial_id':'T1','profile':{}}])
    assert caught.value.code == 'MAX_REPORT_CANDIDATE_SCREEN_INVALID'
    assert 'unknown trial IDs' in caplog.text
    assert 'PRIVATE_TRIAL' not in caplog.text
