from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from enum import Enum


class ConversionStatus(str, Enum):
    """Status of conversion process."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class TerraformResource(BaseModel):
    """Represents a Terraform resource."""
    type: str
    name: str
    attributes: Dict[str, Any]
    file_path: str
    line_number: Optional[int] = None


class TerraformFile(BaseModel):
    """Represents a Terraform file and its contents."""
    path: str
    content: str
    resources: List[TerraformResource] = []
    variables: List[str] = []
    outputs: List[str] = []
    locals: List[str] = []


class RepoScanResult(BaseModel):
    """Result of repository scanning."""
    repo_path: str
    terraform_files: List[TerraformFile]
    azurerm_resources: List[TerraformResource]
    total_resources: int
    scan_timestamp: str


class AVMModule(BaseModel):
    """Represents an Azure Verified Module."""
    name: str
    display_name: str
    description: Optional[str] = None
    source_url: Optional[str] = None
    version: Optional[str] = None
    inputs: List[Dict[str, Any]] = []
    outputs: List[Dict[str, Any]] = []


class AVMKnowledgeResult(BaseModel):
    """Result of AVM knowledge gathering."""
    modules: List[AVMModule]
    index_url: str
    fetch_timestamp: str
    total_modules: int


class ResourceMapping(BaseModel):
    """Mapping between Terraform resource and AVM module."""
    source_resource: TerraformResource
    target_module: Optional[AVMModule] = None
    confidence_score: float
    mapping_reason: str
    is_convertible: bool


class MappingResult(BaseModel):
    """Result of resource mapping process."""
    mappings: List[ResourceMapping]
    convertible_count: int
    unconvertible_count: int
    mapping_timestamp: str


class ConvertedFile(BaseModel):
    """Represents a converted Terraform file."""
    original_path: str
    converted_path: str
    original_content: str
    converted_content: str
    changes_made: List[str]


class ConversionResult(BaseModel):
    """Result of conversion process."""
    status: ConversionStatus
    converted_files: List[ConvertedFile]
    output_directory: str
    conversion_timestamp: str
    avm_mapping_file: Optional[str] = None


class ValidationIssue(BaseModel):
    """Represents a validation issue."""
    severity: str  # "error", "warning", "info"
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    suggestion: Optional[str] = None


class ValidationResult(BaseModel):
    """Result of validation process."""
    status: ConversionStatus
    issues: List[ValidationIssue]
    validation_timestamp: str
    is_valid: bool


class ConversionReport(BaseModel):
    """Comprehensive conversion report."""
    repo_path: str
    output_directory: str
    scan_result: RepoScanResult
    avm_knowledge: AVMKnowledgeResult
    mapping_result: MappingResult
    conversion_result: ConversionResult
    validation_result: ValidationResult
    report_timestamp: str
    next_steps: List[str]


class WorkflowState(BaseModel):
    """Represents the state of the conversion workflow."""
    repo_path: str
    output_directory: str
    current_agent: str
    scan_result: Optional[RepoScanResult] = None
    avm_knowledge: Optional[AVMKnowledgeResult] = None
    mapping_result: Optional[MappingResult] = None
    conversion_result: Optional[ConversionResult] = None
    validation_result: Optional[ValidationResult] = None
    report: Optional[ConversionReport] = None
    errors: List[str] = []
    completed_steps: List[str] = []