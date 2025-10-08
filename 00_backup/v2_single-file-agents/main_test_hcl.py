import logging
import os
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv
import hcl2  # type: ignore

from semantic_kernel.agents import ChatCompletionAgent, ChatHistoryAgentThread


#

import asyncio

from semantic_kernel import Kernel
from semantic_kernel.utils.logging import setup_logging
from semantic_kernel.functions import kernel_function
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.functions.kernel_arguments import KernelArguments

from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.azure_chat_prompt_execution_settings import (
    AzureChatPromptExecutionSettings,
)

def _is_local_path(repo_folder: str) -> bool:
    p = Path(repo_folder)
    return p.exists() and p.is_dir()

def _load_hcl_file(path: Path) -> Dict[str, Any]:
    if not _is_local_path(path.parent):
        raise ValueError(f"Invalid repo folder: {path.parent}")
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        return hcl2.load(f)
    
# Python
import json

load_dotenv()

async def main():
    # read all tf files
    hcl_collected = []   # was: hcl_full_data = ""
    tf_dir = Path(r"D:\\repos\\tf2avm\\tests\\fixtures\\repo_tf_basic")
    tf_files = list(tf_dir.glob("*.tf"))
    for tf_file in tf_files:
        print(f"File: {tf_file}")
        hcl_data = _load_hcl_file(tf_file)
        print(hcl_data)
        hcl_collected.append({"file": str(tf_file.name), "data": hcl_data})

    hcl_full_json = json.dumps(hcl_collected, ensure_ascii=False)

    # Initialize the kernel (unchanged...)
    chat_completion_service = AzureChatCompletion(
            deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),  
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION")
        )

    agent = ChatCompletionAgent(
            service=chat_completion_service,
            name="TerraformAgent",
            instructions="""You are a Terraform documentation assistant. You will receive hcl structured data from Terraform files.
                Your task is to help users understand the Terraform configuration and provide relevant information based on the data.
                A child resource is a resource that is defined within the context of another resource, often indicating a hierarchical relationship or dependency between the two resources. They are tightly associated with another (typically by explicit references or required unique identifiers).
                Examples of child resources:
                - A network interface (child) associated with a virtual machine (parent).
                - A disk (child) attached to a virtual machine (parent).
                - azurerm_monitor_diagnostic_setting (child) associated with an Azure resource (parent).
                Instruction: Identify the resources and their child resources. Output in MD format a list of resources with their types and names, and for each resource list its child resources indented.""",
        )

    thread: ChatHistoryAgentThread | None = None


    response = await agent.get_response(messages="HCL data (JSON array of files): " + hcl_full_json, thread=thread)
    thread = response.thread
    response_text = str(response)

    print("Response:")
    print(response_text)


# Run the main function
if __name__ == "__main__":
    asyncio.run(main())