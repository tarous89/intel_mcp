from copy import deepcopy
import hashlib
import json
import pytest

from intel_mcp.prepared_selection import prepare_selection
from intel_mcp.selection import SelectionDataset
from intel_mcp.selection import SelectionError
from test_selection import criteria, record


def test_freeze_keeps_flexible_filters_exact_results_and_private_source_profiles():
    selection = criteria(base_text={"terms": ["lung", "EGFR"], "operator": "all",
                                   "exclude_terms": ["healthy"], "fields": ["title"]},
                         entity_countries=["DE"], function_code=1)
    rows = [record(1), record(2, direct=False, related=True)]
    rows[0]["profile"]["classification_variables"]["trial_title"] = "Étude 🧬"
    data = SelectionDataset(selection, rows)
    data.selection_origin = {"rationale": "Refined after inspecting the first search"}
    original = deepcopy(data.records)
    frozen = prepare_selection(data)
    assert frozen["criteria"] == selection.model_dump(mode="json")
    assert frozen["selection_snapshot"] == data.snapshot
    assert frozen["provenance"] == "captured-profile-content"
    restored = {}
    for item in frozen["records"]:
        assert hashlib.sha256(item["json"].encode()).hexdigest() == item["sha256"]
        restored[item["trial_id"]] = json.loads(item["json"])
    assert restored == original
    assert data.records == original
    frozen["criteria"]["base_text"]["terms"].append("mutated")
    frozen["selection_origin"]["rationale"] = "mutated"
    assert data.criteria == selection
    assert data.selection_origin["rationale"] != "mutated"


def test_refine_and_broaden_freezes_new_revision_without_mutating_previous_selection():
    first = SelectionDataset(criteria(), [record(1)])
    a = prepare_selection(first)
    narrowed = SelectionDataset(criteria(entity_countries=["DE"]), [record(1)])
    b = prepare_selection(narrowed)
    broadened = SelectionDataset(criteria(), [record(1), record(2)])
    c = prepare_selection(broadened)
    assert len({x["selection_snapshot"] for x in (a, b, c)}) == 3
    assert a == prepare_selection(first)
    assert a["records"][0] == b["records"][0] == c["records"][0]
    assert len(c["records"]) == 2


def test_changed_source_cannot_be_frozen_under_previous_identity():
    data = SelectionDataset(criteria(), [record(1)])
    next(iter(data.records.values()))["profile"]["classification_variables"]["trial_title"] = "Changed"
    with pytest.raises(SelectionError, match="SELECTION_CHANGED"):
        prepare_selection(data)
