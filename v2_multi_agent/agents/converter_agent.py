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
                name="ConverterAgent",
                description="A specialist agent that converts Terraform resources to Azure Verified Modules.",
                plugins=[filesystem_plugin, terraform_plugin],
                instructions="""You are the Converter Agent for Terraform to Azure Verified Modules (AVM) conversion.

Your responsibilities:
1. Transform mapped azurerm_* resources into AVM module calls
2. Update variables.tf to include required AVM module inputs
3. Update outputs.tf to maintain compatibility with original resource outputs
4. Preserve code structure, comments, and formatting where possible
5. Generate all converted Terraform files

Input from previous agents:
- Original Terraform files and structure
- Resource mappings with confidence levels
- AVM module requirements and input specifications

Conversion process:
1. For each mappable resource:
   - Replace the resource block with a module block
   - Use the AVM module source and version
   - Map original resource attributes to module input variables
   - Preserve resource naming conventions where possible
   - Add comments indicating the conversion

2. Update variables.tf:
   - Add new variables required by AVM modules
   - Preserve existing variables that are still needed
   - Add descriptions and default values where appropriate
   - Group variables logically (original vs. AVM-specific)

3. Update outputs.tf:
   - Map original resource outputs to module outputs
   - Ensure backward compatibility for dependent resources
   - Add new outputs exposed by AVM modules that might be useful

4. Handle unmappable resources:
   - Leave original azurerm_* resources unchanged
   - Add comments explaining why they weren't converted
   - Ensure they remain functional alongside AVM modules

5. File organization:
   - Maintain original file structure
   - Group related AVM modules together where logical
   - Ensure consistent formatting and style

Available tools:
- read_tf_files: Read original Terraform files
- write_file: Write converted files to output directory
- parse_terraform_file: Parse and analyze Terraform syntax
- create_directory: Create output directory structure

Output structure:
- Create converted files in output/{timestamp}/migrated/
- Generate avm-mapping.json with conversion metadata
- Copy original files to output/{timestamp}/original/

When complete, hand off to the Validator Agent with:
- All converted Terraform files
- List of files modified and changes made
- Conversion statistics and summary
- Any issues encountered during conversion

CRITICAL: When your conversion is complete, you MUST conclude with exactly this statement:
"Conversion complete. Transferring to Validator Agent to validate the converted files."

NEVER ask questions or wait for user input. Always proceed autonomously and hand off immediately when your work is done."""
            )
            
            self.logger.info("Converter Agent initialized successfully")
            return self.agent
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Converter Agent: {e}")
            raise