# Terraform to AVM Converter - Test Suite

This directory contains the test suite for the Terraform to Azure Verified Modules (AVM) converter project.

## Test Structure

The test suite is organized into specialized test folders:

- **`tf_metadata_agent/`** - Tests for the Terraform metadata extraction agent
- **`converter_planning_agent_per_resource/`** - Tests for the resource conversion planning agent
- **`main_test/`** - End-to-end orchestrator tests for the complete conversion workflow
- **`e2e/`** - Additional end-to-end integration tests

Each test folder contains:
- Test case directories (e.g., `001_repo_tf_basic/`, `case_001_basic_resources/`)
- `inputs/` subdirectories with test Terraform files
- `expected/` subdirectories with expected JSON outputs (where applicable)
- Test files (e.g., `*_test.py`)

## Prerequisites

1. **Python Environment**: Python 3.8 or higher
2. **Dependencies**: Install all required packages:
   ```powershell
   pip install -r requirements.txt
   ```

3. **Environment Variables**: Configure Azure OpenAI credentials in `.env` file:
   ```bash
   AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment
   AZURE_OPENAI_API_KEY=your-key
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   AZURE_OPENAI_API_VERSION=2024-02-01
   ```

4. **pytest**: The test runner (included in requirements.txt)

## Running Tests

**Important**: All pytest commands must be run from the **project root directory** (`d:\repos\tf2avm`), not from the `tests/` folder, to ensure proper module imports.

### Run All Tests

Execute all tests in the test suite:

```powershell
# From project root directory
pytest tests/
```

Or set PYTHONPATH if running from a different location:

```powershell
$env:PYTHONPATH = "d:\repos\tf2avm"
pytest tests/
```

### Run Tests with Verbose Output

Get detailed test execution information:

```powershell
pytest tests/ -v
```

### Run Tests for a Specific Agent

Run tests for a specific agent/component:

```powershell
# TF Metadata Agent tests
pytest tests/tf_metadata_agent/

# Converter Planning Agent tests
pytest tests/converter_planning_agent_per_resource/

# End-to-end orchestrator tests
pytest tests/main_test/
```

### Run a Specific Test File

Execute a single test file:

```powershell
pytest tests/main_test/main_test.py -v
```

### Run a Specific Test Case

Execute a specific test function using the `-k` flag:

```powershell
# Run only the basic resources test
pytest tests/main_test/main_test.py -v -k test_case_001_repo_tf_basic

# Run only TF metadata agent basic test
pytest tests/tf_metadata_agent/tf_metadata_agent_test.py -v -k test_case_001_basic_resources
```

### Run Tests with Live Log Output

See real-time log output during test execution (enabled by default in `pytest.ini`):

```powershell
pytest tests/ -v --log-cli-level=INFO
```

### Run Tests and Stop on First Failure

Useful for debugging:

```powershell
pytest tests/ -x
```

### Run Tests with Coverage

Generate code coverage reports:

```powershell
# Install coverage support
pip install pytest-cov

# Run with coverage
pytest tests/ --cov=agents --cov=services --cov=main

# Generate HTML coverage report
pytest tests/ --cov=agents --cov=services --cov=main --cov-report=html
```

## Test Output Locations

Test runs generate output in the `tests_runs/` directory (git-ignored):

```
tests_runs/
├── tf_metadata_agent/
│   └── test_case_001_basic_resources_YYYYMMDD_HHMMSS/
│       └── 01_tf_metadata.json
├── main_test/
│   └── test_case_001_repo_tf_basic_YYYYMMDD_HHMMSS/
│       ├── original/          # Backup of original .tf files
│       ├── migrated/          # Converted Terraform using AVM modules
│       ├── 01_tf_metadata.json
│       ├── 02_avm_knowledge.json
│       ├── 03_mappings.json
│       └── ...
```

## Test Configuration

The test suite is configured via `pytest.ini` in the project root:

- **Async mode**: `auto` - Automatically handles async test functions
- **Logging**: Enabled with INFO level by default
- **Log format**: Timestamped with log level

## Common Test Patterns

### Async Tests

All agent tests are asynchronous and use the `@pytest.mark.asyncio` decorator:

```python
@pytest.mark.asyncio
async def test_something():
    agent = await SomeAgent.create()
    result = await agent.do_something()
    assert result is not None
```

### Fixture-based Test Data

Tests use pytest fixtures to load test data:

```python
@pytest.fixture
def test_data_dir(self):
    """Return the test data directory"""
    return Path(__file__).parent

def load_tf_files(self, case_dir: Path) -> dict:
    """Load all .tf files from a case inputs directory"""
    inputs_dir = case_dir / "inputs"
    tf_files = {}
    for tf_file in inputs_dir.glob("*.tf"):
        tf_files[tf_file.name] = tf_file.read_text(encoding="utf-8")
    return tf_files
```

## Troubleshooting

### Test Failures

1. **Environment not configured**: Ensure `.env` file exists with valid Azure OpenAI credentials
2. **Missing dependencies**: Run `pip install -r requirements.txt`
3. **Async runtime errors**: Verify `pytest-asyncio` is installed

### Debugging Tests

Run tests with extra verbosity and show local variables on failure:

```powershell
pytest tests/ -vv -l
```

Use pytest's built-in debugger:

```powershell
pytest tests/ --pdb
```

### Test Output Cleanup

Test outputs are stored in `tests_runs/` and are git-ignored. To clean up:

```powershell
Remove-Item -Recurse -Force tests_runs/
```

## Writing New Tests

When adding new tests:

1. Create a test case directory under the appropriate agent folder
2. Add `inputs/` subdirectory with test Terraform files
3. (Optional) Add `expected/` subdirectory with expected outputs
4. Create a test file following the naming pattern `*_test.py`
5. Use fixtures to load test data
6. Use `@pytest.mark.asyncio` for async tests
7. Save outputs to `tests_runs/` for debugging

Example test structure:

```
tests/
└── my_agent/
    ├── case_001_scenario/
    │   ├── inputs/
    │   │   └── main.tf
    │   └── expected/
    │       └── output.json
    └── my_agent_test.py
```

## CI/CD Integration

For continuous integration, use:

```powershell
# Run all tests with JUnit XML output
pytest tests/ --junitxml=test-results.xml

# Run with coverage and fail if coverage < 80%
pytest tests/ --cov=agents --cov=services --cov-report=xml --cov-fail-under=80
```

## Additional Resources

- **Project Documentation**: See `README.md` in project root
- **Architecture**: See `FLOW.md` for workflow diagrams
- **Implementation Details**: See `IMPLEMENTATION_SUMMARY.md`
- **Agent Instructions**: Check `.github/copilot-instructions.md`
