from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel import Kernel
from config.settings import get_settings
from config.logging import get_logger
from plugins.filesystem_plugin import FileSystemPlugin
from plugins.terraform_plugin import TerraformPlugin


class RepoScannerAgent:
    """
    Repository Scanner Agent - Terraform repository analysis specialist.
    
    Responsibilities:
    - Parse all Terraform files (.tf)
    - Extract resources, variables, outputs, locals
    - Build dependency maps
    - Identify azurerm_* resources for conversion
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
            filesystem_plugin = FileSystemPlugin(self.settings.base_path)
            terraform_plugin = TerraformPlugin()
            
            # Create the agent
            self.agent = ChatCompletionAgent(
                service=chat_completion_service,
                kernel=kernel,
                name="RepoScannerAgent",
                description="A specialist agent that analyzes Terraform repositories and extracts resource information.",
                plugins=[filesystem_plugin, terraform_plugin],
                instructions="""You are the Repository Scanner Agent for Terraform to Azure Verified Modules (AVM) conversion.

Your responsibilities:
1. Scan and parse all Terraform (.tf) files in the provided repository
2. Extract and catalog all resources, variables, outputs, and locals
3. Identify azurerm_* resources that are candidates for AVM conversion
4. Build a dependency map of resources
5. Generate a comprehensive repository manifest

Available tools:
- read_tf_files: Read all Terraform files from a directory
- parse_terraform_file: Parse individual Terraform files to extract components
- validate_terraform: Basic syntax validation

Process:
1. Read all .tf files from the repository
2. Parse each file to identify resources, variables, outputs, locals
3. Focus on azurerm_* resources as conversion candidates
4. Document file structure and dependencies
5. Create a detailed scan result
6. AUTOMATICALLY proceed to handoff when scanning is complete

CRITICAL: Provide comprehensive analysis results that will be used by the AVM Knowledge Agent in the next step.

NEVER ask questions or wait for user input. Always proceed autonomously and provide complete analysis results.

Provide detailed analysis including:
- Total number of Terraform files processed
- List of all azurerm_* resources found
- Variables and outputs that may need mapping
- Any parsing errors or issues encountered
- Recommendations for conversion priority"""
            )
            
            self.logger.info("Repository Scanner Agent initialized successfully")
            return self.agent
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Repository Scanner Agent: {e}")
            raise