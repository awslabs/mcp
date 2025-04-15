# Core MCP Server Tests

This directory contains tests for the Core MCP Server.

## Test Structure

The tests are organized as follows:

- `conftest.py`: Contains pytest configuration and fixtures
- `test_available_servers.py`: Tests for the available_servers module
- `test_init.py`: Tests for the package initialization
- `test_main.py`: Tests for the main function
- `test_response_types.py`: Tests for the response type classes
- `test_server.py`: Tests for the server module
- `test_static.py`: Tests for the static module

## Running Tests

To run the tests, use the following command from the root directory of the project:

```bash
pytest
```

This will run all tests and generate a coverage report.

### Running Specific Tests

To run a specific test file:

```bash
pytest tests/test_server.py
```

To run a specific test class:

```bash
pytest tests/test_server.py::TestPromptUnderstanding
```

To run a specific test method:

```bash
pytest tests/test_server.py::TestPromptUnderstanding::test_get_prompt_understanding
```

### Running Tests with Coverage

To run tests with coverage:

```bash
pytest --cov=awslabs.core_mcp_server
```

To generate an HTML coverage report:

```bash
pytest --cov=awslabs.core_mcp_server --cov-report=html
```

This will create a `htmlcov` directory with the coverage report.

### Running Live Tests

Some tests are marked as "live" because they make actual API calls. These tests are skipped by default. To run them:

```bash
pytest --run-live
```

## Test Dependencies

The tests require the following dependencies:

- pytest
- pytest-cov
- pytest-mock

These dependencies are included in the `dev` dependency group in `pyproject.toml`.
