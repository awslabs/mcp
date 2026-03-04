# AGENTS.md

## Project Overview

This is the **AWS DynamoDB MCP Server** - an official AWS Labs Model Context Protocol (MCP) server that provides DynamoDB expert design guidance and data modeling assistance. The project is built with Python 3.10+ and uses `uv` for dependency management.

**Current Version**: See `version` in [pyproject.toml](pyproject.toml)

**Project URLs**:
- Homepage: https://awslabs.github.io/mcp/
- Documentation: https://awslabs.github.io/mcp/servers/dynamodb-mcp-server/
- Repository: https://github.com/awslabs/mcp.git
- Changelog: https://github.com/awslabs/mcp/blob/main/src/dynamodb-mcp-server/CHANGELOG.md

**Package Information**:
- PyPI Package: `awslabs.dynamodb-mcp-server`
- License: Apache-2.0

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

# Docker healthcheck
# The container includes a healthcheck script at /app/docker-healthcheck.sh
```

## Code Style and Quality

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

### Code Style Configuration
- **Formatter**: Ruff (see pyproject.toml for complete configuration)
- **Type Checker**: Pyright (configured in pyproject.toml)
- Complete style rules and exceptions are defined in pyproject.toml

### Pre-commit Setup
```bash
# Install pre-commit hooks (if .pre-commit-config.yaml exists)
uv run pre-commit install

# Run pre-commit on all files
uv run pre-commit run --all-files
```

**Note**: This project includes pre-commit as a dev dependency but does not have a `.pre-commit-config.yaml` file configured.

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

# Run tests by marker
uv run pytest -m integration  # Run integration tests
uv run pytest -m "not live"   # Skip live tests (default behavior)
uv run pytest -m unit         # Run unit tests only
```

### Test Categories and Markers
The project uses pytest markers to categorize tests (configured in pyproject.toml):
- **integration**: Integration tests (slower, end-to-end)
- **live**: Live API calls (skipped by default)
- **asyncio**: Async tests (auto-mode enabled)
- **unit**: Unit tests (fast, isolated)
- **file_generation**: File generation tests
- **slow**: Comprehensive/slow tests
- **python**: Python language-specific tests
- **snapshot**: Snapshot tests for generated code consistency

**Default Test Behavior**: Tests marked with `integration` or `live` are excluded by default (configured via pytest addopts: `-m 'not integration and not live'`)

### Test Suite
- **Property-based tests**: Using `hypothesis` for comprehensive input validation
- **Comprehensive test coverage**: Unit, integration, and evaluation tests
- **Async test support**: pytest-asyncio with auto mode
- **Mocking support**: Using `moto` for AWS service mocking
- **Coverage exclusions**: Pragma comments and main blocks are excluded

### Available Test Files and Directories
- `tests/test_dynamodb_server.py` - Main MCP server tests
- `tests/test_common.py` - Common utilities tests
- `tests/test_markdown_formatter.py` - Markdown formatting tests
- `tests/test_model_validation_utils.py` - DynamoDB validation tests
- `tests/db_analyzer/` - Database analyzer tests
- `tests/evals/` - Evaluation framework tests
- `tests/cdk_generator/` - CDK code generation tests
- `tests/repo_generation_tool/` - Data access layer generation tests
- `tests/conftest.py` - Shared pytest fixtures and configuration

### Test Environment Setup
- Tests use `pytest` with `asyncio_mode = "auto"` (configured in pyproject.toml)
- MySQL integration tests use environment variable fixtures (mysql_env_setup)
- Coverage reports exclude pragma comments and main blocks (configured in pyproject.toml)
- Coverage source: `awslabs` directory
- Coverage omits: `awslabs/dynamodb_mcp_server/repo_generation_tool/languages/python/base_repository.py`

## Project Structure

### Core Components
- `awslabs/dynamodb_mcp_server/server.py` - Main MCP server implementation with FastMCP
- `awslabs/dynamodb_mcp_server/common.py` - Shared utilities and types
- `awslabs/dynamodb_mcp_server/model_validation_utils.py` - DynamoDB Local validation
- `awslabs/dynamodb_mcp_server/markdown_formatter.py` - Output formatting
- `awslabs/dynamodb_mcp_server/__init__.py` - Package initialization with version info

### Key Directories
- `awslabs/dynamodb_mcp_server/prompts/` - Expert prompts and guidance
  - `dynamodb_architect.md` - Main data modeling expert prompt
  - `dynamodb_schema_generator.md` - Schema generation guidance
  - `json_generation_guide.md` - JSON specification guide
  - `transform_model_validation_result.md` - Validation result formatting
  - `usage_data_generator.md` - Test data generation instructions
  - `dal_implementation/` - Data access layer implementation templates
  - `next_steps/` - Post-modeling guidance
- `awslabs/dynamodb_mcp_server/db_analyzer/` - Database analysis tools (MySQL, PostgreSQL, SQL Server)
  - `base_plugin.py` - Base analyzer plugin interface
  - `mysql.py` - MySQL analyzer implementation
  - `postgresql.py` - PostgreSQL analyzer implementation
  - `sqlserver.py` - SQL Server analyzer implementation
  - `plugin_registry.py` - Plugin discovery and registration
  - `analyzer_utils.py` - Common analyzer utilities
- `awslabs/dynamodb_mcp_server/cdk_generator/` - CDK infrastructure code generation
  - `generator.py` - CDK app generator
  - `models.py` - CDK generation models
- `awslabs/dynamodb_mcp_server/repo_generation_tool/` - Data access layer code generation
  - `core/` - Core validation and parsing logic
  - `languages/` - Language-specific code generators
  - `codegen.py` - Main code generation orchestration
- `tests/` - Test suite with unit, integration, and evaluation tests

### Available MCP Tools

The DynamoDB MCP server provides **7 tools** for data modeling, validation, and code generation:

1. **dynamodb_data_modeling** - Interactive data model design with expert guidance. Retrieves the complete DynamoDB Data Modeling Expert prompt with enterprise-level design patterns, cost optimization strategies, and multi-table design philosophy.

2. **dynamodb_data_model_validation** - Automated validation using DynamoDB Local. Validates your DynamoDB data model by loading dynamodb_data_model.json, setting up DynamoDB Local, creating tables with test data, and executing all defined access patterns.

3. **source_db_analyzer** - Extract schema and patterns from existing databases. Analyzes existing MySQL/PostgreSQL/SQL Server databases to extract schema structure and access patterns from Performance Schema.

4. **generate_resources** - Generates various resources from the DynamoDB data model JSON file. Currently supports CDK infrastructure code generation for deploying DynamoDB tables.

5. **dynamodb_data_model_schema_converter** - Converts your data model (dynamodb_data_model.md) into a structured schema.json file representing your DynamoDB tables, indexes, entities, fields, and access patterns. Automatically validates the schema with up to 8 iterations.

6. **dynamodb_data_model_schema_validator** - Validates schema.json files for code generation compatibility. Checks field types, operations, GSI mappings, pattern IDs, and provides detailed error messages with fix suggestions.

7. **generate_data_access_layer** - Generates type-safe Python code from schema.json including entity classes with field validation, repository classes with CRUD operations, fully implemented access patterns, and optional usage examples.

### Generated Files and Artifacts
When using the MCP tools, the following files are typically generated:
- `dynamodb_requirements.md` - Requirements gathering output
- `dynamodb_data_model.md` - Human-readable data model design
- `dynamodb_data_model.json` - Machine-readable model specification
- `dynamodb_model_validation.json` - Validation results
- `validation_result.md` - Validation summary
- `schema.json` - Structured schema for code generation
- `generated_dal/` - Generated data access layer code
- `database_analysis_YYYYMMDD_HHMMSS/` - Database analysis results

## Development Workflow

### Making Changes
1. Make changes following code style guidelines
2. Add/update tests for new functionality
3. Run quality checks: `uv run ruff check && uv run pyright`
4. Run test suite: `uv run pytest`
5. Commit with conventional commit format (commitizen is configured)
6. Submit pull request or create code review

### Commit Message Format
Follow [Conventional Commits](https://www.conventionalcommits.org/):
```
<type>[optional scope]: <description>

[optional body]
[optional footer(s)]
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `ci`

**Examples**:
- `feat(cdk): add support for point-in-time recovery`
- `fix(validation): handle empty access pattern lists`
- `docs: update AGENTS.md with new tool descriptions`

### Version Management
- Version is managed in `pyproject.toml` and `awslabs/dynamodb_mcp_server/__init__.py`
- Both files must be updated: `pyproject.toml` for packaging/distribution, `__init__.py` for runtime version checking
- Check `pyproject.toml` for current version number
- CHANGELOG.md exists and commitizen is configured to update it
- Version format follows [Semantic Versioning](https://semver.org/)


## Debugging and Troubleshooting

### Logging
- Set `FASTMCP_LOG_LEVEL=DEBUG` for verbose logging
- Available levels: DEBUG, INFO, WARNING, ERROR
- Project uses `loguru` for structured logging (see pyproject.toml for version)
- Logs include timestamps, levels, and contextual information

### Common Issues

#### DynamoDB Local Validation
- **Issue**: Container runtime not found
- **Solution**: Ensure Docker, Podman, Finch, or nerdctl is installed and running
- **Alternative**: Install Java 17+ and set JAVA_HOME environment variable

#### MySQL Analyzer
- **Issue**: Connection timeout or permission denied
- **Solution**: Verify AWS credentials, check Security Group rules, ensure RDS Data API is enabled
- **Debug**: Set `FASTMCP_LOG_LEVEL=DEBUG` to see detailed connection logs

#### Code Generation
- **Issue**: Schema validation fails
- **Solution**: Run `dynamodb_data_model_schema_validator` to get detailed error messages
- **Common fixes**: Check field types, ensure GSI names match, verify pattern IDs are unique

### Performance Considerations
- DynamoDB Local validation requires container runtime (Docker/Podman/Finch/nerdctl) or Java 17+
- MySQL analyzer result sets are limited by `MYSQL_MAX_QUERY_RESULTS` environment variable (default: 500, defined in `db_analyzer/mysql.py`)
- Schema validation can take up to 8 iterations for complex models
- Code generation is optimized for schemas with up to 50 entities

## Security Considerations

### Data Handling
- MySQL analyzer has built-in read-only mode by default (DEFAULT_READONLY = True)
- Schema validation blocks path traversal attempts
- All database operations use parameterized queries to prevent SQL injection
- Secrets are retrieved from AWS Secrets Manager, never hardcoded
- AWS credentials follow standard AWS SDK credential chain

### Best Practices
- Use least-privilege IAM roles for AWS operations
- Rotate database credentials regularly in Secrets Manager
- Review generated code before deploying to production
- Run validation tests against DynamoDB Local, not production tables
- Use read-only replicas for source database analysis when possible

## Dependencies and Compatibility

### Python Version Support
- **Minimum**: Python 3.10
- **Tested**: Python 3.10, 3.11, 3.12, 3.13
- **Docker production build**: Python 3.13 (as specified in Dockerfile)
- **Recommended**: Python 3.12+ for best performance

### Dependencies
- See [pyproject.toml](pyproject.toml) for complete list of production and development dependencies

### Compatibility Notes
- FastMCP framework is used for MCP server implementation
- Compatible with MCP clients: Kiro CLI, Cursor, VS Code, Claude Desktop
- AWS SDK follows standard credential chain (env vars, config files, IAM roles)
- Database analyzers support AWS RDS Data API and direct connections

## Build System

### Build Configuration
- **Build backend**: Hatchling
- **Package name**: awslabs.dynamodb-mcp-server
- **License**: Apache-2.0 (see LICENSE and NOTICE files)
- **Entry point**: awslabs.dynamodb-mcp-server (maps to awslabs.dynamodb_mcp_server.server:main)

### Build Commands
```bash
# Build with uv
uv build

# Install in editable mode for development
uv pip install -e .
```

### Package Distribution
- Published to PyPI as `awslabs.dynamodb-mcp-server`
- Version updates require changes to both `pyproject.toml` (for packaging) and `__init__.py` (for runtime)
- Changelog maintained in CHANGELOG.md following Keep a Changelog format
- Supports installation via `uvx` for latest version

### Hatch Configuration
- Direct references allowed via `allow-direct-references = true`
- Packages list: `["awslabs"]` - includes entire awslabs namespace
- Excludes: `.venv`, `__pycache__`, `node_modules`, `dist`, `build`, etc.

## Additional Resources

### Documentation Links
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)
- [AWS SDK for Python (Boto3)](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)

### Community and Support
- Report issues on [GitHub](https://github.com/awslabs/mcp/issues)
- Refer to official documentation at [AWS Labs MCP](https://awslabs.github.io/mcp/)
- Review CHANGELOG.md for version history and breaking changes
