from copy import deepcopy
from dataclasses import replace
import json

import httpx
import pytest

from intel_mcp.max_candidate_screening import CandidateAssessment, select_screened_candidates
from intel_mcp.max_source_text import source_passages, SOURCE_TEXT_BUDGET
from intel_mcp.max_report import TerraMaxReportRunner, AnalysisSpecification
from intel_mcp.profiles import FullProfileItem
from intel_mcp.report_plan import REPORT_PLAN_INSTRUCTIONS
from intel_mcp.engine_read.filtering import build_where
from intel_mcp.server import settings
from test_max_report_quality import sample
from intel_mcp.max_report_quality import filter_objective, public_section

@pytest.fixture
def anyio_backend():
    return 'asyncio'


def test_unassigned_adjacent_trials_fill_the_shared_100_without_padding_irrelevance():
    candidates = [CandidateAssessment(trial_id=str(i), tier='adjacent', relevance_score=70,
        segment_keys=[], uncertain_segment_keys=[], rationale='Transferable endpoint experience.') for i in range(125)]
    candidates.append(CandidateAssessment(trial_id='irrelevant', tier='exclude', relevance_score=99,
        segment_keys=[], uncertain_segment_keys=[], rationale='Unrelated indication and intervention.'))
    selected = select_screened_candidates(candidates, segment_cohort_indices={'primary': 0, 'broader': 1},
                                         maximum=100, trial_cohort_indices={})
    assert len(selected) == len({item.trial_id for item in selected}) == 100
    assert all(item.tier == 'adjacent' and not item.segment_keys for item in selected)


def test_max_text_discovery_searches_narrative_without_changing_public_title_semantics():
    filters = {'trial_title': {'operator': 'contains', 'value': "prostat%'"}}
    sql, params = build_where(filters, all_profiles=True)
    assert 'report_search_v1' in sql and 'search_text' in sql
    assert "prostat%'" not in sql  # parameterized, LIKE wildcards escaped
    assert params == ["%prostat\\%'%"] * 2
    public_sql, _ = build_where(filters)
    assert 'profile_json' not in public_sql and 'approved' in public_sql


def test_source_access_recovers_late_narrative_and_remains_bounded_at_future_sizes():
    profile = {'classification_variables': {'trial_title': 'Study of a treatment'},
               'filtering_variables': {'inclusion_criteria': 'Routine criteria. ' * 100 + 'Bone metastases require imaging confirmation and measurable disease.'}}
    for size in (100, 300, 500):
        limit = SOURCE_TEXT_BUDGET // size
        text = source_passages(profile, 'Bone metastases imaging confirmation', limit)
        assert len(text) <= limit
        assert 'Bone metastases' in text or 'imaging confirmation' in text


def test_independent_supported_series_survives_an_empty_series():
    result, rows, definitions = sample()
    visual = result.sub_analyses[0].visual
    visual.kind = 'bar'; visual.values.append(0); visual.labels.append('Other designs')
    kept = filter_objective(result, rows, definitions)
    assert kept.sub_analyses[0].visual.values == [6]
    assert kept.sub_analyses[0].visual.labels == ['Studies']
    assert kept.qa_warnings and kept.summary_sentences == ['']


def test_adjacent_trial_can_be_a_directly_relevant_descriptive_precedent_for_this_objective():
    result, rows, definitions = sample(2, 'adjacent')
    for row in rows:
        row['values']['source_text'] = 'Objective response endpoint in measurable prostate cancer.'
    definitions['source_text'] = {'kind': 'text'}
    result.sub_analyses[0].small_sample_reason = 'Measurable prostate cancer and objective response provide a concrete endpoint precedent for this decision.'
    assert len(filter_objective(result, rows, definitions).sub_analyses) == 1


def test_planner_requests_actual_broadening_and_narrowing_without_objective_admission_rules():
    assert '1 to 2 clinically broader cohorts AND 1 to 2 narrower cohorts' in REPORT_PLAN_INSTRUCTIONS
    assert 'not admission rules or objective assignments' in REPORT_PLAN_INSTRUCTIONS
    assert 'including unapproved profiles' in REPORT_PLAN_INSTRUCTIONS
    assert len(REPORT_PLAN_INSTRUCTIONS) < 9500


@pytest.mark.anyio
async def test_analyst_sees_unstructured_source_and_repair_uses_one_existing_call_budget():
    draft, alias_rows, definitions = sample()
    original = draft.model_dump(mode='json')
    calls = []
    async def handler(request):
        payload = json.loads(request.content)
        calls.append(payload)
        evidence = json.loads(payload['input'][1]['content'][0]['text'])
        assert len(evidence['evidence_rows']) == 6
        assert all('Phase II ADC' in row['values']['source_text'] for row in evidence['evidence_rows'])
        if len(calls) == 1:
            output = deepcopy(original)
            output['sub_analyses'][0]['items'] = [{'label': 'Weak recommendation', 'value': '1', 'explanation': 'A possible option.', 'trial_ids': ['T001']}]
        else:
            assert 'PUBLICATION CORRECTION' in payload['input'][0]['content'][0]['text']
            output = original
        return httpx.Response(200, json={'status': 'completed', 'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(output)}]}]})
    rows = [{'trial_id': f'2026-{i:06}-00-00', 'values': {'endpoint': 'ORR'}, 'segment_keys': ['mcrpc']} for i in range(6)]
    profiles = [FullProfileItem(eu_number=row['trial_id'], profile_schema_version='11.0.0', approved_at=None,
        approval_status='deterministic', profile={'classification_variables': {'trial_title': 'Phase II ADC study in prostate cancer'}}) for row in rows]
    runner = TerraMaxReportRunner(replace(settings, openai_api_key='test-key'), transport=httpx.MockTransport(handler))
    result = await runner.analyze_objective(context='Endpoint choices', pair={'maxAnalysis': {'title': draft.title}},
        specification=AnalysisSpecification(analysis_index=0, purpose='Choose endpoints', methods=['Count', 'Compare'], variable_names=['endpoint'], segment_keys=[]),
        rows=rows, definitions=definitions, segment_metadata=[], profiles=profiles)
    assert len(calls) == 2
    assert len(result.sub_analyses) == 1 and not result.sub_analyses[0].items
    assert len(result.analysis_audit['sourcePassages']) == 6
    assert result.analysis_audit['attempts'][0]['issues']
    assert 'analysis_audit' not in public_section(result)
