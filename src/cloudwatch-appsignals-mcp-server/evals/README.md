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
