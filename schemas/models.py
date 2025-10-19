from __future__ import annotations
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum



class TerraformOutputreference(BaseModel):
    """Represents a Terraform output variable."""
    name: str = Field(description="The name of the output variable")
    value: str = Field(description="The value of the output variable")
    attribute: str = Field(description="The specific attribute of the resource being referenced")
    description: Optional[str] = Field(default=None, description="Description of the output variable")
    sensitive: bool = Field(default=False, description="Whether the output is sensitive")

class TerraformResource(BaseModel):
    """Represents a Terraform resource."""
    type: str = Field(description="The resource type (e.g., 'azurerm_resource_group')")
    name: str = Field(description="The resource name as defined in Terraform")
    file_path: str = Field(description="Path to the file containing this resource")

class TerraformResourceWithRelations(TerraformResource):
    """Represents relationships between Terraform resources."""
    child_resources: Optional[List['TerraformResource']] = Field(default=None, description="List of child resources nested within this resource")
    parent_resource: Optional['TerraformResource'] = Field(default=None, description="The parent resource if this is a child resource")
    referenced_outputs: Optional[List[TerraformOutputreference]] = Field(default=None, description="List of outputs that reference this resource")

class TerraformMetadataAgentResult(BaseModel):
    """Result of repository scanning."""
    azurerm_resources: List[TerraformResourceWithRelations] = Field(description="List of Azure Resource Manager resources found in the repository")
    
class AVMModuleInput(BaseModel):
    """Represents a module input parameter."""
    name: str = Field(description="Name of the input parameter")
    type: str = Field(description="Type of the input parameter")
    required: bool = Field(default=True, description="Whether the input is required")
    # description: Optional[str] = Field(default=None, description="Description of the input parameter")
    # default: Optional[str] = Field(default=None, description="Default value if any")

class AVMModuleOutput(BaseModel):
    """Represents a module output value."""
    name: str = Field(description="Name of the output value")
    description: Optional[str] = Field(default=None, description="Description of the output value")
    sensitive: bool = Field(default=False, description="Whether the output is sensitive")


class AVMModule(BaseModel):
    """Represents an Azure Verified Module."""
    name: str = Field(description="The module name")
    display_name: str = Field(description="Human-readable display name of the module")
    version: str = Field(default=None, description="Version of the module")
    description: Optional[str] = Field(default=None, description="Description of what the module does")

class AVMModuleDetailed(AVMModule):
    """Represents an AVM module with full details."""
    terraform_registry_url: str = Field(default=None, description="URL to the Terraform registry entry")
    source_code_url: str = Field(default=None, description="URL to the source code repository")
    requirements: Optional[List[str]] = Field(default=None, description="List of software requirements for the module. For ex.: azurerm (>= 4.0, < 5.0)")
    resources: Optional[List[str]] = Field(default=None, description="List of Terraform resources managed by this module")
    inputs: List[AVMModuleInput] = Field(description="List of input parameters for the module")
    outputs: List[AVMModuleOutput] = Field(description="List of output values from the module")

class AVMKnowledgeAgentResult(BaseModel):
    """Result of AVM knowledge gathering."""
    modules: List[AVMModuleDetailed] = Field(description="List of available AVM modules")

class AVMResourceDetailsAgentResult(BaseModel):
    """Result of AVM resource details gathering."""
    module: AVMModuleDetailed = Field(description="AVM module details")

class ResourceMapping(BaseModel):
    """Mapping between Terraform resource and AVM module."""
    source_resource: TerraformResource = Field(description="The original Terraform resource to be mapped")
    target_module: Optional[AVMModule] = Field(default=None, description="The AVM module that replaces the Terraform resource")
    confidence_score: str = Field(description="Confidence level of the mapping: High (100pct), Medium (99pct - 50pct), Low (49pct - 20pct) or None if unmappable")
    mapping_reason: str = Field(description="Explanation of why this mapping was suggested")
    mapping_details: str = Field(description="Detailed mapping analysis and considerations")

class MappingAgentResult(BaseModel):
    """Result of resource mapping process."""
    mappings: List[ResourceMapping] = Field(description="List of resource-to-module mappings")


class ConvertedFile(BaseModel):
    """Represents a converted Terraform file."""
    original_path: str
    converted_path: str
    original_content: str
    converted_content: str
    changes_made: List[str]


class ConversionResult(BaseModel):
    """Result of conversion process."""
    # status: ConversionStatus
    converted_files: List[ConvertedFile]
    output_directory: str
    conversion_timestamp: str
    avm_mapping_file: Optional[str] = None


class TerraformValidationError(BaseModel):
    """Represents a single Terraform validation error."""
    severity: str = Field(description="Error severity: 'error', 'warning', 'info'")
    summary: str = Field(description="Brief summary of the error")
    detail: str = Field(description="Detailed description of the error")
    file_path: Optional[str] = Field(default=None, description="Path to the file containing the error")
    line_number: Optional[int] = Field(default=None, description="Line number where the error occurs")
    column_number: Optional[int] = Field(default=None, description="Column number where the error occurs")
    error_code: Optional[str] = Field(default=None, description="Terraform error code if available")

class FileValidationErrors(BaseModel):
    """Represents validation errors grouped by file."""
    file_path: str = Field(description="Path to the Terraform file")
    errors: List[TerraformValidationError] = Field(description="List of validation errors in this file")
    error_count: int = Field(description="Total number of errors in this file")
    warning_count: int = Field(description="Total number of warnings in this file")

class TerraformValidatorAgentResult(BaseModel):
    """Result of Terraform validation analysis."""
    validation_success: bool = Field(description="Whether the Terraform validation passed")
    total_errors: int = Field(description="Total number of validation errors across all files")
    total_warnings: int = Field(description="Total number of validation warnings across all files")
    files_with_errors: List[FileValidationErrors] = Field(description="List of files containing validation errors")
    validation_summary: str = Field(description="Summary of the validation results and recommended actions")
    raw_terraform_output: Optional[str] = Field(default=None, description="Raw output from terraform validate command")


class ValidationIssue(BaseModel):
    """Represents a validation issue."""
    severity: str  # "error", "warning", "info"
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    suggestion: Optional[str] = None


class ValidationResult(BaseModel):
    """Result of validation process."""
    # status: ConversionStatus
    issues: List[ValidationIssue]
    validation_timestamp: str
    is_valid: bool


class ConversionReport(BaseModel):
    """Comprehensive conversion report."""
    repo_path: str
    output_directory: str
    # scan_result: RepoScanResult
    avm_knowledge: AVMKnowledgeAgentResult
    conversion_result: ConversionResult
    validation_result: ValidationResult
    report_timestamp: str
    next_steps: List[str]


class AttributeMapping(BaseModel):
    """Mapping between a Terraform resource attribute and AVM module input."""
    resource_input_name: str = Field(description="Name of the Terraform resource attribute")
    resource_input_value: Optional[str] = Field(default=None, description="Value of the resource attribute")
    avm_input_name: str = Field(description="Name of the corresponding AVM module input parameter")
    avm_input_value: Optional[str] = Field(default=None, description="Proposed value for the AVM input")
    is_required: bool = Field(description="Whether this AVM input is required")
    handling: str = Field(description="How to handle this mapping: 'direct', 'transform', 'new_variable', 'unmappable'")
    transform: Optional[str] = Field(default=None, description="Transformation logic if needed")
    notes: Optional[str] = Field(default=None, description="Additional notes about this mapping")

class VariableProposal(BaseModel):
    """Proposed new variable for the conversion."""
    name: str = Field(description="Variable name")
    type: str = Field(description="Variable type (string, number, bool, list, map, etc.)")
    source: str = Field(description="Source of this variable (inferred, required by AVM, etc.)")
    reason: str = Field(description="Why this variable is needed")
    default_value: Optional[Any] = Field(default=None, description="Proposed default value")

class OutputMapping(BaseModel):
    """Mapping between original Terraform output and new AVM module output."""
    original_output_name: str = Field(description="Name of the original Terraform output")
    original_source: str = Field(description="Current source expression (e.g., azurerm_key_vault.kv.vault_uri)")
    new_source: str = Field(description="New source using module output (e.g., module.kv.uri)")
    change_type: str = Field(description="Type of change: 'remap', 'new', 'remove'")
    notes: Optional[str] = Field(default=None, description="Additional context about this output mapping")

class ResourceConversionPlan(BaseModel):
    """Detailed conversion plan for a single Terraform resource."""
    resource_type: str = Field(description="Original Terraform resource type (e.g., azurerm_key_vault)")
    resource_name: str = Field(description="Original Terraform resource name")
    source_file: str = Field(description="Path to the source Terraform file")
    target_avm_module: str = Field(description="Target AVM module name")
    target_avm_version: str = Field(description="Target AVM module version")
    avm_resource_name: str = Field(description="Proposed name for the AVM module instance")
    transformation_action: str = Field(
        description="Action to take: 'convert_to_module', 'convert_to_parameter', 'skip'"
    )
    transformation_reason: Optional[str] = Field(
        default=None, 
        description="Reason for skip or special handling"
    )
    attribute_mappings: List[AttributeMapping] = Field(
        description="Detailed mappings between resource attributes and AVM inputs"
    )
    existing_variables_reused: List[str] = Field(
        default_factory=list,
        description="List of existing variable names that will be reused"
    )
    new_variables_required: List[VariableProposal] = Field(
        default_factory=list,
        description="New variables that need to be created"
    )
    output_mappings: List[OutputMapping] = Field(
        default_factory=list,
        description="Mappings for outputs referencing this resource"
    )
    required_providers: List[str] = Field(
        default_factory=list,
        description="Required provider versions from the AVM module"
    )
    risk_level: str = Field(
        default="Low",
        description="Risk assessment: 'High', 'Medium', 'Low'"
    )
    risk_notes: Optional[str] = Field(
        default=None,
        description="Explanation of risks or concerns"
    )

class ResourceConverterPlanningAgentResult(BaseModel):
    """Result from the Resource Converter Planning Agent for a single resource."""
    conversion_plan: ResourceConversionPlan = Field(
        description="Detailed conversion plan for the resource"
    )
    markdown_plan: str = Field(
        description="Full conversion plan in markdown format for human readability"
    )
    planning_summary: str = Field(
        description="Brief summary of the planning outcome"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Any warnings or concerns identified during planning"
    )

class WorkflowState(BaseModel):
    """Represents the state of the conversion workflow."""
    repo_path: str
    output_directory: str
    current_agent: str
    # scan_result: Optional[RepoScanResult] = None
    avm_knowledge: Optional[AVMKnowledgeAgentResult] = None
    conversion_result: Optional[ConversionResult] = None
    validation_result: Optional[ValidationResult] = None
    report: Optional[ConversionReport] = None
    errors: List[str] = []
    completed_steps: List[str] = []