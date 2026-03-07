# Development Guide - MWAA MCP Server

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) for package management
- AWS credentials configured with MWAA permissions

## Setup

```bash
cd src/mwaa-mcp-server
uv venv && uv sync --all-groups
```

## Running Tests

```bash
# Run all tests with coverage
uv run --frozen pytest --cov --cov-branch --cov-report=term-missing

# Run specific test file
uv run --frozen pytest tests/test_server.py -v

# Run integration tests only
uv run --frozen pytest tests/integ_test_server.py -v
```

## Code Quality

```bash
# Install pre-commit hooks
pre-commit install

# Run all checks
pre-commit run --all-files

# Type checking
uv run --frozen pyright

# Linting
uv run --frozen ruff check .

# Formatting
uv run --frozen ruff format .
```

## Running the Server Locally

```bash
# Using stdio transport (default)
uv run --frozen mwaa-mcp-server

# With environment variables
AWS_REGION=us-east-1 AWS_PROFILE=default uv run --frozen mwaa-mcp-server
```
