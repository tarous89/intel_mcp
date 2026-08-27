from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


MAX_PROFILES_PER_CALL = 10
MAX_PROFILE_RESPONSE_BYTES = 500_000


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


class ProfileBudget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(ge=0)
    used: int = Field(ge=0)
    remaining: int = Field(ge=0)
    exhausted: bool


class GetProfilesOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profiles: list[FullProfileItem]
    unavailable_trial_ids: list[str]
    remaining_trial_ids: list[str]
    allowance_excluded_trial_ids: list[str]
    requested: int = Field(ge=1, le=MAX_PROFILES_PER_CALL)
    returned: int = Field(ge=0, le=MAX_PROFILES_PER_CALL)
    warnings: list[str]
    analysis_budget: ProfileBudget
    schema_version: str


def select_complete_profile_batch(
    profiles: list[FullProfileItem],
    *,
    max_bytes: int = MAX_PROFILE_RESPONSE_BYTES,
) -> tuple[list[FullProfileItem], list[FullProfileItem], bool]:
    """Select an ordered prefix without ever cutting through a profile.

    One profile is always allowed through, even when that individual profile is
    larger than the normal aggregate cap. This prevents an otherwise valid
    profile from becoming permanently unretrievable through the simple public
    contract.
    """
    selected: list[FullProfileItem] = []
    total_bytes = 0
    first_profile_oversized = False

    for index, item in enumerate(profiles):
        encoded_size = len(
            json.dumps(
                item.model_dump(mode="json"),
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        )
        if selected and total_bytes + encoded_size > max_bytes:
            return selected, profiles[index:], first_profile_oversized
        if not selected and encoded_size > max_bytes:
            first_profile_oversized = True
        selected.append(item)
        total_bytes += encoded_size

    return selected, [], first_profile_oversized
