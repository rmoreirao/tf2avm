import json
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel import Kernel
from config.settings import get_settings
from config.logging import get_logger
from plugins.terraform_plugin import TerraformPlugin
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion, OpenAIChatPromptExecutionSettings
from semantic_kernel.functions import KernelArguments

from schemas.models import TerraformMetadataAgentResult


class TFMetadataAgent:
    """
    Terraform Metadata Agent - Terraform repository analysis specialist.
    
    Responsibilities:
    - Parse all Terraform files (.tf)
    - Extract resources, variables, outputs, locals
    - Build dependency maps
    - Identify azurerm_* resources for conversion
    """
    
    def __init__(self, agent: ChatCompletionAgent):
        self.logger = get_logger(__name__)
        self.settings = get_settings()
        self.agent = agent
        
    @classmethod
    async def create(cls) -> 'TFMetadataAgent':
        """Factory method to create and initialize the agent."""
        logger = get_logger(__name__)
        settings = get_settings()
    
        # Create kernel and add services
        kernel = Kernel()
        execution_settings = OpenAIChatPromptExecutionSettings(response_format=TerraformMetadataAgentResult)
        chat_completion_service = AzureChatCompletion(
            deployment_name=settings.azure_openai_deployment_name,
            api_key=settings.azure_openai_api_key,
            endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version,
        )
        
        kernel.add_service(chat_completion_service)
        
                
        # Create the agent
        agent = ChatCompletionAgent(
            service=chat_completion_service,
            kernel=kernel,
            name="RepoScannerAgent",
            description="A specialist agent that analyzes Terraform repositories and extracts resource information.",
            arguments=KernelArguments(execution_settings),
            instructions="""You are the Repository Scanner Agent for Terraform to Azure Verified Modules (AVM) conversion.

Your responsibilities:
1. Scan and parse all provided Terraform (.tf) file contents
2. Extract and catalog all resources, variables, outputs, and locals
3. Identify azurerm_* resources that are candidates for AVM conversion
4. Build a dependency map of resources and identify child resources
5. Generate a comprehensive repository manifest

Input format:
You will receive file contents directly in the message, formatted as:
File: relative_path/filename.tf
Content:
[file content]
---

Process:
1. Parse each provided file content to identify resources, variables, outputs, locals
2. Focus on azurerm_* resources as conversion candidates
3. Document file structure and dependencies
4. Determine the Child Resources for each azure resource:
A child resource is a resource that is defined within the context of another resource, often indicating a hierarchical relationship or dependency between the two resources. 
They are tightly associated with another (typically by explicit references or required unique identifiers).
Child resources can be defined on different files within the same repository.
Examples of child resources:
- A network interface (child) associated with a virtual machine (parent).
- A disk (child) attached to a virtual machine (parent).
- azurerm_monitor_diagnostic_setting (child) associated with an Azure resource (parent).
5. Identify any Outputs that reference these resources:
    - For example, the output below references the azurerm_linux_web_app resource type, the ""web"" resource name, and the ""default_hostname"" attribute of the resource.:
        output "web_app_url" {
            description = "URL of the Web App"
            value = "https://$\{azurerm_linux_web_app.web.default_hostname\}"
        }
    - The output can be on different files within the same repository.
6. Create a detailed scan result

>>>Instructions:

NEVER ask questions or wait for user input. Always proceed autonomously and provide the output as specified below."""
        )
        
        logger.info("Repository Scanner Agent initialized successfully")
        return cls(agent)
        
    async def scan_repository(self, tf_files: dict) -> TerraformMetadataAgentResult:
        """
        Scan and analyze Terraform repository from tf_files dictionary.
        
        Args:
            tf_files: Dictionary mapping relative file paths to file contents
                     e.g., {'main.tf': 'content...', 'variables.tf': 'content...'}
        
        Returns:
            Markdown analysis of the repository.
        """
        
        # Format tf_files for the agent
        files_summary = "\n".join([f"File: {path}\nContent:\n{content}\n---" for path, content in tf_files.items()])
        
        message = f"Scan and analyze Terraform repository from the following files:\n\n{files_summary}"
        response = await self.agent.get_response(message)
        output = TerraformMetadataAgentResult.model_validate(json.loads(response.message.content))
        return output