import logging
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from dotenv import load_dotenv
import os
import logging
import asyncio
import re
from datetime import datetime
from pathlib import Path

from semantic_kernel import Kernel
from semantic_kernel.functions import kernel_function
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.mcp import MCPStdioPlugin
from semantic_kernel.agents import ChatCompletionAgent, ChatHistoryAgentThread
from semantic_kernel.functions import kernel_function

from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.azure_chat_prompt_execution_settings import (
    AzureChatPromptExecutionSettings,
)

# load from environment variables or configure directly

load_dotenv()  # Ensure to load environment variables from a .env file if needed

class HttpClientPlugin:
    def __init__(self):
        pass

    @kernel_function(
        description="Fetch content from a given URL. Returns the response text.",
        name="fetch_url",
    )
    async def fetch_url(self, url: str) -> str:
        """Fetch content from the specified URL and return the response text."""
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.text()

class FileSystemManagerPlugin:
    def __init__(self, base_path="d:/repos/tf2avm"):
        self.base_path = Path(base_path)

    @kernel_function(
        description="Read all Terraform (.tf) files from a specified directory path. Returns a dictionary of file paths and their contents.",
        name="read_tf_files",
    )
    def read_tf_files(self, directory_path: str = None) -> dict:
        """Read all .tf files from the specified directory and return as a dictionary with filename as key and content as value."""
        search_path = Path(directory_path) if directory_path else self.base_path
        tf_files = {}
        for tf_file in search_path.glob("**/*.tf"):
            try:
                with open(tf_file, "r", encoding="utf-8") as f:
                    tf_files[str(tf_file.relative_to(search_path))] = f.read()
            except Exception as e:
                print(f"Error reading {tf_file}: {e}")
        return tf_files

    @kernel_function(
        description="Write content to a file in the specified output directory. Returns the path to the created file.",
        name="write_file",
    )
    def write_file(self, output_dir: str, filename: str, content: str) -> str:
        """Write content to a file in the output directory and return the file path."""
        file_path = Path(output_dir) / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return str(file_path)


def validate_environment():
    """Validate required environment variables"""
    required_vars = [
        "AZURE_OPENAI_DEPLOYMENT_NAME",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_VERSION",
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
            args=["run", "-i", "--rm", "hashicorp/terraform-mcp-server"],
        ) as terraform_plugin:
            logger.info("Terraform MCP Plugin initialized successfully")

            kernel = Kernel()

            # Add Azure OpenAI chat completion
            chat_completion_service = AzureChatCompletion(
                deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            )

            kernel.add_service(chat_completion_service)

            agent = ChatCompletionAgent(
                service=chat_completion_service,
                kernel=kernel,
                name="TerraformAVMAgent",
                plugins=[terraform_plugin, FileSystemManagerPlugin(), HttpClientPlugin()],
                instructions="""Role: Terraform → Azure Verified Modules (AVM) Conversion Agent

Goal:
Convert a given Terraform repository containing Azure (azurerm_*) resources into an AVM-based Terraform structure. Replace eligible azurerm_* resources with the correct AVM resource/module calls while preserving intent. Produce a Markdown conversion report summarizing actions, mappings, issues, and next steps.

Inputs (provided as context):
- Folder with the Terraform files to convert.
- Output folder for the converted files - consider that this folder already exists.

Authoritative References (you must rely on these conceptually):
- Official AVM module registry naming (e.g., avm-res-network-virtualnetwork)
- Terraform Registry module input/output variables for matched AVM modules
- Standard azurerm provider schema (for source resources)

>>>>> Core Tasks:
1. Parse all Terraform files:
   - Collect resources (type, name, attributes)
   - Collect variables, outputs, locals, module calls
   - Build simple dependency awareness (e.g., referencing order)

2. Retrieve AVM Modules mapping from AVM Docs:
    - Use fetch_url tool to fetch and parse the AVM module index from https://azure.github.io/Azure-Verified-Modules/indexes/terraform/tf-resource-modules/
    - Read the mapping from the "Published modules" section
    - Display Name represents the azurerm resource type (e.g., "Virtual Network" → azurerm_virtual_network)
    - Module Name represents the AVM module name (e.g., "avm-res-network-virtualnetwork")

3. Determine AVM Mappings:
   - For each azurerm_* resource, attempt to map to an AVM module from the previous step
   - Record: original resource address → AVM module name, confidence
   - If no AVM equivalent, mark unmapped (do NOT delete original; leave as-is)

4. Plan Conversion:
   - Identify required AVM inputs missing from existing variables
   - Propose new variables where necessary
   - Identify new mandatory AVM attributes not present in original resources

5. Perform Conversion:
   - Replace eligible azurerm_* resource blocks with module blocks calling the AVM module
   - Map original attributes to AVM inputs where possible
   - Preserve comments when possible
   - Keep unmapped resources intact
   - Update variables.tf with any new required variables
   - Update outputs.tf to expose key module outputs analogous to original resources
   - Create the converted files and store the new files in the directory /output/{ddMMyyyy-hhmmss}/migrated.
   - Create a copy of the original TF files on the folder /output/{ddMMyyyy-hhmmss}/original.
   - Use the createFile and createDirectory tools to create the new files and directories.

6. Validation Hints (simulate):
   - Flag missing required AVM inputs
   - Flag attributes that have no direct AVM equivalent
   - Flag potential breaking changes (naming, implicit dependencies)

7. Produce Report (exact format below):
   - Converted files list
   - Successful mappings (original → AVM)
   - Issues (missing vars, unmapped resources, incompatible attributes)
   - Next steps (manual actions)
   - Do NOT fabricate success; be explicit about gaps.
   - Store the report in /output/{ddMMyyyy-hhmmss}/conversion_report.md

   
7.1 Mandatory Report Format (exact sections, omit empty sections):

# Conversion Report: <repo_name>

## ✅ Converted Files
- <file> → AVM
...

## ✅ Successful Mappings
- <azurerm_type> → <avm-module-name>
...

## ⚠️ Issues Found
- <issue 1>
- <issue 2>

## 🔧 Next Steps
- <action 1>
- <action 2>

8. Tools available:
- fetch_url
    Purpose: Fetch content from a given URL
    What it returns: The response text from the URL

- get_module_details	
      Purpose: Get comprehensive Terraform module information	
      What it returns: Complete Terraform documentation with inputs, outputs, examples, and submodules

- read_tf_files
      Purpose: Read all Terraform (.tf) files from a specified directory path
      What it returns: Dictionary of file paths and their contents

- write_file
      Purpose: Write content to a file in the specified output directory
      What it returns: Path to the created file

9. Output Requirements:
   Produce BOTH:
   1. New Terraform converted files and mapping file. Use the available tools to create the files and directories:
      - Converted .tf files (/output/{ddMMyyyy-hhmmss}/migrated/)
      - Original .tf files (/output/{ddMMyyyy-hhmmss}/original/)
      - avm-mapping.json (resource → module mapping with confidence)
   2. Markdown conversion report in /output/{ddMMyyyy-hhmmss}/:conversion_report.md


10. Rules:
- Do not guess AVM modules if uncertain; mark unmapped.
- Preserve original variable naming unless conflicting.
- Use placeholder versions if unknown (e.g., ">= 1.0.0") and note in Issues.
- Avoid removing functionality (log instead).
- If nothing convertible: produce report with empty Converted Files and full rationale.
- Be deterministic and concise.
- Edge Cases:
    - Mixed providers: only process azurerm_*.
    - Embedded module calls that already use AVM: list as already compliant.
    - Count/for_each/meta-arguments: replicate into module block where safe.

>>>>> Instructions:
- Validate the Inputs and make no assumptions.
- If you don't understand something, ask for clarification and don't make assumptions. On this case, don't execute any steps.
- Use the tools provided.
- Plan all the steps before executing the steps: create a step-by-step plan and execute the steps one by one. Output the plan as part of the final Output.
- Generate the full Output in a single response.

""")

            # Initialize file system manager and analyzer

            thread: ChatHistoryAgentThread | None = None

            # Create the output directory
            output_folder = f"output/{datetime.now().strftime('%d%m%Y-%H%M%S')}"
            os.makedirs(output_folder, exist_ok=True)

            # Conversion scenarios
            response = await agent.get_response(
                messages="Convert files from folder D:\\repos\\tf2avm\\tests\\fixtures\\repo_tf_basic to output folder " + output_folder,
                thread=thread,
            )
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
