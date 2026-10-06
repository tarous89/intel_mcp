"""Reviewed exact aliases; no prefix, fuzzy or acquisition-date inference."""
import re

IDENTITY_VERSION = "reviewed-aliases-2026-10-06-v1"
SYNEOS_SOURCE = "https://www.sec.gov/Archives/edgar/data/1610950/000095017023002928/synh-ex21_1.htm"
# Historical source-backed grouping, not a claim about ownership at trial time.
CRO_ALIASES = [
    {"name": name, "country": country, "group": "Syneos Health", "source": SYNEOS_SOURCE,
     "source_period": "2022 annual report", "reviewed_on": "2026-10-06"}
    for name, country in [
        ("Syneos Health Clinical Spain, S.L.U.", "ES"),
        ("Syneos Health UK Limited", "GB"),
        ("Syneos Health Germany GmbH", "DE"),
        ("Syneos Health France SARL", "FR"),
    ]
]

IQVIA_SOURCE = "https://s201.q4cdn.com/580005511/files/doc_financials/2023/ar/iqv-2023-12-31_10k_filed-with-exhibits.pdf"
CRO_ALIASES += [
    {"name": name, "country": country, "group": "IQVIA", "source": IQVIA_SOURCE,
     "source_period": "2023 annual report, exhibit 21", "reviewed_on": "2026-10-06"}
    for name, country in [
        ("IQVIA Ltd.", "GB"), ("IQVIA RDS Spain S.L.", "ES"),
        ("IQVIA RDS GmbH", "DE"), ("IQVIA RDS France SAS", "FR"),
        ("IQVIA RDS Ireland Ltd.", "IE"), ("IQVIA RDS Italy S.r.l.", "IT"),
    ]
]
CRO_ALIASES.append({"name": "IQVIA Limited", "country": "GB", "group": "IQVIA",
    "source": "https://www.iqvia.com/locations/switzerland/information-for-members-of-the-public/privacy-policy",
    "source_period": "policy retrieved 2026-10-06", "reviewed_on": "2026-10-06"})

def alias_key(name):
    # Punctuation and spacing variants only; never drop words or corporate suffixes.
    return re.sub(r"[^\w]", "", name.casefold())


def reviewed_cro_group(names, countries):
    matches = [a for a in CRO_ALIASES if a["country"] in countries and alias_key(a["name"]) in {alias_key(n) for n in names}]
    if not matches or len({a["group"] for a in matches}) != 1:
        return None
    return matches[0]
