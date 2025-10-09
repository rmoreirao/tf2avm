import asyncio
from datetime import datetime
import json
from pathlib import Path
import shutil
import traceback
from typing import Dict, Any, List

from agents.converter_planning_agent_per_resource import ResourceConverterPlanningAgent
from services.avm_service import AVMService
from config.settings import get_settings, validate_environment
from config.logging import setup_logging
from agents.tf_metadata_agent import TFMetadataAgent
from agents.converter_planning_agent import ConverterPlanningAgent
from agents.converter_agent import ConverterAgent
from agents.validator_agent import ValidatorAgent
from agents.report_agent import ReportAgent
from schemas.models import AVMKnowledgeAgentResult, AVMResourceDetailsAgentResult, MappingAgentResult, TerraformMetadataAgentResult
from agents.mapping_agent import MappingAgent


class TerraformAVMOrchestrator:
    """
    Main orchestrator for the Terraform to AVM conversion using Semantic Kernel Handoff Orchestration.
    """
    
    def __init__(self):
        self.logger = setup_logging()
        self.settings = get_settings()
        self.avm_service = AVMService(cache_enabled=True) 
        
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
    
    async def _store_avm_cache(self) -> None:
        self.logger.info("Storing AVM Knowledge Agent into local cache")
        knowledge_result : AVMKnowledgeAgentResult = await self.avm_service.fetch_avm_knowledge(use_cache=True)

        for module in knowledge_result.modules:
            try:
                await self.avm_service.fetch_avm_resource_details(
                    module_name=module.name,
                    module_version=module.version,
                    use_cache=True
                )
            except Exception as e:
                self.logger.warning(f"Failed to fetch details for module {module.name} version {module.version}: {e}")
                continue



    async def _run_sequential_workflow(self, repo_path: str, output_dir: str) -> str:
        """Run the agents in sequence with an interactive approval gate after planning."""

        # await self._store_avm_cache()

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


        self.logger.info("Step 1: Running Repository Scanner Agent")
        tf_metadata_agent = await TFMetadataAgent.create()
        tf_metadata_agent_output : TerraformMetadataAgentResult = await tf_metadata_agent.scan_repository(tf_files)
        self._log_agent_response("TFMetadataAgent", tf_metadata_agent_output)

        with open(f"{output_dir}/01_tf_metadata.json", "w", encoding="utf-8") as f:
            f.write(tf_metadata_agent_output.model_dump_json(indent=2))
               
        self.logger.info("Step 2: Running AVM Knowledge Agent")
        knowledge_result : AVMKnowledgeAgentResult = await self.avm_service.fetch_avm_knowledge(use_cache=True)
        self._log_agent_response("AVMKnowledgeAgent", knowledge_result)

        with open(f"{output_dir}/02_avm_knowledge.json", "w", encoding="utf-8") as f:
            f.write(knowledge_result.model_dump_json(indent=2))

        self.logger.info("Step 3: Running Mapping Agent")
        mapping_agent = await MappingAgent.create()
        mapping_result : MappingAgentResult = await mapping_agent.create_mappings(tf_metadata_agent_output, knowledge_result)
        self._log_agent_response("MappingAgent", mapping_result)

        with open(f"{output_dir}/03_mappings.json", "w", encoding="utf-8") as f:
            f.write(mapping_result.model_dump_json(indent=2))


        self.logger.info("Step 4: Retrieving AVM Resource Details")

        # filter all mappings where target_module is not None
        valid_mappings = [m for m in mapping_result.mappings if m.target_module is not None]
        # store the module detail in dictionary: module_name -> details
        modules_details: List[AVMResourceDetailsAgentResult] = []

        for mapping in valid_mappings:
            self.logger.info(f"Fetching details for AVM module: {mapping.target_module.name}, version: {mapping.target_module.version}")

            module_detail = await self.avm_service.fetch_avm_resource_details(
                module_name=mapping.target_module.name, 
                module_version=mapping.target_module.version, 
                use_cache=True
            )
            modules_details.append(module_detail)
            # self._log_agent_response(f"AVMResourceDetailsAgent - {mapping.target_module.name} {mapping.target_module.version}", modules_details)

        with open(f"{output_dir}/04_avm_module_details.json", "w", encoding="utf-8") as f:
            f.write(json.dumps([v.model_dump() for v in modules_details], indent=2))

        
        # if there are resources without mappings, execute again the planning agent with the AVM resource details
        if len(valid_mappings) < len(mapping_result.mappings):
            self.logger.info("Some resources do not have mappings. Re-running planning with AVM resource details integrated.")

            mapping_result : MappingAgentResult = await mapping_agent.review_mappings(tf_metadata_agent_output, knowledge_result, mapping_result, modules_details)
            self._log_agent_response("MappingAgent", mapping_result)

            with open(f"{output_dir}/04_01_retry_mappings.json", "w", encoding="utf-8") as f:
                f.write(mapping_result.model_dump_json(indent=2))

        
        # filter all mappings where target_module is not None
        valid_mappings = [m for m in mapping_result.mappings if m.target_module is not None]
        # store the module detail in dictionary: module_name -> details
        modules_details: List[AVMResourceDetailsAgentResult] = []

        for mapping in valid_mappings:
            self.logger.info(f"Fetching details for AVM module: {mapping.target_module.name}, version: {mapping.target_module.version}")

            module_detail = await self.avm_service.fetch_avm_resource_details(
                module_name=mapping.target_module.name, 
                module_version=mapping.target_module.version, 
                use_cache=True
            )
            modules_details.append(module_detail)
            # self._log_agent_response(f"AVMResourceDetailsAgent - {mapping.target_module.name} {mapping.target_module.version}", modules_details)

        with open(f"{output_dir}/05_avm_module_details.json", "w", encoding="utf-8") as f:
            f.write(json.dumps([v.model_dump() for v in modules_details], indent=2))
        
        self.logger.info("Step 5: Running Converter Planning Agent Per Resource")
        resource_planning_agent = await ResourceConverterPlanningAgent.create()

        resources_planings = []
        for mapping_result in mapping_result.mappings:
            if mapping_result.target_module is None:
                resources_planings.append(f"Resource {mapping_result.source_resource.type} {mapping_result.source_resource.name} has no mapping and will be skipped.")
                continue
            
            avm_module_detail = next((m for m in modules_details if m.module.name == mapping_result.target_module.name and m.module.version == mapping_result.target_module.version), None)
            if avm_module_detail is None:
                resources_planings.append(f"Resource {mapping_result.source_resource.type} {mapping_result.source_resource.name} mapping to module {mapping_result.target_module.name} version {mapping_result.target_module.version} but details not found. It will be skipped.")
                continue

            tf_file = next(((k, v) for k, v in tf_files.items() if f'resource "{mapping_result.source_resource.type}" "{mapping_result.source_resource.name}"' in v), None)
            if tf_file is None:
                resources_planings.append(f"Resource {mapping_result.source_resource.type} {mapping_result.source_resource.name} mapping to module {mapping_result.target_module.name} version {mapping_result.target_module.version} but source file not found. It will be skipped.")
                continue

            # look up the tf_metadata_agent_output to find the resource with type and name
            tf_metadata = next((m for m in tf_metadata_agent_output.azurerm_resources if m.type == mapping_result.source_resource.type and m.name == mapping_result.source_resource.name), None)
            if tf_metadata is None:
                resources_planings.append(f"Resource {mapping_result.source_resource.type} {mapping_result.source_resource.name} mapping to module {mapping_result.target_module.name} version {mapping_result.target_module.version} but metadata not found. It will be skipped.")
                continue

            referenced_outputs = tf_metadata.referenced_outputs or []
            planning_result = await resource_planning_agent.create_conversion_plan(avm_module_detail=avm_module_detail,resource_mapping=mapping_result, tf_file=tf_file, original_tf_resource_output_paramers=referenced_outputs)
            self._log_agent_response("ResourceConverterPlanningAgent", planning_result)
            with open(f"{output_dir}/05_{mapping_result.source_resource.type}_{mapping_result.source_resource.name}_conversion_plan.md", "w", encoding="utf-8") as f:
                f.write(str(planning_result))

            resources_planings.append(str(planning_result))

        #1) apply the changes per file / per resource
        # For each file / resource:
        # Logic: 
        #   - load the current version of the file
        #   - find the resource that you change to modify
        #   - find the mapping of that resource
        #   - find the planning of that resource
        #   - replace the resource with the new AVM module
        
        #2) apply changes on variables and outputs

        # self.logger.info("Step 5: Running Converter Planning Agent (with integrated mapping)")
        # planning_agent = await ConverterPlanningAgent.create()
        # planning_result = await planning_agent.create_conversion_plan(mapping_result, modules_details, tf_files)
        # self._log_agent_response("ConverterPlanningAgent", planning_result)
        # with open(f"{output_dir}/05_conversion_plan.md", "w", encoding="utf-8") as f:
        #     f.write(str(planning_result))

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
        planning_result = "\n\n".join(resources_planings)
        converter_result = await converter_agent.run_conversion(planning_result, migrated_output_dir, tf_files)
        self._log_agent_response("ConverterAgent", converter_result)

        exit()

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
        
        try:
            self.logger.info(f"[{agent_name}] Response: {response_text}")
        except UnicodeEncodeError:
            safe = response_text.encode("utf-8", errors="replace").decode("utf-8")
            self.logger.info(f"[{agent_name}] Response: {safe}")

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