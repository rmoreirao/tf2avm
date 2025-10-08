import json
from typing import List
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel import Kernel
from config.settings import get_settings
from config.logging import get_logger
from plugins.terraform_plugin import TerraformPlugin

from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion, OpenAIChatPromptExecutionSettings
from semantic_kernel.functions import KernelArguments

from schemas.models import AVMModule, AVMResourceDetailsAgentResult, MappingAgentResult


class MappingAgent:
    """
    Mapping Agent - Resource mapping specialist.
    
    Responsibilities:
    - Match azurerm_* resources to AVM modules
    - Determine conversion confidence levels
    - Identify unmappable resources
    
    """
    
    def __init__(self, agent: ChatCompletionAgent):
        self.logger = get_logger(__name__)
        self.settings = get_settings()
        self.agent = agent
        
    @classmethod
    async def create(cls) -> 'MappingAgent':
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

            execution_settings = OpenAIChatPromptExecutionSettings(response_format=MappingAgentResult)
            
            # Create the agent
            agent = ChatCompletionAgent(
                service=chat_completion_service,
                kernel=kernel,
                name="MappingAgent",
                description="A specialist agent that maps Terraform resources to Azure Verified Modules.",
                arguments=KernelArguments(execution_settings),
                instructions="""You are the Mapping Agent for Terraform to Azure Verified Modules (AVM) conversion.

Your responsibilities:
1. Analyze the azurerm_* resources identified from the repository scan
2. Match each resource to appropriate AVM modules using the knowledge from AVM knowledge base
3. Determine conversion confidence levels for each mapping
4. Identify resources that does not have a direct mapping to AVM modules

Inputs:
- Mandatory:
    - Repository scan results with azurerm_* resources
    - AVM Index knowledge base with available modules
- Optional:
    - Detailed AVM module information for better mapping accuracy
    - Previous mapping results for review and improvement
    
Mapping process:
1. For each azurerm_* resource found in the repository:
   - Match the resource type to available AVM modules
   - Assess compatibility between resource attributes and module inputs
   - Assign a confidence score
   - Document any mapping limitations or concerns

2. Document unmappable resources:
   - Resources with no AVM equivalent
   - Resources that would break existing dependencies
   - Complex resources that require manual intervention

3. Review Mappings (if previous results provided):
    - Evaluate previous mappings based on the Detailed AVM module information
    - Compare new mappings with previous results
    - Adjust confidence scores based on new information
    - For the Unmapped resources, check if new AVM details provide a possible mapping:
        - In many cases, the child resources are managed within the context of their parent resources in AVM modules.
        - Search if the child resources are being handled as inputs or underlying resources within the parent AVM module.
        - If so, update the mapping to reflect that the child resource is covered by the parent AVM module.
        - Document the rationale for this mapping decision.

NEVER ask questions or wait for user input. Always proceed autonomously and hand off immediately when your work is done."""
            )
            
            logger.info("Mapping Agent initialized successfully")
            return cls(agent)
            
        except Exception as e:
            logger.error(f"Failed to initialize Mapping Agent: {e}")
            raise
            
    async def create_mappings(self, repo_scan_result: str, avm_knowledge: str) -> str:
        """
        Create resource mappings between Terraform resources and AVM modules.
        Returns mapping analysis and conversion plan.
        """
        
        message = f"Map Terraform resources to AVM modules. Repository: {repo_scan_result} AVM Knowledge: {avm_knowledge}"
        response = await self.agent.get_response(message)
        result = MappingAgentResult.model_validate(json.loads(response.message.content))
        return result
    
    async def review_mappings(self, previous_mapping_result: MappingAgentResult, avm_modules_details: List[AVMModule]) -> MappingAgentResult:
        