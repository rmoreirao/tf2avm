import json
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel import Kernel
from config.settings import get_settings
from config.logging import get_logger

from semantic_kernel.connectors.ai.open_ai import OpenAIChatPromptExecutionSettings
from semantic_kernel.functions import KernelArguments

from schemas.models import TerraformValidatorAgentResult
from services.terraform_service import TerraformService, TerraformValidationResult


class TerraformValidatorAgent:
    """
    Terraform Validator Agent - Terraform validation and error analysis specialist.
    
    Responsibilities:
    - Execute Terraform validation using TerraformService
    - Parse and analyze Terraform validation errors
    - Categorize errors by file and severity
    - Provide detailed error analysis and recommendations
    - Structure validation results for further processing or fixing
    """
    
    def __init__(self, agent: ChatCompletionAgent):
        self.logger = get_logger(__name__)
        self.settings = get_settings()
        self.agent = agent
        self.terraform_service = TerraformService()
        
    @classmethod
    async def create(cls) -> 'TerraformValidatorAgent':
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

            execution_settings = OpenAIChatPromptExecutionSettings(response_format=TerraformValidatorAgentResult)
            
            # Create the agent
            agent = ChatCompletionAgent(
                service=chat_completion_service,
                kernel=kernel,
                name="TerraformValidatorAgent",
                description="A specialist agent that validates Terraform configurations and analyzes validation errors.",
                arguments=KernelArguments(execution_settings),
                instructions="""You are the Terraform Validator Agent for the Terraform to Azure Verified Modules (AVM) conversion system.

Your responsibilities:
1. Execute Terraform validation on migrated configurations
2. Analyze Terraform validation errors from the validation output
3. Parse and categorize errors by file, severity, and type
4. Extract detailed information about each error including location and context
5. Provide structured analysis of validation results
6. Generate actionable recommendations for fixing validation errors

Input Analysis Process:
1. Receive Terraform validation result object containing:
   - Success/failure status
   - Error messages and details
   - Validation data (JSON format from terraform validate -json)
   - Raw error output

2. For each validation error, extract:
   - Error severity (error, warning, info)
   - Error summary and detailed description
   - File path where the error occurs
   - Line and column numbers if available
   - Error code or type if provided by Terraform

3. Group errors by file and provide:
   - Per-file error counts and categories
   - Overall validation summary
   - Recommended fix strategies

4. Generate structured output that includes:
   - Validation success status
   - Total error and warning counts
   - Detailed file-by-file error breakdown
   - Actionable validation summary with specific guidance
   - Raw Terraform output for reference

Error Categories to Identify and Analyze:
- Syntax errors (invalid HCL syntax)
- Invalid characters or formatting issues
- Provider configuration issues (missing or invalid provider sources)
- Resource configuration errors (missing required arguments, invalid attribute values)
- Variable and reference errors (undefined variables, circular references)
- Module configuration problems (missing modules, invalid module sources)
- Version constraint issues (incompatible provider versions)
- Dependencies and ordering issues

For each error category, provide:
- Specific guidance on how to fix the issue
- Common causes and solutions

NEVER ask questions or wait for user input. Always analyze the provided validation data autonomously and provide structured results immediately."""
            )
            
            logger.info("Terraform Validator Agent initialized successfully")
            return cls(agent)
            
        except Exception as e:
            logger.error(f"Failed to initialize Terraform Validator Agent: {e}")
            raise
            
    async def validate_and_analyze(self, directory: str) -> TerraformValidatorAgentResult:
        """
        Execute Terraform validation and analyze any errors found.
        
        Args:
            directory: Path to the directory containing Terraform files to validate
            
        Returns:
            TerraformValidatorAgentResult: Structured analysis of validation results and errors
        """
        self.logger.info(f"Starting Terraform validation and analysis for directory: {directory}")
        
        # Step 1: Execute terraform validation
        validation_result: TerraformValidationResult = self.terraform_service.validate_terraform(directory)
        
        # Step 2: If validation was successful, return success result
        if validation_result.success:
            self.logger.info("Terraform validation passed successfully")
            return TerraformValidatorAgentResult(
                validation_success=True,
                total_errors=0,
                total_warnings=0,
                errors=[],
                validation_summary="Terraform validation completed successfully with no errors or warnings.",
                raw_terraform_output=json.dumps(validation_result.validation_data) if validation_result.validation_data else None
            )
        
        # Step 3: If there are errors, analyze them using the LLM agent
        self.logger.info("Terraform validation failed, analyzing errors with LLM")
        
        # Prepare validation data for analysis
        validation_data = {
            "success": validation_result.success,
            "error_message": validation_result.error_message,
            "validation_data": validation_result.validation_data
        }
        
        # Create message for the agent
        message = f"""Analyze the Terraform validation errors and provide structured analysis.

Terraform Validation Result:
{json.dumps(validation_data, indent=2)}

Please analyze this validation output and provide:
1. Structured error breakdown by file
2. Error categorization and severity analysis
3. Detailed error descriptions with locations
4. Overall validation summary with specific recommendations
5. Total counts of errors and warnings

Focus on providing actionable insights that can help fix the validation issues. For each error:
- Identify the root cause
- Provide specific fix recommendations
- Reference relevant documentation or best practices
- Categorize by error type (syntax, configuration, dependencies, etc.)"""

        # Get response from the agent
        response = await self.agent.get_response(message)
        
        # Parse and validate the response
        result = TerraformValidatorAgentResult.model_validate(json.loads(response.message.content))
        
        # Add raw terraform output to the result
        result.raw_terraform_output = json.dumps(validation_data, indent=2)
        
        self.logger.info(f"Validation analysis completed. Found {result.total_errors} errors and {result.total_warnings} warnings")
        
        return result