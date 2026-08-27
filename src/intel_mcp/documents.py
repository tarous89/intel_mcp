from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from intel_mcp.models import AnalysisAllowance, DocumentType


MAX_DOCUMENT_TEXT_CHARACTERS = 200_000


class EngineDocumentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trial_id: str
    document_name: str
    document_type: DocumentType
    part: int = Field(ge=1)
    text: str = Field(max_length=MAX_DOCUMENT_TEXT_CHARACTERS)
    next_part: int | None = Field(default=None, ge=2)
    document_access_key: str = Field(pattern=r"^[a-f0-9]{64}$")
    schema_version: str


class AppDocumentAccess(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    document_key: str = Field(alias="documentKey", pattern=r"^[a-f0-9]{64}$")
    limit: int = Field(ge=0)
    used: int = Field(ge=0)
    remaining: int = Field(ge=0)
    exhausted: bool


class AppDocumentAccessResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access: AppDocumentAccess


class GetDocumentsOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trial_id: str
    document_name: str
    document_type: DocumentType
    part: int = Field(ge=1)
    text: str = Field(max_length=MAX_DOCUMENT_TEXT_CHARACTERS)
    next_part: int | None = Field(default=None, ge=2)
    analysis_allowance: AnalysisAllowance
