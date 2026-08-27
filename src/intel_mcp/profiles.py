from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from intel_mcp.models import AnalysisAllowance


MAX_PROFILES_PER_CALL = 10


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
