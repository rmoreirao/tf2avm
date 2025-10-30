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

@pytest.fixture
def test_data_dir():
    """Return the test data directory for converter planning agent tests."""
    return Path(__file__).parent / "001_basic_resources" / "inputs"

@pytest.fixture
def tf_files(test_data_dir):
    """Load all .tf files from the test data directory."""
    tf_dir = test_data_dir / "tf"
    files = {}
    for tf_file in tf_dir.glob("*.tf"):
        files[tf_file.name] = tf_file.read_text(encoding="utf-8")
    return files

@pytest.fixture
def avm_knowledge(test_data_dir):
    """Load AVM knowledge JSON."""
    with open(test_data_dir / "avm_knowledge.json", "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture
def avm_modules_details(test_data_dir):
    """Load AVM modules details JSON."""
    with open(test_data_dir / "avm_modules_details_final.json", "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture
def mappings(test_data_dir):
    """Load resource mappings JSON."""
    with open(test_data_dir / "mappings.json", "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture
def tf_metadata(test_data_dir):
    """Load TF metadata JSON."""
    with open(test_data_dir / "tf_metadata.json", "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.mark.asyncio
async def test_create_conversion_plan(tf_files, mappings, avm_modules_details, tf_metadata):
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
        assert result.resource is not None
        assert result.plan is not None
        print(result.model_dump_json(indent=2))

@pytest.mark.asyncio
async def test_agent_creation():
    """Test agent creation."""
    agent = await ResourceConverterPlanningAgent.create()
    assert agent is not None
    assert agent.agent is not None