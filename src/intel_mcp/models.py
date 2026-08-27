from __future__ import annotations

from datetime import datetime
from typing import Annotated, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AppAnalysisLimits(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    filtered_trial_ids: int = Field(alias="filteredTrialIds", ge=0)
    profiles: int = Field(ge=0)
    classified_trials: int = Field(alias="classifiedTrials", ge=0)
    document_metadata: int = Field(alias="documentMetadata", ge=0)
    document_text_documents: int = Field(alias="documentTextDocuments", ge=0)
    document_text_characters: int = Field(alias="documentTextCharacters", ge=0)
    extraction_trials: int = Field(alias="extractionTrials", ge=0)
    extraction_documents: int = Field(alias="extractionDocuments", ge=0)
    variables: int = Field(ge=0)


class AnalysisLimits(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filtered_trial_ids: int = Field(ge=0)
    profiles: int = Field(ge=0)
    classified_trials: int = Field(ge=0)
    document_metadata: int = Field(ge=0)
    document_text_documents: int = Field(ge=0)
    document_text_characters: int = Field(ge=0)
    extraction_trials: int = Field(ge=0)
    extraction_documents: int = Field(ge=0)
    variables: int = Field(ge=0)


class AppAnalysis(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    analysis_id: str = Field(alias="analysisId", min_length=20)
    report_run_id: str = Field(alias="reportRunId", min_length=1)
    tier: Literal["light", "max"]
    expires_at: datetime = Field(alias="expiresAt")
    enabled_tools: list[str] = Field(alias="enabledTools")
    limits: AppAnalysisLimits
    reused: bool


class AppStartAnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis: AppAnalysis


class StartAnalysisOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_id: str
    report_run_id: str
    status: Literal["active"] = "active"
    tier: Literal["light", "max"]
    expires_at: datetime
    enabled_tools: list[str]
    limits: AnalysisLimits
    reused: bool


TextOperator = Literal["contains", "is", "does_not_contain", "is_not"]
SetOperator = Literal["contains_any", "contains_all", "contains_none"]
ComparisonOperator = Literal[
    "is",
    "is_not",
    "greater_than",
    "greater_than_or_equal",
    "less_than",
    "less_than_or_equal",
    "between",
]
BooleanValue = bool | Literal["unknown"]

TherapeuticArea = Literal[
    "Solid Tumor Oncology", "Haematological Malignancies", "Blood Disorders",
    "Cardiology", "Neurology", "Immunology", "Rheumatology", "Allergy",
    "Infectious Disease", "Endocrinology", "Metabolic Disorders", "Respiratory",
    "Gastroenterology", "Hepatology", "Dermatology", "Musculoskeletal",
    "Ophthalmology", "Otolaryngology", "Oral Health and Dentistry", "Nephrology",
    "Psychiatry", "Pain Medicine", "Gynecology", "Obstetrics",
    "Reproductive Medicine", "Urology", "Emergency Medicine", "Critical Care",
    "Surgery and Perioperative Care", "Transplantation", "Trauma and Injury",
    "Genetic and Congenital Disorders", "Nutrition", "Other",
]
Modality = Literal[
    "Biologic", "Antibody", "Small molecule", "Monoclonal antibody", "Bispecific antibody",
    "Other antibody", "ADC", "Cell therapy", "Gene therapy", "mRNA", "Other RNA",
    "Peptide/protein/enzyme", "Oligonucleotide", "Vaccine", "Radiopharmaceutical",
    "Diagnostic agent", "Medical device", "Procedure", "Other",
]
Route = Literal[
    "Oral", "Intravenous", "Subcutaneous", "Intramuscular", "Intratumoral", "Inhaled",
    "Topical", "Ophthalmic", "Intrathecal", "Other",
]
ComparatorType = Literal[
    "Placebo", "Active comparator", "Standard of care", "Historical control",
    "External or real-world control", "No comparator", "Other",
]
DocumentType = Literal[
    "protocol", "recruitment_arrangements", "patient_information_and_informed_consent",
    "assessments_and_forms", "results_report",
]
RecruitmentStatus = Literal[
    "Authorised", "Not authorised", "Under evaluation", "Ended", "Halted", "Lapsed",
    "Withdrawn", "Expired", "Suspended", "Not valid", "Pending", "Revoked",
]
CountryCode = Annotated[str, Field(pattern=r"^[A-Za-z]{2}$")]


class TextFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operator: TextOperator = "contains"
    value: str = Field(min_length=1, max_length=500)


class StringSetFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")
    canonical_values: ClassVar[tuple[str, ...]] = ()

    operator: SetOperator = "contains_any"
    values: list[str] = Field(min_length=1, max_length=50)

    @field_validator("values", mode="before")
    @classmethod
    def normalize_controlled_values(cls, values: object) -> object:
        if not cls.canonical_values or not isinstance(values, list):
            return values
        lookup = {value.casefold(): value for value in cls.canonical_values}
        return [lookup.get(value.casefold(), value) if isinstance(value, str) else value for value in values]


class TherapeuticAreaFilter(StringSetFilter):
    canonical_values = (
        "Solid Tumor Oncology", "Haematological Malignancies", "Blood Disorders",
        "Cardiology", "Neurology", "Immunology", "Rheumatology", "Allergy",
        "Infectious Disease", "Endocrinology", "Metabolic Disorders", "Respiratory",
        "Gastroenterology", "Hepatology", "Dermatology", "Musculoskeletal",
        "Ophthalmology", "Otolaryngology", "Oral Health and Dentistry", "Nephrology",
        "Psychiatry", "Pain Medicine", "Gynecology", "Obstetrics",
        "Reproductive Medicine", "Urology", "Emergency Medicine", "Critical Care",
        "Surgery and Perioperative Care", "Transplantation", "Trauma and Injury",
        "Genetic and Congenital Disorders", "Nutrition", "Other",
    )
    values: list[TherapeuticArea] = Field(min_length=1, max_length=34)


class ModalityFilter(StringSetFilter):
    canonical_values = (
        "Biologic", "Antibody", "Small molecule", "Monoclonal antibody", "Bispecific antibody",
        "Other antibody", "ADC", "Cell therapy", "Gene therapy", "mRNA", "Other RNA",
        "Peptide/protein/enzyme", "Oligonucleotide", "Vaccine", "Radiopharmaceutical",
        "Diagnostic agent", "Medical device", "Procedure", "Other",
    )
    values: list[Modality] = Field(min_length=1, max_length=19)


class RouteFilter(StringSetFilter):
    canonical_values = (
        "Oral", "Intravenous", "Subcutaneous", "Intramuscular", "Intratumoral", "Inhaled",
        "Topical", "Ophthalmic", "Intrathecal", "Other",
    )
    values: list[Route] = Field(min_length=1, max_length=10)


class SexFilter(StringSetFilter):
    canonical_values = ("Female", "Male")
    values: list[Literal["Female", "Male"]] = Field(min_length=1, max_length=2)


class ComparatorFilter(StringSetFilter):
    canonical_values = (
        "Placebo", "Active comparator", "Standard of care", "Historical control",
        "External or real-world control", "No comparator", "Other",
    )
    values: list[ComparatorType] = Field(min_length=1, max_length=7)


class DocumentTypeFilter(StringSetFilter):
    canonical_values = (
        "protocol", "recruitment_arrangements", "patient_information_and_informed_consent",
        "assessments_and_forms", "results_report",
    )
    values: list[DocumentType] = Field(min_length=1, max_length=5)


class RecruitmentStatusFilter(StringSetFilter):
    canonical_values = (
        "Authorised", "Not authorised", "Under evaluation", "Ended", "Halted", "Lapsed",
        "Withdrawn", "Expired", "Suspended", "Not valid", "Pending", "Revoked",
    )
    values: list[RecruitmentStatus] = Field(min_length=1, max_length=12)


class CountryCodeFilter(StringSetFilter):
    values: list[CountryCode] = Field(
        min_length=1,
        max_length=50,
        description="ISO 3166-1 alpha-2 country codes; matching is case-insensitive.",
    )

    @field_validator("values", mode="before")
    @classmethod
    def uppercase_codes(cls, values: object) -> object:
        if not isinstance(values, list):
            return values
        return [value.upper() if isinstance(value, str) else value for value in values]


class PhaseFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operator: SetOperator = "contains_any"
    values: list[Literal[1, 2, 3, 4]] = Field(min_length=1, max_length=4)


class ScalarControlledFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")
    canonical_values: ClassVar[tuple[str, ...]] = ()

    operator: Literal["is", "is_not"] = "is"
    value: str

    @field_validator("value", mode="before")
    @classmethod
    def normalize_controlled_value(cls, value: object) -> object:
        if not cls.canonical_values or not isinstance(value, str):
            return value
        lookup = {item.casefold(): item for item in cls.canonical_values}
        return lookup.get(value.casefold(), value)


class AllocationFilter(ScalarControlledFilter):
    canonical_values = ("Randomised", "Non-randomised", "Not applicable")
    value: Literal["Randomised", "Non-randomised", "Not applicable"]


class MaskingFilter(ScalarControlledFilter):
    canonical_values = (
        "Open label", "Single blind", "Double blind", "Triple blind", "Quadruple blind", "Other"
    )
    value: Literal[
        "Open label", "Single blind", "Double blind", "Triple blind", "Quadruple blind", "Other"
    ]


class InterventionModelFilter(ScalarControlledFilter):
    canonical_values = ("Parallel", "Single group", "Crossover", "Factorial", "Sequential", "Other")
    value: Literal["Parallel", "Single group", "Crossover", "Factorial", "Sequential", "Other"]


class BooleanFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operator: Literal["is", "is_not"] = "is"
    value: BooleanValue


class NumberFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operator: ComparisonOperator = "is"
    value: int | None = Field(default=None, ge=0)
    minimum: int | None = Field(default=None, ge=0)
    maximum: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_operand(self) -> "NumberFilter":
        if self.operator == "between":
            if self.minimum is None or self.maximum is None:
                raise ValueError("minimum and maximum are required for between")
            if self.minimum > self.maximum:
                raise ValueError("minimum cannot exceed maximum")
        elif self.value is None:
            raise ValueError("value is required unless operator is between")
        return self


class DateFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operator: ComparisonOperator = "is"
    value: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    minimum: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    maximum: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")

    @model_validator(mode="after")
    def validate_operand(self) -> "DateFilter":
        if self.operator == "between":
            if self.minimum is None or self.maximum is None:
                raise ValueError("minimum and maximum are required for between")
            if self.minimum > self.maximum:
                raise ValueError("minimum cannot exceed maximum")
        elif self.value is None:
            raise ValueError("value is required unless operator is between")
        return self


class CountryFilter(BaseModel):
    """Conditions in one object must match the same Trial Profile country row."""

    model_config = ConfigDict(extra="forbid")

    country_codes: CountryCodeFilter | None = Field(
        default=None,
        description="ISO 3166-1 alpha-2 country codes. Values are matched case-insensitively.",
    )
    recruitment_statuses: Annotated[
        RecruitmentStatusFilter | None,
        Field(
            default=None,
            description=(
                "Normalized CTIS country statuses. Expected values: Authorised, Not authorised, "
                "Under evaluation, Ended, Halted, Lapsed, Withdrawn, Expired, Suspended, "
                "Not valid, Pending, Revoked."
            ),
        ),
    ]
    initial_submission_date: DateFilter | None = None
    latest_submission_date: DateFilter | None = None
    decision_date: DateFilter | None = None
    latest_submission_result_date: DateFilter | None = None
    number_of_sites: NumberFilter | None = None
    planned_sample_size: NumberFilter | None = None


class TrialFilters(BaseModel):
    """Approved structured Trial Profile fields only; different fields combine with AND."""

    model_config = ConfigDict(extra="forbid")

    eu_number: TextFilter | None = None
    trial_title: TextFilter | None = None
    trial_acronym: TextFilter | None = None
    sponsor_name: TextFilter | None = Field(
        default=None,
        description=(
            "Structured sponsor-name text. The CTIS source may sometimes identify a subsidy or "
            "funding source, or omit part of the sponsor's complete legal entity name; treat matches "
            "as shortlist evidence rather than definitive legal-entity resolution."
        ),
    )
    latest_country_submission_or_approval_date: DateFilter | None = None
    initial_ctis_submission_date: DateFilter | None = None
    first_ctis_authorization_date: DateFilter | None = None
    latest_ctis_authorization_date: DateFilter | None = None
    available_extracted_document_types: DocumentTypeFilter | None = None
    available_extracted_document_names: StringSetFilter | None = Field(
        default=None,
        description="Case-insensitive matching against individual available extracted document names.",
    )
    therapeutic_areas: TherapeuticAreaFilter | None = None
    rare_disease_trial: BooleanFilter | None = None
    orphan_designation: BooleanFilter | None = None
    paediatric_trial: BooleanFilter | None = None
    first_in_human: BooleanFilter | None = None
    phase: PhaseFilter | None = None
    modalities: ModalityFilter | None = None
    routes_of_administration: RouteFilter | None = None
    country_codes: CountryCodeFilter | None = Field(
        default=None,
        description="ISO 3166-1 alpha-2 codes present anywhere in the Trial Profile.",
    )
    eligible_sexes: SexFilter | None = None
    planned_sample_size: NumberFilter | None = None
    number_of_countries: NumberFilter | None = None
    number_of_sites: NumberFilter | None = None
    allocation: AllocationFilter | None = None
    masking: MaskingFilter | None = None
    intervention_model: InterventionModelFilter | None = None
    comparator_types: ComparatorFilter | None = None
    countries: list[CountryFilter] = Field(
        default_factory=list,
        max_length=20,
        description=(
            "Country-row groups. Every condition inside one group applies to the same country row; "
            "multiple groups combine with AND and may match different country rows."
        ),
    )


class TrialSort(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: Literal[
        "latest_country_submission_or_approval_date", "initial_ctis_submission_date",
        "first_ctis_authorization_date", "latest_ctis_authorization_date",
        "planned_sample_size", "number_of_countries", "number_of_sites", "eu_number",
    ] = "latest_country_submission_or_approval_date"
    direction: Literal["asc", "desc"] = "desc"


class FilterTrialItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eu_number: str
    trial_title: str | None
    sponsor_name: str | None
    available_extracted_document_names: list[str]


class FilterCounts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_profiles: int = Field(ge=0)
    total_matches: int = Field(ge=0)
    returned: int = Field(ge=0, le=100)


class AnalysisAllowance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(ge=0)
    used: int = Field(ge=0)
    remaining: int = Field(ge=0)


class FilterTrialsOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: list[FilterTrialItem]
    counts: FilterCounts
    analysis_allowance: AnalysisAllowance


class EngineFilterResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: list[FilterTrialItem]
    counts: FilterCounts


class AppFilterAccess(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    allowed_trial_ids: list[str] = Field(alias="allowedTrialIds", max_length=100)
    limit: int = Field(ge=0)
    used: int = Field(ge=0)
    remaining: int = Field(ge=0)
    exhausted: bool


class AppFilterAccessResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access: AppFilterAccess
