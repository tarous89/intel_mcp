import copy
import unittest

from intel_mcp.site_ranking import phrase_in, rank_profiles


CRITERIA = {
    "therapeutic_areas": ["Solid Tumor Oncology"],
    "disease_terms": ["NSCLC", "non-small cell lung cancer", "lung"],
    "countries": [],
}


def contact(first="Ada", *, last="Example", role=True, email="ada@example.org", function=""):
    return {
        "first_name": first,
        "last_name": last,
        "principal_investigator": role,
        "function": function,
        "department_or_division": "Oncology",
        "email": email,
    }


def item(number=1, *, title="NSCLC study", diseases=None, biomarker="EGFR", site="Example hospital",
         country="DE", contacts=None, sponsor="Example sponsor", year=2024):
    return {"eu_number": f"{year}-{number:06d}-00-00", "profile": {
        "classification_variables": {
            "trial_title": title,
            "diseases": diseases if diseases is not None else ["Non-small cell lung cancer"],
            "biomarkers": [biomarker] if biomarker else [],
            "sponsor": {"name": sponsor},
            "sites": [{
                "name": site,
                "country_code": country,
                "site_contacts": contacts if contacts is not None else [contact()],
            }],
        },
        "ctis_lifecycle": {"countries": [{"country_code": country, "updates": [{"date": f"{year}-02-01", "label": "Start of trial"}]}]},
    }}


class RankingTests(unittest.TestCase):
    def test_disease_terms_rank_but_do_not_filter_therapeutic_area_cohort(self):
        result = rank_profiles([
            item(1, site="Other disease hospital", diseases=["Breast cancer"]),
            item(2, site="Matched hospital", diseases=["Non-small cell lung cancer"]),
        ], CRITERIA)
        self.assertEqual(result["counts"]["sites"], 2)
        self.assertEqual([row["name"] for row in result["sites"]], ["Matched hospital", "Other disease hospital"])
        self.assertEqual(result["sites"][1]["metrics"]["diseaseMatchedTrials"], 0)

    def test_non_disease_profile_fields_do_not_influence_ranking(self):
        result = rank_profiles([
            item(1, site="Title-only hospital", title="NSCLC study", diseases=["Breast cancer"], biomarker="NSCLC"),
            item(2, site="Disease hospital", title="Other study", diseases=["Lung carcinoma"], biomarker=""),
        ], CRITERIA)
        self.assertEqual(result["sites"][0]["name"], "Disease hospital")
        self.assertEqual(result["sites"][1]["metrics"]["diseaseMatchedTrials"], 0)

    def test_requested_countries_limit_sites_and_pi_affiliations(self):
        criteria = {**CRITERIA, "countries": ["DE"]}
        result = rank_profiles([
            item(1, site="German hospital", country="DE"),
            item(2, site="French hospital", country="FR"),
        ], criteria)
        self.assertEqual([row["name"] for row in result["sites"]], ["German hospital"])
        self.assertEqual(result["pis"][0]["sites"][0]["country"], "DE")

    def test_site_and_pi_trials_are_distinct_and_aggregated(self):
        record = item()
        result = rank_profiles([record, copy.deepcopy(record), item(2)], CRITERIA)
        self.assertEqual(result["sites"][0]["metrics"]["therapeuticAreaTrials"], 2)
        self.assertEqual(result["pis"][0]["metrics"]["therapeuticAreaTrials"], 2)
        self.assertEqual(result["counts"], {
            "sites": 1, "pis": 1, "confirmedPIs": 1, "unconfirmedContacts": 0,
            "previewSites": 1, "previewPIs": 1,
        })

    def test_contacts_are_returned_and_site_prefers_confirmed_pi(self):
        contacts = [
            contact("Study", last="Office", role=False, email="office@example.org", function="Study office"),
            contact("Ada", role=True, email="PI@Example.org"),
        ]
        result = rank_profiles([item(contacts=contacts)], CRITERIA)
        self.assertEqual(result["sites"][0]["contact"]["email"], "pi@example.org")
        self.assertEqual(result["sites"][0]["contact"]["role"], "Principal investigator")
        self.assertEqual(result["pis"][0]["email"], "pi@example.org")

    def test_unknown_contact_is_labelled_and_explicit_non_pi_is_excluded(self):
        result = rank_profiles([item(contacts=[
            contact("Unknown", role=None, email="unknown@example.org"),
            contact("Coordinator", role=False, email="coordinator@example.org"),
        ])], CRITERIA)
        self.assertEqual(result["counts"]["sites"], 1)
        self.assertEqual(result["counts"]["pis"], 1)
        self.assertEqual(result["counts"]["confirmedPIs"], 0)
        self.assertEqual(result["pis"][0]["role"], "role_unconfirmed")
        self.assertEqual(result["sites"][0]["contact"]["email"], "coordinator@example.org")

    def test_pi_role_string_is_supported(self):
        result = rank_profiles([item(contacts=[contact(role=None, function="Principal investigator")])], CRITERIA)
        self.assertEqual(result["counts"]["pis"], 1)

    def test_same_pi_email_aggregates_across_sites(self):
        result = rank_profiles([
            item(1, site="Hospital A", contacts=[contact(email="ada@example.org")]),
            item(2, site="Hospital B", country="FR", contacts=[contact(email="ADA@example.org")]),
        ], CRITERIA)
        self.assertEqual(result["counts"]["pis"], 1)
        self.assertEqual(len(result["pis"][0]["sites"]), 1)
        self.assertEqual(result["pis"][0]["metrics"]["therapeuticAreaTrials"], 2)

    def test_same_normalized_pi_name_is_not_duplicated_when_emails_change(self):
        result = rank_profiles([
            item(1, site="Hospital A", contacts=[contact(email="ada.old@example.org")]),
            item(2, site="Hospital B", contacts=[contact(email="ada.new@example.org")]),
        ], CRITERIA)
        self.assertEqual(result["counts"]["pis"], 1)
        self.assertEqual(len(result["pis"]), 1)

    def test_pi_exposes_only_the_latest_recorded_affiliation(self):
        result = rank_profiles([
            item(1, site="Older Hospital", country="DE", contacts=[contact(email="ada.old@example.org")], year=2023),
            item(2, site="Latest Hospital", country="FR", contacts=[contact(email="ada.new@example.org")], year=2025),
        ], CRITERIA)
        self.assertEqual(result["pis"][0]["sites"], [{
            "id": result["pis"][0]["sites"][0]["id"],
            "name": "Latest Hospital", "country": "FR", "trials": 1,
        }])
        self.assertEqual(result["pis"][0]["email"], "ada.new@example.org")

    def test_preview_is_top_ten_but_counts_cover_full_list(self):
        result = rank_profiles([item(index + 1, site=f"Hospital {index:02d}") for index in range(15)], CRITERIA)
        self.assertEqual(len(result["sites"]), 10)
        self.assertEqual(result["counts"]["sites"], 15)
        self.assertEqual(result["counts"]["previewSites"], 10)

    def test_disease_evidence_and_sponsors_are_explainable(self):
        result = rank_profiles([item(1), item(2, biomarker="", sponsor="Other sponsor")], CRITERIA)
        metrics = result["sites"][0]["metrics"]
        self.assertEqual(metrics["diseaseMatchedTrials"], 2)
        self.assertEqual(metrics["matchedDiseaseTerms"][0], {"term": "lung", "trials": 2})
        self.assertEqual({sponsor["name"] for sponsor in metrics["sponsors"]}, {"Example sponsor", "Other sponsor"})
        self.assertEqual(metrics["latestTrialYear"], 2024)
        self.assertEqual(set(metrics["evidence"][0]), {"id", "title"})

    def test_sclc_is_not_a_substring_match_for_nsclc(self):
        self.assertFalse(phrase_in("SCLC", "NSCLC study"))
        self.assertTrue(phrase_in("NSCLC", "A trial in NSCLC."))

    def test_order_is_stable(self):
        records = [item(1, site="A"), item(2, site="B")]
        self.assertEqual(rank_profiles(records, CRITERIA), rank_profiles(list(reversed(records)), CRITERIA))
