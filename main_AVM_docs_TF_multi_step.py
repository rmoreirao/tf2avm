import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json
from datetime import datetime
import asyncio
import os
from enum import Enum
from dotenv import load_dotenv

from semantic_kernel import Kernel
from semantic_kernel.agents import ChatCompletionAgent, ChatHistoryAgentThread
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.mcp import MCPStdioPlugin
from semantic_kernel.functions import kernel_function


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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


class ConversionState(Enum):
    """Track the state of conversion process"""
    INITIALIZED = "initialized"
    PARSING = "parsing"
    MAPPING = "mapping"
    CONVERTING = "converting"
    VALIDATING = "validating"
    WRITING = "writing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class ConversionContext:
    """Store conversion context and intermediate results"""
    source_path: Path
    output_path: Path
    state: ConversionState
    parsed_files: Dict[str, str] = None
    avm_mappings: Dict[str, Dict] = None
    converted_files: Dict[str, str] = None
    validation_results: Dict[str, List[str]] = None
    report: str = None
    
    def to_dict(self):
        """Serialize context for checkpointing"""
        return {
            "source_path": str(self.source_path),
            "output_path": str(self.output_path),
            "state": self.state.value,
            "parsed_files": self.parsed_files,
            "avm_mappings": self.avm_mappings,
            "converted_files": self.converted_files,
            "validation_results": self.validation_results,
            "report": self.report
        }
    
    def save_checkpoint(self):
        """Save current state to checkpoint file"""
        checkpoint_path = self.output_path / "checkpoint.json"
        with open(checkpoint_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
        logger.info(f"Checkpoint saved to {checkpoint_path}")

class TerraformParser:
    """Dedicated parser for Terraform files"""
    
    def __init__(self, kernel: Kernel, agent: ChatCompletionAgent):
        self.kernel = kernel
        self.agent = agent
    
    async def parse_terraform_files(self, context: ConversionContext) -> Dict[str, str]:
        """Parse and analyze Terraform files"""
        logger.info("Starting Terraform file parsing")
        context.state = ConversionState.PARSING
        
        try:
            response = await self.agent.get_response(
                messages=f"""Parse all Terraform files in {context.source_path} and return:
                1. List of all resources (type, name, attributes)
                2. Variables, outputs, locals, and module calls
                3. Basic dependency information
                
                Return as structured JSON."""
            )
            
            # Extract parsed data from response
            parsed_data = self._extract_parsed_data(response)
            context.parsed_files = parsed_data
            context.save_checkpoint()
            
            return parsed_data
            
        except Exception as e:
            logger.error(f"Error parsing Terraform files: {e}")
            context.state = ConversionState.FAILED
            raise

    def _extract_parsed_data(self, response) -> Dict[str, str]:
        """Extract and validate parsed data from agent response"""
        # Implementation to extract structured data from response
        # Add validation logic here
        return {}

class AVMMapper:
    """Handle AVM module mapping logic"""
    
    def __init__(self, kernel: Kernel, agent: ChatCompletionAgent):
        self.kernel = kernel
        self.agent = agent
        self.avm_index_url = "https://azure.github.io/Azure-Verified-Modules/indexes/terraform/tf-resource-modules/"
    
    async def fetch_avm_mappings(self) -> Dict[str, str]:
        """Fetch AVM module mappings from official documentation"""
        logger.info("Fetching AVM module mappings")
        
        response = await self.agent.get_response(
            messages=f"""Fetch and parse the AVM module index from {self.avm_index_url}.
            Extract the mapping between azurerm resources and AVM modules.
            Return as JSON with format: {{"azurerm_resource_type": "avm-module-name"}}"""
        )
        
        # Validate and return mappings
        return self._validate_mappings(response)
    
    async def map_resources_to_avm(self, context: ConversionContext) -> Dict[str, Dict]:
        """Map parsed resources to AVM modules"""
        logger.info("Mapping resources to AVM modules")
        context.state = ConversionState.MAPPING
        
        avm_mappings = await self.fetch_avm_mappings()
        
        response = await self.agent.get_response(
            messages=f"""Given these parsed Terraform resources: {json.dumps(context.parsed_files)}
            And these AVM mappings: {json.dumps(avm_mappings)}
            
            Create a mapping plan with:
            - Original resource → AVM module
            - Confidence level (high/medium/low)
            - Required input transformations
            - Unmapped resources
            
            Return as structured JSON."""
        )
        
        context.avm_mappings = self._extract_mappings(response)
        context.save_checkpoint()
        return context.avm_mappings
    
    def _validate_mappings(self, response) -> Dict[str, str]:
        """Validate AVM mappings"""
        # Add validation logic
        return {}
    
    def _extract_mappings(self, response) -> Dict[str, Dict]:
        """Extract and validate resource mappings"""
        # Add extraction logic
        return {}

class TerraformConverter:
    """Handle the actual conversion of Terraform files"""
    
    def __init__(self, kernel: Kernel, agent: ChatCompletionAgent):
        self.kernel = kernel
        self.agent = agent
    
    async def convert_files(self, context: ConversionContext) -> Dict[str, str]:
        """Convert Terraform files to use AVM modules"""
        logger.info("Starting file conversion")
        context.state = ConversionState.CONVERTING
        
        response = await self.agent.get_response(
            messages=f"""Convert these Terraform files based on the mapping plan:
            Source files: {json.dumps(context.parsed_files)}
            Mappings: {json.dumps(context.avm_mappings)}
            
            Rules:
            - Replace azurerm resources with AVM module calls
            - Preserve functionality and comments
            - Keep unmapped resources as-is
            - Generate new variables if needed
            
            Return the converted files as JSON with filename as key."""
        )
        
        context.converted_files = self._extract_converted_files(response)
        context.save_checkpoint()
        return context.converted_files
    
    def _extract_converted_files(self, response) -> Dict[str, str]:
        """Extract converted files from response"""
        # Add extraction and validation logic
        return {}

class ConversionValidator:
    """Validate the conversion results"""
    
    def __init__(self, kernel: Kernel, agent: ChatCompletionAgent):
        self.kernel = kernel
        self.agent = agent
    
    async def validate_conversion(self, context: ConversionContext) -> Dict[str, List[str]]:
        """Validate the converted files"""
        logger.info("Validating conversion")
        context.state = ConversionState.VALIDATING
        
        response = await self.agent.get_response(
            messages=f"""Validate these converted Terraform files:
            {json.dumps(context.converted_files)}
            
            Check for:
            - Missing required AVM inputs
            - Incompatible attribute mappings
            - Potential breaking changes
            - Syntax validity
            
            Return validation results as JSON."""
        )
        
        context.validation_results = self._extract_validation_results(response)
        context.save_checkpoint()
        return context.validation_results
    
    def _extract_validation_results(self, response) -> Dict[str, List[str]]:
        """Extract validation results"""
        # Add extraction logic
        return {}

class FileWriter:
    """Handle all file writing operations with proper error handling"""
    
    @staticmethod
    async def write_conversion_output(context: ConversionContext):
        """Write all conversion outputs to disk"""
        logger.info("Writing conversion output")
        context.state = ConversionState.WRITING
        
        try:
            # Create directory structure
            migrated_path = context.output_path / "migrated"
            original_path = context.output_path / "original"
            
            migrated_path.mkdir(parents=True, exist_ok=True)
            original_path.mkdir(parents=True, exist_ok=True)
            
            # Write converted files
            for filename, content in context.converted_files.items():
                file_path = migrated_path / filename
                file_path.write_text(content, encoding='utf-8')
                logger.info(f"Written converted file: {file_path}")
            
            # Copy original files
            for tf_file in context.source_path.glob("**/*.tf"):
                relative_path = tf_file.relative_to(context.source_path)
                dest_path = original_path / relative_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                dest_path.write_text(tf_file.read_text(encoding='utf-8'), encoding='utf-8')
                logger.info(f"Copied original file: {dest_path}")
            
            # Write mapping file
            mapping_path = context.output_path / "avm-mapping.json"
            mapping_path.write_text(json.dumps(context.avm_mappings, indent=2), encoding='utf-8')
            
            # Write report
            report_path = context.output_path / "conversion_report.md"
            report_path.write_text(context.report, encoding='utf-8')
            
            context.state = ConversionState.COMPLETED
            context.save_checkpoint()
            
        except Exception as e:
            logger.error(f"Error writing files: {e}")
            context.state = ConversionState.FAILED
            raise

class ReportGenerator:
    """Generate conversion reports"""
    
    def __init__(self, kernel: Kernel, agent: ChatCompletionAgent):
        self.kernel = kernel
        self.agent = agent
    
    async def generate_report(self, context: ConversionContext) -> str:
        """Generate comprehensive conversion report"""
        logger.info("Generating conversion report")
        
        response = await self.agent.get_response(
            messages=f"""Generate a conversion report based on:
            Mappings: {json.dumps(context.avm_mappings)}
            Validation: {json.dumps(context.validation_results)}
            
            Use this exact format:
            # Conversion Report: {context.source_path.name}
            
            ## ✅ Converted Files
            - List files that were successfully converted
            
            ## ✅ Successful Mappings
            - List resource type mappings
            
            ## ⚠️ Issues Found
            - List any issues or warnings
            
            ## 🔧 Next Steps
            - List manual actions required
            """
        )
        
        context.report = str(response.message.content)
        return context.report

class TerraformToAVMConverter:
    """Main orchestrator for the conversion process"""
    
    def __init__(self, kernel: Kernel):
        self.kernel = kernel
        self.agent = None
        
    async def initialize(self):
        """Initialize the conversion agent and plugins"""
        # Initialize plugins
        self.terraform_plugin = await self._init_terraform_plugin()
        self.file_plugin = FileSystemManagerPlugin()
        self.http_plugin = HttpClientPlugin()
        
        # Create agent
        service = self.kernel.get_service()
        self.agent = ChatCompletionAgent(
            service=service,
            kernel=self.kernel,
            name="TerraformAVMAgent",
            instructions="You are a helpful AI assistant for Terraform to AVM conversion.",
            plugins=[self.terraform_plugin, self.file_plugin, self.http_plugin]
        )
        
        # Initialize components
        self.parser = TerraformParser(self.kernel, self.agent)
        self.mapper = AVMMapper(self.kernel, self.agent)
        self.converter = TerraformConverter(self.kernel, self.agent)
        self.validator = ConversionValidator(self.kernel, self.agent)
        self.reporter = ReportGenerator(self.kernel, self.agent)
    
    async def _init_terraform_plugin(self):
        """Initialize Terraform MCP plugin"""
        return MCPStdioPlugin(
            name="Terraform",
            description="Search for current Terraform provider documentation",
            command="docker",
            args=["run", "-i", "--rm", "hashicorp/terraform-mcp-server"]
        )
    
    async def convert(self, source_path: str, output_path: str = None) -> ConversionContext:
        """Main conversion method with step-by-step execution"""
        # Create output directory
        if not output_path:
            output_path = f"output/{datetime.now().strftime('%d%m%Y-%H%M%S')}"
        
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize context
        context = ConversionContext(
            source_path=Path(source_path),
            output_path=output_dir,
            state=ConversionState.INITIALIZED
        )
        
        try:
            # Step 1: Parse Terraform files
            await self.parser.parse_terraform_files(context)
            logger.info("✓ Parsing completed")
            
            # Step 2: Map resources to AVM modules
            await self.mapper.map_resources_to_avm(context)
            logger.info("✓ Mapping completed")
            
            # Step 3: Convert files
            await self.converter.convert_files(context)
            logger.info("✓ Conversion completed")
            
            # Step 4: Validate conversion
            await self.validator.validate_conversion(context)
            logger.info("✓ Validation completed")
            
            # Step 5: Generate report
            await self.reporter.generate_report(context)
            logger.info("✓ Report generated")
            
            # Step 6: Write output files
            await FileWriter.write_conversion_output(context)
            logger.info("✓ Files written successfully")
            
            return context
            
        except Exception as e:
            logger.error(f"Conversion failed: {e}")
            context.state = ConversionState.FAILED
            context.save_checkpoint()
            raise


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

# Usage example
async def main():
    """Example usage of the improved converter"""
    try:
        load_dotenv()  # Load environment variables from .env file if present
        # Validate environment
        validate_environment()
        
        # Initialize kernel
        kernel = Kernel()
        
        # Add Azure OpenAI service
        chat_service = AzureChatCompletion(
            deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION")
        )
        kernel.add_service(chat_service)
        
        # Create and initialize converter
        converter = TerraformToAVMConverter(kernel)
        await converter.initialize()
        
        # Run conversion
        context = await converter.convert(
            source_path="D:\\repos\\tf2avm\\tests\\fixtures\\repo_tf_basic"
        )
        
        logger.info(f"Conversion completed successfully!")
        logger.info(f"Output directory: {context.output_path}")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())