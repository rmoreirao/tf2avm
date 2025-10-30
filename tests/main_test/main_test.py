import pytest
import json
import shutil
from pathlib import Path
from main import TerraformAVMOrchestrator


class TestTerraformAVMOrchestrator:
    """End-to-end tests for Terraform AVM Orchestrator"""
    
    @pytest.fixture
    def test_data_dir(self):
        """Return the test data directory"""
        return Path(__file__).parent
    
    @pytest.fixture
    def output_dir(self, request):
        """Create and return output directory based on test name"""
        # Get the test name (e.g., test_case_001_repo_tf_basic)
        test_name = request.node.name
        
        # Create output directory: tests\test_run\{test_name}\output
        base_output = Path(__file__).parent.parent.parent / "tests_runs" / "main_test" / test_name / "output"

        # Clean the output directory if it exists
        if base_output.exists():
            shutil.rmtree(base_output)

        base_output.mkdir(parents=True, exist_ok=True)
        return base_output
    
    def load_tf_files_from_inputs(self, case_dir: Path) -> Path:
        """Return the path to the inputs directory containing .tf files"""
        inputs_dir = case_dir / "inputs"
        if not inputs_dir.exists():
            raise FileNotFoundError(f"Inputs directory not found: {inputs_dir}")
        return inputs_dir
    
    def load_expected_output(self, case_dir: Path, filename: str) -> dict:
        """Load expected JSON output from a case"""
        expected_file = case_dir / "expected" / filename
        with open(expected_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def verify_output_files(self, output_dir: Path, expected_files: list):
        """Verify that expected output files were created"""
        missing_files = []
        for filename in expected_files:
            if not (output_dir / filename).exists():
                missing_files.append(filename)
        
        if missing_files:
            raise AssertionError(f"Expected output files not found: {missing_files}")
    
    @pytest.mark.asyncio
    async def test_case_001_repo_tf_basic(self, test_data_dir, output_dir):
        """Test basic Terraform repository conversion"""
        case_dir = test_data_dir / "001_repo_tf_basic"
        
        # Get input directory path
        inputs_dir = self.load_tf_files_from_inputs(case_dir)
        
        # Execute orchestrator
        orchestrator = TerraformAVMOrchestrator()
        await orchestrator.initialize()
        
        result = await orchestrator.convert_repository(
            repo_path=str(inputs_dir),
            output_dir=str(output_dir)
        )
        
        # Verify result structure
        assert result is not None
        assert result["status"] == "completed"
        assert result["repo_path"] == str(inputs_dir)
        assert result["output_directory"] == str(output_dir)
        
        # Verify migrated folder was created
        migrated_dir = output_dir / "migrated"
        assert migrated_dir.exists(), "Migrated directory should be created"
        
        # Verify original folder was created with TF files
        original_dir = output_dir / "original"
        assert original_dir.exists(), "Original directory should be created"
        
        tf_files_copied = list(original_dir.glob("*.tf"))
        assert len(tf_files_copied) > 0, "Original TF files should be copied"
        
        print(f"Test completed successfully. Output saved to: {output_dir}")
    
    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self):
        """Test orchestrator can be initialized successfully"""
        orchestrator = TerraformAVMOrchestrator()
        await orchestrator.initialize()
        
        assert orchestrator is not None
        assert orchestrator.logger is not None
        assert orchestrator.settings is not None
        assert orchestrator.avm_service is not None
    
    @pytest.mark.asyncio
    async def test_invalid_repo_path(self, output_dir):
        """Test handling of invalid repository path"""
        orchestrator = TerraformAVMOrchestrator()
        await orchestrator.initialize()
        
        invalid_path = "D:\\nonexistent\\path"
        
        with pytest.raises(FileNotFoundError) as exc_info:
            await orchestrator.convert_repository(
                repo_path=invalid_path,
                output_dir=str(output_dir)
            )
        
        assert "does not exist or is not a directory" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_empty_repository(self, output_dir, tmp_path):
        """Test conversion of an empty repository (no .tf files)"""
        # Create an empty directory
        empty_repo = tmp_path / "empty_repo"
        empty_repo.mkdir()
        
        orchestrator = TerraformAVMOrchestrator()
        await orchestrator.initialize()
        
        # This should complete but may have minimal output
        result = await orchestrator.convert_repository(
            repo_path=str(empty_repo),
            output_dir=str(output_dir)
        )
        
        assert result is not None
        assert result["status"] == "completed"


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
async def test_initialization_only():
    """Run only initialization tests"""
    pytest.main([__file__, "-v", "-k", "initialization"])


if __name__ == "__main__":
    # Run all tests when executed directly
    pytest.main([__file__, "-v"])
