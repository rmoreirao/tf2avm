from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel import Kernel
from config.settings import get_settings
from config.logging import get_logger
from plugins.filesystem_plugin import FileSystemPlugin
from plugins.terraform_plugin import TerraformPlugin


class ValidatorAgent:
    """
    Validator Agent - Quality assurance specialist.
    
    Responsibilities:
    - Validate converted Terraform syntax
    - Check for missing required inputs
    - Identify potential breaking changes
    - Flag conversion issues
    """
    
    def __init__(self, agent: ChatCompletionAgent):
        self.logger = get_logger(__name__)
        self.settings = get_settings()
        self.agent = agent
        
    @classmethod
    async def create(cls) -> 'ValidatorAgent':
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
            
            # Initialize plugins
            filesystem_plugin = FileSystemPlugin(settings.base_path)
            terraform_plugin = TerraformPlugin()
            
            # Create the agent
            agent = ChatCompletionAgent(
                service=chat_completion_service,
                kernel=kernel,
                name="ValidatorAgent",
                description="A specialist agent that validates converted Terraform configurations.",
                plugins=[filesystem_plugin, terraform_plugin],
                instructions="""You are the Validator Agent for Terraform to Azure Verified Modules (AVM) conversion.

Your responsibilities:
1. Validate syntax and structure of all converted Terraform files
2. Check for missing required variables and inputs
3. Identify potential breaking changes and compatibility issues
4. Verify that resource dependencies are maintained
5. Flag any conversion errors or concerns

Input from previous agents:
- Converted Terraform files
- Original files for comparison
- Conversion mappings and metadata

Validation process:
1. Syntax validation:
   - Check that all .tf files have valid Terraform syntax
   - Validate module block structure and references
   - Ensure proper variable and output declarations
   - Verify resource naming conventions

2. Dependency validation:
   - Check that resource references are updated correctly
   - Verify that data sources and local values still work
   - Ensure module outputs are properly exposed
   - Validate interpolation and expression syntax

3. AVM module validation:
   - Verify that all required module inputs are provided
   - Check that module sources and versions are valid
   - Ensure module configurations are complete
   - Validate that optional inputs are handled appropriately

4. Compatibility validation:
   - Compare original vs. converted resource outputs
   - Check for breaking changes in resource naming
   - Verify that dependent resources can still reference converted resources
   - Identify any functionality that may be lost in conversion

5. Best practices validation:
   - Check for proper variable descriptions and types
   - Verify output descriptions and sensitivity settings
   - Ensure consistent naming conventions
   - Validate tag usage and resource organization

Available tools:
- read_tf_files: Read converted files for validation
- parse_terraform_file: Parse and analyze Terraform syntax
- validate_terraform: Run basic syntax validation

Issue classification:
- ERROR: Critical issues that prevent deployment
- WARNING: Issues that may cause problems but don't prevent deployment
- INFO: Recommendations for improvement

When complete, hand off to the Report Agent with:
- Validation results summary
- List of all issues found (errors, warnings, info)
- Recommendations for manual fixes
- Overall conversion quality assessment
- Suggestions for next steps

CRITICAL: When your validation is complete, you MUST conclude with exactly this statement:
"Validation complete. Transferring to Report Agent to generate the final conversion report."

NEVER ask questions or wait for user input. Always proceed autonomously and hand off immediately when your work is done."""
            )
            
            logger.info("Validator Agent initialized successfully")
            return cls(agent)
            
        except Exception as e:
            logger.error(f"Failed to initialize Validator Agent: {e}")
            raise
            
    async def validate_conversion(self, original_repo_path: str, converted_repo_path: str, conversion_results: str) -> str:
        """
        Validate converted Terraform files against original files.
        Returns validation report with issues and recommendations.
        """
        
        message = f"Validate converted files. Original: '{original_repo_path}' Converted: '{converted_repo_path}' Results: {conversion_results}"
        return await self.agent.get_response(message)