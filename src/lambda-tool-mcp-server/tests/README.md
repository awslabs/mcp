# Lambda MCP Server Tests

This directory contains tests for the lambda-tool-mcp-server. The tests are organized by module and cover all aspects of the server's functionality.

## Test Structure

- `test_server.py`: Unit tests for the server module functions
- `test_integration.py`: Integration tests for the MCP server and Lambda function tools

## Running the Tests

To run the tests, use the provided script from the root directory of the project:

```bash
./run_tests.sh
```

This script will automatically install pytest and its dependencies if they're not already installed.

Alternatively, if you have pytest installed, you can run the tests directly:

```bash
pytest -xvs tests/
```

To run a specific test file:

```bash
pytest -xvs tests/test_server.py
```

To run a specific test class:

```bash
pytest -xvs tests/test_server.py::TestValidateFunctionName
```

To run a specific test:

```bash
pytest -xvs tests/test_server.py::TestValidateFunctionName::test_empty_prefix_and_list
```

## Test Coverage

To generate a test coverage report, use the following command:

```bash
pytest --cov=awslabs.lambda_tool_mcp_server tests/
```

For a more detailed HTML coverage report:

```bash
pytest --cov=awslabs.lambda_tool_mcp_server --cov-report=html tests/
```

This will generate a coverage report in the `htmlcov` directory. Open `htmlcov/index.html` in a web browser to view the report.

## Test Dependencies

The tests require the following dependencies:

- pytest
- pytest-asyncio
- pytest-cov (for coverage reports)
- unittest.mock (for mocking)

These dependencies are included in the project's development dependencies.

## Test Fixtures

The test fixtures are defined in `conftest.py` and include:

- `mock_lambda_client`: A mock boto3 Lambda client
- `mock_env_vars`: Sets up and tears down environment variables for testing
- `clear_env_vars`: Clears environment variables for testing

## Adding New Tests

When adding new tests, follow these guidelines:

1. Place tests in the appropriate file based on the module being tested
2. Use descriptive test names that clearly indicate what is being tested
3. Use pytest fixtures for common setup and teardown
4. Use pytest.mark.asyncio for async tests
5. Use mocks for external dependencies
6. Add docstrings to test classes and methods

## Mocking Strategy

Since we can't actually invoke AWS Lambda functions in tests, we use mocking:

1. Mock the boto3 Lambda client:
   - Mock `list_functions` to return predefined functions
   - Mock `list_tags` to return predefined tags
   - Mock `invoke` to return predefined responses

2. Mock environment variables:
   - AWS_PROFILE
   - AWS_REGION
   - FUNCTION_PREFIX
   - FUNCTION_LIST
   - FUNCTION_TAG_KEY
   - FUNCTION_TAG_VALUE
