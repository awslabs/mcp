# MCP Tool Evaluation Framework

Generic evaluation framework for testing AI agents using Model Context Protocol (MCP) tools. Provides reusable components for metrics tracking, agent orchestration, and validation.

Currently used for evaluating CloudWatch Application Signals MCP tools. Designed to be easily extended to other MCP tools.

## Quick Start

### Prerequisites

- Python 3.10+
- AWS credentials configured

### Running Evals

```bash
# List all available tasks
python -m evals applicationsignals --list

# Run specific task by ID
python -m evals applicationsignals --task-id <task_id>

# Run all tasks from a task file
python -m evals applicationsignals --task <task_file>

# Run with verbose logging
python -m evals applicationsignals --task-id <task_id> -v

# Skip cleanup (useful for inspecting changes)
python -m evals applicationsignals --task-id <task_id> --no-cleanup
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
- `list_services` is mocked - returns fixture data
- Other boto3 operations (e.g., `get_service_level_objective`) raise `UnmockedMethodError`
- Other libraries (e.g., `requests`) make real API calls

**Minimal stub configuration:**
```python
mock_config = {'boto3': {}}  # Patches boto3, but all operations raise UnmockedMethodError
```

**Best practice:** Always mock all external libraries your MCP server uses to prevent accidental real API calls during testing.

## Extending the Framework

### Adding New Mock Handlers

TODO: Add comprehensive guide for creating new mock handlers for different libraries (requests, database clients, etc.). Should cover:
- Creating a new MockHandler subclass
- Implementing required abstract methods
- Registering the handler in `_register_builtin_handlers()` (or consider auto-discovery pattern)
- Testing the mock handler
