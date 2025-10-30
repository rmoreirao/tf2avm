import pytest
import json
import os
import shutil
from pathlib import Path
from agents.tf_metadata_agent import TFMetadataAgent
from schemas.models import TerraformMetadataAgentResult


class TestTFMetadataAgent:
    """End-to-end tests for TF Metadata Agent"""
    
    @pytest.fixture
    def test_data_dir(self):
        """Return the test data directory"""
        return Path(__file__).parent
    
    @pytest.fixture
    def output_dir(self, request):
        """Create and return output directory based on test name"""
        # Get the test name (e.g., test_case_001_basic_resources)
        test_name = request.node.name

        
        # Create output directory: tests\test_run\{test_name}\output
        base_output = Path(__file__).parent.parent / "test_run" / test_name / "output"

        # Clean the output directory if it exists
        if base_output.exists():
            shutil.rmtree(base_output)

        base_output.mkdir(parents=True, exist_ok=True)
        return base_output
    
    def load_tf_files(self, case_dir: Path) -> dict:
        """Load all .tf files from a case inputs directory"""
        inputs_dir = case_dir / "inputs"
        tf_files = {}
        
        for tf_file in inputs_dir.glob("*.tf"):
            relative_path = tf_file.name
            with open(tf_file, 'r', encoding='utf-8') as f:
                tf_files[relative_path] = f.read()
        
        return tf_files
    
    def load_expected_output(self, case_dir: Path, filename: str) -> dict:
        """Load expected JSON output from a case"""
        expected_file = case_dir / "expected" / filename
        with open(expected_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_output(self, output_dir: Path, filename: str, content: str):
        """Save output to file"""
        output_file = output_dir / filename
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Output saved to: {output_file}")
    
    @pytest.mark.asyncio
    async def test_case_001_basic_resources(self, test_data_dir, output_dir):
        """Test basic resources scenario"""
        case_dir = test_data_dir / "case_001_basic_resources"
        
        # Load input files
        tf_files = self.load_tf_files(case_dir)
        
        # Execute agent
        tf_metadata_agent = await TFMetadataAgent.create()
        tf_metadata_agent_output: TerraformMetadataAgentResult = await tf_metadata_agent.scan_repository(tf_files)
        
        # Save output
        output_json = tf_metadata_agent_output.model_dump_json(indent=2)
        self.save_output(output_dir, "01_tf_metadata.json", output_json)
        
        # Load expected output
        expected = self.load_expected_output(case_dir, "01_tf_metadata.json")
        actual = json.loads(output_json)
        
        # Assertions
        assert actual is not None
        # assert "resources" in actual or "scan_result" in actual
        # Add more specific assertions based on your expected structure
    
    @pytest.mark.asyncio
    async def test_agent_creation(self):
        """Test agent can be created successfully"""
        agent = await TFMetadataAgent.create()
        assert agent is not None
        assert agent.agent is not None
    
    @pytest.mark.asyncio
    async def test_scan_empty_repository(self, output_dir):
        """Test scanning an empty repository"""
        tf_files = {}
        
        agent = await TFMetadataAgent.create()
        result = await agent.scan_repository(tf_files)
        
        assert result is not None
        output_json = result.model_dump_json(indent=2)
        self.save_output(output_dir, "empty_repo.json", output_json)
    

# Convenience functions to run specific test subsets
@pytest.mark.asyncio
async def test_all_cases():
    """Run all test cases"""
    pytest.main([__file__, "-v"])


@pytest.mark.asyncio  
async def test_basic_only():
    """Run only basic test cases"""
    pytest.main([__file__, "-v", "-k", "basic"])


@pytest.mark.asyncio
async def test_agent_creation_only():
    """Run only agent creation tests"""
    pytest.main([__file__, "-v", "-k", "creation"])


if __name__ == "__main__":
    # Run all tests when executed directly
    pytest.main([__file__, "-v"])