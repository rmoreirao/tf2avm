import json
import aiohttp
from semantic_kernel.functions import kernel_function
from semantic_kernel.connectors.mcp import MCPStdioPlugin
from typing import List, Optional, Dict, Any
from schemas.models import AVMModuleDetailed, AVMModuleInput, AVMModuleOutput



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
    # docs : https://developer.hashicorp.com/terraform/registry/api-docs#get-a-specific-module
    @kernel_function(
        description="Retrieve AVM module details in JSON format. Inputs: module_name, module_version",
        name="get_avm_module_details_json",
    )
    async def get_avm_module_details_json(self, module_name: str, module_version: str) -> str:
        # do not use the mcp plugin here
        # fetch the module details from url https://registry.terraform.io/v1/modules/Azure/{module name}/azurerm/{module version}

        # there are some resources with provider "azure" instead of "azurerm"
        providers = ["azurerm","azure"]

        for provider in providers:
            module_details_url = f"https://registry.terraform.io/v1/modules/Azure/{module_name}/{provider}/{module_version}".strip()

            # log
            print(f"Fetching AVM module details for module: {module_name}, version: {module_version}. URL: {module_details_url}")

            async with aiohttp.ClientSession() as session:
                async with session.get(module_details_url) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 404:
                        print(f"Module not found with provider {provider}, trying next if available.")
                        continue
                    else:
                        raise ValueError(f"Failed to retrieve module details for {module_name} version {module_version}. URL: {module_details_url}, HTTP Status: {response.status}, Response: {await response.text()}")
                    

    async def get_avm_module_details_model(self, module_name: str, module_version: str) -> AVMModuleDetailed:
        """
        Parse Terraform Registry API response to create AVMModuleDetailed object.
        
        Args:
            json_data: Dictionary containing the JSON response from Terraform Registry API
            
        Returns:
            AVMModuleDetailed: Parsed module details
        """

        response = await self.get_avm_module_details_json(module_name, module_version)

        if isinstance(response, dict):
            json_data = response
        elif isinstance(response, str):
            json_data = json.loads(response)
        else:
            raise ValueError(f"Unexpected response type: {type(response)}")
        
        # Extract basic module information
        name = json_data.get("name", "")
        description = json_data.get("description", "")
        version = json_data.get("version", "")
        source_url = json_data.get("source", "")
        
        # Construct display name from namespace and name
        namespace = json_data.get("namespace", "")
        display_name = f"{namespace}/{name}" if namespace else name
        
        # Construct Terraform Registry URL
        provider = json_data.get("provider", "")
        terraform_registry_url = f"https://registry.terraform.io/modules/{namespace}/{name}/{provider}"
        
        # Extract requirements from root module
        requirements = []
        if "root" in json_data and "provider_dependencies" in json_data["root"]:
            for provider_dep in json_data["root"]["provider_dependencies"]:
                provider_name = provider_dep.get("name", "")
                version_constraint = provider_dep.get("version", "")
                if provider_name and version_constraint:
                    requirements.append(f"{provider_name} {version_constraint}")
        
        # Extract resources from root module
        resources = []
        if "root" in json_data and "resources" in json_data["root"]:
            for resource in json_data["root"]["resources"]:
                resource_type = resource.get("type", "")
                if resource_type:
                    resources.append(resource_type)
        
        # Parse inputs
        inputs = []
        if "root" in json_data and "inputs" in json_data["root"]:
            for input_data in json_data["root"]["inputs"]:
                input_obj = AVMModuleInput(
                    name=input_data.get("name", ""),
                    type=input_data.get("type", ""),
                    required=input_data.get("required", True)
                )
                inputs.append(input_obj)
        
        # Parse outputs
        outputs = []
        if "root" in json_data and "outputs" in json_data["root"]:
            for output_data in json_data["root"]["outputs"]:
                output_obj = AVMModuleOutput(
                    name=output_data.get("name", ""),
                    description=output_data.get("description", "")
                )
                outputs.append(output_obj)
        
        
        return AVMModuleDetailed(
            name=name,
            display_name=display_name,
            version=version,
            description=description,
            terraform_registry_url=terraform_registry_url,
            source_code_url=source_url,
            requirements=requirements,
            resources=resources,
            inputs=inputs,
            outputs=outputs
        )