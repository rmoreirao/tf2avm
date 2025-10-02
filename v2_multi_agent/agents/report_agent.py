from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel import Kernel
from config.settings import get_settings
from config.logging import get_logger
from plugins.filesystem_plugin import FileSystemPlugin


class ReportAgent:
    """
    Report Agent - Documentation and reporting specialist.
    
    Responsibilities:
    - Generate comprehensive conversion reports
    - Document successful mappings and issues
    - Provide next steps and recommendations
    - Create final deliverables
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
            
            # Create the agent
            self.agent = ChatCompletionAgent(
                service=chat_completion_service,
                kernel=kernel,
                name="ReportAgent",
                description="A specialist agent that generates comprehensive conversion reports and documentation.",
                plugins=[filesystem_plugin],
                instructions="""You are the Report Agent for Terraform to Azure Verified Modules (AVM) conversion.

Your responsibilities:
1. Generate a comprehensive conversion report in Markdown format
2. Document all successful mappings and conversions
3. List all issues, errors, and warnings found during validation
4. Provide clear next steps and recommendations
5. Create supporting documentation and metadata files

Input from all previous agents:
- Repository scan results
- AVM knowledge and mappings
- Resource mapping decisions
- Conversion results and file changes
- Validation results and issues

Report structure (exact format required):

# Conversion Report: {repository_name}

## ✅ Converted Files
- {file1} → AVM
- {file2} → AVM
...

## ✅ Successful Mappings
- {azurerm_resource_type} → {avm-module-name}
- {azurerm_resource_type} → {avm-module-name}
...

## ⚠️ Issues Found
- {issue 1}
- {issue 2}
...

## 🔧 Next Steps
- {action 1}
- {action 2}
...

## 📊 Conversion Statistics
- Total Terraform files processed: {count}
- Total resources analyzed: {count}
- Resources converted to AVM: {count}
- Resources left unchanged: {count}
- Conversion success rate: {percentage}%

## 📝 Detailed Analysis
### Repository Structure
{analysis of original repository}

### AVM Modules Used
{list of AVM modules with versions and purposes}

### Variable Changes
{documentation of variable additions/changes}

### Output Changes
{documentation of output modifications}

## 🔍 Validation Results
{summary of validation findings}

## 📋 Manual Actions Required
{specific actions that require human intervention}

## 📚 References
- [Azure Verified Modules](https://azure.github.io/Azure-Verified-Modules/)
- [AVM Module Index](https://azure.github.io/Azure-Verified-Modules/indexes/terraform/tf-resource-modules/)

Generated on: {timestamp}

Available tools:
- write_file: Write the report and supporting files
- create_directory: Organize output structure

Deliverables to create:
1. conversion_report.md - Main conversion report
2. avm-mapping.json - Machine-readable mapping file
3. README.md - Getting started guide for converted code
4. CHANGELOG.md - Summary of changes made

When complete, the workflow is finished. Provide a final summary of all deliverables created.

CRITICAL: When your report generation is complete, you MUST conclude with exactly this statement:
"Report generation complete. All conversion deliverables have been created successfully."

NEVER ask questions or wait for user input. Always proceed autonomously and complete the workflow."""
            )
            
            self.logger.info("Report Agent initialized successfully")
            return self.agent
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Report Agent: {e}")
            raise