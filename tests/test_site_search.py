import json
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from intel_mcp.models import TherapeuticAreaFilter
from intel_mcp.site_search import SiteSearchError, interpret_context, search_deterministically


AREA = TherapeuticAreaFilter.canonical_values[0]
SETTINGS = SimpleNamespace(
    openai_api_key="test-only",
    openai_base_url="https://test.invalid/v1",
    classifier_model="gpt-5.6-terra",
    report_plan_service_token="test-service",
)
PLANNER_OUTPUT = {
    "sufficient_context": True,
    "therapeutic_areas": [AREA],
    "keywords": ["NSCLC", "EGFR", "osimertinib"],
}
CRITERIA = {"therapeutic_areas": [AREA], "keywords": ["NSCLC", "EGFR", "osimertinib"]}


def completion(criteria):
    return {
        "status": "completed",
        "output": [{"content": [{"type": "output_text", "text": json.dumps(criteria)}]}],
        "usage": {"input_tokens": 10, "output_tokens": 20},
    }


class SearchTests(unittest.IsolatedAsyncioTestCase):
    async def test_planner_extracts_only_areas_and_keywords_with_terra(self):
        def handler(request):
            payload = json.loads(request.content)
            self.assertEqual(payload["model"], "gpt-5.6-terra")
            self.assertEqual(payload["reasoning"]["effort"], "low")
            self.assertFalse(payload["store"])
            self.assertNotIn("tools", payload)
            self.assertEqual(set(payload["text"]["format"]["schema"]["properties"]), {
                "sufficient_context", "therapeutic_areas", "keywords",
            })
            self.assertNotIn(
                "uniqueItems",
                payload["text"]["format"]["schema"]["properties"]["therapeutic_areas"],
            )
            self.assertNotIn(
                "uniqueItems",
                payload["text"]["format"]["schema"]["properties"]["keywords"],
            )
            return httpx.Response(200, json=completion(PLANNER_OUTPUT))

        criteria, usage = await interpret_context(
            SETTINGS, "Phase III EGFR-mutated NSCLC treated with osimertinib",
            transport=httpx.MockTransport(handler),
        )
        self.assertEqual(criteria, CRITERIA)
        self.assertEqual(usage, {"model": "gpt-5.6-terra", "inputTokens": 10, "outputTokens": 20})

    async def test_planner_deduplicates_keywords(self):
        output = {**PLANNER_OUTPUT, "keywords": [" NSCLC ", "nsclc", "EGFR"]}
        criteria, _ = await interpret_context(
            SETTINGS, "EGFR-mutated non-small-cell lung cancer",
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json=completion(output))),
        )
        self.assertEqual(criteria["keywords"], ["NSCLC", "EGFR"])

    async def test_refusal_fails_closed(self):
        payload = {"status": "completed", "output": [{"content": [{"type": "refusal", "refusal": "No"}]}]}
        with self.assertRaises(SiteSearchError) as caught:
            await interpret_context(
                SETTINGS, "NSCLC trial context",
                transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload)),
            )
        self.assertEqual(caught.exception.status, 422)

    async def test_invalid_controlled_area_fails(self):
        output = {**PLANNER_OUTPUT, "therapeutic_areas": ["Invented"]}
        with self.assertRaises(SiteSearchError):
            await interpret_context(
                SETTINGS, "NSCLC trial context",
                transport=httpx.MockTransport(lambda request: httpx.Response(200, json=completion(output))),
            )

    async def test_context_bounds_are_checked_before_model(self):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as request:
            with self.assertRaises(SiteSearchError):
                await interpret_context(SETTINGS, "short")
            request.assert_not_called()

    async def test_search_reads_every_therapeutic_area_profile_in_ten_trial_batches(self):
        class Engine:
            def __init__(self):
                self.offsets = []
                self.batches = []

            async def filter_trials(self, *, filters, sort, limit, offset):
                self.offsets.append(offset)
                self.filters = filters
                remaining = max(0, 250 - offset)
                count = min(100, remaining)
                rows = [SimpleNamespace(eu_number=f"2024-{number:06d}-00-00") for number in range(offset + 1, offset + count + 1)]
                return SimpleNamespace(counts=SimpleNamespace(total_matches=250, total_profiles=900), data=rows)

            async def get_profiles(self, ids):
                self.batches.append(ids)
                rows = [SimpleNamespace(model_dump=lambda trial_id=trial_id: {"eu_number": trial_id, "profile": {"classification_variables": {"sites": []}}}) for trial_id in ids]
                return SimpleNamespace(data=rows, unavailable_trial_ids=[])

        engine = Engine()
        result = await search_deterministically(engine, CRITERIA)
        self.assertEqual(engine.offsets, [0, 100, 200])
        self.assertEqual(sum(map(len, engine.batches)), 250)
        self.assertTrue(all(len(batch) <= 10 for batch in engine.batches))
        self.assertEqual(engine.filters.therapeutic_areas.values, [AREA])
        self.assertIsNone(engine.filters.country_codes)
        self.assertEqual(result["coverage"]["profilesReviewed"], 250)
        self.assertFalse(result["coverage"]["partial"])
        self.assertNotIn("usage", result)

    async def test_deterministic_search_never_calls_planner(self):
        engine = SimpleNamespace(filter_trials=AsyncMock(return_value=SimpleNamespace(
            counts=SimpleNamespace(total_matches=0, total_profiles=0), data=[],
        )))
        with patch("intel_mcp.site_search.interpret_context", new_callable=AsyncMock) as planner:
            await search_deterministically(engine, CRITERIA)
            planner.assert_not_called()
