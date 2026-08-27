from __future__ import annotations

from mcp import Client
import pytest

from intel_mcp.classification import (
    AppClassificationAccess,
    AppClassificationAccessResponse,
    ClassificationProfileItem,
    CriterionResult,
    EngineClassificationProfilesResponse,
    TrialWorkerResult,
    aggregate_trial_result,
    classification_key,
)
from intel_mcp.server import mcp


class StubClassificationControlPlane:
    def __init__(self) -> None:
        self.operations: list[str] = []

    async def authorize_classifications(
        self, analysis_id: str, classification_keys: list[str], operation: str = "reserve"
    ) -> AppClassificationAccessResponse:
        assert analysis_id == "ana_123456789012345678901234"
        self.operations.append(operation)
        return AppClassificationAccessResponse(
            access=AppClassificationAccess(
                allowedClassificationKeys=classification_keys,
                limit=200,
                used=len(classification_keys) if operation == "commit" else 0,
                remaining=200 - len(classification_keys),
                exhausted=False,
            )
        )


class StubClassificationEngine:
    async def classification_profiles(self, trial_ids: list[str]) -> EngineClassificationProfilesResponse:
        return EngineClassificationProfilesResponse(
            data=[ClassificationProfileItem(eu_number=trial_id, profile={"trial_title": trial_id}) for trial_id in trial_ids],
            schema_version="1.0.0",
        )


def test_ineligible_precedes_uncertain() -> None:
    result = TrialWorkerResult(
        trial_id="2024-500001-00-00",
        inclusion_results=[
            CriterionResult(criterion_id="i1", classification=False, evidence="Profile contradicts i1."),
            CriterionResult(criterion_id="i2", classification=None, evidence="i2 is not stated."),
        ],
        exclusion_results=[
            CriterionResult(criterion_id="e1", classification=False, evidence="Exclusion is affirmatively absent."),
        ],
    )
    assert aggregate_trial_result(result) == "ineligible"


def test_classification_key_is_stable_when_criteria_are_reordered() -> None:
    first = classification_key(
        "2024-500001-00-00",
        ["Condition A", "Condition B"],
        ["Exclude A", "Exclude B"],
    )
    second = classification_key(
        "2024-500001-00-00",
        ["Condition B", "Condition A"],
        ["Exclude B", "Exclude A"],
    )
    assert first == second


@pytest.mark.anyio
async def test_classify_trials_returns_trial_id_buckets_and_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    trial_ids = ["2024-500001-00-00", "2024-500002-00-00", "2024-500003-00-00"]
    control = StubClassificationControlPlane()
    monkeypatch.setattr("intel_mcp.server.control_plane_client", lambda: control)
    monkeypatch.setattr("intel_mcp.server.engine_client", lambda: StubClassificationEngine())

    async def fake_classify_profile_items(_settings, profiles, _inclusion, _exclusion):
        assert [profile.eu_number for profile in profiles] == trial_ids
        return [
            TrialWorkerResult(
                trial_id=trial_ids[0],
                inclusion_results=[CriterionResult(criterion_id="i1", classification=True, evidence="Supported.")],
                exclusion_results=[CriterionResult(criterion_id="e1", classification=False, evidence="Absent.")],
            ),
            TrialWorkerResult(
                trial_id=trial_ids[1],
                inclusion_results=[CriterionResult(criterion_id="i1", classification=False, evidence="Contradicted.")],
                exclusion_results=[CriterionResult(criterion_id="e1", classification=None, evidence="Unknown.")],
            ),
            TrialWorkerResult(
                trial_id=trial_ids[2],
                inclusion_results=[CriterionResult(criterion_id="i1", classification=True, evidence="Supported.")],
                exclusion_results=[CriterionResult(criterion_id="e1", classification=None, evidence="Unknown.")],
            ),
        ]

    monkeypatch.setattr("intel_mcp.server.classify_profile_items", fake_classify_profile_items)

    async with Client(mcp) as client:
        tools = await client.list_tools()
        tool = next(item for item in tools.tools if item.name == "classify_trials")
        assert tool.annotations is not None
        assert tool.annotations.read_only_hint is False
        assert tool.annotations.destructive_hint is False
        assert tool.annotations.idempotent_hint is False
        assert "unknown" in (tool.description or "").lower()
        assert "final semantic classification step" in (tool.description or "").lower()
        assert "filter_trials" in (tool.description or "")

        result = await client.call_tool(
            "classify_trials",
            {
                "analysis_id": "ana_123456789012345678901234",
                "trial_ids": trial_ids,
                "inclusion_criteria": ["Trial includes the target population"],
                "exclusion_criteria": ["Trial is restricted to healthy volunteers"],
            },
        )

    assert result.is_error is False
    assert control.operations == ["reserve", "commit"]
    assert result.structured_content == {
        "eligible_trials": [trial_ids[0]],
        "ineligible_trials": [trial_ids[1]],
        "uncertain_trials": [trial_ids[2]],
        "counts": {
            "classified": 3,
            "eligible": 1,
            "ineligible": 1,
            "uncertain": 1,
        },
        "analysis_allowance": {
            "limit": 200,
            "used": 3,
            "remaining": 197,
        },
    }
