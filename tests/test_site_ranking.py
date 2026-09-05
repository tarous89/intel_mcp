import copy
import json
import unittest
from datetime import date
from intel_mcp.site_ranking import rank_profiles, phrase_in, country_activity

CRITERIA = {"indication_terms": ["NSCLC"], "phases": [3], "modality": "Monoclonal antibody", "countries": []}

def person(first, role=True, department="Oncology"):
    return {"first_name": first, "last_name": "Example", "principal_investigator": role,
            "department_or_division": department, "email": "private@example.org", "phone": "+49123456789"}

def item(n=1, *, people=None, site="Example hospital", country="DE", title="NSCLC study", events=None):
    return {"eu_number": f"2024-{n:06d}-00-00", "profile": {
        "filtering_variables": {"phase": [3], "modality": "Monoclonal antibody"},
        "classification_variables": {"trial_title": title, "diseases": [title], "sponsor": {"name": "Example sponsor"},
          "sites": [{"name": site, "country_code": country, "site_contacts": people if people is not None else [person("A")] }]},
        "ctis_lifecycle": {"countries": [{"country_code": country, "updates": events or []}]},
    }}

class RankingTests(unittest.TestCase):
    def test_distinct_pis_same_site_are_independent_rows(self):
        result = rank_profiles([item(people=[person("A"), person("B")]), item(2, people=[person("B")])], CRITERIA)
        self.assertEqual(result["counts"]["uniqueSites"], 1)
        self.assertEqual(result["counts"]["confirmedPIRecords"], 2)
        self.assertEqual([r["name"] for r in result["rows"]], ["B Example", "A Example"])
        self.assertEqual(result["rows"][0]["pi"]["total"], 2)
        self.assertEqual(result["rows"][1]["pi"]["total"], 1)
        self.assertEqual(result["rows"][1]["site"]["metrics"]["total"], 2)

    def test_duplicate_trials_and_contact_entries_do_not_inflate(self):
        record = item(people=[person("A"), person("A")])
        result = rank_profiles([record, copy.deepcopy(record)], CRITERIA)
        self.assertEqual(len(result["rows"]), 1)
        self.assertEqual(result["rows"][0]["pi"]["total"], 1)
        self.assertEqual(result["rows"][0]["site"]["metrics"]["sponsors"][0]["trials"], 1)

    def test_unknown_contacts_have_no_pi_score(self):
        result = rank_profiles([item(people=[person("Unknown", None), person("NotPI", False)])], CRITERIA)
        self.assertEqual(result["counts"]["confirmedPIRecords"], 0)
        self.assertEqual(result["counts"]["unconfirmedContacts"], 1)
        self.assertIsNone(result["rows"][0]["pi"])
        self.assertEqual(result["rows"][0]["role"], "unconfirmed_contact")

    def test_role_on_one_trial_does_not_confirm_other_trials(self):
        result = rank_profiles([item(1), item(2, people=[person("A", None)])], CRITERIA)
        self.assertEqual(result["rows"][0]["pi"]["total"], 1)
        self.assertEqual(result["rows"][0]["linkedRelevantTrials"], 2)

    def test_no_contact_values_escape(self):
        result = rank_profiles([item()], CRITERIA)
        rendered = json.dumps(result)
        self.assertNotIn("private@example.org", rendered)
        self.assertNotIn("+49123456789", rendered)
        self.assertTrue(result["rows"][0]["contactsLocked"])

    def test_name_not_merged_across_sites(self):
        result = rank_profiles([item(), item(2, site="Other hospital")], CRITERIA)
        self.assertEqual(len(result["rows"]), 2)
        self.assertEqual(result["counts"]["uniqueSites"], 2)

    def test_preview_country_cap_and_counts(self):
        records = [item(n + 1, people=[person(str(n))], country=c) for c in ["DE", "FR", "ES", "IT", "PL", "BE"] for n in range(12)]
        for i, record in enumerate(records): record["eu_number"] = f"2024-{i+1:06d}-00-00"
        result = rank_profiles(records, CRITERIA)
        self.assertEqual(result["counts"]["matchedRecords"], 72)
        self.assertEqual(len(result["rows"]), 50)
        for c in {row["site"]["country"] for row in result["rows"]}:
            self.assertLessEqual(sum(row["site"]["country"] == c for row in result["rows"]), 10)

    def test_country_filter_does_not_leak_other_sites(self):
        result = rank_profiles([item(), item(2, country="FR")], {**CRITERIA, "countries": ["FR"]})
        self.assertEqual([r["site"]["country"] for r in result["rows"]], ["FR"])

    def test_sclc_is_not_substring_match_for_nsclc(self):
        self.assertFalse(phrase_in("SCLC", "NSCLC study"))
        self.assertTrue(phrase_in("NSCLC", "A trial in NSCLC."))

    def test_authorisation_is_not_recruitment(self):
        result = rank_profiles([item(events=[{"date": "2024-01-01", "label": "Authorised"}])], CRITERIA)
        self.assertEqual(result["rows"][0]["pi"]["potentialOverlap"], 0)
        self.assertEqual(result["rows"][0]["pi"]["unknownActivity"], 1)

    def test_actual_country_events_and_future_events(self):
        record = item(events=[{"date": "2024-01-01", "label": "Start of trial"}, {"date": "2024-02-01", "label": "Start of recruitment"}, {"date": "2030-01-01", "label": "End of recruitment"}])
        self.assertEqual(country_activity(record["profile"], "DE", date(2026, 9, 5)), (True, 2024))

    def test_stop_wins_same_day(self):
        record = item(events=[{"date": "2024-01-01", "label": "Start of recruitment"}, {"date": "2024-01-01", "label": "End of recruitment"}])
        self.assertEqual(country_activity(record["profile"], "DE", date(2026, 9, 5))[0], False)

    def test_order_stable(self):
        records = [item(1, people=[person("A")]), item(2, people=[person("B")])]
        self.assertEqual(rank_profiles(records, CRITERIA), rank_profiles(list(reversed(records)), CRITERIA))
