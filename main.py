import logging
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from dotenv import load_dotenv
import os
import logging, sys
import asyncio
import re
from datetime import datetime
from pathlib import Path

from semantic_kernel import Kernel
from semantic_kernel.utils.logging import setup_logging
from semantic_kernel.functions import kernel_function
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.functions.kernel_arguments import KernelArguments
from semantic_kernel.connectors.mcp import MCPStdioPlugin
from semantic_kernel.agents import ChatCompletionAgent, ChatHistoryAgentThread

from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.azure_chat_prompt_execution_settings import (
    AzureChatPromptExecutionSettings,
)

# load from environment variables or configure directly

load_dotenv()  # Ensure to load environment variables from a .env file if needed

class FileSystemManager:
    def __init__(self, base_path="d:/repos/tf2avm"):
        self.base_path = Path(base_path)
        
    def create_output_directory(self):
        timestamp = datetime.now().strftime("%d%m%Y-%H%M%S")
        output_dir = self.base_path / "output" / timestamp
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir
    
    def read_tf_files(self, directory_path=None):
        search_path = Path(directory_path) if directory_path else self.base_path
        tf_files = {}
        for tf_file in search_path.glob("**/*.tf"):
            try:
                with open(tf_file, 'r', encoding='utf-8') as f:
                    tf_files[str(tf_file.relative_to(search_path))] = f.read()
            except Exception as e:
                print(f"Error reading {tf_file}: {e}")
        return tf_files
    
    def write_file(self, output_dir, filename, content):
        file_path = output_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return str(file_path)

class TerraformAnalyzer:
    def __init__(self):
        self.azurerm_resources = []
        self.variables = []
        self.outputs = []
        self.modules = []
    
    def parse_tf_content(self, tf_files):
        """Basic parsing to identify azurerm resources, variables, outputs"""
        for filename, content in tf_files.items():
            # Simple regex-based parsing (could be enhanced with HCL parser)
            
            # Find azurerm resources
            resource_pattern = r'resource\s+"(azurerm_\w+)"\s+"([^"]+)"'
            resources = re.findall(resource_pattern, content)
            for resource_type, resource_name in resources:
                self.azurerm_resources.append({
                    'file': filename,
                    'type': resource_type,
                    'name': resource_name,
                    'full_address': f'{resource_type}.{resource_name}'
                })
            
            # Find variables
            var_pattern = r'variable\s+"([^"]+)"'
            variables = re.findall(var_pattern, content)
            for var_name in variables:
                self.variables.append({
                    'file': filename,
                    'name': var_name
                })
            
            # Find outputs
            output_pattern = r'output\s+"([^"]+)"'
            outputs = re.findall(output_pattern, content)
            for output_name in outputs:
                self.outputs.append({
                    'file': filename,
                    'name': output_name
                })
        
        return {
            'resources': self.azurerm_resources,
            'variables': self.variables,
            'outputs': self.outputs
        }

def validate_environment():
    """Validate required environment variables"""
    required_vars = [
        "AZURE_OPENAI_DEPLOYMENT_NAME",
        "AZURE_OPENAI_API_KEY", 
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_VERSION"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {missing_vars}")
    
    return True

async def main():
    # Enable logging for debugging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        # Validate environment before starting
        validate_environment()
        logger.info("Environment validation passed")
        
        async with MCPStdioPlugin(
                name="Terraform",
                description="Search for current Terraform provider documentation, modules, and policies from the Terraform registry.",
                command="docker",
                args=["run","-i","--rm","hashicorp/terraform-mcp-server"]
            ) as terraform_plugin:
            
            logger.info("Terraform MCP Plugin initialized successfully")
            
            kernel = Kernel()

            # Add Azure OpenAI chat completion
            chat_completion_service = AzureChatCompletion(
                deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),  
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION")
            )
            
            kernel.add_service(chat_completion_service)
            kernel.add_plugin(terraform_plugin, plugin_name="Terraform")

            agent = ChatCompletionAgent(
                    service=chat_completion_service,
                    kernel=kernel,
                    name="TerraformAVMAgent",
                    instructions="""You are a Terraform → Azure Verified Modules (AVM) Conversion Agent.

Your primary goal is to convert existing Terraform repositories containing Azure (azurerm_*) resources into AVM-based structures.

Core Capabilities:
1. Parse Terraform files (.tf) to identify azurerm_* resources, variables, outputs, and modules
2. Search for appropriate AVM modules using the Terraform registry tools
3. Map azurerm_* resources to their AVM module equivalents
4. Generate converted Terraform files with module blocks replacing resource blocks
5. Produce comprehensive conversion reports

Workflow for conversion requests:
1. Analyze input Terraform files for azurerm_* resources
2. Use search_modules to find matching AVM modules
3. Use get_module_details to get comprehensive module documentation
4. Create conversion mappings (resource → AVM module)
5. Generate converted files in /output/{timestamp}/ directory
6. Produce detailed conversion report

Always be explicit about:
- Successful conversions vs. unmapped resources
- Missing required variables
- Potential breaking changes
- Required manual actions

Format responses as structured reports with clear sections for conversions, issues, and next steps.""",
                    plugins=[terraform_plugin],
                )

            # Initialize file system manager and analyzer
            fs_manager = FileSystemManager()
            tf_analyzer = TerraformAnalyzer()

            thread: ChatHistoryAgentThread | None = None

            # Conversion scenarios
            conversion_requests = [
                {
                    "description": "Convert Virtual Network Resources to AVM",
                    "context": "Analyze current directory for azurerm_virtual_network, azurerm_subnet resources and convert to avm-res-network-virtualnetwork module"
                }
            ]

            for request in conversion_requests:
                print(f"\n=== Processing: {request['description']} ===")
                
                # Read current Terraform files from test fixture
                tf_files = fs_manager.read_tf_files("tests/fixtures/repo_basic")
                if not tf_files:
                    print("No .tf files found in test fixture directory")
                    continue
                    
                # Analyze Terraform content
                tf_analyzer = TerraformAnalyzer()  # Reset for each request
                analysis = tf_analyzer.parse_tf_content(tf_files)
                print(f"Found {len(analysis['resources'])} azurerm resources")
                
                # Create context message with file contents and analysis
                context_message = f"""
CONVERSION REQUEST: {request['description']}

CONTEXT: {request['context']}

TERRAFORM FILES ANALYSIS:
- Files found: {list(tf_files.keys())}
- azurerm resources: {[r['full_address'] for r in analysis['resources']]}
- Variables: {[v['name'] for v in analysis['variables']]}
- Outputs: {[o['name'] for o in analysis['outputs']]}

TERRAFORM FILE CONTENTS:
{chr(10).join([f"=== {filename} ==={chr(10)}{content}{chr(10)}" for filename, content in tf_files.items()])}

Please perform the AVM conversion following the established workflow:
1. Search for appropriate AVM modules for each azurerm resource
2. Create conversion mappings
3. Generate converted Terraform files
4. Provide detailed conversion report

Create output files in /output/{{timestamp}}/ directory structure.
"""

                response = await agent.get_response(messages=[context_message], thread=thread)
                thread = response.thread

                # Process the response
                response_text = str(response.message.content)
                print(f"Conversion Result:\n{response_text}")
                print("-" * 50)

            # Cleanup
            if thread:
                await thread.delete()
                print("Thread cleaned up")
            
    except Exception as e:
        logger.error(f"Error during conversion process: {e}")
        raise

# Run the main function
if __name__ == "__main__":
    asyncio.run(main())
