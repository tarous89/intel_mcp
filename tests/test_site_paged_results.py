import unittest
from unittest.mock import ANY, AsyncMock, patch

from intel_mcp.site_search import SiteSearchError, page_deterministic_result, search_page_deterministically


def metric(value):
    return {
        "therapeuticAreaTrials": value + 2,
        "diseaseMatchedTrials": value,
        "phaseMatchedTrials": value % 3,
        "modalityMatchedTrials": 1,
        "paediatricMatchedTrials": None,
        "recentActivityTrials": value % 2,
        "matchedDiseaseTerms": [], "sponsors": [], "latestTrialYear": 2026, "evidence": [],
    }


def result():
    sites = [
        {"id": f"site-{i}", "rank": i, "name": f"Hospital {i}", "country": "DE",
         "contact": {"name": f"Person {i}", "email": f"p{i}@example.invalid", "role": "PI"},
         "matchedPIs": [], "metrics": metric(i % 7)}
        for i in range(1, 126)
    ]
    pis = [
        {"id": f"pi-{i}", "rank": i, "name": f"Investigator {i}", "department": "Oncology",
         "email": f"pi{i}@example.invalid", "role": "confirmed_pi",
         "sites": [{"id": f"site-{i}", "name": f"Hospital {i}", "country": "DE", "trials": 1}],
         "metrics": metric(i % 11)}
        for i in range(1, 208)
    ]
    return {
        "scoringVersion": "fixture-v5", "criteria": {"therapeutic_areas": ["Oncology"], "disease_terms": ["lung"], "countries": []},
        "sites": sites, "pis": pis,
        "counts": {"sites": len(sites), "pis": len(pis), "confirmedPIs": len(pis), "unconfirmedContacts": 0, "previewSites": len(sites), "previewPIs": len(pis)},
        "coverage": {"approvedProfiles": 300, "therapeuticAreaTrials": 300, "profilesReviewed": 300, "unavailableProfiles": 0, "partial": False, "scope": "fixture", "generatedAt": "2026-09-09T00:00:00Z"},
    }


class PageTests(unittest.IsolatedAsyncioTestCase):
    def test_default_page_is_ten_rows(self):
        page = page_deterministic_result(result(), {"kind": "sites", "page": 1, "controls": {}})
        self.assertEqual(len(page["sites"]), 10)
        self.assertEqual(page["page"], {"kind": "sites", "page": 1, "size": 10, "pages": 13, "total": 125})

    def test_page_never_serializes_more_than_requested_rows(self):
        page = page_deterministic_result(result(), {"kind": "pis", "page": 3, "size": 50, "controls": {"sort": "rank", "search": "", "minimum_metric": "diseaseMatchedTrials", "minimum_trials": None}})
        self.assertEqual(len(page["pis"]), 50)
        self.assertEqual(page["pis"][0]["id"], "pi-101")
        self.assertEqual(page["sites"], [])
        self.assertEqual(page["page"], {"kind": "pis", "page": 3, "size": 50, "pages": 5, "total": 207})
        self.assertEqual(page["counts"]["pis"], 207, "global cohort counts are retained")

    def test_ten_row_page_is_supported(self):
        page = page_deterministic_result(result(), {"kind": "sites", "page": 2, "size": 10, "controls": {}})
        self.assertEqual(len(page["sites"]), 10)
        self.assertEqual(page["sites"][0]["id"], "site-11")
        self.assertEqual(page["page"]["pages"], 13)

    def test_search_filter_and_metric_sort_apply_before_slicing(self):
        filtered = page_deterministic_result(result(), {"kind": "sites", "page": 1, "size": 25, "controls": {"sort": "diseaseMatchedTrials", "search": "Hospital 12", "minimum_metric": "diseaseMatchedTrials", "minimum_trials": 3}})
        self.assertLessEqual(len(filtered["sites"]), 25)
        self.assertTrue(all("12" in row["name"] for row in filtered["sites"]))
        self.assertTrue(all(row["metrics"]["diseaseMatchedTrials"] >= 3 for row in filtered["sites"]))
        values = [row["metrics"]["diseaseMatchedTrials"] for row in filtered["sites"]]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_invalid_controls_fail_before_transport(self):
        for value in [
            {"kind": "sites", "page": 1, "size": 100, "controls": {}},
            {"kind": "other", "page": 1, "size": 25, "controls": {}},
            {"kind": "sites", "page": True, "size": 25, "controls": {}},
            {"kind": "sites", "page": 1, "size": 25, "controls": {"sort": "secret"}},
            {"kind": "sites", "page": 1, "size": 25, "controls": {"minimum_trials": -1}},
        ]:
            with self.assertRaises(SiteSearchError):
                page_deterministic_result(result(), value)

    async def test_async_page_wrapper_requests_full_cohort_only_inside_mcp(self):
        full = result()
        with patch("intel_mcp.site_search.search_deterministically", new=AsyncMock(return_value=full)) as search:
            page = await search_page_deterministically(object(), {"criteria": "fixture"}, {"kind": "sites", "page": 1, "size": 10, "controls": {}})
        search.assert_awaited_once_with(ANY, {"criteria": "fixture"}, full_list=True)
        self.assertEqual(len(page["sites"]), 10)
        self.assertEqual(page["pis"], [])


if __name__ == "__main__":
    unittest.main()
