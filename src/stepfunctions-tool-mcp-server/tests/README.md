# Step Functions Tool MCP Server Tests

This directory contains tests for the stepfunctions-tool-mcp-server. The tests are organized by module and cover all aspects of the server's functionality.

## Test Structure

The tests are organized into separate files, each focused on testing a specific functionality:

- `test_create_state_machine_tool.py`: Tests for state machine creation functionality
- `test_filter_state_machines_by_tag.py`: Tests for filtering state machines using tags
- `test_format_state_machine_response.py`: Tests for state machine response formatting
- `test_get_schema_arn_from_state_machine_arn.py`: Tests for schema ARN extraction
- `test_get_schema_from_registry.py`: Tests for schema registry operations
- `test_invoke_express_state_machine_impl.py`: Tests for Express state machine invocation
- `test_invoke_standard_state_machine_impl.py`: Tests for Standard state machine invocation
- `test_main.py`: Tests for the main server functionality
- `test_register_state_machines.py`: Tests for state machine registration
- `test_sanitize_tool_name.py`: Tests for tool name sanitization
- `test_validate_state_machine_name.py`: Tests for state machine name validation

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
pytest -xvs tests/test_validate_state_machine_name.py
```

To run a specific test class:

```bash
pytest -xvs tests/test_validate_state_machine_name.py::TestValidateStateMachineName
```

To run a specific test:

```bash
pytest -xvs tests/test_validate_state_machine_name.py::TestValidateStateMachineName::test_empty_prefix_and_list
```

## Test Coverage

To generate a test coverage report, use the following command:

```bash
pytest --cov=awslabs.stepfunctions_tool_mcp_server tests/
```

For a more detailed HTML coverage report:

```bash
pytest --cov=awslabs.stepfunctions_tool_mcp_server --cov-report=html tests/
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

- `mock_sfn_client`: A mock boto3 client (will be updated to Step Functions in phase 2)
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
