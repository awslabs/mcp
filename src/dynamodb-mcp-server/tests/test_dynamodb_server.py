import pytest
import pytest_asyncio
from awslabs.dynamodb_mcp_server.server import (
    dynamodb_data_modeling,
)


@pytest_asyncio.fixture
async def aws_credentials():
    """Mocked AWS Credentials for moto."""
    import os

    os.environ['AWS_DEFAULT_REGION'] = 'us-west-2'


@pytest.mark.asyncio
async def test_dynamodb_data_modeling():
    """Test the dynamodb_data_modeling tool directly."""
    result = await dynamodb_data_modeling()

    assert isinstance(result, str), 'Expected string response'
    assert len(result) > 1000, 'Expected substantial content (>1000 characters)'

    expected_sections = [
        'DynamoDB Data Modeling Expert System Prompt',
        'Access Patterns Analysis',
        'Enhanced Aggregate Analysis',
        'Important DynamoDB Context',
    ]

    for section in expected_sections:
        assert section in result, f"Expected section '{section}' not found in content"


@pytest.mark.asyncio
async def test_dynamodb_data_modeling_mcp_integration():
    """Test the dynamodb_data_modeling tool through MCP client."""
    from awslabs.dynamodb_mcp_server.server import app

    # Verify tool is registered in the MCP server
    tools = await app.list_tools()
    tool_names = [tool.name for tool in tools]
    assert 'dynamodb_data_modeling' in tool_names, (
        'dynamodb_data_modeling tool not found in MCP server'
    )

    # Get tool metadata
    modeling_tool = next((tool for tool in tools if tool.name == 'dynamodb_data_modeling'), None)
    assert modeling_tool is not None, 'dynamodb_data_modeling tool not found'

    assert modeling_tool.description is not None
    assert 'DynamoDB' in modeling_tool.description
    assert 'data modeling' in modeling_tool.description.lower()
