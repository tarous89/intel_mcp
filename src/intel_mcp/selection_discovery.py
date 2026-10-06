"""Explicit, bounded discovery rules. No semantic inference or user-provided SQL."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .models import TrialFilters

# Search narrative fields only: never contacts, organizations or arbitrary JSON.
TEXT_PATHS = {
    "title": ("classification_variables", "trial_title"),
    "diseases": ("classification_variables", "diseases"),
    "population": ("classification_variables", "target_population_summary"),
    "stages": ("classification_variables", "disease_stages_or_severity"),
    "settings": ("classification_variables", "treatment_settings"),
    "inclusion": ("filtering_variables", "inclusion_criteria"),
    "exclusion": ("filtering_variables", "exclusion_criteria"),
}
TextField = Literal["title", "diseases", "population", "stages", "settings", "inclusion", "exclusion"]
Term = Annotated[str, Field(min_length=2, max_length=120)]

class TextQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fields: list[TextField] = Field(min_length=1, max_length=7)
    terms: list[Term] = Field(min_length=1, max_length=20)
    operator: Literal["any", "all"] = "any"
    exclude_terms: list[Term] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def normalize(self):
        self.fields = sorted(set(self.fields))
        self.terms = sorted(set(t.strip().lower() for t in self.terms))
        self.exclude_terms = sorted(set(t.strip().lower() for t in self.exclude_terms))
        if any(len(t) < 2 for t in self.terms + self.exclude_terms):
            raise ValueError("Search terms must contain at least two non-whitespace characters")
        return self

class DiscoveryGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,39}$")
    label: str = Field(min_length=1, max_length=120)
    bucket: Literal["direct", "related", "broader"]
    filters: TrialFilters = Field(default_factory=TrialFilters)
    text: TextQuery | None = None
    phase_title_fallback: bool = False

    @model_validator(mode="after")
    def explicit_rule(self):
        if not self.text and not any(v is not None and v != [] for v in self.filters.model_dump().values()):
            raise ValueError("Subgroups require an explicit filter or text rule")
        if self.phase_title_fallback and self.filters.phase is None:
            raise ValueError("Phase title fallback requires a phase filter")
        return self

def text_evidence(profile, query):
    if query is None:
        return []
    matches = []
    for field in query.fields:
        value = profile
        for part in TEXT_PATHS[field]:
            value = value.get(part) if isinstance(value, dict) else None
        values = value if isinstance(value, list) else [value]
        for value in values:
            if not isinstance(value, str):
                continue
            for term in query.terms:
                index = value.lower().find(term)
                if index >= 0:
                    matches.append({"field": field, "path": ".".join(TEXT_PATHS[field]),
                                    "term": term, "excerpt": value[max(0, index-60):index+len(term)+100]})
    return matches
