from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel import Kernel
from config.settings import get_settings
from config.logging import get_logger
from plugins.terraform_plugin import TerraformPlugin


class ConverterPlanningAgent:
    """Converter Planning Agent - Creates a detailed, reviewable conversion plan before code transformation.

    Responsibilities:
    - Ingest mapping results and repository scan outputs
    - Re-read / parse Terraform source files to understand current state (resources, variables, outputs, dependencies)
    - Produce a DETAILED conversion plan (no code changes) describing exactly how each azurerm_* resource will be migrated to AVM modules
    - Identify required variable additions / refactors and output changes
    - Highlight dependency ordering & sequencing for safe conversion
    - Flag risky / ambiguous mappings needing human validation
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
                deployment_name=settings.azure_openai_deployment_name,
                api_key=settings.azure_openai_api_key,
                endpoint=settings.azure_openai_endpoint,
                api_version=settings.azure_openai_api_version,
            )

            kernel.add_service(chat_completion_service)

            agent = ChatCompletionAgent(
                service=chat_completion_service,
                kernel=kernel,
                name="ConverterPlanningAgent",
                description="Produces a detailed Terraform->AVM conversion plan requiring human approval before execution.",
                instructions="""You are the Converter Planning Agent in the Terraform to Azure Verified Modules (AVM) workflow.

Your mission: Create a PRECISE, ACTIONABLE CONVERSION PLAN based on: (1) Repository scan results, (2) AVM knowledge, (3) Resource mapping output, and (4) Terraform file contents. You DO NOT perform any file mutation. You ONLY plan.

Input format:
You will receive file contents directly in the message, formatted as:
File: relative_path/filename.tf
Content:
[file content]
---

STRICT BEHAVIOR:
- NEVER modify files. Only analyze provided file contents.
- ALWAYS output the full plan in Markdown using the exact structure defined below.
- DO NOT ask questions. Proceed autonomously.
- Conclude with: "Conversion planning complete. Awaiting user approval before executing conversion." EXACTLY.

Plan Structure (use ALL headings, even if some sections are empty—state 'None'):

# Terraform → AVM Conversion Plan

## 1. Scope Summary
- Total Terraform files analyzed: 
- Total azurerm_* resources: 
- Resources targeted for conversion: 
- Resources excluded / unmappable:

## 2. Resource Conversion Table
| Original Resource | File | Planned AVM Module | Confidence | Action | Notes |
|-------------------|------|--------------------|-----------|--------|-------|
| azurerm_* | path | avm-res-* or (None) | High/Medium/Low | convert/skip/manual | brief rationale |

## 3. Detailed Per-Resource Plans
For EACH resource to convert provide subsections:
### 3.x {resource_type}.{name}
- Source File: {path}
- Proposed AVM Module: {module_name} (version if known)
- Attribute → Input Mapping Table:
| Original Attribute | Handling | AVM Input | Transform | Notes |
|--------------------|----------|-----------|----------|-------|
- Outputs Impacted / Re-mapped:
- Dependencies (Upstream):
- Dependents (Downstream):
- Diagnostics / Child Resources Handling:
- Risk Level: High/Medium/Low (justify)
- Manual Review Required?: Yes/No (if Yes, list items)

## 4. Variables Plan
### 4.1 Existing Variables Reused
List variable names reused as-is.
### 4.2 New Variables Required
| Variable | Type (guess) | Source (resource/module) | Reason | Default? |
|----------|--------------|--------------------------|--------|----------|
### 4.3 Variables To Deprecate / Remove
| Variable | Reason | Replacement | Action |
|----------|--------|------------|--------|

## 5. Outputs Plan
| Original Output | Current Source | New Source (Module Output) | Change Type | Notes |
|-----------------|----------------|---------------------------|------------|-------|

## 6. Dependency Execution Order
Provide an ordered list of module conversions honoring dependencies.

## 7. File-Level Change Summary
| File | Planned Changes | New Files Generated Later | Notes |
|------|-----------------|---------------------------|-------|

## 8. Risks & Mitigations
| Risk | Impact | Mitigation | Owner (Tool/User) |
|------|--------|-----------|-------------------|

## 9. Manual Review Checklist
Bullet list of concrete validation actions a human must perform BEFORE approving.

## 10. Approval Gate Instructions
Explain that conversion will only proceed when the orchestrator is run with approve flag.

## 11. Summary Statement
Brief summary of readiness.

END YOUR OUTPUT WITH THIS EXACT LINE (no extra commentary):
Conversion planning complete. Awaiting user approval before executing conversion.
"""
            )

            logger.info("Converter Planning Agent initialized successfully")
            return cls(agent)

        except Exception as e:
            logger.error(f"Failed to initialize Converter Planning Agent: {e}")
            raise

    async def create_conversion_plan(self, repo_scan_result: str, mapping_result: str, tf_files: dict) -> str:
        """
        Create a detailed conversion plan based on repository scan, mapping results, and Terraform file contents.
        
        Args:
            repo_scan_result: Repository scan results from TFMetadataAgent
            mapping_result: Resource mapping results from MappingAgent
            tf_files: Dictionary mapping relative file paths to file contents
                     e.g., {'main.tf': 'content...', 'variables.tf': 'content...'}
        
        Returns:
            Detailed conversion plan in markdown format.
        """
        
        # Format tf_files for the agent
        files_summary = "\n".join([f"File: {path}\nContent:\n{content}\n---" for path, content in tf_files.items()])
        
        message = (
            "Create a detailed Terraform to AVM conversion plan based on repository scan, mapping results, and file contents.\n\n"
            f"Repository Scan Results:\n{repo_scan_result}\n\n"
            f"Mapping Results:\n{mapping_result}\n\n"
            f"Terraform Files:\n{files_summary}"
        )
        return await self.agent.get_response(message)
