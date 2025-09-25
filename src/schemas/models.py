from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class RepoInput(BaseModel):
    repo_url: str = Field(..., description="URL or path to the Terraform repository")


class FileManifest(BaseModel):
    path: str
    resources: List[dict] = Field(default_factory=list)  # {type, name}


class RepoManifest(BaseModel):
    files: List[FileManifest]
    variables: List[dict] = Field(default_factory=list)
    outputs: List[dict] = Field(default_factory=list)
    providers: List[str] = Field(default_factory=list)
    terraform_version: Optional[str] = None


class AVMIndexEntry(BaseModel):
    resource_type: str
    avm_module: str
    version: str


class AVMIndex(BaseModel):
    entries: List[AVMIndexEntry]


class MappingEntry(BaseModel):
    original: str
    mapped_to: Optional[str]
    confidence: float


class MappingResult(BaseModel):
    mappings: List[MappingEntry]
    unmapped: List[str] = Field(default_factory=list)


class ConversionResult(BaseModel):
    converted_repo_path: str
    files_converted: List[str]


class ValidationErrorItem(BaseModel):
    tool: str
    message: str


class ValidationResult(BaseModel):
    status: str  # success | failed
    errors: List[ValidationErrorItem] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ReviewReport(BaseModel):
    markdown: str


class FinalOutcome(BaseModel):
    status: str
    converted_repo_path: Optional[str]
    report_path: Optional[str]
    message: Optional[str] = None
