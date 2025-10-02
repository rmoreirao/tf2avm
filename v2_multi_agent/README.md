# Terraform to Azure Verified Modules (AVM) Converter v2

This is a multi-agent system built with Semantic Kernel's Handoff Orchestration for converting Terraform configurations to use Azure Verified Modules (AVM).

## Overview

The v2 multi-agent system breaks down the conversion process into specialized agents that work together through a handoff orchestration pattern. Each agent has a specific responsibility and can transfer control to appropriate specialists based on the workflow requirements.

## Architecture

### Agents

1. **Triage Agent** - Entry point coordinator and workflow orchestrator
   - Validates inputs and environment
   - Determines conversion strategy
   - Routes to appropriate specialist agents

2. **Repository Scanner Agent** - Terraform repository analysis specialist
   - Parses all Terraform files (.tf)
   - Extracts resources, variables, outputs, locals
   - Identifies azurerm_* resources for conversion

3. **AVM Knowledge Agent** - Azure Verified Modules expert
   - Fetches AVM module index from official sources
   - Maintains AVM module mappings and documentation
   - Provides module requirements and compatibility information

4. **Mapping Agent** - Resource mapping specialist
   - Matches azurerm_* resources to AVM modules
   - Determines conversion confidence levels
   - Plans variable and output mappings

5. **Converter Agent** - Code transformation specialist
   - Transforms azurerm_* resources to AVM module calls
   - Updates variables.tf and outputs.tf
   - Preserves code structure and comments

6. **Validator Agent** - Quality assurance specialist
   - Validates converted Terraform syntax
   - Checks for missing required inputs
   - Identifies potential breaking changes

7. **Report Agent** - Documentation and reporting specialist
   - Generates comprehensive conversion reports
   - Documents successful mappings and issues
   - Provides next steps and recommendations

### Handoff Orchestration Flow

```
Triage Agent
    ↓
Repository Scanner Agent
    ↓
AVM Knowledge Agent
    ↓
Mapping Agent
    ↓
Converter Agent
    ↓
Validator Agent
    ↓
Report Agent
```

Any agent can hand off to the Report Agent in case of critical errors.

## Prerequisites

1. **Python 3.8+**
2. **Azure OpenAI Service** with a deployed model
3. **Docker** (for Terraform MCP server)
4. **Environment Variables**:
   ```bash
   AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment-name
   AZURE_OPENAI_API_KEY=your-api-key
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   AZURE_OPENAI_API_VERSION=2024-02-01
   ```

## Installation

1. **Clone the repository** (if not already done):
   ```bash
   git clone <repository-url>
   cd tf2avm/v2_multi_agent
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   Create a `.env` file in the v2_multi_agent directory:
   ```env
   AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment-name
   AZURE_OPENAI_API_KEY=your-api-key
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   AZURE_OPENAI_API_VERSION=2024-02-01
   ```

## Usage

### Command Line Interface

```bash
python main.py --repo-path /path/to/terraform/repo --output-dir /path/to/output
```

### Programmatic Usage

```python
from main import TerraformAVMOrchestrator
import asyncio

async def convert_repo():
    orchestrator = TerraformAVMOrchestrator()
    try:
        await orchestrator.initialize()
        result = await orchestrator.convert_repository(
            repo_path="/path/to/terraform/repo",
            output_dir="/path/to/output"
        )
        print(f"Conversion result: {result}")
    finally:
        await orchestrator.cleanup()

asyncio.run(convert_repo())
```

### Test Run

To run a test conversion with the fixture repository:

```bash
python main.py
```

This will use the default test repository at `tests/fixtures/repo_tf_basic`.

## Output Structure

The conversion process creates the following output structure:

```
output/
└── {timestamp}/
    ├── original/          # Original Terraform files (backup)
    ├── migrated/          # Converted files using AVM modules
    │   ├── main.tf
    │   ├── variables.tf
    │   ├── outputs.tf
    │   └── ...
    ├── conversion_report.md    # Detailed conversion report
    ├── avm-mapping.json       # Machine-readable mapping data
    └── README.md              # Getting started guide
```

## Key Features

### Handoff Orchestration Benefits
- **Modularity**: Each agent has focused responsibility
- **Reusability**: Agents can be reused in different workflows
- **Extensibility**: Easy to add new agents or modify existing ones
- **Error Recovery**: Failed agents can handoff back for alternative approaches
- **Human-in-the-Loop**: Natural integration points for human oversight

### Conversion Capabilities
- **Intelligent Mapping**: Matches azurerm_* resources to appropriate AVM modules
- **Confidence Scoring**: Provides confidence levels for each conversion
- **Preserves Structure**: Maintains original code organization and comments
- **Variable Management**: Automatically updates variables and outputs
- **Validation**: Comprehensive syntax and compatibility validation
- **Detailed Reporting**: Clear documentation of changes and issues

## Configuration

### Settings
Modify `config/settings.py` to adjust:
- Azure OpenAI service configuration
- Default paths and directories
- Agent behavior parameters
- Timeout and iteration limits

### Logging
Logs are written to:
- Console output (for real-time monitoring)
- `logs/tf2avm_v2.log` (for detailed analysis)

Adjust log levels in `config/logging.py`.

## Extending the System

### Adding New Agents
1. Create a new agent class in `agents/`
2. Follow the existing agent pattern with `initialize()` method
3. Add appropriate plugins and instructions
4. Update handoff relationships in `main.py`

### Custom Plugins
1. Create plugin classes in `plugins/`
2. Use `@kernel_function` decorators for available functions
3. Add plugins to relevant agents during initialization

### Custom Validation Rules
Extend the Validator Agent with additional validation logic for:
- Organization-specific naming conventions
- Security requirements
- Compliance checks

## Testing

Run the test suite:

```bash
pytest tests/
```

For development, run specific test categories:

```bash
# Test individual agents
pytest tests/test_agents.py::TestAgents -v

# Test orchestration
pytest tests/test_agents.py::TestOrchestrator -v

# Integration tests
pytest tests/test_agents.py::TestIntegration -v
```

## Troubleshooting

### Common Issues

1. **Azure OpenAI Authentication Errors**
   - Verify environment variables are set correctly
   - Check Azure OpenAI service availability and quotas

2. **Docker Terraform MCP Issues**
   - Ensure Docker is running
   - Verify Docker can pull `hashicorp/terraform-mcp-server`

3. **Agent Initialization Failures**
   - Check logs in `logs/tf2avm_v2.log`
   - Verify all dependencies are installed

4. **Conversion Errors**
   - Review the generated conversion report
   - Check validation results for specific issues

### Debug Mode

Enable debug logging by setting the log level to DEBUG in `config/logging.py`:

```python
def setup_logging(log_level: str = "DEBUG"):
```

## Comparison with v1

| Feature | v1 (LangGraph) | v2 (Semantic Kernel Handoff) |
|---------|----------------|-------------------------------|
| Architecture | State-based workflow | Agent handoff orchestration |
| Human Interaction | Limited | Built-in human-in-the-loop |
| Error Handling | State transitions | Agent handoffs |
| Extensibility | Workflow modification | Agent addition |
| Debugging | State inspection | Agent conversation logs |
| Scalability | Linear pipeline | Dynamic routing |

## Contributing

1. Follow the existing agent pattern for new components
2. Add comprehensive tests for new functionality
3. Update documentation for any configuration changes
4. Ensure all agents maintain clear handoff protocols

## License

[Add your license information here]

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review logs for detailed error information
3. Create an issue with conversion report and logs