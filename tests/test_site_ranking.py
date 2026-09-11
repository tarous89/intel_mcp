import copy
import unittest
from datetime import UTC, datetime, timedelta

from intel_mcp.site_ranking import phrase_in, rank_profiles

CRITERIA = {
    "therapeutic_areas": ["Solid Tumor Oncology"],
    "disease_terms": ["NSCLC", "non-small cell lung cancer", "lung"],
    "countries": [],
    "phases": [3],
    "modalities": ["Monoclonal antibody"],
    "paediatric_relevant": False,
}


def investigator(first="Ada", *, last="Example", email="ada@example.org", function=""):
    return {
        "first_name": first,
        "last_name": last,
        "function": function,
        "department_or_division": "Oncology",
        "email": email,
    }


def item(number=1, *, title="NSCLC study", diseases=None, biomarker="EGFR", site="Example hospital",
         country="DE", investigators=None, sponsor="Example sponsor", year=2024,
         authorization_date=None, phases=None, modality="Monoclonal antibody", paediatric=False):
    authorization_date = authorization_date or f"{year}-02-01"
    return {"eu_number": f"{year}-{number:06d}-00-00", "profile": {
        "filtering_variables": {
            "phase": phases if phases is not None else [3],
            "modality": modality,
            "paediatric_trial": paediatric,
        },
        "classification_variables": {
            "trial_title": title,
            "diseases": diseases if diseases is not None else ["Non-small cell lung cancer"],
            "biomarkers": [biomarker] if biomarker else [],
            "sponsor": {"name": sponsor},
            "sites": [{
                "name": site,
                "country_code": country,
                "investigators": investigators if investigators is not None else [investigator()],
            }],
        },
        "ctis_lifecycle": {"countries": [{"country_code": country, "updates": [{
            "date": authorization_date, "label": "Initial country decision", "outcome": "Authorised",
        }]}]},
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

    def test_investigators_are_returned_and_site_prefers_best_ranked_pi(self):
        investigators = [
            investigator("Study", last="Office", email="office@example.org", function="Study office"),
            investigator("Ada", email="PI@Example.org"),
        ]
        result = rank_profiles([item(investigators=investigators)], CRITERIA)
        self.assertEqual(result["sites"][0]["contact"]["email"], "pi@example.org")
        self.assertEqual(result["sites"][0]["contact"]["role"], "Principal investigator")
        self.assertEqual(result["pis"][0]["email"], "pi@example.org")
        self.assertEqual(result["sites"][0]["matchedPICount"], 2)
        self.assertEqual(result["sites"][0]["matchedPIs"][0]["name"], "Ada Example")

    def test_site_investigator_is_the_best_matching_confirmed_pi_with_an_email(self):
        result = rank_profiles([
            item(1, diseases=["Breast cancer"], investigators=[investigator("Broad", email="broad@example.org")]),
            item(2, diseases=["Non-small cell lung cancer"], investigators=[investigator("Lung", email="lung@example.org")]),
        ], CRITERIA)
        site = result["sites"][0]
        self.assertEqual(site["matchedPICount"], 2)
        self.assertEqual([person["name"] for person in site["matchedPIs"]], ["Lung Example", "Broad Example"])
        self.assertEqual(site["contact"]["email"], "lung@example.org")
        self.assertEqual(site["matchedPIs"][0]["indicationTrials"], 1)

    def test_removed_legacy_site_people_are_not_read_as_v11_investigators(self):
        record = item()
        site = record["profile"]["classification_variables"]["sites"][0]
        site["site_contacts"] = [
            {**investigator("Unknown", email="unknown@example.org"), "principal_investigator": None},
            {**investigator("Coordinator", email="coordinator@example.org"), "principal_investigator": False},
        ]
        site.pop("investigators")
        result = rank_profiles([record], CRITERIA)
        self.assertEqual(result["counts"]["sites"], 1)
        self.assertEqual(result["counts"]["pis"], 0)
        self.assertEqual(result["counts"]["confirmedPIs"], 0)
        self.assertEqual(result["counts"]["unconfirmedContacts"], 0)
        self.assertEqual(result["pis"], [])
        self.assertIsNone(result["sites"][0]["contact"])

    def test_investigator_function_is_not_required_to_establish_pi_role(self):
        result = rank_profiles([item(investigators=[investigator(function="Study office")])], CRITERIA)
        self.assertEqual(result["counts"]["pis"], 1)
        self.assertEqual(result["pis"][0]["role"], "confirmed_pi")

    def test_same_pi_email_aggregates_across_sites(self):
        result = rank_profiles([
            item(1, site="Hospital A", investigators=[investigator(email="ada@example.org")]),
            item(2, site="Hospital B", country="FR", investigators=[investigator(email="ADA@example.org")]),
        ], CRITERIA)
        self.assertEqual(result["counts"]["pis"], 1)
        self.assertEqual(len(result["pis"][0]["sites"]), 1)
        self.assertEqual(result["pis"][0]["metrics"]["therapeuticAreaTrials"], 2)

    def test_same_normalized_pi_name_is_not_duplicated_when_emails_change(self):
        result = rank_profiles([
            item(1, site="Hospital A", investigators=[investigator(email="ada.old@example.org")]),
            item(2, site="Hospital B", investigators=[investigator(email="ada.new@example.org")]),
        ], CRITERIA)
        self.assertEqual(result["counts"]["pis"], 1)
        self.assertEqual(len(result["pis"]), 1)

    def test_pi_exposes_only_the_latest_recorded_affiliation(self):
        result = rank_profiles([
            item(1, site="Older Hospital", country="DE", investigators=[investigator(email="ada.old@example.org")], year=2023),
            item(2, site="Latest Hospital", country="FR", investigators=[investigator(email="ada.new@example.org")], year=2025),
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

    def test_sponsor_spelling_and_legal_variants_are_consolidated_conservatively(self):
        result = rank_profiles([
            item(1, sponsor="AstraZeneca"),
            item(2, sponsor="ASTRAZENECA AB"),
            item(3, sponsor="Astra Zeneca LLC"),
            item(4, sponsor="Merck & Co"),
            item(5, sponsor="Merck KGaA"),
            item(6, sponsor="Example Biopharma Inc."),
            item(7, sponsor="example biopharma LLC"),
        ], CRITERIA)
        sponsors = result["sites"][0]["metrics"]["sponsors"]
        self.assertEqual(sponsors[0]["name"], "AstraZeneca")
        self.assertEqual(sponsors[0]["trials"], 3)
        self.assertEqual(set(sponsors[0]["variants"]), {"Astra Zeneca LLC", "AstraZeneca", "ASTRAZENECA AB"})
        self.assertEqual(sponsors[1]["name"], "Example Biopharma")
        self.assertEqual(sponsors[1]["trials"], 2)
        merck_result = rank_profiles([
            item(20, sponsor="Merck & Co"), item(21, sponsor="Merck KGaA"),
        ], CRITERIA)
        self.assertEqual(
            {sponsor["name"] for sponsor in merck_result["sites"][0]["metrics"]["sponsors"]},
            {"Merck & Co.", "Merck KGaA"},
        )

    def test_experience_metrics_use_five_year_window_and_activity_uses_six_months(self):
        today = datetime.now(UTC).date()
        recent_date = (today - timedelta(days=30)).isoformat()
        old_year = today.year - 6
        result = rank_profiles([
            item(1, year=today.year, authorization_date=recent_date, paediatric=True),
            item(2, year=old_year, authorization_date=f"{old_year}-01-01", paediatric=True),
        ], {**CRITERIA, "paediatric_relevant": True})
        metrics = result["sites"][0]["metrics"]
        self.assertEqual(metrics["therapeuticAreaTrials"], 1)
        self.assertEqual(metrics["diseaseMatchedTrials"], 1)
        self.assertEqual(metrics["phaseMatchedTrials"], 1)
        self.assertEqual(metrics["modalityMatchedTrials"], 1)
        self.assertEqual(metrics["paediatricMatchedTrials"], 1)
        self.assertEqual(metrics["recentActivityTrials"], 1)

    def test_phase_modality_and_paediatric_experience_break_disease_ties(self):
        criteria = {**CRITERIA, "paediatric_relevant": True}
        result = rank_profiles([
            item(1, site="Broad match", phases=[2], modality="Small molecule", paediatric=False),
            item(2, site="Priority match", phases=[3], modality="Monoclonal antibody", paediatric=True),
        ], criteria)
        self.assertEqual(result["sites"][0]["name"], "Priority match")

    def test_cohort_bands_are_calculated_before_preview_and_zero_is_neutral_bottom(self):
        rows = []
        for index in range(12):
            for trial in range(index + 1):
                rows.append(item(1000 + index * 20 + trial, site=f"Hospital {index:02d}"))
        result = rank_profiles(rows, CRITERIA)
        self.assertEqual(result["sites"][0]["metrics"]["bands"]["therapeuticAreaTrials"], "leading_10")
        self.assertEqual(len(result["sites"]), 10)
        unmatched = rank_profiles([item(1, diseases=["Breast cancer"])], CRITERIA)
        self.assertEqual(unmatched["sites"][0]["metrics"]["bands"]["diseaseMatchedTrials"], "bottom_25")

    def test_sclc_is_not_a_substring_match_for_nsclc(self):
        self.assertFalse(phrase_in("SCLC", "NSCLC study"))
        self.assertTrue(phrase_in("NSCLC", "A trial in NSCLC."))

    def test_order_is_stable(self):
        records = [item(1, site="A"), item(2, site="B")]
        self.assertEqual(rank_profiles(records, CRITERIA), rank_profiles(list(reversed(records)), CRITERIA))

class FullListTests(unittest.TestCase):
    def test_premium_returns_all_matching_sites_and_pis_without_truncation(self):
        from intel_mcp.site_ranking import ProfileRanker
        items = [item(i + 1, site=f"Hospital {i}", investigators=[investigator(first=f"PI{i}", email=f"pi{i}@example.org")]) for i in range(65)]
        preview = rank_profiles(items, CRITERIA)
        full = ProfileRanker(CRITERIA)
        full.add(items)
        result = full.result(None)
        self.assertEqual(len(preview["sites"]), 10)
        self.assertEqual(len(result["sites"]), 65)
        self.assertEqual(len(result["pis"]), 65)
        self.assertEqual(result["counts"]["sites"], 65)
        self.assertEqual(result["sites"][:10], preview["sites"])
