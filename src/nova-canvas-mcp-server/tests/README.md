# Nova Canvas MCP Server Tests

This directory contains tests for the Nova Canvas MCP Server, which provides tools for generating images using Amazon Nova Canvas through Amazon Bedrock.

## Test Structure

The test suite is organized as follows:

- `conftest.py`: Contains pytest fixtures used across the test suite
- `test_models.py`: Tests for the Pydantic models used for request/response handling
- `test_novacanvas.py`: Tests for the Nova Canvas API interaction functions
- `test_server.py`: Tests for the MCP server functionality

## Running Tests

You can run the tests using the provided `run_tests.sh` script in the parent directory:

```bash
cd src/nova-canvas-mcp-server
./run_tests.sh
```

This script will:
1. Set up the Python environment
2. Install any missing dependencies
3. Run the tests with pytest
4. Generate a coverage report
5. Run code quality checks (ruff format, ruff lint, pyright)

## Test Coverage

The test suite aims to provide comprehensive coverage of the Nova Canvas MCP Server functionality, including:

- Validation of input parameters
- Error handling
- API interaction
- Image generation with text prompts
- Image generation with color guidance
- File saving functionality
- MCP server integration

## Adding New Tests

When adding new tests, please follow these guidelines:

1. Use the appropriate test file based on what you're testing
2. Follow the existing test patterns
3. Use descriptive test names that clearly indicate what is being tested
4. Use fixtures from `conftest.py` where appropriate
5. Mock external dependencies (e.g., Bedrock runtime client)
6. Test both success and error cases
