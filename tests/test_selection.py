from copy import deepcopy
from datetime import date

import pytest
from pydantic import ValidationError
from intel_mcp.selection import SelectionCriteria, SelectionDataset, SelectionError, MAX_COHORT


def criteria(kind="cros", **overrides):
    return SelectionCriteria.model_validate({"base": {"therapeutic_areas": {"values": ["Solid Tumor Oncology"]}},
        "entity_type": kind, "as_of": "2026-10-06", **overrides})


def record(i=1, *, direct=True, related=False, providers=None):
    return {"trial_id": f"2024-{i:06d}-00-00", "schema_version": "11.0.0", "direct": direct, "related": related,
        "profile": {"filtering_variables": {"therapeutic_areas": ["Solid Tumor Oncology"], "phase": [2], "modality": "Small molecule"},
            "classification_variables": {"trial_title": f"Study {i}", "diseases": ["Lung cancer"],
                "sponsor": {"name": "Sponsor GmbH"},
                "third_party_organizations": providers if providers is not None else [provider()],
                "sites": [{"name": "Hospital", "country_code": "DE", "investigators": [
                    {"first_name": "Ada", "last_name": "Example", "email": "ada@example.test"}]}]},
            "ctis_lifecycle": {"countries": [{"country_code": "DE", "updates": [
                {"label": "Decision", "date": "2026-08-01", "outcome": "Authorised"}]}]},
            "results": {"trial_operational_findings": ["Recruitment extended."]}}}


def provider(name="Example CRO", function="On site monitoring"):
    return {"name": name, "country_code": "DE", "function": function}


def test_role_specific_distinct_trials_and_disjoint_matches():
    rows = [record(1, direct=True, related=True, providers=[provider(), provider(), provider(function="Data management")]),
        record(2, direct=False, related=True), record(3, direct=False),
        record(4, providers=[provider("Big CRO", "Laboratory analysis")])]
    dataset = SelectionDataset(criteria(function_code=1), rows)
    assert dataset.summary().counts == {"base": 4, "direct": 2, "related": 1, "broader": 1}
    result = dataset.rank()
    assert result.total_entities == 1
    assert result.entities[0].trial_counts == {"direct": 1, "related": 1, "broader": 0, "total": 2}
    assert result.entities[0].function_counts["1"] == 2
    assert result.entities[0].sponsors[0]["trial_count"] == 2
    assert result.entities[0].evidence[0]["findings_attribution"] == "trial_only"


def test_direct_experience_beats_larger_related_provider():
    rows = [record(1, providers=[provider("Specialist")])]
    rows += [record(i, direct=False, related=True, providers=[provider("Large")]) for i in range(2, 15)]
    assert SelectionDataset(criteria(), rows).rank().entities[0].name == "Specialist"


def test_top_ten_applies_after_complete_aggregation():
    rows = [record(i, providers=[provider(f"CRO {i:02d}")]) for i in range(1, 21)]
    rows += [record(21, providers=[provider("CRO 20")])]
    result = SelectionDataset(criteria(), rows).rank()
    assert result.total_entities == 20 and result.returned == 10
    assert result.entities[0].name == "CRO 20"


@pytest.mark.parametrize("kind", ["sites", "pis"])
def test_site_pi_dedup_and_country(kind):
    rows = [record(1), record(2, direct=False, related=True)]
    rows[0]["profile"]["classification_variables"]["sites"] *= 2
    result = SelectionDataset(criteria(kind), rows).rank()
    assert result.total_entities == 1
    assert result.entities[0].trial_counts["total"] == 2
    assert result.entities[0].recent_authorization_trials == 2
    assert SelectionDataset(criteria(kind, entity_countries=["PL"]), rows).rank().returned == 0


def test_stable_snapshot_ties_and_evidence_pagination():
    rows = [record(i) for i in range(1, 15)]
    a = SelectionDataset(criteria(), rows)
    b = SelectionDataset(criteria(), list(reversed(rows)))
    assert a.snapshot == b.snapshot
    assert a.rank() == b.rank()
    entity_id = a.rank().entities[0].id
    first = a.evidence(entity_id)
    second = a.evidence(entity_id, first.next_offset)
    assert len(first.trials) == 10 and len(second.trials) == 4 and second.next_offset is None
    assert not {r["trial_id"] for r in first.trials} & {r["trial_id"] for r in second.trials}
    changed = deepcopy(rows)
    changed[0]["profile"]["results"]["trial_operational_findings"] = []
    with pytest.raises(SelectionError, match="SELECTION_CHANGED"):
        SelectionDataset(criteria(), changed).check_snapshot(a.snapshot)


def test_limits_and_unknowns_are_not_padded():
    assert SelectionDataset(criteria(), []).rank().returned == 0
    with pytest.raises(SelectionError, match="AMBIGUOUS_PROFILE"):
        SelectionDataset(criteria(), [record(), record()])
    with pytest.raises(SelectionError, match="COHORT_TOO_LARGE"):
        SelectionDataset(criteria(), [record(i) for i in range(MAX_COHORT + 1)])
    with pytest.raises(SelectionError, match="ENTITY_NOT_IN_SELECTION"):
        SelectionDataset(criteria(), [record()]).evidence("missing")
    assert SelectionDataset(criteria(function_code=1), [record(providers=[provider(function="Unknown role")])]).rank().returned == 0


def test_countries_do_not_merge_cro_legal_entities():
    other = provider(); other["country_code"] = "PL"
    dataset = SelectionDataset(criteria(), [record(providers=[provider(), other])])
    assert dataset.rank().total_entities == 2


def test_criteria_requires_scope_and_explicit_relaxation():
    for overrides in ({"base": {}}, {"related": {}}, {"entity_type": "pis", "function_code": 1},
                      {"function_code": True}, {"entity_countries": ["Germany"]}):
        with pytest.raises(ValidationError):
            criteria(**overrides)


def test_broader_experience_is_opt_in():
    rows = [record(direct=False)]
    assert SelectionDataset(criteria(), rows).rank().returned == 0
    assert SelectionDataset(criteria(include_broader=True), rows).rank().entities[0].trial_counts["broader"] == 1


def test_function_evidence_unions_separate_provider_rows_in_same_trial():
    rows = [record(providers=[provider(), provider(function='Data management')]),
            record(2, providers=[provider(function='Data management')])]
    result = SelectionDataset(criteria(function_code=1), rows).rank().entities[0]
    assert result.trial_counts['total'] == 1
    assert result.function_counts == {'1': 1, '6': 1}
    assert result.evidence[0]['roles'] == ['Data management', 'On site monitoring']


def test_pi_recency_uses_its_affiliation_in_each_trial():
    rows = [record(1), record(2)]
    rows[0]['profile']['classification_variables']['sites'][0]['country_code'] = 'FR'
    # The first trial is recently authorised only in DE, where this PI is not listed.
    result = SelectionDataset(criteria('pis'), rows).rank().entities[0]
    assert result.trial_counts['total'] == 2
    assert result.recent_authorization_trials == 1
