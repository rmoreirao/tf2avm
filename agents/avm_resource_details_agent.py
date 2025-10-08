import json
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel import Kernel
from config.settings import get_settings
from config.logging import get_logger
from plugins.http_plugin import HttpClientPlugin
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion, OpenAIChatPromptExecutionSettings
from semantic_kernel.functions import KernelArguments

from plugins.terraform_plugin import TerraformPlugin
from schemas.models import  AVMResourceDetailsAgentResult


class AVMResourceDetailsAgent:
    """
    AVM Knowledge Agent - Azure Verified Modules expert.
    
    Responsibilities:
    - Parse terraform registry module details JSON
    """
    
    def __init__(self, agent: ChatCompletionAgent):
        self.logger = get_logger(__name__)
        self.settings = get_settings()
        self.agent = agent
        
    @classmethod
    async def create(cls) -> 'AVMResourceDetailsAgent':
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
            
            execution_settings = OpenAIChatPromptExecutionSettings(response_format=AVMResourceDetailsAgentResult)

            # Create the agent
            agent = ChatCompletionAgent(
                service=chat_completion_service,
                kernel=kernel,
                name="AVMKnowledgeAgent",
                description="A specialist agent that gathers and maintains Azure Verified Modules knowledge.",
                
                arguments=KernelArguments(execution_settings),
                instructions="""You are the AVM Resource Details Agent for Terraform to Azure Verified Modules (AVM) conversion.

Inputs:
- module_name: The name of the AVM module to fetch details for
- module_version: The version of the AVM module to fetch details for
- Raw JSON data from the Terraform Registry for the specified AVM module

                
Process:
1. Analyze the raw JSON data to extract module details
2. Parse into output format
3. Gather detailed module information including inputs, outputs, and requirements

Only output the JSON mapping format. Output the full list and never truncate it. NEVER ask questions or wait for user input. Always proceed autonomously.
"""
            )
            
            logger.info("AVM Resource Details Agent initialized successfully.")
            return cls(agent)
            
        except Exception as e:
            logger.error(f"Failed to initialize AVM Resource Details Agent: {e}")
            raise

    async def fetch_avm_resource_details(self, module_name:str,module_version:str) -> AVMResourceDetailsAgentResult:
        """
        Fetch AVM module details from Terraform Registry.
        """
        
        terraform_plugin = TerraformPlugin()
        raw_avm_module_details_json = await terraform_plugin.get_avm_module_details(module_name=module_name, module_version=module_version)

        message = f"Parse the AVM module details. module_name is {module_name}, module_version is {module_version}. Here is the raw JSON data for the AVM module: {raw_avm_module_details_json}"
        response = await self.agent.get_response(message)
        result = AVMResourceDetailsAgentResult.model_validate(json.loads(response.message.content))
        return result