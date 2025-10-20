import json
from typing import List
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel import Kernel
from config.settings import get_settings
from config.logging import get_logger
from plugins.terraform_plugin import TerraformPlugin
from plugins.http_plugin import HttpClientPlugin
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion, OpenAIChatPromptExecutionSettings
from semantic_kernel.functions import KernelArguments
from schemas.models import (
    AVMModuleDetailed, 
    ResourceMapping, 
    TerraformOutputreference,
    ResourceConverterPlanningAgentResult
)


class ResourceConverterPlanningAgent:
    """Converter Planning Agent - Creates detailed conversion plans with integrated resource mapping.

    Responsibilities:
    - Ingest repository scan results and AVM knowledge
    - Determine conversion confidence levels and identify unmappable resources
    - Parse Terraform source files to understand current state (resources, variables, outputs, dependencies)
    - Produce a DETAILED conversion plan describing exactly how each azurerm_* resource will be migrated to AVM modules
    - Plan required variable additions/refactors and output changes
    - Highlight dependency ordering & sequencing for safe conversion
    - Flag risky/ambiguous mappings needing human validation
    - Provide an execution checklist the Converter Agent will follow    
    """

    def __init__(self, agent: ChatCompletionAgent):
        self.logger = get_logger(__name__)
        self.settings = get_settings()
        self.agent = agent

    @classmethod
    async def create(cls) -> 'ResourceConverterPlanningAgent':
        """Factory method to create and initialize the agent."""
        logger = get_logger(__name__)
        settings = get_settings()
        

        kernel = Kernel()

        chat_completion_service = AzureChatCompletion(
            deployment_name=settings.azure_openai_deployment_name,
            api_key=settings.azure_openai_api_key,
            endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version,
        )

        kernel.add_service(chat_completion_service)

        execution_settings = OpenAIChatPromptExecutionSettings(response_format=ResourceConverterPlanningAgentResult)

        # Initialize plugins
        terraform_plugin = TerraformPlugin()
        http_plugin = HttpClientPlugin()

        agent = ChatCompletionAgent(
            service=chat_completion_service,
            kernel=kernel,
            name="ResourceConverterPlanningAgent",
            description="Produces detailed Terraform->AVM conversion plans with integrated resource mapping functionality.",
            plugins=[terraform_plugin, http_plugin],
            arguments=KernelArguments(execution_settings),
            instructions="""You are the Resource Converter Planning Agent in the Terraform to Azure Verified Modules (AVM) workflow.

You are the Resource Planning Agent analyzing ONE SPECIFIC RESOURCE at a time.

Your mission: Create a PRECISE conversion plan for the SINGLE azurerm_* resource provided, outputting structured JSON.

--> Input format:
- Resource Mapping: JSON object with source resource and target AVM module
- AVM Module Details: JSON object with the target module's full specifications
- Resource Content: The specific resource block from Terraform
- Variables: Available variables from the Terraform configuration
- Outputs from the original resource: this is to help map outputs to the new module outputs

--> Planning Process for THIS ONE RESOURCE:
1. Parse the specific azurerm_* resource block
2. Extract all attributes and their values
3. Map each attribute to the corresponding AVM module input
4. Ensure ALL required AVM inputs are satisfied (from attributes or propose new variables)
5. Document any unmapped attributes
6. Identify dependencies and child resources

--> Critical Requirements:
- EVERY required AVM module input MUST have a mapping or proposed solution
- If a required input has no source, propose a new variable with default value
- Flag any attributes that cannot be mapped to module inputs


--> STRICT BEHAVIOR:
- ALWAYS output VALID JSON - including all required fields
- !!!ONLY output the JSON!!!
- DO NOT ask questions. Proceed autonomously.
- Include mapping analysis as part of the planning process.

"""
            )

        logger.info("Converter Planning Agent initialized successfully")
        return cls(agent)


    async def create_conversion_plan(
        self, 
        resource_mapping: ResourceMapping, 
        avm_module_detail: AVMModuleDetailed, 
        tf_file: tuple[str, str], 
        original_tf_resource_output_paramers: List[TerraformOutputreference]
    ) -> ResourceConverterPlanningAgentResult:
       
        # Unpack the tuple
        filename, file_content = tf_file
        
        # Format file for the agent
        file_summary = f"File: {filename}\nContent:\n{file_content}\n---"
        avm_detail_json = avm_module_detail.model_dump_json()

        message = (
            "Create a detailed Terraform to AVM conversion plan with integrated resource mapping.\n\n"
            f"Resource Mapping JSON:\n{resource_mapping.model_dump_json()}\n\n"
            f"AVM Module Details JSON:\n{avm_detail_json}\n\n"
            f"Terraform File:\n{file_summary}\n\n"
            f"Original Resource Referenced Outputs JSON:\n{json.dumps([output.model_dump() for output in original_tf_resource_output_paramers], indent=2)}\n\n"
        )
        
        response = await self.agent.get_response(message)


        result = ResourceConverterPlanningAgentResult.model_validate(json.loads(response.message.content))

        return result