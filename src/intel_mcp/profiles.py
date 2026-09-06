from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from intel_mcp.models import AnalysisAllowance


MAX_PROFILES_PER_CALL = 10

ProfileSection = Literal[
    "overview",
    "population",
    "trial_design",
    "interventions",
    "eligibility",
    "objectives",
    "endpoints",
    "sponsor_and_organizations",
    "contacts",
    "countries",
    "sites",
    "documents",
    "lifecycle",
    "results",
]

PROFILE_SECTIONS: tuple[ProfileSection, ...] = (
    "overview",
    "population",
    "trial_design",
    "interventions",
    "eligibility",
    "objectives",
    "endpoints",
    "sponsor_and_organizations",
    "contacts",
    "countries",
    "sites",
    "documents",
    "lifecycle",
    "results",
)

# Trial Profile 10.0.0 semantic projections. Each stored field has one primary
# section so section combinations merge deterministically without summarization.
PROFILE_SECTION_FIELDS: dict[ProfileSection, dict[str, tuple[str, ...]]] = {
    "overview": {
        "filtering_variables": (
            "therapeutic_areas",
            "phase",
            "rare_disease_trial",
            "orphan_designation",
            "paediatric_trial",
            "first_in_human",
        ),
        "classification_variables": (
            "trial_title",
            "trial_acronym",
            "diseases",
            "classification_summary",
        ),
    },
    "population": {
        "filtering_variables": ("eligible_sexes",),
        "classification_variables": (
            "target_population_summary",
            "disease_stages_or_severity",
            "treatment_settings",
            "population_characteristics",
            "biomarkers",
        ),
    },
    "trial_design": {
        "filtering_variables": (
            "planned_sample_size",
            "allocation",
            "masking",
            "intervention_model",
            "comparator_types",
        ),
    },
    "interventions": {
        "filtering_variables": ("modality", "routes_of_administration"),
        "classification_variables": (
            "molecular_targets",
            "mechanisms_of_action",
            "interventional_products",
            "non_interventional_products",
        ),
    },
    "eligibility": {
        "filtering_variables": ("inclusion_criteria", "exclusion_criteria"),
    },
    "objectives": {
        "classification_variables": ("primary_objectives", "secondary_objectives"),
    },
    "endpoints": {
        "classification_variables": ("endpoints",),
    },
    "sponsor_and_organizations": {
        "classification_variables": (
            "sponsor",
            "legal_representative",
            "third_party_organizations",
        ),
    },
    "contacts": {
        "classification_variables": (
            "trial_management_contact",
            "trial_scientific_contact",
            "trial_recruitment_contact",
            "trial_public_ctis_contact",
        ),
    },
    "countries": {
        "filtering_variables": ("country_codes", "number_of_countries"),
        "classification_variables": ("countries",),
    },
    "sites": {
        "filtering_variables": ("number_of_sites",),
        "classification_variables": ("sites",),
    },
    "documents": {
        "filtering_variables": ("available_extracted_documents",),
    },
    "lifecycle": {"ctis_lifecycle": ()},
    "results": {"results": ()},
}


def normalize_profile_sections(sections: list[ProfileSection] | None) -> list[ProfileSection]:
    """De-duplicate requested sections while preserving caller order."""
    return list(dict.fromkeys(sections or []))


def project_profile(profile: dict[str, Any], sections: list[ProfileSection]) -> dict[str, Any]:
    """Return an exact field projection of a stored profile, never a summary."""
    selected = normalize_profile_sections(sections)
    if not selected:
        return deepcopy(profile)

    projected: dict[str, Any] = {}
    for section in selected:
        for object_name, field_names in PROFILE_SECTION_FIELDS[section].items():
            source = profile.get(object_name)
            if field_names == ():
                if object_name in profile:
                    projected[object_name] = deepcopy(source)
                continue
            if not isinstance(source, dict):
                continue
            target = projected.setdefault(object_name, {})
            for field_name in field_names:
                if field_name in source:
                    target[field_name] = deepcopy(source[field_name])
    return projected


class FullProfileItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eu_number: str
    profile_schema_version: str
    approved_at: str | None
    profile: dict[str, Any]


class EngineProfilesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: list[FullProfileItem]
    unavailable_trial_ids: list[str]
    schema_version: str


class AppProfileAccess(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    allowed_trial_ids: list[str] = Field(alias="allowedTrialIds", max_length=MAX_PROFILES_PER_CALL)
    limit: int = Field(ge=0)
    used: int = Field(ge=0)
    remaining: int = Field(ge=0)
    exhausted: bool


class AppProfileAccessResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access: AppProfileAccess


class GetProfilesCounts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requested: int = Field(ge=1, le=MAX_PROFILES_PER_CALL)
    returned: int = Field(ge=0, le=MAX_PROFILES_PER_CALL)
    unavailable: int = Field(ge=0, le=MAX_PROFILES_PER_CALL)
    allowance_reached: int = Field(ge=0, le=MAX_PROFILES_PER_CALL)


class GetProfilesOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profiles: list[FullProfileItem]
    unavailable_trial_ids: list[str]
    allowance_reached_trial_ids: list[str]
    counts: GetProfilesCounts
    analysis_allowance: AnalysisAllowance
