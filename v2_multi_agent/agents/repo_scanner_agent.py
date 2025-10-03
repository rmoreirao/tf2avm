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
4. Build a dependency map of resources and identify child resources
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
5. Determine the Child Resources for each azure resource:
A child resource is a resource that is defined within the context of another resource, often indicating a hierarchical relationship or dependency between the two resources. 
They are tightly associated with another (typically by explicit references or required unique identifiers).
Child resources can be defined on different files within the same repository.
Examples of child resources:
- A network interface (child) associated with a virtual machine (parent).
- A disk (child) attached to a virtual machine (parent).
- azurerm_monitor_diagnostic_setting (child) associated with an Azure resource (parent).
6. Create a detailed scan result

>>>Instructions:

NEVER ask questions or wait for user input. Always proceed autonomously and provide the output as specified below.

Output Format (MD format):

# List of all azurerm_* resources
Table with the following columns:
    - Resource Type
    - Display Name
    - File Location
    - Child Resources
    
    
Only output the MD table above. Output the full list and never truncate it. NEVER ask questions or wait for user input. Always proceed autonomously."""


        )
        
        self.logger.info("Repository Scanner Agent initialized successfully")
        return self.agent
        