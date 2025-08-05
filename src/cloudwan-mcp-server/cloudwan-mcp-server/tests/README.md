# CloudWAN MCP Server Test Suite

This document provides comprehensive testing guidelines for the AWS Labs CloudWAN MCP Server, following AWS Labs testing standards and best practices.

## Table of Contents

- [Test Structure](#test-structure)
- [Test Categories](#test-categories)
- [Running Tests](#running-tests)
- [Test Markers](#test-markers)
- [Coverage Requirements](#coverage-requirements)
- [Writing Tests](#writing-tests)
- [AWS Labs Standards](#aws-labs-standards)
- [Live API Testing](#live-api-testing)
- [Troubleshooting](#troubleshooting)

## Test Structure

Our test suite follows AWS Labs standard organization:

```
tests/
├── README.md                           # This documentation
├── conftest.py                         # Shared fixtures and configuration
├── fixtures/                           # Test data and mock responses
│   ├── aws_responses/                  # Mock AWS API responses
│   ├── policy_documents/               # Sample CloudWAN policies
│   └── network_configurations/         # Network topology samples
├── unit/                               # Unit tests (fast, isolated)
│   ├── test_comprehensive_models.py    # Data model validation tests
│   ├── test_aws_helpers.py             # AWS utility function tests
│   ├── test_aws_labs_patterns.py       # AWS Labs compliance tests
│   └── test_*.py                       # Other unit tests
├── integration/                        # Integration tests (slower, AWS mocks)
│   ├── test_comprehensive_server.py    # Server initialization tests
│   ├── test_main_entry_point.py        # Main entry point tests
│   ├── test_aws_labs_compliance.py     # AWS Labs integration patterns
│   └── test_*.py                       # Other integration tests
└── live/                              # Live API tests (optional, requires AWS creds)
    ├── test_live_core_networks.py     # Live CloudWAN API tests
    └── test_live_*.py                 # Other live tests
```

## Test Categories

### Unit Tests (`tests/unit/`)
- **Purpose**: Fast, isolated tests for individual functions and classes
- **Dependencies**: No external dependencies (AWS APIs, network calls)
- **Execution Time**: < 1 second per test
- **Coverage Target**: 95%+

**Key Test Files:**
- `test_comprehensive_models.py` - Data model validation and serialization
- `test_aws_helpers.py` - AWS utility functions and client management
- `test_aws_labs_patterns.py` - AWS Labs compliance patterns

### Integration Tests (`tests/integration/`)
- **Purpose**: Test component interactions and server behavior
- **Dependencies**: Mocked AWS services using `moto`
- **Execution Time**: 1-10 seconds per test
- **Coverage Target**: 90%+

**Key Test Files:**
- `test_comprehensive_server.py` - MCP server initialization and tool registration
- `test_main_entry_point.py` - Application entry points and CLI behavior
- `test_aws_labs_compliance.py` - AWS Labs integration patterns

### Live Tests (`tests/live/`)
- **Purpose**: End-to-end testing against real AWS services
- **Dependencies**: Valid AWS credentials and permissions
- **Execution Time**: 5-60 seconds per test
- **Coverage Target**: Core functionality only

## Running Tests

### Quick Start
```bash
# Install dependencies
uv sync --dev

# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=awslabs --cov-report=term-missing

# Run specific test categories
uv run pytest tests/unit/                    # Unit tests only
uv run pytest tests/integration/             # Integration tests only
uv run pytest -m "not live"                  # Exclude live tests
```

### Advanced Test Execution
```bash
# Run tests with specific markers
uv run pytest -m unit                        # Unit tests only
uv run pytest -m integration                 # Integration tests only
uv run pytest -m slow                        # Slow tests only
uv run pytest -m "not slow"                  # Exclude slow tests

# Parallel test execution
uv run pytest -n auto                        # Auto-detect CPU cores
uv run pytest -n 4                          # Use 4 workers

# Verbose output
uv run pytest -v                            # Verbose test names
uv run pytest -vv                           # Very verbose output
uv run pytest -s                            # Show print statements

# Specific test files/functions
uv run pytest tests/unit/test_models.py     # Single file
uv run pytest tests/unit/test_models.py::TestContentItemModel::test_content_item_valid_creation
```

### Live API Testing
```bash
# Prerequisites: Set up AWS credentials
export AWS_PROFILE=your-cloudwan-profile
export AWS_DEFAULT_REGION=us-east-1

# Run live tests (requires AWS credentials)
uv run pytest tests/live/ -m live

# Run specific live test
uv run pytest tests/live/test_live_core_networks.py -m live -v
```

## Test Markers

We use pytest markers to categorize and control test execution:

### Standard Markers
- `@pytest.mark.unit` - Fast, isolated unit tests
- `@pytest.mark.integration` - Integration tests with mocked dependencies  
- `@pytest.mark.live` - Tests requiring real AWS API calls
- `@pytest.mark.slow` - Tests taking >10 seconds to execute
- `@pytest.mark.asyncio` - Async/await test functions

### AWS Labs Markers
- `@pytest.mark.aws_labs` - Tests verifying AWS Labs standard compliance
- `@pytest.mark.security` - Security-focused tests
- `@pytest.mark.performance` - Performance and load tests

### Example Usage
```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_core_network_model_validation():
    """Test CoreNetwork model validation patterns."""
    pass

@pytest.mark.integration
@pytest.mark.slow
def test_comprehensive_server_startup():
    """Test complete server initialization process."""
    pass

@pytest.mark.live
@pytest.mark.skipif(not os.getenv('AWS_PROFILE'), reason="Requires AWS credentials")
def test_live_core_network_listing():
    """Test against real CloudWAN API."""
    pass
```

## Coverage Requirements

### Minimum Coverage Targets
- **Overall Coverage**: 90%+
- **Unit Tests**: 95%+
- **Integration Tests**: 90%+
- **Critical Functions**: 100% (error handling, data validation)

### Coverage Configuration
Coverage is configured in `pyproject.toml`:
```toml
[tool.coverage.run]
source = ["awslabs"]

[tool.coverage.report]
skip_covered = true
show_missing = true
```

### Generate Coverage Reports
```bash
# Terminal report
uv run pytest --cov=awslabs --cov-report=term-missing

# HTML report
uv run pytest --cov=awslabs --cov-report=html
open htmlcov/index.html

# XML report (for CI/CD)
uv run pytest --cov=awslabs --cov-report=xml
```

## Writing Tests

### AWS Labs Test Standards

#### 1. Test Structure
```python
# Standard test file header
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# Licensed under the Apache License, Version 2.0

"""Module description following AWS Labs patterns."""

import pytest
from unittest.mock import Mock, patch
from awslabs.cloudwan_mcp_server.module import function_to_test

class TestFunctionToTest:
    """Test class following AWS Labs naming conventions."""

    @pytest.mark.unit
    def test_success_scenario(self):
        """Test successful execution path."""
        # Arrange
        input_data = {"key": "value"}
        
        # Act
        result = function_to_test(input_data)
        
        # Assert
        assert result["success"] is True
        assert "data" in result

    @pytest.mark.unit
    def test_error_scenario(self):
        """Test error handling following AWS Labs patterns."""
        # Test error conditions and verify proper error response format
        pass
```

#### 2. AWS Service Mocking
```python
@pytest.mark.unit
@patch('awslabs.cloudwan_mcp_server.server.get_aws_client')
def test_aws_service_integration(self, mock_get_client):
    """Test AWS service integration with proper mocking."""
    # Setup
    mock_client = Mock()
    mock_client.list_core_networks.return_value = {
        'CoreNetworks': [{'CoreNetworkId': 'test-123'}]
    }
    mock_get_client.return_value = mock_client
    
    # Test
    result = await list_core_networks()
    
    # Verify
    assert result["success"] is True
    mock_client.list_core_networks.assert_called_once()
```

#### 3. Error Response Testing
```python
@pytest.mark.unit
def test_aws_labs_error_format(self):
    """Test error responses follow AWS Labs format."""
    error_response = handle_error("Test error", "TEST_CODE")
    
    # Verify AWS Labs standard error format
    assert error_response["success"] is False
    assert "error" in error_response
    assert "error_code" in error_response
    assert error_response["error_code"] == "TEST_CODE"
```

### Best Practices

#### 1. Test Isolation
- Each test should be independent and not rely on other tests
- Use `setup_method`/`teardown_method` for test-specific setup
- Clear shared state (caches, globals) between tests

#### 2. Mock External Dependencies
- Mock all AWS API calls in unit/integration tests
- Use `moto` for AWS service mocking
- Mock filesystem and network operations

#### 3. Async Test Handling
```python
@pytest.mark.asyncio
async def test_async_function():
    """Test async functions properly."""
    result = await async_function()
    assert result is not None
```

#### 4. Parametrized Testing
```python
@pytest.mark.parametrize("input_value,expected", [
    ("10.0.0.0/16", True),
    ("192.168.1.0/24", True), 
    ("invalid-cidr", False),
])
def test_cidr_validation(input_value, expected):
    """Test CIDR validation with multiple inputs."""
    result = validate_cidr(input_value)
    assert result == expected
```

## AWS Labs Standards

### Response Format Standards
All CloudWAN MCP tools should return responses in AWS Labs standard format:

#### Success Response
```json
{
  "success": true,
  "data": {
    "CoreNetworks": [...],
    "metadata": {...}
  },
  "timestamp": "2024-01-15T10:30:45"
}
```

#### Error Response
```json
{
  "success": false,
  "error": "Descriptive error message",
  "error_code": "AWS_ERROR_CODE",
  "timestamp": "2024-01-15T10:30:45"
}
```

### Testing Standards Compliance
Tests should verify:
- Response format consistency
- Error handling patterns
- AWS service integration patterns
- Security best practices
- Performance characteristics

## Live API Testing

### Prerequisites
1. **AWS Credentials**: Configure AWS credentials with appropriate permissions
2. **CloudWAN Resources**: Access to CloudWAN resources for testing
3. **Test Environment**: Dedicated test environment (not production)

### Setup
```bash
# Configure AWS credentials
aws configure --profile cloudwan-test

# Set environment variables
export AWS_PROFILE=cloudwan-test
export AWS_DEFAULT_REGION=us-east-1

# Verify access
aws networkmanager describe-global-networks --profile cloudwan-test
```

### Running Live Tests
```bash
# Run all live tests
uv run pytest tests/live/ -m live -v

# Run specific live test category
uv run pytest tests/live/test_live_core_networks.py -m live

# Run with detailed output
uv run pytest tests/live/ -m live -v -s
```

### Live Test Guidelines
1. **Non-Destructive**: Live tests should not create/modify/delete resources
2. **Idempotent**: Tests should produce same results when run multiple times
3. **Isolated**: Tests should not depend on specific resource states
4. **Documented**: Clearly document required permissions and setup

## Troubleshooting

### Common Issues

#### 1. Import Errors
```bash
# Error: ModuleNotFoundError: No module named 'awslabs'
# Solution: Ensure package is installed in development mode
uv sync --dev
```

#### 2. AWS Credential Issues
```bash
# Error: NoCredentialsError
# Solutions:
export AWS_PROFILE=your-profile
# OR
aws configure
# OR skip live tests
uv run pytest -m "not live"
```

#### 3. Async Test Issues
```bash
# Error: RuntimeWarning: coroutine was never awaited
# Solution: Add @pytest.mark.asyncio decorator
@pytest.mark.asyncio
async def test_async_function():
    pass
```

#### 4. Coverage Issues
```bash
# Low coverage warnings
# Solution: Add missing test cases or exclude non-testable code
# Exclude lines with: # pragma: no cover
```

### Debug Commands
```bash
# Run tests with debug output
uv run pytest -v -s --tb=long

# Run single test with maximum verbosity
uv run pytest tests/unit/test_models.py::TestContentItemModel::test_content_item_valid_creation -vv -s

# Check test discovery
uv run pytest --collect-only

# Profile test execution
uv run pytest --durations=10
```

## Continuous Integration

### GitHub Actions Integration
```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install uv
          uv sync --dev
      - name: Run tests
        run: |
          uv run pytest --cov=awslabs --cov-report=xml -m "not live"
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest-unit
        name: pytest-unit
        entry: uv run pytest tests/unit/ -x
        language: system
        pass_filenames: false
```

## Contributing

### Adding New Tests
1. **Follow naming conventions**: `test_*.py` for files, `test_*` for functions
2. **Use appropriate markers**: Add `@pytest.mark.unit` or `@pytest.mark.integration`
3. **Follow AWS Labs patterns**: Use standard response formats and error handling
4. **Add documentation**: Include docstrings and comments for complex tests
5. **Maintain coverage**: Ensure new code is covered by tests

### Test Review Checklist
- [ ] Test files follow AWS Labs naming conventions
- [ ] Tests use appropriate markers (`@pytest.mark.unit`, etc.)
- [ ] AWS services are properly mocked (no live API calls in unit/integration tests)
- [ ] Error handling is tested with AWS Labs standard formats
- [ ] Tests are isolated and don't depend on external state
- [ ] Coverage targets are maintained (90%+ overall)
- [ ] Documentation is updated for new test patterns

## Support

For questions or issues with the test suite:

1. **Check this documentation** for common patterns and solutions
2. **Review existing tests** for similar patterns and examples
3. **Run tests with verbose output** to debug specific issues
4. **Check AWS Labs MCP standards** for compliance requirements

## References

- [AWS Labs MCP Standards](https://awslabs.github.io/mcp/)
- [pytest Documentation](https://docs.pytest.org/)
- [moto Documentation](https://docs.getmoto.org/)
- [AWS CloudWAN API Reference](https://docs.aws.amazon.com/networkmanager/latest/cloudwan/)