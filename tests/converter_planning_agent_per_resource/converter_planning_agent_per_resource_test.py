import shutil
from typing import List
import pytest
import json
from pathlib import Path
from agents.converter_planning_agent_per_resource import ResourceConverterPlanningAgent
from schemas.models import (
    ResourceMapping,
    AVMModuleDetailed,
    TerraformOutputreference,
    ResourceConverterPlanningAgentResult,
)

class TestResourceConverterPlanningAgent:
    """End-to-end tests for Resource Converter Planning Agent"""

    @pytest.fixture
    def test_data_dir_001(self):
        """Return the test data directory for converter planning agent tests."""
        return Path(__file__).parent / "001_basic_resources" / "inputs"
    
    @pytest.fixture
    def monitoring_test_data_dir_002(self):
        """Return the test data directory for monitoring resources test 002."""
        return Path(__file__).parent / "002_monitoring_mapping" / "inputs"

    @pytest.fixture
    def output_dir(self, request):
        """Create and return output directory based on test name"""
        # Get the test name (e.g., test_case_001_repo_tf_basic)
        test_name = request.node.name
        
        # Create output directory: tests\test_run\{test_name}\output
        base_output = Path(__file__).parent.parent.parent / "tests_runs" / "converter_planning_test" / test_name / "output"

        # Clean the output directory if it exists
        if base_output.exists():
            shutil.rmtree(base_output)

        base_output.mkdir(parents=True, exist_ok=True)
        return base_output

    @pytest.fixture
    def tf_files(self, test_data_dir_001):
        """Load all .tf files from the test data directory."""
        tf_dir = test_data_dir_001 / "tf"
        files = {}
        for tf_file in tf_dir.glob("*.tf"):
            files[tf_file.name] = tf_file.read_text(encoding="utf-8")
        return files

    @pytest.fixture
    def avm_knowledge(self, test_data_dir_001):
        """Load AVM knowledge JSON."""
        with open(test_data_dir_001 / "avm_knowledge.json", "r", encoding="utf-8") as f:
            return json.load(f)

    @pytest.fixture
    def avm_modules_details(self, test_data_dir_001):
        """Load AVM modules details JSON."""
        with open(test_data_dir_001 / "avm_modules_details_final.json", "r", encoding="utf-8") as f:
            return json.load(f)

    @pytest.fixture
    def mappings(self, test_data_dir_001):
        """Load resource mappings JSON."""
        with open(test_data_dir_001 / "mappings.json", "r", encoding="utf-8") as f:
            return json.load(f)

    @pytest.fixture
    def tf_metadata(self, test_data_dir_001):
        """Load TF metadata JSON."""
        with open(test_data_dir_001 / "tf_metadata.json", "r", encoding="utf-8") as f:
            return json.load(f)
        
    def save_output(self, output_dir: Path, filename: str, content: str):
        """Save output to file"""
        output_file = output_dir / filename
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Output saved to: {output_file}")

    @pytest.mark.asyncio
    async def test_create_conversion_plan_001(self, tf_files, mappings, avm_modules_details, tf_metadata):
        """Test ResourceConverterPlanningAgent conversion plan for each mapping."""
        agent = await ResourceConverterPlanningAgent.create()

        # Prepare test data for one resource mapping
        for mapping_json in mappings["mappings"]:
            resource_mapping = ResourceMapping.model_validate(mapping_json)
            # Find AVM module detail for the mapping
            avm_module_detail = None
            if resource_mapping.target_module:
                for module_json in avm_modules_details:
                    module = AVMModuleDetailed.model_validate(module_json)
                    if (
                        module.module.name == resource_mapping.target_module["name"]
                        and module.module.version == resource_mapping.target_module["version"]
                    ):
                        avm_module_detail = module
                        break

            # Find the tf_file for the mapping
            tf_file_name = resource_mapping.source_file
            tf_file = (tf_file_name, tf_files.get(tf_file_name, ""))

            # Find referenced outputs for the resource
            referenced_outputs = []
            for res in tf_metadata.get("azurerm_resources", []):
                if (
                    res["type"] == resource_mapping.source_resource["type"]
                    and res["name"] == resource_mapping.source_resource["name"]
                ):
                    referenced_outputs = [
                        TerraformOutputreference.model_validate(o)
                        for o in res.get("referenced_outputs", [])
                    ]
                    break

            # Run the agent
            result: ResourceConverterPlanningAgentResult = await agent.create_conversion_plan(
                resource_mapping=resource_mapping,
                avm_module_detail=avm_module_detail,
                tf_file=tf_file,
                original_tf_resource_output_paramers=referenced_outputs,
            )

            # Save or assert result
            assert isinstance(result, ResourceConverterPlanningAgentResult)
            assert result.planning_summary is not None
            assert result.plan is not None
            print(result.model_dump_json(indent=2))

    

    @pytest.mark.asyncio
    async def test_conversion_plan_monitoring_resources_002(self, monitoring_test_data_dir_002, output_dir):
        """Test ResourceConverterPlanningAgent for monitoring diagnostic setting mapping."""
        agent = await ResourceConverterPlanningAgent.create()

        # Load mapping
        mapping_path = monitoring_test_data_dir_002 / "mapping_azurerm_monitor_diagnostic_setting_web_app.json"
        with open(mapping_path, "r", encoding="utf-8") as f:
            mapping_json = json.load(f)
        resource_mapping = ResourceMapping.model_validate(mapping_json)

        # Load AVM module detail
        avm_module_detail_path = monitoring_test_data_dir_002 / "avm_module_detail_avm-res-web-site.json"
        with open(avm_module_detail_path, "r", encoding="utf-8") as f:
            avm_module_detail_json = json.load(f)
        avm_module_detail = AVMModuleDetailed.model_validate(avm_module_detail_json)

        # Load TF file content
        tf_file_path = monitoring_test_data_dir_002 / "monitoring.tf"
        tf_file = (tf_file_path.name, tf_file_path.read_text(encoding="utf-8"))

        # No referenced outputs for this test
        output: List[TerraformOutputreference] = []

        # Run the agent
        result: ResourceConverterPlanningAgentResult = await agent.create_conversion_plan(
            resource_mapping=resource_mapping,
            avm_module_detail=avm_module_detail,
            tf_file=tf_file,
            original_tf_resource_output_paramers=output,
        )

        result_json = result.model_dump_json(indent=2)
        self.save_output(output_dir, "conversion_plan.json", result_json)

        # Assertions
        assert isinstance(result, ResourceConverterPlanningAgentResult)
        assert result.planning_summary is not None

    @pytest.mark.asyncio
    async def test_agent_creation(self):
        """Test agent creation."""
        agent = await ResourceConverterPlanningAgent.create()
        assert agent is not None
        assert agent.agent is not None


# Convenience functions to run specific test subsets
@pytest.mark.asyncio
async def test_all_cases():
    """Run all test cases"""
    pytest.main([__file__, "-v"])

if __name__ == "__main__":
    # Run all tests when executed directly
    pytest.main([__file__, "-v"])