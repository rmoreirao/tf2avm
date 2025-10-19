from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel import Kernel
from config.settings import get_settings
from config.logging import get_logger
from plugins.terraform_plugin import TerraformPlugin
from plugins.filesystem_plugin import FileSystemPlugin


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
        
        # Initialize plugins (only terraform plugin needed since we receive file contents directly)
        # terraform_plugin = TerraformPlugin()
        file_system_plugin = FileSystemPlugin()  

        # Create the agent
        agent = ChatCompletionAgent(
            service=chat_completion_service,
            kernel=kernel,
            name="ConverterAgent",
            description="A specialist agent that converts Terraform resources to Azure Verified Modules.",
            plugins=[file_system_plugin],
            instructions="""You are the Converter Agent for Terraform to Azure Verified Modules (AVM) conversion.

Your responsibilities:
1. Transform mapped azurerm_* resources into AVM module calls according to the provided conversion plan
2. Update variables.tf to include required AVM module inputs according to the provided conversion plan
3. Update outputs.tf to maintain compatibility with original resource outputs according to the provided conversion plan
4. Preserve code structure, comments, and formatting where possible
5. Generate all converted Terraform files

Inputs:
- Conversion Plan: Detailed conversion per file and resource
- Terraform File Contents: The contents of all .tf files to be converted
- Output Directory: The directory where converted files should be written
---

Authoritative Conversion Plan (follow this precisely; it overrides generic guidance if conflicts arise): the conversion plan will be provided at runtime.

Operational Process:
1. Retrieve and parse the conversion plan provided at runtime.
2. Parse the original Terraform file contents provided directly in the message.
3. Use ONLY the resources and mappings declared in the conversion plan.
4. For each resource in plan.mappings:
- Replace resource blocks with AVM module blocks (source, version from plan).
- Map attributes exactly as specified.
- Insert conversion comment header.
5. Update variables and outputs per plan.
6. Preserve unmapped resources as described.
7. Clean up any resource which is fully converted to module.
8. Write converted files to output folder maintaining structure. Output directory will be provided at runtime.
9. Validate that all mapped resources were converted as per the plan and report any deviations.
10. Summarize the conversion: counts (converted, skipped, unmapped), new variables, new outputs, deviations from plan.

Available tools:
- write_file: Write a file to the specified path with given content.

Output:
- Provide a summary of the conversion process including counts of converted resources, skipped resources, unmapped resources, new variables added, new outputs created, and any deviations from the plan.
- Use MD formatting for the summary.

Instructions:
- Always follow the provided conversion plan exactly.
- Never ask for clarifications; proceed autonomously.
- Create all output files in the specified output directory maintaining original structure when possible.
- At the end of the process, vaidate that all mapped resources were converted as per the plan and report any deviations."""
        )
        
        logger.info("Converter Agent initialized successfully with conversion plan")
        return cls(agent)


    async def run_conversion(self, conversion_plan: str, output_dir: str, tf_files: dict) -> str:        
        # Format tf_files for the agent
        files_summary = "\n".join([f"File: {path}\nContent:\n{content}\n---" for path, content in tf_files.items()])
        
        kickoff_message = (
            f"Begin conversion now using the conversion plan and Terraform file contents.\n\n"
            f"Conversion Plan per file / resource:\n{conversion_plan}\n\n"
            f"Output Directory: '{output_dir}'\n\n"
            f"Terraform Files:\n{files_summary}"
        )
        
        return await self.agent.get_response(kickoff_message)
        