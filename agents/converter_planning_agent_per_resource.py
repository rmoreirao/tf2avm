import json
from typing import List
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel import Kernel
from config.settings import get_settings
from config.logging import get_logger
from plugins.terraform_plugin import TerraformPlugin
from plugins.http_plugin import HttpClientPlugin
from schemas.models import (
    AVMModuleDetailed, 
    ResourceMapping, 
    TerraformOutputreference,
    ResourceConverterPlanningAgentResult,
    ResourceConversionPlan
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

        # Initialize plugins
        terraform_plugin = TerraformPlugin()
        http_plugin = HttpClientPlugin()

        agent = ChatCompletionAgent(
            service=chat_completion_service,
            kernel=kernel,
            name="ResourceConverterPlanningAgent",
            description="Produces detailed Terraform->AVM conversion plans with integrated resource mapping functionality.",
            plugins=[terraform_plugin, http_plugin],
            instructions="""You are the Resource Converter Planning Agent in the Terraform to Azure Verified Modules (AVM) workflow.

You are the Resource Planning Agent analyzing ONE SPECIFIC RESOURCE at a time.

Your mission: Create a PRECISE conversion plan for the SINGLE azurerm_* resource provided, outputting BOTH structured JSON and human-readable Markdown.

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
- ALWAYS output VALID JSON
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
        """
        Create a detailed conversion plan with integrated resource mapping based on repository scan, AVM knowledge, and Terraform file contents.
        
        Args:
            resource_mapping: Mapping results from MappingAgent
            avm_module_detail: AVM module knowledge from AVMKnowledgeAgent
            tf_file: Tuple of (filename, file_content)
            original_tf_resource_output_paramers: List of outputs referencing this resource
        
        Returns:
            ResourceConverterPlanningAgentResult with both structured and markdown plans.
        """
        
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
            "Output the response in two parts:\n"
            "1. First, a valid JSON object with the structured plan\n"
            "2. Then, the markdown formatted plan\n"
        )
        
        response = await self.agent.get_response(message)
        
        # Parse the response to extract JSON and markdown
        response_text = str(response)
        
        try:
            # Try to extract JSON from the response
            # Look for JSON code block or raw JSON
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                result_dict = json.loads(json_str)
                
                # Extract markdown (everything after the JSON)
                markdown_start = response_text.find('#', json_end)
                if markdown_start == -1:
                    # If no markdown section found, use a default
                    markdown_plan = "# Conversion Plan\n\nSee structured output for details."
                else:
                    markdown_plan = response_text[markdown_start:].strip()
                
                # Create the result object
                return ResourceConverterPlanningAgentResult(
                    conversion_plan=ResourceConversionPlan(**result_dict['conversion_plan']),
                    markdown_plan=markdown_plan,
                    planning_summary=result_dict.get('planning_summary', 'Conversion plan created'),
                    warnings=result_dict.get('warnings', [])
                )
            else:
                # Fallback: if JSON parsing fails, treat entire response as markdown
                self.logger.warning("Failed to parse JSON from agent response, using fallback structure")
                return self._create_fallback_result(resource_mapping, avm_module_detail, filename, response_text)
                
        except Exception as e:
            self.logger.error(f"Error parsing agent response: {e}")
            return self._create_fallback_result(resource_mapping, avm_module_detail, filename, response_text)
    
    def _create_fallback_result(
        self, 
        resource_mapping: ResourceMapping, 
        avm_module_detail: AVMModuleDetailed, 
        filename: str, 
        response_text: str
    ) -> ResourceConverterPlanningAgentResult:
        """Create a fallback result when JSON parsing fails."""
        return ResourceConverterPlanningAgentResult(
            conversion_plan=ResourceConversionPlan(
                resource_type=resource_mapping.source_resource.type,
                resource_name=resource_mapping.source_resource.name,
                source_file=filename,
                target_avm_module=resource_mapping.target_module.name if resource_mapping.target_module else "unknown",
                target_avm_version=resource_mapping.target_module.version if resource_mapping.target_module else "unknown",
                avm_resource_name=f"{resource_mapping.source_resource.name}_avm",
                transformation_action="convert_to_module",
                attribute_mappings=[],
                existing_variables_reused=[],
                new_variables_required=[],
                output_mappings=[],
                required_providers=[],
                risk_level="High",
                risk_notes="Fallback result due to parsing error - manual review required"
            ),
            markdown_plan=response_text,
            planning_summary="Fallback result created due to response parsing error",
            warnings=["Failed to parse structured output from agent - using fallback"]
        )
