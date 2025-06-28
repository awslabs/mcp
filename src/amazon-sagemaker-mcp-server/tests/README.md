# Amazon SageMaker MCP Server Tests

This directory contains comprehensive unit tests for the Amazon SageMaker MCP Server.

## Test Structure

### Test Files

- **`test_server.py`** - Tests for the main server functionality including:
  - Server initialization and structure
  - Command line argument parsing
  - Notebook instance management tools
  - Domain management tools
  - Endpoint management tools
  - Error handling
  - Main function and entry point

- **`test_aws_client.py`** - Tests for AWS client utilities including:
  - AWS configuration creation
  - Session management with different credential types
  - Client creation for SageMaker and SageMaker Runtime
  - Credential validation
  - Utility functions for region and account ID retrieval
  - Error handling scenarios

- **`test_permissions.py`** - Tests for permission management including:
  - Permission checking functions
  - Environment variable handling
  - Write access and sensitive data access controls
  - Permission requirement enforcement
  - Permission summary functionality
  - Custom PermissionError exception

- **`test_utils.py`** - Integration tests for utils modules including:
  - Cross-module integration testing
  - Real-world usage scenarios
  - Configuration precedence testing
  - Module structure validation

- **`conftest.py`** - Test configuration and fixtures including:
  - Environment cleanup fixtures
  - Mock client fixtures
  - Permission control fixtures
  - AWS credential fixtures

## Test Coverage

The test suite provides comprehensive coverage of:

- **Server functionality**: 89% coverage of server.py
- **AWS client utilities**: 100% coverage of aws_client.py
- **Permission management**: 100% coverage of permissions.py
- **Overall coverage**: 92% of the codebase

## Running Tests

### Using pytest directly
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_server.py -v

# Run with coverage
python -m pytest tests/ --cov=awslabs.amazon_sagemaker_mcp_server --cov-report=term-missing
```

### Using the test runner script
```bash
# Run all tests
python run_tests.py

# Run specific test type
python run_tests.py --type server
python run_tests.py --type utils

# Run with verbose output
python run_tests.py --verbose

# Run with coverage
python run_tests.py --coverage
```

### Using Make
```bash
# Run all tests
make test

# Run with verbose output
make test-verbose

# Run with coverage
make test-coverage

# Run specific test types
make test-server
make test-utils
```

## Test Categories

### Unit Tests
- Test individual functions and methods in isolation
- Use mocking to avoid external dependencies
- Focus on specific functionality and edge cases

### Integration Tests
- Test interaction between different modules
- Verify configuration precedence and environment handling
- Test real-world usage scenarios

### Error Handling Tests
- Test various error conditions and exceptions
- Verify proper error messages and responses
- Test permission enforcement

### Mock Usage
The tests extensively use mocking to:
- Avoid making actual AWS API calls
- Control test environment and responses
- Test error conditions safely
- Ensure tests run quickly and reliably

## Key Testing Patterns

### Environment Management
Tests use fixtures to:
- Clean up environment variables before and after tests
- Set up specific test conditions
- Avoid test interference

### Async Testing
Server tools are async functions, so tests use:
- `@pytest.mark.asyncio` decorator
- `async def` test functions
- Proper async/await patterns

### Permission Testing
Tests verify:
- Default read-only behavior
- Write access controls
- Sensitive data access controls
- Proper error messages for permission violations

### AWS Client Testing
Tests verify:
- Proper session creation with different credential types
- Client configuration and initialization
- Error handling for credential issues
- Region and account ID utilities

## Test Data and Fixtures

### Mock Responses
Tests use realistic mock responses that match AWS API structures:
- SageMaker notebook instances
- SageMaker endpoints
- SageMaker domains
- Error responses

### Fixtures
Common test fixtures provide:
- Clean environment setup
- Mock AWS clients
- Permission controls
- Credential configurations

## Continuous Integration

The test suite is designed to:
- Run quickly (< 1 second)
- Be reliable and deterministic
- Provide clear failure messages
- Work in CI/CD environments
- Not require actual AWS credentials or resources

## Contributing

When adding new functionality:
1. Add corresponding unit tests
2. Maintain or improve test coverage
3. Follow existing test patterns
4. Update this README if needed
5. Ensure all tests pass before submitting
