# AWS Well-Architected Security Tool MCP Server Tests

This directory contains tests for the AWS Well-Architected Security Tool MCP Server.

## Test Structure

The tests are organized by module:

- `test_prompt_utils.py`: Tests for prompt template utilities
- `test_resource_utils.py`: Tests for AWS resource operations
- `test_storage_security.py`: Tests for storage encryption checks
- `test_network_security.py`: Tests for network security checks
- `test_security_services.py`: Tests for AWS security services

## Running Tests

### Using the run_tests.sh Script

The easiest way to run all tests is to use the provided script:

```bash
# Make the script executable if needed
chmod +x ../run_tests.sh

# Run the tests
../run_tests.sh
```

This script will:
1. Install required dependencies (pytest, pytest-asyncio, pytest-cov)
2. Run all tests with coverage reporting

### Running Tests Manually

If you prefer to run tests manually:

1. Install the required dependencies:

```bash
pip install pytest pytest-asyncio pytest-cov
```

2. Run all tests:

```bash
python -m pytest -v
```

3. Run tests with coverage:

```bash
python -m pytest -v --cov=awslabs.aws_wa_sec_tool_mcp_server --cov-report=term-missing
```

4. Run a specific test file:

```bash
python -m pytest test_prompt_utils.py -v
```

5. Run a specific test function:

```bash
python -m pytest test_prompt_utils.py::test_load_prompt_templates_valid_file -v
```

## Test Requirements

- Python 3.8 or higher
- pytest
- pytest-asyncio (for testing async functions)
- pytest-cov (for coverage reporting)

## Notes

- The tests use mocks to avoid making actual AWS API calls
- Async tests are marked with `@pytest.mark.asyncio` and require the pytest-asyncio plugin
