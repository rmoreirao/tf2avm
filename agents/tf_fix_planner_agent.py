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


class TerraformFixPlannerAgent:
    """
    Terraform Fix Planner Agent - Terraform validation and error analysis specialist. Will plan the fixes needed for Terraform files.

    Responsibilities:
    - Inputs: 
        - errors from TerraformValidatorAgentResult
        - Converter planning Result for context

    - Parse and analyze Terraform validation errors
    - Categorize errors by file
    - Anaylyze the errors and plan the fixes needed
    - Outputs a plan for fixing the errors with the following structure:
    {
        "fix_plan": [
            {
                "file_path": "path/to/file.tf",
                "errors_to_fix": [
                    {
                        "error_summary": "Description of the error",
                        "proposed_fix": "Detailed plan on how to fix the error"
                    },
                    ...
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

            execution_settings = OpenAIChatPromptExecutionSettings(response_format=TerraformValidatorAgentResult)
            
            # Create the agent
            agent = ChatCompletionAgent(
                service=chat_completion_service,
                kernel=kernel,
                name="TerraformValidatorAgent",
                description="A specialist agent that validates Terraform configurations and analyzes validation errors.",
                arguments=KernelArguments(execution_settings),
                instructions="""TODO"""
            )
            
            logger.info("Terraform Fix Planner Agent initialized successfully")
            return cls(agent)
            
        except Exception as e:
            logger.error(f"Failed to initialize Terraform Fix Planner Agent: {e}")
            raise

    ## TODO: implement plan_fixes method