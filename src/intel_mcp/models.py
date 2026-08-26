from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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
