import logging
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from dotenv import load_dotenv
import os
import logging, sys
import asyncio

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





async def main():
    # root = logging.getLogger()
    # if not root.handlers:
    #     h = logging.StreamHandler(sys.stdout)
    #     h.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s"))
    #     root.addHandler(h)
    # root.setLevel(logging.DEBUG)

    # # Extra noisy libs
    # logging.getLogger("openai").setLevel(logging.DEBUG)
    # logging.getLogger("httpx").setLevel(logging.DEBUG)
    # logging.getLogger("semantic_kernel").setLevel(logging.DEBUG)

    # Initialize the kernel
    # kernel = Kernel()

    async with MCPStdioPlugin(
            name="Terraform",
            description="Search forcurrent Terraform provider documentation, modules, and policies from the Terraform registry.",
            command="docker",
            args=["run","-i","--rm","hashicorp/terraform-mcp-server"]
        ) as terraform_plugin:

        # Add Azure OpenAI chat completion
        chat_completion_service = AzureChatCompletion(
            deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),  
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION")
        )

        agent = ChatCompletionAgent(
                service=chat_completion_service,
                name="TerraformAgent",
                instructions="""You are a Terraform documentation assistant. Use the available functions to search for Terraform resources. 
                Format results in a clear HTML table with columns for resource name, type, and link.""",
                plugins=[terraform_plugin],
            )

        thread: ChatHistoryAgentThread | None = None


        user_inputs = [
            "Virtual Network Resource for Azure Verified Modules (AVM)",
            "Azure APIM Resource for AWS Verified Modules (AVM)",
        ]

        for user_input in user_inputs:
            response = await agent.get_response(messages=user_input, thread=thread)
            thread = response.thread

            # Process the response text
            response_text = str(response)

            print("Agent response: " + response_text)

        # Cleanup
        if thread:
            await thread.delete()
            print("Thread cleaned up")

        # kernel.add_service(chat_completion_service)

        # # Set the logging level for  semantic_kernel.kernel to DEBUG.
        # setup_logging()
        # logging.getLogger("kernel").setLevel(logging.DEBUG)


        # # Enable planning
        # execution_settings = AzureChatPromptExecutionSettings()
        # execution_settings.function_choice_behavior = FunctionChoiceBehavior.Auto()

        # # Create a history of the conversation
        # history = ChatHistory()

        # # Initiate a back-and-forth chat
        # userInput = None
        # while True:
        #     # Collect user input
        #     userInput = input("User > ")

        #     # Terminate the loop if the user says "exit"
        #     if userInput == "exit":
        #         break

        #     # Add user input to the history
        #     history.add_user_message(userInput)

        #     # Get the response from the AI
        #     result = await chat_completion_service.get_chat_message_content(
        #         chat_history=history,
        #         settings=execution_settings,
        #         kernel=kernel,
        #     )

        #     # Print the results
        #     print("Assistant > " + str(result))

        #     # Add the message from the agent to the chat history
        #     history.add_message(result)

# Run the main function
if __name__ == "__main__":
    asyncio.run(main())
