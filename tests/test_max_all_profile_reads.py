import asyncio
from intel_mcp.engine_read.filtering import filter_approved_trials
from intel_mcp.engine_read.profile_retrieval import get_approved_profiles
from intel_mcp.max_report_execution import MaxReportExecutor
from intel_mcp.max_candidate_screening import CandidateFilter
from intel_mcp.engine_database import DatabaseEngineClient
from test_engine_database import database_settings


class Result:
    def __init__(self, rows): self.rows = rows
    def fetchone(self): return self.rows[0]
    def fetchall(self): return self.rows


class DB:
    def __init__(self): self.queries = []
    def execute(self, query, params=()):
        self.queries.append((query, params))
        if 'COUNT(*)' in query: return Result([(2,)])
        if 'profile.profile_json' in query:
            return Result([('2024-516036-94-00', '11.0.0', None, {}, None, 'deterministic')])
        return Result([('2024-516036-94-00', 'A prostate study', 'Sponsor')])


def test_max_filters_use_all_four_scoped_views_without_an_approval_predicate():
    db = DB()
    result = filter_approved_trials(db, {'filters': {'diseases': {'values': ['Prostate cancer']}, 'countries': [{'country_codes': {'values': ['DE']}}]}}, all_profiles=True)
    sql = ' '.join(q for q, _ in db.queries)
    assert 'report_filter_v1' in sql and 'report_countries_v1' in sql and 'report_diseases_v1' in sql
    assert "approval_status = 'approved'" not in sql
    assert result['data'][0]['eu_number'] == '2024-516036-94-00'


def test_complete_deterministic_profile_is_retrievable_and_status_is_preserved():
    db = DB()
    result = get_approved_profiles(db, {'trial_ids': ['2024-516036-94-00']}, all_profiles=True)
    assert result['unavailable_trial_ids'] == []
    assert result['data'][0]['approval_status'] == 'deterministic'
    assert result['data'][0]['approved_at'] is None
    assert 'mcp_serving.report_profiles_v1' in db.queries[0][0]


def test_default_light_and_site_reads_keep_the_existing_approved_contract():
    db = DB()
    filter_approved_trials(db, {'filters': {}})
    get_approved_profiles(db, {'trial_ids': ['2024-516036-94-00']})
    sql = ' '.join(q for q, _ in db.queries)
    assert 'report_profiles_v1' not in sql and 'report_filter_v1' not in sql
    assert "p.approval_status = 'approved'" in sql
    assert 'mcp_serving.approved_profiles_v1' in sql


def test_only_max_executor_opts_in_and_title_only_discovery_is_valid():
    settings = database_settings()
    assert DatabaseEngineClient(settings)._all_profiles is False
    assert MaxReportExecutor(settings)._engine._all_profiles is True
    assert CandidateFilter(label='Prostate variants', title_terms=['prostat', 'mCRPC']).title_terms
