import pytest
from pydantic import ValidationError
from intel_mcp.engine_read.selection import read_selection
from intel_mcp.selection import MAX_COHORT, SelectionError
from test_selection import criteria, record


class Connection:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []
    def execute(self, sql, params):
        self.calls.append((sql, params))
        return self
    def cursor(self, *, name):
        assert name == 'selection_profiles'
        return self
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return None
    def fetchmany(self, size):
        assert size == 10
        batch, self.rows = self.rows[:size], self.rows[size:]
        return batch


def dbrow(i=1):
    r = record(i)
    return (r['trial_id'], '11.0.0', r['profile'], None, True, False)


def test_query_reuses_validated_filters_and_single_statement_snapshot():
    c = Connection([dbrow()])
    request = criteria(direct={"diseases": {"values": ["lung' OR TRUE --"]}, "phase": {"values": [2]}},
                       related={"modalities": {"values": ["Small molecule"]}})
    result = read_selection(c, request.model_dump(mode='json'))
    assert result.summary().counts['direct'] == 1
    assert len(c.calls) == 1
    sql, params = c.calls[0]
    assert 'approved_profiles_v1' in sql and 'profile_filter_v1' in sql
    assert "lung' OR TRUE --" not in sql
    assert any("lung' OR TRUE --" in str(p) for p in params)
    assert params[-1] == MAX_COHORT + 1
    assert "report_profiles" not in sql
    assert 'phase' in sql


def test_latest_eight_hundred_cap_applies_before_full_profile_load():
    c = Connection([dbrow()])
    chosen = criteria(max_recent_trials=800)
    result = read_selection(c, chosen.model_dump(mode='json'))
    sql, params = c.calls[0]
    assert 'ORDER BY p.latest_country_submission_or_approval_date DESC NULLS LAST, p.eu_number ASC' in sql
    assert params[-1] == 800
    assert result.summary().counts['base'] == 1
    assert 'latest 800' in ' '.join(result.summary().limitations)
    assert result.criteria.max_recent_trials == 800
    with pytest.raises(ValidationError):
        criteria(max_recent_trials=801)
    with pytest.raises(ValidationError):
        criteria(max_recent_trials=0)


def test_never_return_partial_or_ambiguous_cohort():
    for rows, error in (([dbrow()] * (MAX_COHORT + 1), 'COHORT_TOO_LARGE'),
                        ([dbrow(), dbrow()], 'AMBIGUOUS_PROFILE'),
                        ([(dbrow()[0], '10.0.0', {}, None, True, False)], 'UNSUPPORTED_PROFILE')):
        with pytest.raises(SelectionError, match=error):
            read_selection(Connection(rows), criteria().model_dump(mode='json'))

def test_optional_cap_preserves_uncapped_serialization():
    assert "max_recent_trials" not in criteria().model_dump(mode="json")
    assert "max_recent_trials" not in criteria(max_recent_trials=None).model_dump(mode="json")
    assert criteria(max_recent_trials=800).model_dump(mode="json")["max_recent_trials"] == 800
    for invalid in (True, 1.5, "800"):
        with pytest.raises(ValidationError):
            criteria(max_recent_trials=invalid)
