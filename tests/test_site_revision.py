import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
from intel_mcp.models import TherapeuticAreaFilter
from intel_mcp.site_revision import interpret_revision, shares_original_anchor, ViewControls
from intel_mcp.site_search import SiteSearchError, search_deterministically
from intel_mcp.site_ranking import ProfileRanker, _apply_bands, _band, METRIC_FIELDS

AREA, OTHER = TherapeuticAreaFilter.canonical_values[:2]
INITIAL = {"therapeutic_areas": [AREA, OTHER], "disease_terms": ["NSCLC", "lung"], "countries": ["DE", "FR"], "phases": [3], "modalities": [], "paediatric_relevant": True, "prioritized_experience": "Experience in Phase III lung cancer trials."}
SETTINGS = SimpleNamespace(openai_api_key="test-only", openai_base_url="https://mock.invalid/v1")
CONTROLS = ViewControls().model_dump()


def completion(criteria=None, outcome="apply", name="apply_site_revision", controls=None):
    return {"status": "completed", "output": [{"type": "function_call", "name": name, "arguments": json.dumps({"criteria": {"sufficient_context": True, **(criteria or INITIAL)}, "outcome": outcome, "controls": controls or CONTROLS})}], "usage": {"input_tokens": 10, "output_tokens": 20}}


class RevisionTests(unittest.IsolatedAsyncioTestCase):
    async def call(self, response, message="Focus on Germany"):
        def handler(request):
            payload = json.loads(request.content)
            self.assertEqual(payload["tool_choice"], {"type": "function", "name": "apply_site_revision"})
            self.assertFalse(payload["parallel_tool_calls"])
            self.assertTrue(payload["tools"][0]["strict"])
            self.assertFalse(payload["store"])
            self.assertNotIn("profiles", payload)
            fields = json.loads(payload["input"][1]["content"])
            self.assertEqual(set(fields), {"initial_criteria", "current_criteria", "controls", "revision_instruction"})
            return httpx.Response(200, json=response)
        return await interpret_revision(SETTINGS, {"message": message, "initial_criteria": INITIAL, "current_criteria": INITIAL, "controls": CONTROLS}, transport=httpx.MockTransport(handler))

    async def test_function_only_output_and_multi_value_anchor(self):
        for field, kept in [("therapeutic_areas", OTHER), ("disease_terms", "LUNG"), ("countries", "FR")]:
            revised = {**INITIAL, "therapeutic_areas": [OTHER], "disease_terms": ["migraine"], "countries": ["IT"]}
            if field != "therapeutic_areas":
                revised["therapeutic_areas"] = [next(x for x in TherapeuticAreaFilter.canonical_values if x not in INITIAL["therapeutic_areas"])]
            revised[field] = [kept]
            result = await self.call(completion(revised))
            self.assertEqual(result["criteria"][field], [kept])

    async def test_phase_and_paediatric_alone_do_not_anchor(self):
        revised = {**INITIAL, "therapeutic_areas": [next(x for x in TherapeuticAreaFilter.canonical_values if x not in INITIAL["therapeutic_areas"])], "disease_terms": ["migraine"], "countries": []}
        with self.assertRaises(SiteSearchError) as ctx:
            await self.call(completion(revised))
        self.assertEqual(ctx.exception.status, 422)

    async def test_unknown_field_and_function_do_not_execute(self):
        for response in [completion({**INITIAL, "patient_capacity": 100}), completion(name="execute_sql"), completion(controls={**CONTROLS, "pins": []})]:
            with self.assertRaises(SiteSearchError):
                await self.call(response)

    async def test_unsupported_is_not_silently_substituted(self):
        with self.assertRaises(SiteSearchError) as ctx:
            await self.call(completion(outcome="unsupported"), "Find sites with 100 available patients")
        self.assertEqual(ctx.exception.status, 422)

    async def test_plain_text_and_multiple_calls_fail_closed(self):
        for output in [[{"type": "message", "content": [{"type": "output_text", "text": "Trust me"}]}], completion()["output"] * 2]:
            with self.assertRaises(SiteSearchError):
                await self.call({"status": "completed", "output": output})

    def test_anchor_does_not_drift_and_uses_exact_values(self):
        intermediate = {**INITIAL, "therapeutic_areas": [OTHER], "disease_terms": ["migraine"], "countries": ["IT"]}
        drift = {"therapeutic_areas": [], "disease_terms": ["migraine"], "countries": ["IT"]}
        self.assertTrue(shares_original_anchor(INITIAL, intermediate))
        self.assertFalse(shares_original_anchor(INITIAL, drift))
        self.assertFalse(shares_original_anchor(INITIAL, {"disease_terms": ["lung something else"]}))
        self.assertFalse(shares_original_anchor({"countries": []}, {"countries": []}))

    def test_band_optimization_retains_exact_existing_percentiles(self):
        values = [None, 0, 0, 1, 2, 2, 3, 5, 50, 100]
        rows = [{"metrics": {field: val for field in METRIC_FIELDS}} for val in values]
        _apply_bands(rows)
        for row, value in zip(rows, values):
            for field in METRIC_FIELDS:
                self.assertEqual(row["metrics"]["bands"][field], _band(value, [v for v in values if v is not None]))

    def test_full_result_is_unbounded_without_changing_preview_default(self):
        ranker = ProfileRanker(INITIAL)
        self.assertEqual(ranker.result(None)["counts"]["previewSites"], 0)
