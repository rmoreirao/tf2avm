import json
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel import Kernel
from config.settings import get_settings
from config.logging import get_logger
from plugins.http_plugin import HttpClientPlugin
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion, OpenAIChatPromptExecutionSettings
from semantic_kernel.functions import KernelArguments

from schemas.models import AVMKnowledgeAgentResult


class AVMKnowledgeAgent:
    """
    AVM Knowledge Agent - Azure Verified Modules expert.
    
    Responsibilities:
    - Fetch AVM module index from official source
    - Parse and maintain AVM module mappings
    - Provide module documentation and requirements
    """
    
    def __init__(self, agent: ChatCompletionAgent):
        self.logger = get_logger(__name__)
        self.settings = get_settings()
        self.agent = agent
        
    @classmethod
    async def create(cls) -> 'AVMKnowledgeAgent':
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
            
            execution_settings = OpenAIChatPromptExecutionSettings(response_format=AVMKnowledgeAgentResult)

            # Create the agent
            agent = ChatCompletionAgent(
                service=chat_completion_service,
                kernel=kernel,
                name="AVMKnowledgeAgent",
                description="A specialist agent that gathers and maintains Azure Verified Modules knowledge.",
                arguments=KernelArguments(execution_settings),
                instructions="""You are the AVM Knowledge Agent for Terraform to Azure Verified Modules (AVM) conversion.

Inputs:
- Raw HTML content of the AVM module index page

Process:
1. Analyze the HTML content to identify the "Published modules" section
2. Parse the "Published modules" section to extract module information
3. Create mappings between Display Names (Azure resource types) and Module Names
4. For each relevant module, note the version information

Output:
Fill in only the fields on the JSON output: name, display_name, terraform_registry_url, source_code_url, version


Only output the JSON mapping format. Output the full list and never truncate it. NEVER ask questions or wait for user input. Always proceed autonomously.
"""
            )
            
            logger.info("AVM Knowledge Agent initialized successfully")
            return cls(agent)
            
        except Exception as e:
            logger.error(f"Failed to initialize AVM Knowledge Agent: {e}")
            raise
            
    async def fetch_avm_knowledge(self) -> str:
        """
        Fetch AVM module knowledge from official sources.
        Returns JSON mapping of AVM modules.
        """

        http_plugin = HttpClientPlugin()
        tf_module_index_html = await http_plugin.fetch_url("https://azure.github.io/Azure-Verified-Modules/indexes/terraform/tf-resource-modules/")

        message = f"Gather AVM module knowledge from official sources. Here is the raw HTML content of the AVM module index page: {tf_module_index_html}"
        response = await self.agent.get_response(message)
        result = AVMKnowledgeAgentResult.model_validate(json.loads(response.message.content))
        return result