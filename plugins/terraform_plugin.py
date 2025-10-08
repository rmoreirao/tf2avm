import json
import aiohttp
from semantic_kernel.functions import kernel_function
from semantic_kernel.connectors.mcp import MCPStdioPlugin


class TerraformPlugin:
    """Plugin for Terraform-specific operations using MCP."""
    
    def __init__(self):
        self.mcp_plugin = None

    # async def initialize_mcp(self):
        # """Initialize the Terraform MCP plugin."""
        # try:
        #     self.mcp_plugin = MCPStdioPlugin(
        #         name="Terraform",
        #         description="Search for current Terraform provider documentation, modules, and policies from the Terraform registry.",
        #         command="docker",
        #         args=["run", "-i", "--rm", "hashicorp/terraform-mcp-server"],
        #     )
        #     await self.mcp_plugin.__aenter__()
        #     return self.mcp_plugin
        # except Exception as e:
        #     print(f"Failed to initialize Terraform MCP plugin: {e}")
        #     return None

    # @kernel_function(
    #     description="Search for Terraform modules matching a query.",
    #     name="search_terraform_modules",
    # )
    # async def search_terraform_modules(self, query: str) -> str:
    #     """Search for Terraform modules using the MCP plugin."""
    #     if not self.mcp_plugin:
    #         await self.initialize_mcp()
        
    #     # This would use the MCP plugin's search functionality
    #     # For now, return a placeholder response
    #     return f"Searching for Terraform modules with query: {query}"

    # @kernel_function(
    #     description="Get details about a specific Terraform module.",
    #     name="get_module_details",
    # )
    # async def get_module_details(self, module_name: str) -> str:
    #     """Get detailed information about a Terraform module."""
    #     if not self.mcp_plugin:
    #         await self.initialize_mcp()
        
    #     # This would use the MCP plugin's module details functionality
    #     return f"Getting details for module: {module_name}"

    # @kernel_function(
    #     description="Validate Terraform configuration syntax.",
    #     name="validate_terraform",
    # )
    # def validate_terraform(self, terraform_content: str) -> str:
    #     """Validate Terraform configuration syntax."""
    #     # Simple validation - in practice, this would use terraform validate
    #     if "resource" in terraform_content and "{" in terraform_content:
    #         return "Terraform syntax appears valid"
    #     else:
    #         return "Terraform syntax validation failed"
        
    
    # Retrieve input parameters for a specific AVM module
    @kernel_function(
        description="Retrieve input parameters for a specific AVM module.",
        name="get_avm_module_inputs",
    )
    async def get_avm_module_inputs(self, module_name: str, module_version: str) -> str:
        # do not use the mcp plugin here
        # fetch the module details from url https://registry.terraform.io/v1/modules/Azure/{module name}/azurerm/{module version}

        

        module_details_url = f"https://registry.terraform.io/v1/modules/Azure/{module_name}/azurerm/{module_version}"

        # log
        print(f"Fetching input parameters for module: {module_name}, version: {module_version}. URL: {module_details_url}")

        async with aiohttp.ClientSession() as session:
            async with session.get(module_details_url) as response:
                if response.status == 200:
                    module_details = await response.json()
                    # input are on module_details['root']['inputs']
                    inputs = module_details.get("root", {}).get("inputs", [])
                    # print inputs
                    ret_inputs = json.dumps(inputs, indent=2)
                    if not ret_inputs or len(ret_inputs) == 0:
                        raise ValueError(f"No inputs found for {module_name} version {module_version}. HTTP Status: {response.status}")
                    return ret_inputs
                else:
                    raise ValueError(f"Failed to retrieve module details for {module_name} version {module_version}. HTTP Status: {response.status}")


    
    # Retrieve AVM module details
    @kernel_function(
        description="Retrieve AVM module details in JSON format. Inputs: module_name, module_version",
        name="get_avm_module_details",
    )
    async def get_avm_module_details(self, module_name: str, module_version: str) -> str:
        # do not use the mcp plugin here
        # fetch the module details from url https://registry.terraform.io/v1/modules/Azure/{module name}/azurerm/{module version}

        # log
        print(f"Fetching AVM module details for module: {module_name}, version: {module_version}")

        module_details_url = f"https://registry.terraform.io/v1/modules/Azure/{module_name}/azurerm/{module_version}"
        async with aiohttp.ClientSession() as session:
            async with session.get(module_details_url) as response:
                if response.status == 200:
                    return await json.dumps(response, indent=2)
                else:
                    raise ValueError(f"Failed to retrieve module details for {module_name} version {module_version}. HTTP Status: {response.status}")