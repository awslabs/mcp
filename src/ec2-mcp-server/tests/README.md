# AWS EC2 MCP Server - Testing Guide

This directory contains comprehensive test suites for the AWS EC2 MCP Server, following the established patterns from the MCP ecosystem.

## Test Structure

```
tests/
├── README.md                    # This file
├── conftest.py                  # Global test fixtures and configurations
└── unit/                        # Unit tests
    ├── conftest.py              # Unit test specific fixtures
    ├── test_aws_client.py       # AWS client management tests
    ├── test_errors.py           # Error handling tests
    ├── test_models.py           # Pydantic model tests
    ├── test_server.py           # Server entry point tests
    └── modules/                 # Module-specific tests
        ├── test_instances.py    # Instance management tests
        ├── test_security_groups.py # Security group tests
        └── ...                  # Other module tests
```

## Running Tests

### Quick Start

```bash
# Run all tests with coverage
./run_tests.sh

# Run tests with verbose output
./run_tests.sh --verbose

# Run with custom coverage threshold
./run_tests.sh --coverage-threshold 90

# Skip linting for faster execution
./run_tests.sh --skip-linting

# Show help
./run_tests.sh --help
```

### Manual Test Execution

```bash
# Install dependencies
uv sync --dev

# Run unit tests only
pytest tests/unit/ -v

# Run specific test file
pytest tests/unit/test_server.py -v

# Run specific test function
pytest tests/unit/test_server.py::test_main_entry_point -v

# Run with coverage
pytest tests/unit/ --cov=awslabs.ec2_mcp_server --cov-report=html

# Run linting
ruff check awslabs/ tests/
ruff format --check awslabs/ tests/

# Run type checking
pyright awslabs/
```

## Test Categories

### Unit Tests (`tests/unit/`)

Unit tests focus on testing individual components in isolation using mocks and fixtures.

#### Key Features:
- **AWS Service Mocking**: Comprehensive mocking of boto3 EC2 clients
- **Error Handling**: Tests for all error scenarios and exception types
- **Model Validation**: Pydantic model serialization/deserialization tests
- **Async Testing**: Proper async test utilities and fixtures

#### Test Fixtures Available:

**Global Fixtures** (from `conftest.py`):
- `mock_ec2_client`: Mock boto3 EC2 client with common responses
- `mock_context`: Mock MCP context for testing
- `mock_environment`: Automatic environment variable setup
- `mock_boto3_client`: Patches boto3.client globally

**Data Fixtures**:
- `mock_instance_data`: Sample EC2 instance data
- `mock_security_group_data`: Sample security group data
- `mock_key_pair_data`: Sample key pair data
- `mock_volume_data`: Sample EBS volume data
- `mock_snapshot_data`: Sample snapshot data
- `mock_ami_data`: Sample AMI data
- `mock_vpc_data`: Sample VPC data
- `mock_subnet_data`: Sample subnet data

**Unit Test Utilities** (from `unit/conftest.py`):
- `async_test_utils`: Utilities for async testing
- `event_loop`: Async event loop configuration
- `anyio_backend`: AsyncIO backend configuration

## Writing Tests

### Test Naming Conventions

Follow the established patterns:

```python
class TestSpecificFeature:
    """Test suite for specific feature."""
    
    def test_feature_success(self):
        """Test successful feature operation."""
        pass
    
    def test_feature_with_parameters(self):
        """Test feature with specific parameters."""
        pass
    
    def test_feature_error_handling(self):
        """Test feature error scenarios."""
        pass
```

### Mocking AWS Services

Use the provided fixtures for consistent mocking:

```python
@patch('awslabs.ec2_mcp_server.modules.instances.get_ec2_client')
def test_list_instances(self, mock_get_client, mock_ec2_client):
    """Test instance listing."""
    mock_get_client.return_value = mock_ec2_client
    
    # Configure mock response
    mock_ec2_client.describe_instances.return_value = {
        "Reservations": [{"Instances": [...]}]
    }
    
    # Test your function
    result = list_instances()
    
    # Verify behavior
    assert len(result) > 0
    mock_ec2_client.describe_instances.assert_called_once()
```

### Testing Error Handling

Test both AWS errors and custom exceptions:

```python
from botocore.exceptions import ClientError
from awslabs.ec2_mcp_server.errors import Ec2PermissionError

def test_permission_error_handling(self):
    """Test handling of permission errors."""
    client_error = ClientError(
        error_response={
            'Error': {
                'Code': 'UnauthorizedOperation',
                'Message': 'Access denied'
            }
        },
        operation_name='DescribeInstances'
    )
    
    result = handle_ec2_error(client_error)
    assert isinstance(result, Ec2PermissionError)
```

### Testing Pydantic Models

Test model creation, validation, and serialization:

```python
def test_instance_model_creation(self):
    """Test Instance model creation."""
    instance_data = {
        "InstanceId": "i-123456789",
        "InstanceType": "t2.micro",
        "State": {"Name": "running", "Code": 16},
        "ImageId": "ami-123456789"
    }
    
    instance = Instance(**instance_data)
    
    assert instance.instance_id == "i-123456789"
    assert instance.instance_type == "t2.micro"
    
    # Test serialization
    serialized = instance.dict(by_alias=True)
    assert "InstanceId" in serialized
```

## Coverage Requirements

- **Minimum Coverage**: 80% (configurable via `--coverage-threshold`)
- **Branch Coverage**: Enabled for more thorough testing
- **Coverage Reports**: Generated in HTML and XML formats

### Viewing Coverage

```bash
# Generate and view HTML coverage report
./run_tests.sh
open htmlcov/index.html

# View coverage in terminal
coverage report --show-missing
```

## Test Data and Fixtures

### Mock Data Guidelines

- Use realistic AWS resource IDs and values
- Include both required and optional fields
- Provide consistent test data across fixtures
- Use datetime objects for timestamp fields

### Environment Variables

Tests automatically mock common AWS environment variables:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_DEFAULT_REGION`
- `AWS_REGION`

## Integration Testing (Future)

While not yet implemented, integration tests would:

- Test against real AWS services (with proper credentials)
- Use test-specific AWS resources
- Include cleanup procedures
- Test end-to-end workflows

## Best Practices

1. **Isolation**: Each test should be independent and not rely on other tests
2. **Mocking**: Mock external dependencies (AWS services, network calls)
3. **Assertions**: Use descriptive assertions and test both positive and negative cases
4. **Cleanup**: Use fixtures that automatically clean up resources
5. **Documentation**: Include docstrings explaining what each test verifies

## Debugging Tests

### Common Issues

1. **Import Errors**: Ensure the package is installed in development mode
2. **Mock Issues**: Verify that patches are applied to the correct modules
3. **Async Issues**: Use proper async fixtures and utilities

### Debug Commands

```bash
# Run with detailed output
pytest tests/unit/test_specific.py -v -s

# Run with Python debugger
pytest tests/unit/test_specific.py --pdb

# Run with coverage and show missing lines
pytest tests/unit/ --cov --cov-report=term-missing

# Run only failed tests from last run
pytest --lf
```

## Contributing

When adding new features:

1. Write tests first (TDD approach)
2. Ensure all existing tests still pass
3. Add appropriate test fixtures for new functionality
4. Update this README if adding new test categories
5. Maintain coverage above the minimum threshold

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Pydantic Testing Guide](https://pydantic-docs.helpmanual.io/usage/models/)
- [boto3 Mocking with moto](https://github.com/spulec/moto)