from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel import Kernel
from config.settings import get_settings
from config.logging import get_logger
from plugins.filesystem_plugin import FileSystemPlugin
from plugins.terraform_plugin import TerraformPlugin


class ConverterAgent:
    """
    Converter Agent - Code transformation specialist.
    
    Responsibilities:
    - Transform azurerm_* resources to AVM module calls
    - Update variables.tf and outputs.tf
    - Preserve comments and structure
    - Generate converted files
    """
    
    def __init__(self, agent: ChatCompletionAgent):
        self.logger = get_logger(__name__)
        self.settings = get_settings()
        self.agent = agent
        
    @classmethod
    async def create(cls) -> 'ConverterAgent':
        """Factory method to create and initialize the agent."""
        logger = get_logger(__name__)
        settings = get_settings()
        
        # Create kernel and add services
        kernel = Kernel()
        
        chat_completion_service = AzureChatCompletion(
            deployment_name=settings.azure_openai_deployment_name,
            api_key=settings.azure_openai_api_key,
            endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version,
        )
        
        kernel.add_service(chat_completion_service)
        
        # Initialize plugins
        filesystem_plugin = FileSystemPlugin(settings.base_path)
        terraform_plugin = TerraformPlugin()
        
        # Create the agent
        agent = ChatCompletionAgent(
            service=chat_completion_service,
            kernel=kernel,
            name="ConverterAgent",
            description="A specialist agent that converts Terraform resources to Azure Verified Modules.",
            plugins=[filesystem_plugin, terraform_plugin],
            instructions="""You are the Converter Agent for Terraform to Azure Verified Modules (AVM) conversion.

Your responsibilities:
1. Transform mapped azurerm_* resources into AVM module calls according to the provided conversion plan
2. Update variables.tf to include required AVM module inputs according to the provided conversion plan
3. Update outputs.tf to maintain compatibility with original resource outputs according to the provided conversion plan
4. Preserve code structure, comments, and formatting where possible
5. Generate all converted Terraform files

Authoritative Conversion Plan (follow this precisely; it overrides generic guidance if conflicts arise): the conversion plan will be provided at runtime.

Operational Process:
1. Retrieve and parse the conversion plan JSON provided at runtime.
2. Retrieve and parse the original Terraform files from the specified repository path provided at runtime.
3. Use ONLY the resources and mappings declared in the conversion plan.
4. For each resource in plan.mappings:
- Replace resource blocks with AVM module blocks (source, version from plan).
- Map attributes exactly as specified.
- Insert conversion comment header.
5. Update variables.tf and outputs.tf per plan.required_variables and plan.required_outputs.
6. Preserve and annotate unmapped resources as described.
7. Write converted files to output folder maintaining structure. Output directory will be provided at runtime.
8. Summarize the conversion: counts (converted, skipped, unmapped), new variables, new outputs, deviations from plan.

Available tools:
- read_tf_files
- write_file
- parse_terraform_file

Never ask for clarifications; proceed autonomously."""
        )
        
        logger.info("Converter Agent initialized successfully with conversion plan")
        return cls(agent)


    async def run_conversion(self, conversion_plan: str, output_dir: str, repo_path: str) -> str:
        """
        Kick off autonomous conversion using the initialized agent and injected plan.
        Returns the final agent response.
        """
        
        kickoff_message = (
            f"Begin conversion now using the injected conversion plan: {conversion_plan}. "
            f"Output directory: '{output_dir}'. "
            f"Original TF files folder: {str(repo_path)}. "
        )
        
        return await self.agent.get_response(kickoff_message)
        