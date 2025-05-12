# Step Functions MCP Server Tests

This directory contains tests for the stepfunctions-mcp-server. The tests are organized by module and cover all aspects of the server's functionality.

## Test Structure

- `test_server.py`: Unit tests for the server module functions
- `test_integration.py`: Integration tests for the MCP server and Step Functions state machine tools

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
pytest -xvs tests/test_server.py::TestValidateStateMachineName
```

To run a specific test:

```bash
pytest -xvs tests/test_server.py::TestValidateStateMachineName::test_empty_prefix_and_list
```

## Test Coverage

To generate a test coverage report, use the following command:

```bash
pytest --cov=awslabs.stepfunctions_mcp_server tests/
```

For a more detailed HTML coverage report:

```bash
pytest --cov=awslabs.stepfunctions_mcp_server --cov-report=html tests/
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

- `mock_lambda_client`: A mock boto3 client (will be updated to Step Functions in phase 2)
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

Since we can't actually invoke AWS Step Functions state machines in tests, we use mocking:

1. Mock the boto3 Step Functions client:
   - Mock `list_state_machines` to return predefined state machines
   - Mock `list_tags` to return predefined tags
   - Mock `start_execution` to return predefined responses

2. Mock environment variables:
   - AWS_PROFILE
   - AWS_REGION
   - STATE_MACHINE_PREFIX
   - STATE_MACHINE_LIST
   - STATE_MACHINE_TAG_KEY
   - STATE_MACHINE_TAG_VALUE
