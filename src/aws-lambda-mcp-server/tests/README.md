# AWS Lambda MCP Server Tests

This directory contains unit tests for the AWS Lambda MCP Server.

## Running Tests

To run the tests, you can use pytest:

```bash
# Run all tests
pytest

# Run tests with verbose output
pytest -v

# Run a specific test file
pytest tests/test_server.py

# Run a specific test class
pytest tests/test_server.py::TestSamBuildTool

# Run a specific test method
pytest tests/test_server.py::TestSamBuildTool::test_sam_build_tool

# Run tests with coverage report
pytest --cov=awslabs.aws_lambda_mcp_server

# Run tests and generate HTML coverage report
pytest --cov=awslabs.aws_lambda_mcp_server --cov-report=html
```

## Test Structure

The tests are organized by module:

- `test_server.py`: Tests for the MCP server tools
- `test_models.py`: Tests for the data models
- `test_sam_init.py`: Tests for the SAM initialization functionality
- `test_sam_pipeline.py`: Tests for the SAM pipeline functionality
- `test_get_iac_guidance.py`: Tests for the IaC guidance functionality
- `test_get_lambda_event_schemas.py`: Tests for the Lambda event schemas functionality
- `test_logger.py`: Tests for the logger utility
- `test_github.py`: Tests for the GitHub utility functions

## Live Tests

Some tests are marked with `@pytest.mark.live` to indicate that they make live API calls. These tests are skipped by default. To run them, use the `--run-live` option:

```bash
pytest --run-live
```

## Adding New Tests

When adding new tests, follow these conventions:

1. Create a new test file named `test_<module_name>.py` for each module you want to test.
2. Use the `pytest.mark.asyncio` decorator for async test methods.
3. Use `unittest.mock` to mock external dependencies.
4. Follow the existing test structure and naming conventions.
5. Add appropriate docstrings to test classes and methods.
6. Mark tests that make live API calls with `@pytest.mark.live`.

## Test Coverage

To check test coverage, run:

```bash
pytest --cov=awslabs.aws_lambda_mcp_server
```

This will show the coverage report in the terminal. To generate an HTML report:

```bash
pytest --cov=awslabs.aws_lambda_mcp_server --cov-report=html
```

The HTML report will be generated in the `htmlcov` directory.
