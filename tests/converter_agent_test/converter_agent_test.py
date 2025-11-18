import shutil
import pytest
import json
from pathlib import Path
from agents.converter_agent import ConverterAgent
from schemas.models import ResourceConverterPlanningAgentResult
from datetime import datetime


class TestConverterAgent:
    """End-to-end tests for Converter Agent"""

    @pytest.fixture
    def test_data_dir_001(self):
        """Return the test data directory for converter agent tests."""
        return Path(__file__).parent / "001_basic_resources" / "inputs"

    @pytest.fixture
    def output_dir(self, request):
        """Create and return output directory based on test name"""
        # Get the test name
        test_name = request.node.name
        
        # Create output directory: tests_runs/converter_agent_test/{test_name}/{timestamp}/output
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        base_output = (
            Path(__file__).parent.parent.parent
            / "tests_runs"
            / "converter_agent_test"
            / test_name
            / timestamp
            / "output"
        )

        # Clean the output directory if it exists
        if base_output.exists():
            shutil.rmtree(base_output)

        base_output.mkdir(parents=True, exist_ok=True)
        return base_output

    @pytest.fixture
    def tf_files(self, test_data_dir_001):
        """Load all .tf files from the test data directory."""
        tf_dir = test_data_dir_001 / "tf_files"
        files = {}
        for tf_file in tf_dir.glob("*.tf"):
            files[tf_file.name] = tf_file.read_text(encoding="utf-8")
        return files

    @pytest.fixture
    def conversion_plans(self, test_data_dir_001):
        """Load all conversion plan JSON files."""
        plans_dir = test_data_dir_001 / "conversation_plans"
        plans = []
        for plan_file in plans_dir.glob("*.json"):
            with open(plan_file, "r", encoding="utf-8") as f:
                plan_data = json.load(f)
                plans.append(ResourceConverterPlanningAgentResult.model_validate(plan_data))
        return plans

    def save_output(self, output_dir: Path, filename: str, content: str):
        """Save output to file"""
        output_file = output_dir / filename
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Output saved to: {output_file}")

    @pytest.mark.asyncio
    async def test_conversion_001_basic_resources(self, tf_files, conversion_plans, output_dir):
        """Test ConverterAgent with basic resources conversion."""
        agent = await ConverterAgent.create()

        # Create migrated directory within output
        migrated_dir = output_dir / "migrated"
        migrated_dir.mkdir(parents=True, exist_ok=True)

        # Run the conversion
        result = await agent.run_conversion(
            conversion_plans=conversion_plans,
            output_dir=str(migrated_dir),
            tf_files=tf_files,
        )

        # Save the conversion summary
        self.save_output(output_dir, "conversion_summary.md", result)

        # Assertions
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

        # Verify that migrated files were created
        migrated_files = list(migrated_dir.glob("*.tf"))
        assert len(migrated_files) > 0, "No .tf files were created in the migrated directory"

        # Verify key files exist
        expected_files = ["main.tf", "variables.tf", "outputs.tf"]
        for expected_file in expected_files:
            assert (
                migrated_dir / expected_file
            ).exists(), f"Expected file {expected_file} was not created"

        print(f"Conversion completed. {len(migrated_files)} files generated.")
        print(f"Summary:\n{result}")

    @pytest.mark.asyncio
    async def test_agent_creation(self):
        """Test agent creation."""
        agent = await ConverterAgent.create()
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
