# AWS IoT SiteWise MCP Server Development Guide

## Overview

This document provides comprehensive guidance for developing and extending the AWS IoT SiteWise MCP server. The server is built using Python and the FastMCP framework, providing a complete interface to AWS IoT SiteWise functionality.

## Architecture

### Project Structure

```
awslabs/aws_iot_sitewise_mcp_server/
├── server.py                    # Main MCP server entry point
├── utils.py                     # Utility functions
├── tools/                       # MCP tools organized by functionality
│   ├── sitewise_assets.py       # Asset management tools
│   ├── sitewise_asset_models.py # Asset model management tools
│   ├── sitewise_data.py         # Data ingestion and retrieval tools
│   ├── sitewise_gateways.py     # Gateway and time series tools
│   └── sitewise_access.py       # Access control and configuration tools
├── prompts/                     # Intelligent prompts for common scenarios
│   ├── asset_hierarchy.py       # Asset hierarchy visualization
│   ├── data_ingestion.py        # Data ingestion guidance
│   └── dashboard_setup.py       # Dashboard setup assistance
└── __init__.py
```

### Tool Organization

Tools are organized into logical modules based on AWS IoT SiteWise functionality:

1. **Assets** (`sitewise_assets.py`): Core asset lifecycle management
2. **Asset Models** (`sitewise_asset_models.py`): Asset model definitions and management
3. **Data** (`sitewise_data.py`): Data ingestion, retrieval, and analytics
4. **Gateways** (`sitewise_gateways.py`): Edge gateway and time series management
5. **Access** (`sitewise_access.py`): Security, access control, and configuration

## Development Setup

### Prerequisites

1. **Python 3.10+**: Required for development and testing
2. **uv package manager**: For dependency management and virtual environments
3. **AWS Credentials**: Configure with IoT SiteWise permissions

### Testing with MCP Clients During Development

When developing new tools or features, you can test them with MCP clients:

#### Using UVX (Recommended)
After installing with `uv tool install .`, configure your MCP client:

```json
{
  "mcpServers": {
    "aws-iot-sitewise-dev": {
      "command": "uvx",
      "args": ["awslabs.aws-iot-sitewise-mcp-server"],
      "env": {
        "AWS_REGION": "us-west-2",
        "AWS_PROFILE": "your-dev-profile",
        "FASTMCP_LOG_LEVEL": "DEBUG"
      },
      "transportType": "stdio"
    }
  }
}
```

#### Hot Reloading During Development
For development with hot reloading after code changes:

1. **Reinstall after changes**:
   ```bash
   uv tool install . --force
   ```

2. **Or use development mode with direct execution**:
   ```json
   {
     "mcpServers": {
       "aws-iot-sitewise-dev": {
         "command": "uv",
         "args": [
           "--directory",
           "/path/to/your/project",
           "run",
           "python",
           "-m",
           "awslabs.aws_iot_sitewise_mcp_server.server"
         ],
         "env": {
           "AWS_REGION": "us-west-2",
           "AWS_PROFILE": "your-dev-profile",
           "FASTMCP_LOG_LEVEL": "DEBUG"
         },
         "transportType": "stdio"
       }
     }
   }
   ```

### Local Development

#### Option 1: UVX Installation (Recommended for MCP Client Testing)

1. **Clone Repository**:
   ```bash
   git clone https://github.com/awslabs/mcp.git
   cd src/aws-iot-sitewise-mcp-server
   ```

2. **Install as UV Tool**:
   ```bash
   # Install as a uv tool (makes it available globally via uvx)
   uv tool install .

   # Test the installation
   uvx awslabs.aws-iot-sitewise-mcp-server --help
   ```

3. **For Development Work, Also Install Dev Dependencies**:
   ```bash
   # Install development dependencies
   uv sync --group dev
   ```

4. **Run Tests**:
   ```bash
   uv run --frozen pytest --cov --cov-branch --cov-report=term-missing
   ```

5. **Format Code**:
   ```bash
   flake8
   ```

#### Option 2: Traditional UV Development Setup

1. **Clone Repository**:
    ```bash
   git clone https://github.com/awslabs/mcp.git
   cd src/aws-iot-sitewise-mcp-server
   ```

2. **Create Virtual Environment and Install Dependencies**:
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv pip install -e ".[dev]"
   ```

3. **Run Tests**:
   ```bash
   pytest
   ```

4. **Format Code**:
   ```bash
   flake8
   ```

## Adding New Tools

### Tool Development Pattern

All tools follow a consistent pattern for reliability and maintainability:

```python
from awslabs.aws_iot_sitewise_mcp_server.client import create_sitewise_client

def tool_function(
    required_param: str,
    region: str = "us-east-1",
    optional_param: Optional[str] = None
) -> Dict[str, Any]:
    """
    Tool description with clear purpose and usage.

    Args:
        required_param: Description of required parameter
        region: AWS region (default: us-east-1)
        optional_param: Description of optional parameter

    Returns:
        Dictionary containing operation response
    """
    try:
        client = create_sitewise_client(region)

        params = {'requiredParam': required_param}
        if optional_param:
            params['optionalParam'] = optional_param

        response = client.api_operation(**params)

        return {
            'success': True,
            'data': response['relevantData'],
            # Include other relevant response fields
        }

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code']
        }

# Create MCP tool
tool_name_tool = Tool.from_function(
    fn=tool_function,
    name="sitewise_tool_name",
    description="Clear description of what the tool does and when to use it."
)
```

### Key Principles

1. **Consistent Error Handling**: Always catch `ClientError` and return structured error responses
2. **Clear Documentation**: Include comprehensive docstrings with parameter descriptions
3. **Flexible Parameters**: Support optional parameters with sensible defaults
4. **Structured Responses**: Return consistent response format with success/error indicators
5. **Regional Support**: Always include region parameter with default value

### Adding a New Tool

1. **Choose the Right Module**: Add the tool to the appropriate module based on functionality
2. **Implement the Function**: Follow the standard pattern above
3. **Create the Tool**: Use `Tool.from_function` to create the MCP tool
4. **Register the Tool**: Add to the appropriate tool list in `server.py`
5. **Write Tests**: Add comprehensive tests in the `test/` directory
6. **Update Documentation**: Add the tool to the README.md tools reference

### Example: Adding a New Asset Property Tool

```python
# In sitewise_assets.py
def update_asset_property(
    asset_id: str,
    property_id: str,
    property_alias: Optional[str] = None,
    property_notification_state: str = "ENABLED",
    region: str = "us-east-1"
) -> Dict[str, Any]:
    """
    Update an asset property configuration.

    Args:
        asset_id: The ID of the asset
        property_id: The ID of the property to update
        property_alias: The alias for the property
        property_notification_state: The notification state (ENABLED, DISABLED)
        region: AWS region (default: us-east-1)

    Returns:
        Dictionary containing update response
    """
    try:
        client = create_sitewise_client(region)

        params = {
            'assetId': asset_id,
            'propertyId': property_id,
            'propertyNotificationState': property_notification_state
        }

        if property_alias:
            params['propertyAlias'] = property_alias

        client.update_asset_property(**params)
        return {'success': True, 'message': 'Asset property updated successfully'}

    except ClientError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.response['Error']['Code']
        }

# Create the tool
update_asset_property_tool = Tool.from_function(
    fn=update_asset_property,
    name="sitewise_update_asset_property",
    description="Update an asset property's configuration including alias and notification settings."
)
```

## Adding New Prompts

### Prompt Development Pattern

Prompts provide intelligent guidance for complex IoT SiteWise scenarios:

```python
def scenario_prompt(param1: str, param2: str) -> Prompt:
    """
    Generate guidance for a specific IoT SiteWise scenario.

    Args:
        param1: Description of first parameter
        param2: Description of second parameter

    Returns:
        Prompt for scenario guidance
    """
    return Prompt(
        messages=[
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": f"""
You are an AWS IoT SiteWise expert helping with {scenario description}.

Context:
- Parameter 1: {param1}
- Parameter 2: {param2}

Please provide step-by-step guidance including:

1. **Analysis Phase**:
   - Use relevant sitewise tools to gather information
   - Analyze current state and requirements

2. **Planning Phase**:
   - Design approach and architecture
   - Identify required resources and configurations

3. **Implementation Phase**:
   - Provide specific tool calls and configurations
   - Include error handling and validation steps

4. **Validation Phase**:
   - Test and verify the implementation
   - Provide troubleshooting guidance

Format your response with clear sections, specific tool calls, and actionable recommendations.
                    """
                }
            }
        ]
    )
```

### Prompt Best Practices

1. **Clear Context**: Provide specific context and parameters
2. **Structured Guidance**: Break down complex scenarios into manageable steps
3. **Tool Integration**: Reference specific MCP tools to use
4. **Actionable Output**: Provide concrete steps and configurations
5. **Error Handling**: Include troubleshooting and validation steps

## Testing

### Test Structure

Tests are organized to match the tool structure:

```
test/
├── test_sitewise_assets.py       # Asset management tool tests
├── test_sitewise_asset_models.py # Asset model tool tests
├── test_sitewise_data.py         # Data operation tool tests
├── test_sitewise_gateways.py     # Gateway tool tests
└── test_sitewise_access.py       # Access control tool tests
```

### Test Patterns

1. **Mock AWS Clients**: Use `@patch` to mock boto3 clients
2. **Test Success Cases**: Verify correct responses and client calls
3. **Test Error Cases**: Verify proper error handling
4. **Test Parameter Validation**: Ensure parameters are passed correctly

### Example Test

```python
@patch('awslabs.aws_iot_sitewise_mcp_server.tools.sitewise_assets.create_sitewise_client')
def test_create_asset_success(self, mock_boto_client):
    """Test successful asset creation."""
    # Mock setup
    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    mock_client.create_asset.return_value = {
        'assetId': 'test-asset-123',
        'assetArn': 'arn:aws:iotsitewise:us-east-1:123456789012:asset/test-asset-123',
        'assetStatus': {'state': 'CREATING'}
    }

    # Function call
    result = create_asset(
        asset_name="Test Asset",
        asset_model_id="test-model-456"
    )

    # Assertions
    assert result['success'] is True
    assert result['asset_id'] == 'test-asset-123'
    mock_client.create_asset.assert_called_once_with(
        assetName="Test Asset",
        assetModelId="test-model-456"
    )
```

## Code Quality

### Formatting and Linting

The project uses several tools to maintain code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting and style checking
- **mypy**: Static type checking

Run all checks:
```bash
black awslabs test        # Format code
isort awslabs test        # Sort imports
flake8 awslabs test       # Lint code
mypy awslabs              # Type checking
pytest                    # Run tests
```

### Type Hints

All functions should include comprehensive type hints:

```python
from typing import Dict, List, Optional, Any

def example_function(
    required_str: str,
    optional_list: Optional[List[str]] = None,
    region: str = "us-east-1"
) -> Dict[str, Any]:
    """Function with proper type hints."""
    pass
```

### Documentation Standards

1. **Docstrings**: Use Google-style docstrings for all functions
2. **Parameter Documentation**: Document all parameters with types and descriptions
3. **Return Documentation**: Clearly describe return values and structure
4. **Examples**: Include usage examples for complex functions

## Deployment

### Package Building

The project uses uv for package management and building:

```bash
# Build distribution packages
uv build

# Install locally in development mode
uv pip install -e .

# Install from PyPI (if published)
uv pip install awslabs.aws-iot-sitewise-mcp-server
```


## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are in `pyproject.toml`
2. **AWS Permissions**: Verify IAM permissions for IoT SiteWise operations
3. **Region Issues**: Check AWS region configuration and availability
4. **Tool Registration**: Ensure new tools are added to `server.py`

### Debugging

1. **Enable Logging**: Add logging to tools for debugging
2. **Test Isolation**: Use mocks to isolate AWS API calls during testing
3. **Error Messages**: Provide clear error messages with context
4. **Validation**: Add parameter validation for better error handling

### Performance Considerations

1. **Batch Operations**: Use batch APIs when available for better performance
2. **Pagination**: Handle pagination properly for large result sets
3. **Caching**: Consider caching for frequently accessed data
4. **Rate Limiting**: Implement proper retry logic for rate-limited APIs

## Contributing

### Pull Request Process

1. **Create Feature Branch**: Branch from main for new features
2. **Implement Changes**: Follow development patterns and standards
3. **Add Tests**: Ensure comprehensive test coverage
4. **Update Documentation**: Update README and relevant documentation
5. **Code Review**: Submit PR for review and feedback

### Code Review Checklist

- [ ] Follows established patterns and conventions
- [ ] Includes comprehensive error handling
- [ ] Has appropriate test coverage
- [ ] Documentation is updated
- [ ] Type hints are complete
- [ ] Code is formatted and linted

## Future Enhancements

### Planned Features

1. **Advanced Analytics**: Add support for IoT Analytics integration
2. **Alarm Management**: Comprehensive alarm configuration and management
3. **Data Quality**: Enhanced data validation and quality monitoring
4. **Performance Optimization**: Caching and batch operation improvements
5. **Integration Patterns**: Common integration patterns and templates

### Extension Points

The architecture supports easy extension in several areas:

1. **New AWS Services**: Add support for related AWS services
2. **Custom Prompts**: Create domain-specific guidance prompts
3. **Validation Tools**: Add data validation and quality checking tools
4. **Monitoring Tools**: Enhanced monitoring and alerting capabilities
5. **Integration Helpers**: Tools for common integration patterns

## Resources

### AWS IoT SiteWise Documentation

- [AWS IoT SiteWise User Guide](https://docs.aws.amazon.com/iot-sitewise/latest/userguide/)
- [AWS IoT SiteWise API Reference](https://docs.aws.amazon.com/iot-sitewise/latest/APIReference/)
- [AWS IoT SiteWise Best Practices](https://docs.aws.amazon.com/iot-sitewise/latest/userguide/best-practices.html)

### Development Resources

- [FastMCP Documentation](https://github.com/modelcontextprotocol/python-sdk)
- [uv Documentation](https://github.com/astral-sh/uv)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)

### Testing Resources

- [pytest Documentation](https://docs.pytest.org/)
- [unittest.mock Guide](https://docs.python.org/3/library/unittest.mock.html)
