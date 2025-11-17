# MCP Tool Evaluation Framework

Generic evaluation framework for testing AI agents using Model Context Protocol (MCP) tools. Provides reusable components for metrics tracking, agent orchestration, and validation.

Currently used for evaluating CloudWatch Application Signals MCP tools. Designed to be easily extended to other MCP tools.

## Quick Start

### Prerequisites

- Python 3.10+
- AWS credentials configured

### Running Evals

Run the below commands from the `src/cloudwatch-applicationsignals-mcp-server` directory.

```bash
# List all available tasks
python -m evals tasks --list

# Run specific task by ID
python -m evals tasks --task-id <task_id>

# Run all tasks from a task file
python -m evals tasks --task <task_file>

# Run with verbose logging
python -m evals tasks --task-id <task_id> -v

# Skip cleanup (useful for inspecting changes)
python -m evals tasks --task-id <task_id> --no-cleanup
```

### Configuration

The framework can be configured via environment variables.

- **MCP_EVAL_MODEL_ID**: Override default Bedrock model ID (default: `us.anthropic.claude-sonnet-4-20250514-v1:0`)
- **MCP_EVAL_AWS_REGION**: Override default AWS region (default: `us-east-1`)
- **MCP_EVAL_MAX_TURNS**: Override default max conversation turns (default: `20`)
- **MCP_EVAL_TEMPERATURE**: Override default model temperature (default: `0.0`)

**Note:** These settings apply to both the agent being evaluated and the LLM judge, but MAX_TURNS is not relevant for the LLM judge (one-shot call).

**MCP Server Logging (for evaluated agent only, judge does not use MCP):**
- **MCP_CLOUDWATCH_APPLICATION_SIGNALS_LOG_LEVEL**: Control MCP server log verbosity for debugging (default: `WARNING`, options: `DEBUG`, `INFO`, `WARNING`, `ERROR`)

Example:
```bash
export MCP_EVAL_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0
export MCP_EVAL_MAX_TURNS=30
export MCP_CLOUDWATCH_APPLICATION_SIGNALS_LOG_LEVEL=DEBUG  # For debugging server issues
python -m evals tasks --task-id my_task
```

### Creating Task Files

Task files follow a specific convention for auto-discovery:

1. **Filename**: Must end with `_tasks.py` (e.g., `investigation_tasks.py`, `enablement_tasks.py`)
2. **Module attribute**: Must contain a `TASKS` attribute that is a list of `Task` instances

Example task file:

```python
# investigation_tasks.py
from evals.core.task import Task

class MyInvestigationTask(Task):
    id = "my_task_id"

    def get_prompt(self) -> str:
        return "Your task prompt here"

    @property
    def rubric(self) -> list:
        return [
            {
                "criteria": "Task completion criteria",
                "validator": "validator_name"
            }
        ]

# Required: TASKS list containing Task instances
TASKS = [
    MyInvestigationTask(),
    # ... more tasks
]
```

The framework will automatically discover and load all `*_tasks.py` files in your task directory.

### Mock Configuration

The evaluation framework supports mocking external dependencies (boto3, requests, etc.) to isolate tests from real API calls.

**Important behavior:**
- Only libraries listed in your mock config get patched
- Libraries not in the mock config will make **real API calls** during evaluation
- For patched libraries, unmocked operations raise `UnmockedMethodError` with helpful messages

**Example:**
```python
mock_config = {
    'boto3': {
        'application-signals': {
            'list_services': [{'request': {}, 'response': 'fixtures/services.json'}]
        }
    }
}
```

In this example:
- `boto3` is patched - all calls go through the mock system
- `list_services` is mocked - returns fixture data for all requests
- Other boto3 operations (e.g., `get_service_level_objective`) raise `UnmockedMethodError`
- Other libraries (e.g., `requests`) make real API calls

**Minimal stub configuration:**
```python
mock_config = {'boto3': {}}  # Patches boto3, but all operations raise UnmockedMethodError
```

**Best practice:** Always mock all external libraries your MCP server uses to prevent accidental real API calls during testing.

**Supported fixture formats:**
- `.json` - Loaded and parsed as JSON
- `.txt` - Loaded as plain text
- Other file extensions or inline values are passed through as-is

## Extending the Framework

### Adding New Mock Handlers

TODO: Add comprehensive guide for creating new mock handlers for different libraries (requests, database clients, etc.). Should cover:
- Creating a new McpDependencyMockingHandler subclass
- Implementing required abstract methods
- Registering the handler in `_register_builtin_handlers()` (or consider auto-discovery pattern)
- Testing the mock handler
