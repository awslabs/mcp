# AGENTS.md

## Project Overview

This is the **AWS DynamoDB MCP Server** - an official AWS Labs Model Context Protocol (MCP) server that provides DynamoDB expert design guidance and data modeling assistance. The project is built with Python 3.10+ and uses `uv` for dependency management.

## Setup Commands

### Prerequisites
- Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/)
- Install Python: `uv python install 3.10`
- Set up AWS credentials with access to AWS services

### Development Environment
```bash
# Install dependencies
uv sync

# Install development dependencies
uv sync --group dev

# Activate virtual environment
source .venv/bin/activate

# Run the MCP server
uv run awslabs.dynamodb-mcp-server

# Run with uvx (production-like)
uvx awslabs.dynamodb-mcp-server@latest
```

### Docker Development
```bash
# Build Docker image
docker build -t awslabs/dynamodb-mcp-server .

# Run Docker container
docker run --rm --interactive --env FASTMCP_LOG_LEVEL=ERROR awslabs/dynamodb-mcp-server:latest
```

## Code Style and Quality

### Formatting and Linting
- **Formatter**: Ruff with single quotes, no semicolons
- **Line length**: 99 characters
- **Import style**: Lines after imports = 2, no sections
- **Docstring convention**: Google style

### Quality Tools
```bash
# Format code
uv run ruff format

# Lint code
uv run ruff check

# Fix linting issues automatically
uv run ruff check --fix

# Type checking
uv run pyright

# Run all quality checks
uv run ruff check && uv run pyright
```

### Pre-commit Setup
```bash
# Install pre-commit hooks (if .pre-commit-config.yaml exists)
uv run pre-commit install

# Run pre-commit on all files
uv run pre-commit run --all-files
```

**Note**: This project includes pre-commit as a dev dependency but may not have a `.pre-commit-config.yaml` file configured yet.

## Testing

### Test Execution
```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=awslabs --cov-report=html

# Run specific test file
uv run pytest tests/test_dynamodb_server.py

# Run with verbose output
uv run pytest -v

# Run specific test function
uv run pytest tests/test_dynamodb_server.py::test_function_name
```

**Note**: The project defines a "live" test marker in pyproject.toml but no tests currently use it.

### Test Categories
- **Unit tests**: Component tests
- **Property-based tests**: Using `hypothesis` (found in test_dynamodb_server.py)

### Available Test Files
- `tests/test_dynamodb_server.py` - Main MCP server tests
- `tests/test_common.py` - Common utilities tests
- `tests/test_markdown_formatter.py` - Markdown formatting tests
- `tests/test_model_validation_utils.py` - DynamoDB validation tests
- `tests/db_analyzer/` - Database analyzer tests
- `tests/evals/` - Evaluation framework tests

### Test Environment Setup
- Tests use `pytest` with `asyncio_mode = "auto"` (configured in pyproject.toml)
- MySQL integration tests use environment variable fixtures (mysql_env_setup)
- Coverage reports exclude pragma comments and main blocks (configured in pyproject.toml)

## Environment Configuration

### Required Environment Variables
```bash
# AWS Configuration
AWS_PROFILE=default
AWS_REGION=us-west-2
FASTMCP_LOG_LEVEL=ERROR

# MySQL Integration (optional)
MYSQL_CLUSTER_ARN=arn:aws:rds:region:account:cluster:name
MYSQL_SECRET_ARN=arn:aws:secretsmanager:region:account:secret:name
MYSQL_DATABASE=database_name
MYSQL_HOSTNAME=hostname  # Alternative to cluster ARN
MYSQL_PORT=3306          # Optional, default 3306
MYSQL_MAX_QUERY_RESULTS=500  # Optional, default 500
```

### MCP Server Configuration
The server can be configured in MCP clients (Kiro, Cursor, VS Code) using:
```json
{
  "mcpServers": {
    "awslabs.dynamodb-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.dynamodb-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-west-2",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Project Structure

### Core Components
- `awslabs/dynamodb_mcp_server/server.py` - Main MCP server implementation
- `awslabs/dynamodb_mcp_server/common.py` - Shared utilities and types
- `awslabs/dynamodb_mcp_server/model_validation_utils.py` - DynamoDB Local validation
- `awslabs/dynamodb_mcp_server/markdown_formatter.py` - Output formatting

### Key Directories
- `awslabs/dynamodb_mcp_server/prompts/` - Expert prompts and guidance
- `awslabs/dynamodb_mcp_server/db_analyzer/` - Database analysis tools
- `awslabs/dynamodb_mcp_server/cost_performance/` - Cost optimization logic
- `tests/` - Test suite with unit, integration, and evaluation tests

### Available MCP Tools
1. **dynamodb_data_modeling** - Interactive data model design with expert guidance
2. **dynamodb_data_model_validation** - Automated validation using DynamoDB Local
3. **source_db_analyzer** - Extract schema and patterns from existing databases

## Development Workflow

### Making Changes
1. Make changes following code style guidelines
2. Add/update tests for new functionality
3. Run quality checks: `uv run ruff check && uv run pyright`
4. Run test suite: `uv run pytest`
5. Commit with conventional commit format (commitizen is configured)

### Commit Message Format
Follow [Conventional Commits](https://www.conventionalcommits.org/):
```
<type>[optional scope]: <description>

[optional body]
[optional footer(s)]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `ci`

### Version Management
- Version is managed in `pyproject.toml` and `awslabs/dynamodb_mcp_server/__init__.py`
- Commitizen is configured in pyproject.toml for version bumping
- CHANGELOG.md exists and commitizen is configured to update it

## Debugging and Troubleshooting

### Logging
- Set `FASTMCP_LOG_LEVEL=DEBUG` for verbose logging
- Project uses `loguru==0.7.3` for structured logging

### Performance Considerations
- DynamoDB Local validation requires container runtime (Docker/Podman/Finch/nerdctl) or Java 17+
- Large result sets are limited by `MYSQL_MAX_QUERY_RESULTS` setting (default: 500)

## Security Considerations

### Data Handling
- MySQL analyzer has built-in read-only mode by default (DEFAULT_READONLY = True)

## Dependencies and Compatibility

### Python Version Support
- Minimum: Python 3.10
- Tested: Python 3.10, 3.11, 3.12, 3.13
- Docker production build: Python 3.13 (as specified in Dockerfile)

### Key Dependencies
- `mcp[cli]==1.23.0` - Model Context Protocol framework (exact version)
- `boto3>=1.40.5` - AWS SDK
- `loguru==0.7.3` - Structured logging (exact version)
- `strands-agents>=1.5.0` - Agent framework for data modeling
- `dspy-ai>=2.6.27` - Evaluation and reasoning framework
- `pydantic==2.11.7` - Data validation and serialization (exact version)
- `psutil==7.1.1` - System and process utilities (exact version)
- `typing-extensions==4.14.1` - Type hints backport (exact version)
- `awslabs.mysql-mcp-server==1.0.9` - MySQL MCP server integration (exact version)
- `awslabs-aws-api-mcp-server==1.0.2` - AWS API MCP server integration (exact version)

### Development Dependencies
- `commitizen>=4.2.2` - Conventional commits and versioning
- `pre-commit>=4.1.0` - Git pre-commit hooks
- `ruff>=0.9.7` - Linting and formatting
- `pyright>=1.1.398` - Type checking
- `pytest>=8.0.0` - Testing framework
- `pytest-asyncio>=0.26.0` - Async testing support
- `pytest-cov>=4.1.0` - Coverage reporting
- `pytest-mock>=3.12.0` - Mocking utilities
- `hypothesis>=6.100.0` - Property-based testing
- `moto>=5.1.4` - AWS service mocking
- `boto3>=1.38.14` - AWS SDK (separate dev dependency)
