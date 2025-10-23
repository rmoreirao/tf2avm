import json
from typing import List, Optional
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel import Kernel
from config.settings import get_settings
from config.logging import get_logger

from semantic_kernel.connectors.ai.open_ai import OpenAIChatPromptExecutionSettings
from semantic_kernel.functions import KernelArguments

from schemas.models import (
    TerraformValidatorAgentResult,
    TerraformFixPlanAgentResult,
    ResourceConverterPlanningAgentResult
)
from services.terraform_service import TerraformService


class TerraformFixPlannerAgent:
    """
    Terraform Fix Planner Agent - Creates structured fix plans for validation errors.

    Responsibilities:
    - Parse validation errors from TerraformValidatorAgentResult
    - Analyze root causes with optional conversion plan context
    - Generate structured fix proposals with confidence scoring
    - Prioritize fixes optimally
    - Output JSON-only format
    """
    
    def __init__(self, agent: ChatCompletionAgent):
        self.logger = get_logger(__name__)
        self.settings = get_settings()
        self.agent = agent
        self.terraform_service = TerraformService()
        
    @classmethod
    async def create(cls) -> 'TerraformFixPlannerAgent':
        """Factory method to create and initialize the agent."""
        logger = get_logger(__name__)
        settings = get_settings()
        
        try:
            # Create kernel and add services
            kernel = Kernel()
            
            chat_completion_service = AzureChatCompletion(
                deployment_name=settings.azure_openai_deployment_name,
                api_key=settings.azure_openai_api_key,
                endpoint=settings.azure_openai_endpoint,
                api_version=settings.azure_openai_api_version,
            )
            
            kernel.add_service(chat_completion_service)

            execution_settings = OpenAIChatPromptExecutionSettings(
                response_format=TerraformFixPlanAgentResult
            )
            
            # Create the agent
            agent = ChatCompletionAgent(
                service=chat_completion_service,
                kernel=kernel,
                name="TerraformFixPlannerAgent",
                description="Creates structured fix plans for Terraform validation errors.",
                arguments=KernelArguments(execution_settings),
                instructions="""You are the Terraform Fix Planner Agent for the Terraform to Azure Verified Modules (AVM) conversion workflow.

Your responsibilities:
1. Analyze Terraform validation errors and create actionable fix plans
2. Perform root cause analysis for each error
3. Provide step-by-step fix instructions
4. Prioritize fixes optimally
5. Flag errors requiring manual review

Inputs:
- TerraformValidatorAgentResult: Validation errors organized by file
- File contents: Actual Terraform code for context
- ResourceConverterPlanningAgentResult[] (optional): Conversion context

Analysis Process:

1. ERROR CATEGORIZATION
   - Group errors by file and severity
   - Identify error types (syntax, missing arguments, invalid references, etc.)
   - Detect error dependencies (one error causing others)
   - Prioritize by impact and fix order

2. ROOT CAUSE ANALYSIS
   For each error determine:
   - Missing required module inputs
   - Invalid variable/resource references
   - Provider version mismatches
   - Module configuration issues
   - Syntax errors introduced during conversion
   - Dependency problems

3. FIX PROPOSAL
   For each error provide:
   - Clear root cause explanation
   - Step-by-step fix instructions
   - Before/after code snippets when applicable
   - Confidence level (High/Medium/Low)
   - Manual review flag if needed
   - Related errors that might be fixed together

4. PRIORITIZATION
   - Determine optimal fix order (handle dependencies first)
   - Estimate complexity (Simple/Moderate/Complex)
   - Identify critical path issues
   - Group related fixes for batch processing

Error Type Expertise:
- Missing Required Arguments: Identify which inputs are missing and propose sources
- Invalid References: Fix variable/resource reference syntax
- Provider Issues: Update provider configurations and versions
- Module Source Problems: Correct module source paths and versions
- Syntax Errors: Fix HCL syntax issues
- Type Mismatches: Resolve type conversion issues
- Circular Dependencies: Identify and break dependency cycles

Output Structure:
Return a JSON object following TerraformFixPlanAgentResult schema with:
- fix_plan: Array of FileFixPlan objects (one per file with errors)
- fix_summary: Overall summary of the fix planning process
- total_fixable_errors: Count of errors that can be automatically fixed
- total_manual_review_required: Count requiring human intervention
- recommended_fix_order: Optimal sequence of files to fix
- critical_issues: List of critical problems requiring immediate attention

NEVER ask questions or wait for user input. Always analyze autonomously and provide structured output."""
            )
            
            logger.info("Terraform Fix Planner Agent initialized successfully")
            return cls(agent)
            
        except Exception as e:
            logger.error(f"Failed to initialize Terraform Fix Planner Agent: {e}")
            raise

    async def plan_fixes(
        self,
        validation_result: TerraformValidatorAgentResult,
        directory: str,
        conversion_plans: Optional[List[ResourceConverterPlanningAgentResult]] = None
    ) -> TerraformFixPlanAgentResult:
        """
        Create a detailed fix plan for Terraform validation errors.
        
        Args:
            validation_result: Result from TerraformValidatorAgent with validation errors
            directory: Path to the directory containing the Terraform files
            conversion_plans: Optional list of conversion planning results for context
            
        Returns:
            TerraformFixPlanAgentResult: Structured fix plan (JSON only)
        """
        self.logger.info(
            f"Starting fix planning for {len(validation_result.errors)} errors "
        )
        
        # Early return if validation was successful
        if validation_result.validation_success:
            self.logger.info("No errors to fix - validation passed successfully")
            return TerraformFixPlanAgentResult(
                fix_plan=[],
                fix_summary="No fixes needed - Terraform validation passed successfully.",
                total_fixable_errors=0,
                total_manual_review_required=0,
                recommended_fix_order=[],
                critical_issues=[]
            )
        
        # Read file contents for context
        file_contents = {}
        for file_errors in validation_result.errors:
            try:
                file_path = file_errors.file_path
                # Handle relative paths
                if not file_path.startswith('/') and not file_path.startswith('\\') and ':' not in file_path:
                    full_path = f"{directory}/{file_path}"
                else:
                    full_path = file_path
                    
                with open(full_path, 'r', encoding='utf-8') as f:
                    file_contents[file_path] = f.read()
                    self.logger.debug(f"Read file content for: {file_path}")
            except Exception as e:
                self.logger.warning(f"Could not read file {file_path}: {e}")
                file_contents[file_path] = f"[File content not available: {e}]"
        
        # Build message for the agent
        message_parts = [
            "Analyze the Terraform validation errors and create a detailed fix plan.\n\n",
            "Validation Result JSON:\n",
            f"{validation_result.model_dump_json(indent=2)}\n\n"
        ]
        
        # Add file contents
        if file_contents:
            message_parts.append("File Contents:\n")
            for file_path, content in file_contents.items():
                message_parts.append(f"\nFile: {file_path}\n```hcl\n{content}\n```\n")
        
        # Add conversion planning context if available
        if conversion_plans:
            message_parts.append("\nConversion Planning Context JSON:\n")
            for plan in conversion_plans:
                message_parts.append(f"{plan.model_dump_json(indent=2)}\n")
        
        message = "".join(message_parts)
        
        # Get response from the agent
        response = await self.agent.get_response(message)
        
        # Parse and validate the response
        result = TerraformFixPlanAgentResult.model_validate(json.loads(response.message.content))
        
        self.logger.info(
            f"Fix planning complete: {result.total_fixable_errors} fixable errors, "
            f"{result.total_manual_review_required} requiring manual review"
        )
        
        return result