from copy import deepcopy
import pytest
from pydantic import ValidationError
from intel_mcp.selection import SelectionDataset, SelectionError
from intel_mcp.selection_discovery import TextQuery
from intel_mcp.engine_read.selection import read_selection, _text_where
from test_selection import criteria, record, provider
from test_selection_read import Connection


def groups():
    return [
        {"id": "exact", "label": "Phase III hormone-sensitive", "bucket": "direct",
         "filters": {"phase": {"values": [3]}}, "phase_title_fallback": True,
         "text": {"fields": ["title", "population"], "terms": ["hormone-sensitive"]}},
        {"id": "prostate", "label": "Other prostate cancer", "bucket": "related",
         "text": {"fields": ["title"], "terms": ["prostate cancer"]}},
    ]


def test_disjoint_groups_keep_overlapping_tags_and_drilldown():
    rows = [record(1), record(2), record(3)]
    for row, flags in zip(rows, [[True, True], [False, True], [False, False]]):
        row['subgroup_matches'] = flags
    d = SelectionDataset(criteria(subgroups=groups(), include_broader=True), rows)
    assert d.summary().counts == {'base': 3, 'direct': 1, 'related': 1, 'broader': 1}
    assert [g['count'] for g in d.summary().subgroups] == [1, 1, 1]
    assert d.summary().subgroups[1]['overlapping_count'] == 2
    page = d.cohort_trials(limit=1)
    assert page.total_trials == 3 and page.next_offset == 1
    assert page.trials[0]['subgroup_tags'] == ['exact', 'prostate']
    assert d.cohort_trials(subgroup_ids=['unmatched']).total_trials == 1
    assert d.rank().entities[0].trial_counts['total'] == 3
    scoped = d.rank(subgroup_ids=['prostate'])
    assert scoped.entities[0].trial_counts['total'] == 1
    assert scoped.cohort.snapshot == d.snapshot
    assert d.evidence(scoped.entities[0].id, subgroup_ids=['prostate']).trials[0]['trial_id'] == rows[1]['trial_id']
    with pytest.raises(SelectionError, match='UNKNOWN_SUBGROUP'):
        d.rank(subgroup_ids=['bad'])
    with pytest.raises(SelectionError, match='MISSING_SUBGROUP'):
        SelectionDataset(criteria(subgroups=groups()), [record()])


def test_title_search_without_ta_and_parameterized_literal_patterns():
    text = {'fields': ['title', 'population'], 'terms': ["prostate' OR TRUE --", '100%_response'], 'exclude_terms': ['benign']}
    c = criteria(base={}, base_text=text, subgroups=groups())
    row = record(); row['profile']['classification_variables']['trial_title'] = "Phase III prostate' OR TRUE --"
    connection = Connection([(row['trial_id'], '11.0.0', row['profile'], None, True, False, True, False)])
    result = read_selection(connection, c.model_dump(mode='json'))
    sql, params = connection.calls[0]
    assert "prostate' OR TRUE --" not in sql
    assert '%100\\%\\_response%' in params
    assert 'cardinality(p.phase)' in sql
    assert result.records[row['trial_id']]['discovery_evidence'][0]['field'] == 'title'
    with pytest.raises(ValidationError):
        criteria(base={})
    with pytest.raises(ValidationError):
        TextQuery(fields=['contacts'], terms=['prostate'])
    with pytest.raises(ValidationError):
        TextQuery(fields=['title'], terms=['  '])


def test_pi_alias_reencounter_does_not_recreate_empty_person():
    # A record that became an alias in an earlier trial is encountered twice.
    rows = [record(i) for i in range(1, 10)]
    for row in rows:
        sites = row['profile']['classification_variables']['sites']
        sites.extend(deepcopy(sites) * 2)
    result = SelectionDataset(criteria('pis'), rows).rank()
    assert result.total_entities == 1
    assert result.entities[0].trial_counts['total'] == 9


def test_pi_missing_ta_dedups_at_site_but_not_namesakes_elsewhere():
    rows = [record(i) for i in range(1, 4)]
    for row in rows:
        row['profile']['filtering_variables']['therapeutic_areas'] = []
        row['profile']['classification_variables']['sites'][0]['investigators'][0]['email'] = ''
    rows[2]['profile']['classification_variables']['sites'][0]['name'] = 'Other Hospital'
    result = SelectionDataset(criteria('pis'), rows).rank()
    assert result.total_entities == 2
    assert [e.trial_counts['total'] for e in result.entities] == [2, 1]


def test_shared_email_does_not_merge_different_complete_names():
    rows = [record(1), record(2)]
    person = rows[1]['profile']['classification_variables']['sites'][0]['investigators'][0]
    person['last_name'] = 'Different'
    assert SelectionDataset(criteria('pis'), rows).rank().total_entities == 2


def test_reviewed_group_union_preserves_roles_and_country_before_merge():
    spain = {**provider('Syneos Health Clinical Spain S.L.U.'), 'country_code': 'ES'}
    uk = {**provider('Syneos Health UK Limited', 'Data management'), 'country_code': 'GB'}
    rows = [record(1, providers=[spain, uk]), record(2, providers=[uk])]
    d = SelectionDataset(criteria(), rows)
    result = d.rank()
    assert result.total_entities == 1
    assert result.entities[0].name == 'Syneos Health'
    assert result.entities[0].trial_counts['total'] == 2
    assert len(result.entities[0].legal_entities) == 2
    filtered = SelectionDataset(criteria(function_code=1), rows).rank().entities[0]
    assert filtered.trial_counts['total'] == 1
    assert '6' not in filtered.function_counts
    assert filtered.countries == ['ES']
    assert SelectionDataset(criteria(cro_identity='legal_entity'), rows).rank().total_entities == 2
    assert SelectionDataset(criteria(entity_countries=['GB'], function_code=1), rows).rank().total_entities == 0
    impostor = {**spain, 'name': spain['name'] + ' Partner'}
    assert SelectionDataset(criteria(), [record(providers=[spain, impostor])]).rank().total_entities == 2


def test_default_ten():
    d = SelectionDataset(criteria(), [record(i, providers=[provider(str(i))]) for i in range(1, 21)])
    assert d.rank().returned == 10
    assert d.rank(10).returned == 10


def test_iqvia_reviewed_exact_aliases_union_and_snapshot_version(monkeypatch):
    rows = [record(providers=[{**provider('IQVIA Limited'), 'country_code': 'GB'},
                              {**provider('IQVIA RDS Spain S.L.'), 'country_code': 'ES'}])]
    d = SelectionDataset(criteria(), rows)
    assert d.rank().total_entities == 1
    assert d.rank().entities[0].name == 'IQVIA'
    assert d.rank().entities[0].trial_counts['total'] == 1
    from intel_mcp import selection
    monkeypatch.setattr(selection, 'IDENTITY_VERSION', 'next-review')
    assert SelectionDataset(criteria(), rows).snapshot != d.snapshot
