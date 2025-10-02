from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel import Kernel
from config.settings import get_settings
from config.logging import get_logger
from plugins.http_plugin import HttpClientPlugin


class AVMKnowledgeAgent:
    """
    AVM Knowledge Agent - Azure Verified Modules expert.
    
    Responsibilities:
    - Fetch AVM module index from official sources
    - Parse and maintain AVM module mappings
    - Provide module documentation and requirements
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.settings = get_settings()
        self.agent = None
        
    async def initialize(self):
        """Initialize the agent with Azure OpenAI service and plugins."""
        try:
            # Create kernel and add services
            kernel = Kernel()
            
            chat_completion_service = AzureChatCompletion(
                deployment_name=self.settings.azure_openai_deployment_name,
                api_key=self.settings.azure_openai_api_key,
                endpoint=self.settings.azure_openai_endpoint,
                api_version=self.settings.azure_openai_api_version,
            )
            
            kernel.add_service(chat_completion_service)
            
            # Initialize plugins
            http_plugin = HttpClientPlugin()
            
            # Create the agent
            self.agent = ChatCompletionAgent(
                service=chat_completion_service,
                kernel=kernel,
                name="AVMKnowledgeAgent",
                description="A specialist agent that gathers and maintains Azure Verified Modules knowledge.",
                plugins=[http_plugin],
                instructions="""You are the AVM Knowledge Agent for Terraform to Azure Verified Modules (AVM) conversion.

Your responsibilities:
1. Fetch the latest AVM module index from the official Azure documentation
2. Parse the module index to create mappings between Azure resources and AVM modules
3. Gather detailed module information including inputs, outputs, and requirements
4. Maintain an up-to-date knowledge base of available AVM modules

Primary data source:
- AVM Index URL: https://azure.github.io/Azure-Verified-Modules/indexes/terraform/tf-resource-modules/

Available tools:
- fetch_url: Fetch content from the AVM index URL

Process:
1. Fetch the AVM module index from the official documentation
2. Parse the "Published modules" section to extract module information
3. Create mappings between Display Names (Azure resource types) and Module Names
4. For each relevant module, note the source repository and version information

Mapping JSON output format:

[
    {
        "displayName": "Module Display Name",
        "moduleName": "avm_module_name",
        "source": "https://github.com/Azure/avm-modules",
        "version": "x.y.z"
    },
    ...
]


Only output the JSON mapping format. Output the full list and never truncate it. NEVER ask questions or wait for user input. Always proceed autonomously.
"""
            )
            
            self.logger.info("AVM Knowledge Agent initialized successfully")
            return self.agent
            
        except Exception as e:
            self.logger.error(f"Failed to initialize AVM Knowledge Agent: {e}")
            raise