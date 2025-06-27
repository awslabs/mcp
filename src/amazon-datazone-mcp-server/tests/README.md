# Testing Guide for AWS DataZone MCP Server

This directory contains comprehensive tests for the AWS DataZone MCP Server. The testing infrastructure is designed to provide reliable, fast, and maintainable tests for all components.

## Test Structure

```
tests/
├── conftest.py                    # Shared fixtures and configuration
├── test_domain_management.py      # Domain operations tests
├── test_project_management.py     # Project operations tests
├── test_data_management.py        # Data/asset operations tests
├── test_glossary.py              # Glossary operations tests
├── test_environment.py           # Environment operations tests
├── test_server.py                # Server integration tests
├── test_integration.py           # AWS integration tests
└── README.md                     # This file
```

## Quick Start

### Running All Tests

```bash
# Run all unit tests (fast)
pytest

# Run with coverage report
pytest --cov=datazone_mcp_server --cov-report=html

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_domain_management.py
```

### Running Integration Tests

```bash
# Set up environment variables for integration tests
export TEST_DATAZONE_DOMAIN_ID="dzd_your_domain_id"
export TEST_DATAZONE_PROJECT_ID="prj_your_project_id"
export AWS_DEFAULT_REGION="us-east-1"

# Run integration tests (requires AWS credentials)
pytest tests/test_integration.py -m integration

# Skip integration tests (useful for CI)
SKIP_AWS_TESTS=true pytest
```

## Test Types

### 1. Unit Tests
**Files**: `test_domain_management.py`, `test_project_management.py`, etc.

Fast, isolated tests that mock AWS API calls:
- Test success scenarios
- Test error handling
- Test parameter validation
- Test tool registration
- Mock all external dependencies

```python
@patch('datazone_mcp_server.tools.domain_management.datazone_client')
async def test_get_domain_success(self, mock_client, test_data_helper):
    # Arrange
    expected_response = test_data_helper.get_domain_response("dzd_test123")
    mock_client.get_domain.return_value = expected_response

    # Act
    result = await domain_management.get_domain("dzd_test123")

    # Assert
    assert result == expected_response
```

### 2. Integration Tests
**File**: `test_integration.py`

Tests with real AWS services (marked with `@pytest.mark.integration`):
- Real AWS API calls
- Error handling with actual AWS errors
- Performance testing
- End-to-end workflows

### 3. Server Tests
**File**: `test_server.py`

Tests for the main MCP server functionality:
- Server initialization
- Tool registration
- Error handling
- CLI functionality

## Test Configuration

### Fixtures (`conftest.py`)

**Mock Fixtures:**
- `mock_datazone_client` - Mock AWS DataZone client
- `mock_client_error` - Helper for creating AWS errors
- `mock_fastmcp` - Mock FastMCP instance

**Data Fixtures:**
- `sample_domain_data` - Test domain data
- `sample_project_data` - Test project data
- `sample_asset_data` - Test asset data
- `sample_glossary_data` - Test glossary data

**Utility Fixtures:**
- `test_data_helper` - Helper class for generating test data
- `aws_error_scenarios` - Common AWS error scenarios

### Environment Variables

**Required for Integration Tests:**
```bash
TEST_DATAZONE_DOMAIN_ID=dzd_your_domain_id
TEST_DATAZONE_PROJECT_ID=prj_your_project_id
AWS_DEFAULT_REGION=us-east-1
```

**Optional Configuration:**
```bash
SKIP_AWS_TESTS=true           # Skip integration tests
```

### Pytest Markers

```bash
# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"

# Run only unit tests (exclude integration)
pytest -m "not integration"
```

## Coverage Requirements

**Target Coverage: >80%**

```bash
# Generate coverage report
pytest --cov=datazone_mcp_server --cov-report=html --cov-report=term-missing

# View HTML report
open htmlcov/index.html
```

**Coverage Areas:**
- All tool functions
- Error handling paths
- Parameter validation
- Server initialization
- Integration scenarios (when AWS tests run)

## Testing Patterns

### 1. AAA Pattern (Arrange-Act-Assert)

```python
async def test_create_domain_success(self, mock_client, sample_domain_data):
    # Arrange
    expected_response = {"id": "dzd_new123", "name": "Test Domain"}
    mock_client.create_domain.return_value = expected_response

    # Act
    result = await domain_management.create_domain(
        name=sample_domain_data["name"],
        domain_execution_role=sample_domain_data["domain_execution_role"],
        service_role=sample_domain_data["service_role"]
    )

    # Assert
    assert result == expected_response
    mock_client.create_domain.assert_called_once_with(
        name=sample_domain_data["name"],
        domainExecutionRole=sample_domain_data["domain_execution_role"],
        serviceRole=sample_domain_data["service_role"],
        domainVersion="V2"
    )
```

### 2. Error Testing Pattern

```python
async def test_create_domain_access_denied(self, mock_client, mock_client_error):
    # Arrange
    mock_client.create_domain.side_effect = mock_client_error(
        "AccessDeniedException",
        "Insufficient permissions"
    )

    # Act & Assert
    with pytest.raises(Exception) as exc_info:
        await domain_management.create_domain(
            name="Test Domain",
            domain_execution_role="arn:aws:iam::123456789012:role/ExecRole",
            service_role="arn:aws:iam::123456789012:role/ServiceRole"
        )

    assert "Access denied while creating domain" in str(exc_info.value)
```

### 3. Parameter Validation Pattern

```python
async def test_create_domain_with_all_optional_params(self, mock_client):
    # Act
    await domain_management.create_domain(
        name="Full Domain",
        domain_execution_role="arn:aws:iam::123456789012:role/ExecRole",
        service_role="arn:aws:iam::123456789012:role/ServiceRole",
        domain_version="V1",
        description="Full description",
        kms_key_identifier="arn:aws:kms:us-east-1:123456789012:key/12345"
    )

    # Assert all parameters passed correctly
    mock_client.create_domain.assert_called_once_with(
        name="Full Domain",
        domainExecutionRole="arn:aws:iam::123456789012:role/ExecRole",
        serviceRole="arn:aws:iam::123456789012:role/ServiceRole",
        domainVersion="V1",
        description="Full description",
        kmsKeyIdentifier="arn:aws:kms:us-east-1:123456789012:key/12345"
    )
```

## Debugging Tests

### Running Single Tests

```bash
# Run specific test method
pytest tests/test_domain_management.py::TestDomainManagement::test_get_domain_success -v

# Run with debugger
pytest tests/test_domain_management.py::TestDomainManagement::test_get_domain_success --pdb

# Run with print statements
pytest tests/test_domain_management.py -s
```

### Common Issues

**Import Errors:**
```bash
# Ensure package is installed in development mode
pip install -e .
```

**AWS Credential Errors:**
```bash
# Configure AWS credentials
aws configure
# OR set environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
```

**Mock Issues:**
- Ensure mocks are properly patched
- Check mock call assertions
- Verify return values match expected format

## Adding New Tests

### 1. Unit Test Template

```python
"""
Unit tests for new_module tools.
"""
import pytest
from unittest.mock import patch, Mock
from datazone_mcp_server.tools import new_module

class TestNewModule:
    """Test cases for new module tools."""

    @patch('datazone_mcp_server.tools.new_module.datazone_client')
    async def test_new_function_success(self, mock_client):
        """Test successful operation."""
        # Arrange
        expected_response = {"result": "success"}
        mock_client.some_operation.return_value = expected_response

        # Act
        result = await new_module.new_function("param1", "param2")

        # Assert
        assert result == expected_response
        mock_client.some_operation.assert_called_once_with(
            param1="param1",
            param2="param2"
        )

    def test_register_tools(self, mock_fastmcp):
        """Test that tools are properly registered with FastMCP."""
        tools = new_module.register_tools(mock_fastmcp)
        assert mock_fastmcp.tool.call_count > 0
        assert "new_function" in tools
```

### 2. Integration Test Template

```python
@pytest.mark.integration
async def test_new_function_integration(self, real_datazone_client, test_domain_id):
    """Test new function with real AWS service."""
    import datazone_mcp_server.tools.new_module as nm
    original_client = nm.datazone_client
    nm.datazone_client = real_datazone_client

    try:
        result = await nm.new_function(test_domain_id, "param")

        # Verify response structure
        assert "expected_field" in result

    finally:
        nm.datazone_client = original_client
```

## Performance Testing

### Benchmarking

```bash
# Run performance tests
pytest tests/test_integration.py -m slow

# Profile test execution
pytest --profile

# Memory usage testing
pytest --memray tests/test_server.py::TestServerIntegration::test_memory_usage_reasonable
```

### Performance Targets

- Unit tests: <1ms per test
- Server initialization: <1 second
- Integration tests: <5 seconds per test
- Memory usage: <1000 new objects per module load

## Best Practices

### Do's

- Use descriptive test names
- Follow AAA pattern (Arrange-Act-Assert)
- Mock external dependencies
- Test both success and error scenarios
- Use fixtures for common test data
- Write integration tests for critical paths
- Maintain >80% code coverage

### Don'ts

- Don't test implementation details
- Don't write overly complex tests
- Don't ignore test failures
- Don't skip error testing
- Don't hardcode credentials
- Don't make tests dependent on each other

## Getting Help

**Common Commands:**
```bash
# Get help on pytest options
pytest --help

# List all available markers
pytest --markers

# Show available fixtures
pytest --fixtures

# Dry run (collect tests without running)
pytest --collect-only
```

**Resources:**
- [Pytest Documentation](https://docs.pytest.org/)
- [unittest.mock Documentation](https://docs.python.org/3/library/unittest.mock.html)
- [AWS Boto3 Testing Guide](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/testing.html)
