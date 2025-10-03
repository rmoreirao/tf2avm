from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel import Kernel
from config.settings import get_settings
from config.logging import get_logger
from plugins.filesystem_plugin import FileSystemPlugin
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

    def __init__(self):
        self.logger = get_logger(__name__)
        self.settings = get_settings()
        self.agent = None

    async def initialize(self):
        """Initialize the agent with Azure OpenAI service and plugins."""
        try:
            kernel = Kernel()

            chat_completion_service = AzureChatCompletion(
                deployment_name=self.settings.azure_openai_deployment_name,
                api_key=self.settings.azure_openai_api_key,
                endpoint=self.settings.azure_openai_endpoint,
                api_version=self.settings.azure_openai_api_version,
            )

            kernel.add_service(chat_completion_service)

            filesystem_plugin = FileSystemPlugin(self.settings.base_path)
            terraform_plugin = TerraformPlugin()

            self.agent = ChatCompletionAgent(
                service=chat_completion_service,
                kernel=kernel,
                name="ConverterPlanningAgent",
                description="Produces a detailed Terraform->AVM conversion plan requiring human approval before execution.",
                plugins=[filesystem_plugin, terraform_plugin],
                instructions="""You are the Converter Planning Agent in the Terraform to Azure Verified Modules (AVM) workflow.\n\nYour mission: Create a PRECISE, ACTIONABLE CONVERSION PLAN based on: (1) Repository scan results, (2) AVM knowledge, (3) Resource mapping output. You DO NOT perform any file mutation. You ONLY plan.\n\nSTRICT BEHAVIOR:\n- NEVER modify files. Only read / analyze.\n- ALWAYS output the full plan in Markdown using the exact structure defined below.\n- DO NOT ask questions. Proceed autonomously.\n- Conclude with: \"Conversion planning complete. Awaiting user approval before executing conversion.\" EXACTLY.\n\nAvailable tooling (invoke when helpful):\n- read_tf_files: Inspect raw Terraform source\n- parse_terraform_file: Structural parsing / extraction\n\nPlan Structure (use ALL headings, even if some sections are empty—state 'None'):\n\n# Terraform → AVM Conversion Plan\n\n## 1. Scope Summary\n- Total Terraform files analyzed: {n}\n- Total azurerm_* resources: {n}\n- Resources targeted for conversion: {n}\n- Resources excluded / unmappable: {n}\n\n## 2. Resource Conversion Table\n| Original Resource | File | Planned AVM Module | Confidence | Action | Notes |\n|-------------------|------|--------------------|-----------|--------|-------|\n| azurerm_* | path | avm-res-* or (None) | High/Medium/Low | convert/skip/manual | brief rationale |\n\n## 3. Detailed Per-Resource Plans\nFor EACH resource to convert provide subsections:\n### 3.x {resource_type}.{name}\n- Source File: {path}\n- Proposed AVM Module: {module_name} (version if known)\n- Attribute → Input Mapping Table:\n| Original Attribute | Handling | AVM Input | Transform | Notes |\n|--------------------|----------|-----------|----------|-------|\n- Outputs Impacted / Re-mapped:\n- Dependencies (Upstream):\n- Dependents (Downstream):\n- Diagnostics / Child Resources Handling:\n- Risk Level: High/Medium/Low (justify)\n- Manual Review Required?: Yes/No (if Yes, list items)\n\n## 4. Variables Plan\n### 4.1 Existing Variables Reused\nList variable names reused as-is.\n### 4.2 New Variables Required\n| Variable | Type (guess) | Source (resource/module) | Reason | Default? |\n|----------|--------------|--------------------------|--------|----------|\n### 4.3 Variables To Deprecate / Remove\n| Variable | Reason | Replacement | Action |\n|----------|--------|------------|--------|\n\n## 5. Outputs Plan\n| Original Output | Current Source | New Source (Module Output) | Change Type | Notes |\n|-----------------|----------------|---------------------------|------------|-------|\n\n## 6. Dependency Execution Order\nProvide an ordered list of module conversions honoring dependencies.\n\n## 7. File-Level Change Summary\n| File | Planned Changes | New Files Generated Later | Notes |\n|------|-----------------|---------------------------|-------|\n\n## 8. Risks & Mitigations\n| Risk | Impact | Mitigation | Owner (Tool/User) |\n|------|--------|-----------|--------------------|\n\n## 9. Manual Review Checklist\nBullet list of concrete validation actions a human must perform BEFORE approving.\n\n## 10. Approval Gate Instructions\nExplain that conversion will only proceed when the orchestrator is run with approve flag.\n\n## 11. Summary Statement\nBrief summary of readiness.\n\nEND YOUR OUTPUT WITH THIS EXACT LINE (no extra commentary):\nConversion planning complete. Awaiting user approval before executing conversion.\n"""
            )

            self.logger.info("Converter Planning Agent initialized successfully")
            return self.agent

        except Exception as e:
            self.logger.error(f"Failed to initialize Converter Planning Agent: {e}")
            raise
