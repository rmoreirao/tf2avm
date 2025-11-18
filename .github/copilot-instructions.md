# Terraform to AVM Converter - AI Agent Guide

## Project Overview

Multi-agent system that converts Terraform configurations to Azure Verified Modules Terraform (AVM) using Semantic Kernel. The system orchestrates specialized agents through a sequential workflow, processing Terraform files and generating AVM-based equivalents with validation.

## Architecture Pattern: Sequential Agent Orchestration

**Core Principle**: Each agent is a specialist with a single responsibility. Agents communicate through strongly-typed Pydantic models, with all artifacts persisted as JSON/Markdown for transparency.

### Agent Creation Pattern
All agents follow this factory pattern:
```python
@classmethod
async def create(cls) -> 'AgentName':
    kernel = Kernel()
    execution_settings = OpenAIChatPromptExecutionSettings(response_format=ResultModel)
    chat_completion_service = AzureChatCompletion(...)
    kernel.add_service(chat_completion_service)
    
    agent = ChatCompletionAgent(
        service=chat_completion_service,
        kernel=kernel,
        name="AgentName",
        instructions="..."  # Agent-specific instructions
    )
    return cls(agent)
```

### The Sequential Workflow (main.py)

1. **TFMetadataAgent** → Scans .tf files, extracts resources/variables/outputs, identifies parent-child relationships
2. **AVMService** → Fetches AVM module catalog (cached in `avmDataCache/`)
3. **MappingAgent** → Maps azurerm_* resources to AVM modules with confidence scoring
4. **AVMService (again)** → Fetches detailed module info for mapped resources
5. **MappingAgent.review_mappings** → Re-evaluates unmapped resources with module details
6. **ResourceConverterPlanningAgent** → Plans conversion per-resource in parallel batches (batch_size=8)
7. **ConverterAgent** → Generates migrated Terraform code
8. **TerraformValidatorAgent** → Validates syntax/completeness
9. **TerraformFixPlannerAgent** → (Conditional) Plans fixes if validation fails

**Critical**: All results are persisted with numbered prefixes (01_*, 02_*, etc.) for debugging and auditability.

## Key Data Models (schemas/models.py)

- **TerraformResourceWithRelations**: Includes `child_resources`, `parent_resource`, `referenced_outputs` for dependency tracking
- **ResourceMapping**: Links source Terraform resource to target AVM module with confidence_score ("High", "Medium", "Low", "None")
- **AVMModuleDetailed**: Full module spec including inputs/outputs/requirements
- All agent results are strongly-typed Pydantic models for structured JSON serialization

## Service Layer Pattern

### AVMService (services/avm_service.py)
Wrapper around AVM agents with file-based caching:
- `fetch_avm_knowledge(use_cache=True)` → Returns full AVM catalog
- `fetch_avm_resource_details(module_name, version, use_cache=True)` → Returns module specifics
- Cache files: `avmDataCache/avm-res-<module>_<version>.json`

### TerraformService
(Not heavily used - Terraform MCP integration is mostly direct)

## Configuration & Environment

**Required Environment Variables** (`.env`):
```bash
AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-01
```

**Optional Multi-Model Support**:
- `AZURE_OPENAI_REASONING_*` for reasoning-heavy agents
- `AZURE_OPENAI_FAST_*` for simple agents

Settings are validated via `config/settings.py::validate_environment()` before any agent initialization.

## Testing Strategy

**Location**: `tests/` with agent-specific subfolders (`tf_metadata_agent/`, `main_test/`, etc.)

**Key Patterns**:
- All tests use `@pytest.mark.asyncio` (configured in `pytest.ini` with `asyncio_mode = auto`)
- Test data in `tests/main_test/001_repo_tf_basic/inputs/` for E2E scenarios
- Fixture-based setup for test Terraform repositories
- Run tests: `pytest tests/` or `pytest tests/main_test/main_test.py -v -k specific_test`

**Important**: Test outputs go to `tests_runs/` (git-ignored for local dev)

## CLI Usage Patterns (cli.py)

```bash
# Basic conversion
python cli.py convert /path/to/terraform/repo

# With custom output
python cli.py convert /path/to/repo --output-dir ./custom_output

# Test with fixtures
python cli.py test

# Validate environment setup
python cli.py validate
```

**Entry Points**:
- `cli.py`: User-facing CLI with Typer
- `main.py`: Programmatic orchestrator (use `TerraformAVMOrchestrator` class)

## Output Structure Convention

```
output/
├── original/                    # Backup of original .tf files
├── migrated/                    # Converted Terraform using AVM modules
├── 01_tf_metadata.json          # TFMetadataAgent output
├── 02_avm_knowledge.json        # AVM catalog
├── 03_mappings.json             # Initial mappings
├── 04_avm_modules_details.json  # First-pass module details
├── 04_01_mappings_after_review.json  # (Conditional) Re-evaluated mappings
├── 05_avm_modules_details_final.json
├── 06_<type>_<name>_conversion_plan.json  # Per-resource plans
├── 06_conversion_summary.md
├── 07_terraform_validation.json
└── 08_fix_plan.json             # (Conditional) Fix plan if validation fails
```

**Debugging Tip**: Always check numbered JSON artifacts in sequence to trace agent decisions.

## Critical Implementation Details

### Parallel Processing (main.py::_run_sequential_workflow)
ResourceConverterPlanningAgent processes resources in batches:
```python
batch_size = 8
for i in range(0, len(all_mappings), batch_size):
    batch = all_mappings[i:i + batch_size]
    tasks = [process_single_resource(mapping) for mapping in batch]
    batch_results = await asyncio.gather(*tasks)
```
**Why**: Reduces total planning time significantly for repos with many resources.

### Child Resource Detection
TFMetadataAgent identifies hierarchical relationships (e.g., network interface → VM, disk → VM). This is crucial for correct conversion order and dependency management.

### Output Reference Tracking
Agents track which outputs reference which resources (e.g., `output "web_app_url" { value = azurerm_linux_web_app.web.default_hostname }`). This ensures outputs are correctly updated in converted code.

## Common Pitfalls & Solutions

1. **Missing AVM modules in cache**: If `avmDataCache/` is empty or stale, delete it to force fresh fetch
2. **Validation failures**: Check `07_terraform_validation.json` → `08_fix_plan.json` for structured error analysis
3. **Agent initialization errors**: Always `await agent.create()` before use (never instantiate directly)
4. **Unicode encoding issues**: All file I/O uses `encoding="utf-8"` (Windows compatibility)
5. **Async context**: Use `asyncio.run()` in scripts, `await` in async functions. Don't mix blocking and async calls.

## Plugin Architecture (plugins/)

- **filesystem_plugin.py**: File I/O operations (not heavily used - mostly direct pathlib)
- **http_plugin.py**: Fetches AVM index from `https://azure.github.io/Azure-Verified-Modules/indexes/terraform/tf-resource-modules/`
- **terraform_plugin.py**: Terraform MCP integration (requires Docker)

## Adding New Agents

1. Create `agents/new_agent.py` following the factory pattern
2. Define result model in `schemas/models.py`
3. Add agent to workflow in `main.py::_run_sequential_workflow`
4. Persist results with next numbered prefix (e.g., `09_new_agent_result.json`)
5. Add unit tests in `tests/new_agent/`

## Dependencies & Versions

- **Semantic Kernel** ≥1.0.0 (Handoff Orchestration)
- **Python** ≥3.8
- **Azure OpenAI** (required)
- **Docker** (optional, for Terraform MCP server)

See `requirements.txt` for full list.

## Documentation References

- **FLOW.md**: Visual workflow diagrams (Mermaid) and data flow
- **IMPLEMENTATION_SUMMARY.md**: Project history and v1 vs v2 comparison
- **README.md**: User-facing setup and usage guide
- **agents/*.py**: Each agent's instructions are inline in `create()` method
