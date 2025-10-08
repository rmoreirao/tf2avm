import asyncio
from datetime import datetime
import json
from pathlib import Path
import shutil
import traceback
from typing import Dict, Any

from agents.avm_resource_details_agent import AVMResourceDetailsAgent
from config.settings import get_settings, validate_environment
from config.logging import setup_logging
from agents.tf_metadata_agent import TFMetadataAgent
from agents.avm_knowledge_agent import AVMKnowledgeAgent
from agents.converter_planning_agent import ConverterPlanningAgent
from agents.converter_agent import ConverterAgent
from agents.validator_agent import ValidatorAgent
from agents.report_agent import ReportAgent
from schemas.models import AVMKnowledgeAgentResult, MappingAgentResult, TerraformMetadataAgentResult
from agents.mapping_agent import MappingAgent


class TerraformAVMOrchestrator:
    """
    Main orchestrator for the Terraform to AVM conversion using Semantic Kernel Handoff Orchestration.
    """
    
    def __init__(self):
        self.logger = setup_logging()
        self.settings = get_settings()
        
    async def initialize(self):
        """Initialize the orchestrator."""
        try:
            # Validate environment
            validate_environment()
            self.logger.info("Environment validation passed")
            self.logger.info("Orchestrator initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize orchestrator: {e}")
            raise
    
    async def convert_repository(self, repo_path: str, output_dir: str) -> Dict[str, Any]:
        """
        Convert a Terraform repository to use Azure Verified Modules.
        
        Args:
            repo_path: Path to the Terraform repository
            output_dir: Optional output directory (will be generated if not provided)
            (Interactive) Will pause after planning for user approval in CLI mode.
            
        Returns:
            Dict containing conversion results and metadata
        """
        try:
            #validate the repo_path exists and contains .tf files
            repo_path_obj = Path(repo_path)
            if not repo_path_obj.exists() or not repo_path_obj.is_dir():
                raise FileNotFoundError(f"Repository path '{repo_path}' does not exist or is not a directory.")
            
            # Create output directory
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            self.logger.info(f"Starting conversion of repository: {repo_path}")
            self.logger.info(f"Output directory: {output_dir}")
            
            # Execute sequential workflow
            result = await self._run_sequential_workflow(repo_path, output_dir)
            
            self.logger.info("Conversion workflow completed successfully")
            
            return {
                "status": "completed",
                "repo_path": repo_path,
                "output_directory": output_dir,
                "result": str(result),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            full_traceback = traceback.format_exc()
            self.logger.error(f"Error during conversion: {e}\n{full_traceback}")
            return {
                "status": "failed",
                "repo_path": repo_path,
                "output_directory": output_dir,
                "error": str(e),
                "traceback": full_traceback,
                "timestamp": datetime.now().isoformat()
            }
    
    async def _run_sequential_workflow(self, repo_path: str, output_dir: str) -> str:
        """Run the agents in sequence with an interactive approval gate after planning."""

        # read all TF files and store in dictionary: relative folder/name -> content
        tf_files = {}
        for tf_file in Path(repo_path).rglob("*.tf"):
            relative_path = tf_file.relative_to(repo_path)
            tf_files[str(relative_path)] = tf_file.read_text(encoding="utf-8")

        # copy the TF files to output dir / original
        self.logger.info(f"Copying original TF files to output directory {output_dir}/original")
        original_output_dir = Path(output_dir) / "original"
        original_output_dir.mkdir(parents=True, exist_ok=True)
        for tf_file in Path(repo_path).rglob("*.tf"):
            shutil.copy(tf_file, original_output_dir / tf_file.name)


        # Step 0: AVMResourceDetailsAgent
        self.logger.info("Step 0: Initializing AVM Resource Details Agent")
        avm_resource_details_agent = await AVMResourceDetailsAgent.create()
        # Example usage (not part of the main workflow yet)
        example_module_name = "avm-res-web-site"
        example_module_version = "0.19.1"
        example_details = await avm_resource_details_agent.fetch_avm_resource_details(example_module_name, example_module_version)
        self.logger.info(f"Example AVM module details fetched for {example_module_name} version {example_module_version}: {example_details}")

        # store the results on output folder
        with open(f"{output_dir}/00_avm_resource_details_example.json", "w", encoding="utf-8") as f:
            f.write(example_details.model_dump_json(indent=2))

        exit()

        # Step 1: Repository Scanner Agent
        self.logger.info("Step 1: Running Repository Scanner Agent")
        tf_metadata_agent = await TFMetadataAgent.create()
        tf_metadata_agent_output : TerraformMetadataAgentResult = await tf_metadata_agent.scan_repository(tf_files)
        self._log_agent_response("TFMetadataAgent", tf_metadata_agent_output)

        # store the results on output folder
        with open(f"{output_dir}/01_tf_metadata.json", "w", encoding="utf-8") as f:
            f.write(tf_metadata_agent_output.model_dump_json(indent=2))
               
        # Step 2: AVM Knowledge Agent
        self.logger.info("Step 2: Running AVM Knowledge Agent")
        knowledge_agent = await AVMKnowledgeAgent.create()
        knowledge_result : AVMKnowledgeAgentResult = await knowledge_agent.fetch_avm_knowledge()
        self._log_agent_response("AVMKnowledgeAgent", knowledge_result)

        # store the results on output folder
        with open(f"{output_dir}/02_avm_knowledge.json", "w", encoding="utf-8") as f:
            f.write(knowledge_result.model_dump_json(indent=2))

        # Step 3: Mapping Agent
        self.logger.info("Step 3: Running Mapping Agent")
        mapping_agent = await MappingAgent.create()
        mapping_result : MappingAgentResult = await mapping_agent.create_mappings(str(tf_metadata_agent_output), str(knowledge_result))
        self._log_agent_response("MappingAgent", mapping_result)

        # store the results on output folder
        with open(f"{output_dir}/03_mappings.json", "w", encoding="utf-8") as f:
            f.write(mapping_result.model_dump_json(indent=2))

        exit()

        # Step 4: Converter Planning Agent (now includes mapping functionality)
        self.logger.info("Step 4: Running Converter Planning Agent (with integrated mapping)")
        planning_agent = await ConverterPlanningAgent.create()
        planning_result = await planning_agent.create_conversion_plan(str(tf_metadata_agent_output), str(knowledge_result), tf_files)
        self._log_agent_response("ConverterPlanningAgent", planning_result)
        with open(f"{output_dir}/conversion_plan.md", "w", encoding="utf-8") as f:
            f.write(str(planning_result))

        # # Ask user for approval to proceed
        # approved = await self._prompt_user_approval()
        # if not approved:
        #     self.logger.info("User declined to proceed after planning stage. Aborting further conversion steps.")
        #     return "Conversion halted after planning (user declined)."

        # create the migrated folder
        migrated_output_dir = Path(output_dir) / "migrated"
        migrated_output_dir.mkdir(parents=True, exist_ok=True)

        # Step 4: Converter Agent
        self.logger.info("Step 4: Running Converter Agent (user approved)")
        converter_agent = await ConverterAgent.create()
        converter_result = await converter_agent.run_conversion(planning_result, migrated_output_dir, tf_files)
        self._log_agent_response("ConverterAgent", converter_result)

        # Step 5: Validator Agent
        self.logger.info("Step 5: Running Validator Agent")
        validator_agent = await ValidatorAgent.create()
        validator_result = await validator_agent.validate_conversion(repo_path, str(migrated_output_dir), str(converter_result))
        self._log_agent_response("ValidatorAgent", validator_result)

        # Step 6: Report Agent
        self.logger.info("Step 6: Running Report Agent")
        report_agent = await ReportAgent.create()
        
        # Prepare all results for the report
        all_results = {
            "scanner": str(tf_metadata_agent_output),
            "knowledge": str(knowledge_result),
            "planning": str(planning_result),
            "conversion": str(converter_result),
            "validation": str(validator_result)
        }
        
        report_result = await report_agent.generate_report(all_results, output_dir)
        self._log_agent_response("ReportAgent", report_result)

        return str(report_result)
    
    def _log_agent_response(self, agent_name: str, response) -> None:
        """Log agent response in a consistent format."""
        if response and hasattr(response, 'message') and hasattr(response.message, 'content'):
            response_text = str(response.message.content)
        else:
            response_text = str(response) if response else "No response"
        self.logger.info(f"[{agent_name}] Response: {response_text}")
        print(f"[{agent_name}]: {response_text}")

    async def _prompt_user_approval(self) -> bool:
        """Prompt user to approve moving from planning to conversion. Returns True if approved."""
        try:
            # Use a thread to avoid blocking the event loop
            response = await asyncio.to_thread(input, "A conversion plan has been generated (conversion_plan.md). Proceed with conversion? [y/N]: ")
            return response.strip().lower() in ("y", "yes")
        except Exception as e:
            self.logger.warning(f"Failed to capture user approval input: {e}. Defaulting to not approved.")
            return False
    
    async def cleanup(self):
        """Clean up resources."""
        self.logger.info("Cleanup completed")


async def main():
    """Main entry point for the application."""
    import typer
    
    def run_conversion(
        repo_path: str = typer.Option(..., "--repo-path", help="Path to the Terraform repository"),
        output_dir: str = typer.Option(None, "--output-dir", help="Output directory for converted files")
    ):
        """Run the Terraform to AVM conversion."""
        async def _run():
            orchestrator = TerraformAVMOrchestrator()
            try:
                await orchestrator.initialize()
                result = await orchestrator.convert_repository(repo_path, output_dir)
                print(f"Conversion result: {result}")
            finally:
                await orchestrator.cleanup()
        
        asyncio.run(_run())
    
    app = typer.Typer()
    app.command()(run_conversion)
    app()


if __name__ == "__main__":
    # Simple test run
    async def test_run():
        orchestrator = TerraformAVMOrchestrator()
        try:
            await orchestrator.initialize()
            result = await orchestrator.convert_repository(
                repo_path="D:\\repos\\tf2avm\\tests\\fixtures\\repo_tf_basic",
                output_dir="D:\\repos\\tf2avm\\tests\\test_run\\repo_tf_basic\\output\\" + datetime.now().strftime("%Y%m%d_%H%M%S")
            )
            print(f"Test conversion result: {result}")
        finally:
            await orchestrator.cleanup()
    
    asyncio.run(test_run())