import asyncio
from datetime import datetime
from pathlib import Path
import shutil
import traceback
from typing import Dict, Any

from config.settings import get_settings, validate_environment
from config.logging import setup_logging
from agents.repo_scanner_agent import RepoScannerAgent
from agents.avm_knowledge_agent import AVMKnowledgeAgent
from agents.mapping_agent import MappingAgent
from agents.converter_planning_agent import ConverterPlanningAgent
from agents.converter_agent import ConverterAgent
from agents.validator_agent import ValidatorAgent
from agents.report_agent import ReportAgent


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
    
    async def _create_and_initialize_agent(self, agent_class):
        """Helper method to create and initialize an agent on-demand."""
        agent = agent_class()
        return await agent.initialize()
    
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

                # copy the TF files to output dir / original
        self.logger.info(f"Copying original TF files to output directory {output_dir}/original")
        original_output_dir = Path(output_dir) / "original"
        original_output_dir.mkdir(parents=True, exist_ok=True)
        for tf_file in Path(repo_path).rglob("*.tf"):
            shutil.copy(tf_file, original_output_dir / tf_file.name)

        # Step 1: Repository Scanner Agent
        self.logger.info("Step 1: Running Repository Scanner Agent")
        scanner_agent = await self._create_and_initialize_agent(RepoScannerAgent)
        scanner_result = await scanner_agent.get_response(
            f"Scan and analyze Terraform repository at '{repo_path}'."
        )
        self._log_agent_response("RepoScannerAgent", scanner_result)

        # store the results on output folder
        with open(f"{output_dir}/repo_scan.md", "w", encoding="utf-8") as f:
            f.write(str(scanner_result))
               
        # Step 2: AVM Knowledge Agent
        self.logger.info("Step 2: Running AVM Knowledge Agent")
        knowledge_agent = await self._create_and_initialize_agent(AVMKnowledgeAgent)
        knowledge_result = await knowledge_agent.get_response(
            "Gather AVM module knowledge based on repository scan results."
        )
        self._log_agent_response("AVMKnowledgeAgent", knowledge_result)

        # store the results on output folder
        with open(f"{output_dir}/avm_knowledge.json", "w", encoding="utf-8") as f:
            f.write(str(knowledge_result))

        # Step 3: Mapping Agent
        self.logger.info("Step 3: Running Mapping Agent")
        mapping_agent = await self._create_and_initialize_agent(MappingAgent)
        mapping_result = await mapping_agent.get_response(
            f"Map Terraform resources to AVM modules. Repository: {str(scanner_result)} AVM Knowledge: {str(knowledge_result)}"
        )
        self._log_agent_response("MappingAgent", mapping_result)

        # store the results on output folder
        with open(f"{output_dir}/mapping.md", "w", encoding="utf-8") as f:
            f.write(str(mapping_result))

        # Step 4: Converter Planning Agent
        self.logger.info("Step 4: Running Converter Planning Agent")
        planning_agent = await self._create_and_initialize_agent(ConverterPlanningAgent)
        planning_prompt = (
            "Create a detailed Terraform to AVM conversion plan based on repository scan and mapping results. "
            f"Repository Scan: {str(scanner_result)} Mapping: {str(mapping_result)}"
        )
        planning_result = await planning_agent.get_response(planning_prompt)
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

        # Step 5: Converter Agent
        self.logger.info("Step 5: Running Converter Agent (user approved)")
        converter_agent = ConverterAgent()
        await converter_agent.initialize()
        converter_result = await converter_agent.run_conversion(planning_result, migrated_output_dir, repo_path)
        self._log_agent_response("ConverterAgent", converter_result)

        exit()

        # Step 6: Validator Agent
        self.logger.info("Step 6: Running Validator Agent")
        validator_agent = await self._create_and_initialize_agent(ValidatorAgent)
        validator_result = await validator_agent.get_response(
            f"Validate converted files in '{output_dir}'. Conversion results: {str(converter_result)}"
        )
        self._log_agent_response("ValidatorAgent", validator_result)

        # Step 7: Report Agent
        self.logger.info("Step 7: Running Report Agent")
        report_agent = await self._create_and_initialize_agent(ReportAgent)
        report_result = await report_agent.get_response(
            f"Generate final conversion report in '{output_dir}'. All results: Scanner: {str(scanner_result)}, Mapping: {str(mapping_result)}, Conversion: {str(converter_result)}, Validation: {str(validator_result)}"
        )
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