from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel import Kernel
from config.settings import get_settings
from config.logging import get_logger
from plugins.terraform_plugin import TerraformPlugin
from plugins.http_plugin import HttpClientPlugin


class ConverterPlanningAgent:
    """Converter Planning Agent - Creates detailed conversion plans with integrated resource mapping.

    Responsibilities:
    - Ingest repository scan results and AVM knowledge
    - Map azurerm_* resources to appropriate AVM modules
    - Determine conversion confidence levels and identify unmappable resources
    - Parse Terraform source files to understand current state (resources, variables, outputs, dependencies)
    - Produce a DETAILED conversion plan describing exactly how each azurerm_* resource will be migrated to AVM modules
    - Plan required variable additions/refactors and output changes
    - Highlight dependency ordering & sequencing for safe conversion
    - Flag risky/ambiguous mappings needing human validation
    - Provide an execution checklist the Converter Agent will follow
    - STOP the workflow until explicit user approval is granted
    """

    def __init__(self, agent: ChatCompletionAgent):
        self.logger = get_logger(__name__)
        self.settings = get_settings()
        self.agent = agent

    @classmethod
    async def create(cls) -> 'ConverterPlanningAgent':
        """Factory method to create and initialize the agent."""
        logger = get_logger(__name__)
        settings = get_settings()
        
        try:
            kernel = Kernel()

            chat_completion_service = AzureChatCompletion(
                deployment_name=settings.azure_openai_reasoning_deployment_name,
                api_key=settings.azure_openai_reasoning_api_key,
                endpoint=settings.azure_openai_reasoning_endpoint,
                api_version=settings.azure_openai_reasoning_api_version,
            )

            kernel.add_service(chat_completion_service)

            # Initialize plugins
            terraform_plugin = TerraformPlugin()
            http_plugin = HttpClientPlugin()

            agent = ChatCompletionAgent(
                service=chat_completion_service,
                kernel=kernel,
                name="ConverterPlanningAgent",
                description="Produces detailed Terraform->AVM conversion plans with integrated resource mapping functionality.",
                plugins=[terraform_plugin, http_plugin],
                instructions="""You are the Converter Planning Agent in the Terraform to Azure Verified Modules (AVM) workflow.

Your mission: Create a PRECISE, ACTIONABLE CONVERSION PLAN with integrated resource mapping based on: (1) Repository scan results, (2) AVM knowledge base, and (3) Terraform file contents. You DO NOT perform any file mutation. You ONLY analyze and plan.

CORE RESPONSIBILITIES:
1. RESOURCE MAPPING: Match azurerm_* resources to appropriate AVM modules using the provided AVM knowledge
2. CONFIDENCE ASSESSMENT: Determine conversion confidence levels for each mapping
3. DETAILED PLANNING: Create comprehensive conversion plans for each resource
4. DEPENDENCY ANALYSIS: Identify conversion order based on resource dependencies
5. VARIABLE & OUTPUT STRATEGY: Plan necessary variable and output changes

Input format:
- Repository Scan Results: Structured analysis of Terraform resources
- AVM Knowledge: JSON array of available AVM modules with display names and module names
- Terraform Files: File contents formatted as File: path\\nContent:\\n[content]\\n---

MAPPING PROCESS (Integrated):
1. For each azurerm_* resource from repository scan match to an AVM module from the AVM knowledge:
    - Match resource type to available AVM modules using displayName mappings
    - Assign confidence score: High (90-100%), Medium (60-89%), Low (30-59%), None (0-29%)
    - Document mappings, limitations and alternative approaches
   
2. Resource parameters mapping and analysis:
    - For each AVM module match, use the get_avm_module_inputs tool to retrieve input parameters for the module
    - Analyse all input parameters (required and optional) and compare against the resource attributes
    - Make sure all required inputs can be satisfied by existing attributes or variables
    - If required inputs cannot be satisfied, document what is missing and propose solution
    - Assess compatibility between resource attributes and module requirements
    - Document attribute to input mappings in a table format

3. For the resources which are not directly mappable to AVM modules:
    - If the resource is a child resource of a mappable resource:
        - In many cases, child resources are managed within the context of their parent resources in AVM modules.
        - Check if these child resources are being handled as inputs or configurations within the parent AVM module.
        - Use the input parameters retrieved for parent AVM module to check if they include the child resources.
        - Try to match the child resource attributes to the parent module inputs.
        - If they are, document how they are managed within the parent module and propose the migration strategy accordingly.
        - If they are not, document them as unmappable resources with explanations that "Child resources are not mappable to parent module inputs."

Available tools:
- get_avm_module_inputs: Retrieve input parameters for a specific AVM module

STRICT BEHAVIOR:
- ALWAYS output the full plan in Markdown using the exact structure defined below.
- DO NOT ask questions. Proceed autonomously.
- Include mapping analysis as part of the planning process.

Plan Structure (use ALL headings, even if some sections are empty—state 'None'):

# Terraform → AVM Conversion Plan

## 1. Resource Conversion Table
| Original Resource | File | Planned AVM Module | Confidence | Action | Notes |
|-------------------|------|--------------------|-----------|--------|-------|
| azurerm_* | path | avm-res-* or (None) | High/Medium/Low | convert/skip/manual | brief rationale |

## 2. Detailed Per-Resource Plans
For EACH resource to convert provide subsections:
### 2.x {resource_type}.{name}
- Source File: {path}
- Proposed AVM Module: {module_name} (version if known)
- Mapping Confidence: High/Medium/Low with justification
- Resource Input Name → AVM Input Mapping Table:
| Resource Input Name | Input Value | AVM Input Name | Input Value | AVM Optional or Required | Handling | Transform | Notes |
|--------------------|-------------|---------------|-------------|-------------------------|----------|-----------|-------|
|                    |             |               |             |                         |          |           |       |
- Make sure to include in the "Input Mapping Table":
    - all required AVM module inputs.
    - Attributes Available on Current resource which are not mappable to AVM module inputs

- Outputs Impacted / Re-mapped:
- Dependencies (Upstream):
- Dependents (Downstream):
- Child Resources / Diagnostics Handling:
- Risk Level: High/Medium/Low (justify)

## 3. Variables Plan
### 3.1 Existing Variables Reused
List variable names reused as-is.
### 3.2 New Variables Required
| Variable | Type | Source | Reason | Default? |
|----------|------|--------|--------|----------|
### 3.3 Variables To Deprecate / Remove
| Variable | Reason | Replacement | Action |
|----------|--------|------------|--------|

## 4. Outputs Plan
| Original Output | Current Source | New Source (Module Output) | Change Type | Notes |
|-----------------|----------------|---------------------------|------------|-------|


END YOUR OUTPUT.
"""
            )

            logger.info("Converter Planning Agent initialized successfully")
            return cls(agent)

        except Exception as e:
            logger.error(f"Failed to initialize Converter Planning Agent: {e}")
            raise

    async def create_conversion_plan(self, repo_scan_result: str, avm_knowledge: str, tf_files: dict) -> str:
        """
        Create a detailed conversion plan with integrated resource mapping based on repository scan, AVM knowledge, and Terraform file contents.
        
        Args:
            repo_scan_result: Repository scan results from TFMetadataAgent
            avm_knowledge: AVM module knowledge from AVMKnowledgeAgent
            tf_files: Dictionary mapping relative file paths to file contents
                     e.g., {'main.tf': 'content...', 'variables.tf': 'content...'}
        
        Returns:
            Detailed conversion plan with integrated mapping analysis in markdown format.
        """
        
        # Format tf_files for the agent
        files_summary = "\n".join([f"File: {path}\nContent:\n{content}\n---" for path, content in tf_files.items()])
        
        message = (
            "Create a detailed Terraform to AVM conversion plan with integrated resource mapping.\n\n"
            f"Repository Scan Results:\n{repo_scan_result}\n\n"
            f"AVM Knowledge Base:\n{avm_knowledge}\n\n"
            f"Terraform Files:\n{files_summary}"
        )
        return await self.agent.get_response(message)
