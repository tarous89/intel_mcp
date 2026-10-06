"""Real SQL execution against synthetic data in a disposable CI database only."""
import os
import pytest
import psycopg
from psycopg.types.json import Jsonb
from intel_mcp.engine_read.selection import read_selection
from test_selection import criteria, record
from test_selection_discovery import groups

DSN = os.environ.get('TEST_SELECTION_DATABASE_URL')
pytestmark = pytest.mark.skipif(not DSN, reason='Dedicated PostgreSQL test database not configured')


@pytest.fixture
def connection():
    with psycopg.connect(DSN) as conn:
        # Never touch a database with an existing serving schema.
        if conn.execute("SELECT to_regnamespace('mcp_serving')").fetchone()[0] is not None:
            pytest.fail('Refusing to use a database with an existing mcp_serving schema')
        conn.execute('CREATE SCHEMA mcp_serving')
        conn.execute('CREATE TABLE mcp_serving.profile_filter_v1 (id integer, eu_number text, approval_status text, phase integer[])')
        conn.execute('CREATE TABLE mcp_serving.approved_profiles_v1 (eu_number text, schema_version text, profile_json jsonb, ctis_data jsonb)')
        yield conn
        conn.rollback()


def insert(conn, i, title, phase=None, population=''):
    row = record(i)
    row['profile']['classification_variables'].update(trial_title=title, target_population_summary=population)
    row['profile']['filtering_variables']['phase'] = phase
    conn.execute('INSERT INTO mcp_serving.profile_filter_v1 VALUES (%s,%s,%s,%s)', (i, row['trial_id'], 'approved', phase))
    conn.execute('INSERT INTO mcp_serving.approved_profiles_v1 VALUES (%s,%s,%s,NULL)', (row['trial_id'], '11.0.0', Jsonb(row['profile'])))


def test_missing_phase_title_fallback_conflicts_and_exclusions(connection):
    insert(connection, 1, 'Phase III hormone-sensitive prostate cancer', None)
    insert(connection, 2, 'Phase III hormone-sensitive prostate cancer', [2])  # structured contradiction wins
    insert(connection, 3, 'Phase II prostate cancer', [])
    insert(connection, 4, 'Benign prostate enlargement Phase III', None)
    insert(connection, 5, 'Prostate cancer study', [3], 'Hormone-sensitive disease')
    insert(connection, 6, 'Prostate cancer study', None)  # unknown is not phase III
    request = criteria(base={}, base_text={'fields': ['title'], 'terms': ['prostate'], 'exclude_terms': ['benign']}, subgroups=groups(), include_broader=True)
    dataset = read_selection(connection, request.model_dump(mode='json'))
    assert dataset.summary().counts == {'base': 5, 'direct': 2, 'related': 3, 'broader': 0}
    assert [g['count'] for g in dataset.summary().subgroups] == [2, 3, 0]
    assert dataset.summary().subgroups[1]['overlapping_count'] == 5
    evidence = dataset.records['2024-000001-00-00']['discovery_evidence']
    assert any(e.get('basis') == 'title_fallback' for e in evidence)
    assert any(e.get('basis') == 'structured' for e in dataset.records['2024-000005-00-00']['discovery_evidence'])


def test_literal_wildcards_and_no_sql_injection(connection):
    insert(connection, 1, "Prostate 100%_response ' OR TRUE --")
    insert(connection, 2, 'Prostate 100XXresponse')
    request = criteria(base={}, base_text={'fields': ['title'], 'terms': ['100%_response', "' OR TRUE --"], 'operator': 'all'})
    dataset = read_selection(connection, request.model_dump(mode='json'))
    assert list(dataset.records) == ['2024-000001-00-00']
