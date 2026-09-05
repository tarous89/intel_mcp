import json
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
import httpx
from intel_mcp.models import TherapeuticAreaFilter
from intel_mcp.site_search import interpret_context, search_investigators, SiteSearchError

SETTINGS = SimpleNamespace(openai_api_key="test-only", openai_base_url="https://test.invalid/v1", report_plan_service_token="test-service")
CRITERIA = {"sufficient_context": True, "summary": "NSCLC investigator search", "indication_terms": ["NSCLC"], "therapeutic_areas": [TherapeuticAreaFilter.canonical_values[0]], "phases": [3], "modality": None, "countries": [], "feasibility_checks": ["Confirm patient availability"]}

def completion(criteria):
    return {"status": "completed", "output": [{"content": [{"type": "output_text", "text": json.dumps(criteria)}]}], "usage": {"input_tokens": 10, "output_tokens": 20}}

class SearchTests(unittest.IsolatedAsyncioTestCase):
    async def test_structured_ai_and_country_override(self):
        def handler(request):
            payload = json.loads(request.content)
            self.assertFalse(payload["store"])
            self.assertTrue(payload["text"]["format"]["strict"])
            self.assertNotIn("tools", payload)
            return httpx.Response(200, json=completion(CRITERIA))
        criteria, usage = await interpret_context(SETTINGS, "NSCLC trial context", ["DE"], transport=httpx.MockTransport(handler))
        self.assertEqual(criteria["countries"], ["DE"])
        self.assertEqual(usage["inputTokens"], 10)

    async def test_ai_refusal_fails_closed(self):
        payload = {"status": "completed", "output": [{"content": [{"type": "refusal", "refusal": "No"}]}]}
        with self.assertRaises(SiteSearchError) as caught:
            await interpret_context(SETTINGS, "NSCLC trial context", [], transport=httpx.MockTransport(lambda r: httpx.Response(200, json=payload)))
        self.assertEqual(caught.exception.status, 422)

    async def test_invalid_controlled_term_fails(self):
        criteria = {**CRITERIA, "therapeutic_areas": ["Invented"]}
        with self.assertRaises(SiteSearchError):
            await interpret_context(SETTINGS, "NSCLC trial context", [], transport=httpx.MockTransport(lambda r: httpx.Response(200, json=completion(criteria))))

    async def test_context_bounds_before_model(self):
        with patch("intel_mcp.site_search.interpret_context", new_callable=AsyncMock) as planner:
            with self.assertRaises(SiteSearchError): await search_investigators(SETTINGS, None, {"context": "short"})
            planner.assert_not_called()

    async def test_bounded_mcp_adapter_reads_and_partial_coverage(self):
        class Engine:
            batches = []
            async def filter_trials(self, *, filters, sort, limit, offset):
                assert limit == 100
                assert filters.phase is None
                return SimpleNamespace(counts=SimpleNamespace(total_matches=650, total_profiles=1000), data=[SimpleNamespace(eu_number=f"2024-{n:06d}-00-00") for n in range(offset+1, offset+101)])
            async def get_profiles(self, ids):
                self.batches.append(ids)
                return SimpleNamespace(data=[], unavailable_trial_ids=ids)
        engine = Engine()
        with patch("intel_mcp.site_search.interpret_context", new_callable=AsyncMock, return_value=(CRITERIA, {})):
            result = await search_investigators(SETTINGS, engine, {"context": "A phase III NSCLC trial"})
        self.assertEqual(sum(map(len, engine.batches)), 500)
        self.assertTrue(all(len(batch) <= 10 for batch in engine.batches))
        self.assertTrue(result["coverage"]["partial"])
        self.assertEqual(result["coverage"]["unavailableProfiles"], 500)
        self.assertEqual(result["rows"], [])
