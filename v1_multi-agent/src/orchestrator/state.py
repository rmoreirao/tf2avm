from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field
from schemas import (
    RepoInput,
    RepoManifest,
    AVMIndex,
    MappingResult,
    ConversionResult,
    ValidationResult,
    ReviewReport,
    FinalOutcome,
)


class OrchestratorState(BaseModel):
    repo_input: Optional[RepoInput] = None
    repo_manifest: Optional[RepoManifest] = None
    avm_index: Optional[AVMIndex] = None
    mapping_result: Optional[MappingResult] = None
    conversion_result: Optional[ConversionResult] = None
    validation_result: Optional[ValidationResult] = None
    review_report: Optional[ReviewReport] = None
    final_outcome: Optional[FinalOutcome] = None
    internal_errors: list = Field(default_factory=list)
