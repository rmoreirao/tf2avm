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
    source_file: str = Field(description="Path to the source Terraform file containing the resource")
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

class TerraformValidationErrors(BaseModel):
    """Represents validation errors grouped by file."""
    error_type: str = Field(description="'General' for overall errors. 'FileSpecific' for file-specific errors.")
    file_path: Optional[str] = Field(description="Path to the Terraform file")
    errors: List[TerraformValidationError] = Field(description="List of validation errors in this file")

class TerraformValidatorAgentResult(BaseModel):
    """Result of Terraform validation analysis."""
    validation_success: bool = Field(description="Whether the Terraform validation passed")
    errors: List[TerraformValidationErrors] = Field(description="List of files containing validation errors")
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
    resource_input_name: Optional[str] = Field(default=None, description="Name of the Terraform resource attribute")
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
    default_value: Optional[str] = Field(default=None, description="Proposed default value")

class OutputMapping(BaseModel):
    """Mapping between original Terraform output and new AVM module output."""
    original_output_name: str = Field(description="Name of the original Terraform output")
    original_source: str = Field(description="Current source expression (e.g., azurerm_key_vault.kv.vault_uri)")
    new_source: str = Field(description="New source using module output (e.g., module.kv.uri)")
    change_type: str = Field(description="Type of change: 'remap', 'new', 'remove'")
    notes: Optional[str] = Field(default=None, description="Additional context about this output mapping")


class ResourceConverterPlanningAgentResult(BaseModel):
    """Result from the Resource Converter Planning Agent for a single resource."""
    planning_summary: str = Field(
        description="Brief summary of the planning outcome. Must be concise and to the point. Mandatory field."
    )
    
    source_file: str = Field(default=None, description="Path to the source Terraform file. Mandatory field.")
    resource_type: str = Field(default=None, description="Original Terraform resource type (e.g., azurerm_key_vault)")
    resource_name: str = Field(default=None, description="Original Terraform resource name")
    target_avm_module: Optional[str] = Field(default=None, description="Target AVM module name")
    target_avm_version: Optional[str] = Field(default=None, description="Target AVM module version")
    target_avm_module_name: Optional[str] = Field(default=None,
        description=(
            "Proposed name for the AVM module instance. Names are unique, lowercase, and use underscores.\n"
            "Propose a name based on the original resource name and type.\n"
            "1) For ex.: original resource type 'azurerm_cosmosdb_account' and name 'name = var.cosmosdb_account_name' and the AVM target is 'avm-res-documentdb-databaseaccount',\n"
            "the proposed name is 'cosmosdb_account_cosmosdb_account_name'.\n"
            "2) For ex.: original resource type 'azurerm_cosmosdb_account' and name 'name = ''cosmos_database'' ' and the AVM target is 'avm-res-documentdb-databaseaccount',\n"
            "the proposed name is 'cosmosdb_account_cosmos_database'."
        )
    )
    transformation_type: str = Field(
        description=(
            "Action to take for this resource transformation:\n"
            "- 'convert_resource_to_avm_module': Replace the azurerm_* resource with a new AVM module.\n"
            "- 'convert_resource_to_avm_module_parameter': Convert the azurerm_* resource to another AVM module input parameter (e.g., child resources that become module configuration). The original resource will be removed.\n"
            "- 'skip': Leave resource unchanged (not covered by AVM or intentionally excluded)\n"
            "- 'manual_review': Requires human intervention due to complexity or ambiguity"
        )
    )
    transformation_description: str = Field(description="This is the description based on the chosen transformation_type")
    transformation_issue_reason: Optional[str] = Field(
        default=None, 
        description="If transformation_type is 'skip' or 'manual_review', explain the reason or issue that led to this decision."
    )
    attribute_mappings: Optional[List[AttributeMapping]] = Field(
        default_factory=list,
        description="Detailed mappings between resource attributes and AVM inputs"
    )
    existing_variables_reused: Optional[List[str]] = Field(
        default_factory=list,
        description="List of existing variable names that will be reused"
    )
    new_variables_required: Optional[List[VariableProposal]] = Field(
        default_factory=list,
        description="New variables that need to be created. Variables must be simple types (string, number, bool, list, map). Complex types are not allowed."
    )
    output_mappings: Optional[List[OutputMapping]] = Field(
        default_factory=list,
        description="Mappings for outputs referencing this resource"
    )
    required_providers: Optional[List[str]] = Field(
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

class ErrorFixProposal(BaseModel):
    """Proposed fix for a single validation error."""
    error_summary: str = Field(description="Brief error description")
    error_detail: str = Field(description="Full Terraform error message")
    line_number: Optional[int] = Field(default=None, description="Line number of error")
    column_number: Optional[int] = Field(default=None, description="Column number of error")
    root_cause_analysis: str = Field(description="Root cause explanation")
    proposed_fix: str = Field(description="Step-by-step fix instructions")
    code_snippet_before: Optional[str] = Field(default=None, description="Original code")
    code_snippet_after: Optional[str] = Field(default=None, description="Fixed code")
    fix_confidence: str = Field(description="High|Medium|Low")
    requires_manual_review: bool = Field(default=False, description="Manual intervention flag")
    related_errors: List[str] = Field(default_factory=list, description="Related error summaries")

class FileFixPlan(BaseModel):
    """Fix plan for a single file."""
    file_path: str = Field(description="Path to the Terraform file")
    error_count: int = Field(description="Number of errors")
    fix_priority: str = Field(description="Critical|High|Medium|Low")
    errors_to_fix: List[ErrorFixProposal] = Field(description="Error-level fixes")
    overall_fix_strategy: str = Field(description="File-level strategy")
    estimated_complexity: str = Field(description="Simple|Moderate|Complex")

class TerraformFixPlanAgentResult(BaseModel):
    """Complete fix plan result (JSON only)."""
    fix_plan: List[FileFixPlan] = Field(description="Per-file fix plans")
    fix_summary: str = Field(description="Overall summary")
    total_fixable_errors: int = Field(description="Auto-fixable count")
    total_manual_review_required: int = Field(description="Manual review count")
    recommended_fix_order: List[str] = Field(description="File paths in optimal order")
    critical_issues: List[str] = Field(default_factory=list, description="Critical problems")

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