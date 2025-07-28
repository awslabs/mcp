"""Tests for the Boto3ToolRegistry class."""

import pytest
from awslabs.aws_finops_mcp_server.boto3_tools import Boto3ToolRegistry
from awslabs.aws_finops_mcp_server.models import Boto3ToolInfo
from unittest.mock import MagicMock, patch


@pytest.mark.unit
def test_register_tool():
    """Test registering a tool in the registry."""
    # Create a registry
    registry = Boto3ToolRegistry()

    # Create a Boto3ToolInfo object
    tool_info = Boto3ToolInfo(
        service='test_service', method='test_method', docstring='Test docstring'
    )

    # Register a tool
    registry.register_tool(tool_info)

    # Verify the tool was registered with the shortened name
    # Since this is not in our mapping, it will use the original name
    assert 'test_service_test_method' in registry.tools
    assert registry.tools['test_service_test_method'].service == 'test_service'
    assert registry.tools['test_service_test_method'].method == 'test_method'
    assert registry.tools['test_service_test_method'].docstring == 'Test docstring'


@pytest.mark.unit
def test_register_all_tools(registry):
    """Test registering all tools from boto3_docstrings."""
    # Verify tools were registered
    assert len(registry.tools) > 0

    # Check for specific tools we know should be there with shortened names
    assert 'ce_get_cost_usage' in registry.tools
    assert 'co_get_ec2_recs' in registry.tools
    assert 'coh_get_rec' in registry.tools


@pytest.mark.unit
@pytest.mark.asyncio
@patch('boto3.client')
async def test_generic_handler_service_name_mapping(mock_boto3_client):
    """Test that the generic_handler maps service names correctly."""
    # Create a registry
    registry = Boto3ToolRegistry()

    # Create a Boto3ToolInfo object
    tool_info = Boto3ToolInfo(
        service='cost_explorer', method='test_method', docstring='Test docstring'
    )

    # Register a tool
    registry.register_tool(tool_info)

    # Get the shortened tool name
    tool_name = next(
        name
        for name, info in registry.tools.items()
        if info.service == 'cost_explorer' and info.method == 'test_method'
    )

    # Mock the boto3 client and its method
    mock_client = MagicMock()
    mock_boto3_client.return_value = mock_client
    mock_client.test_method.return_value = {'result': 'success'}

    # Call the generic_handler with the shortened name
    await registry.generic_handler(tool_name)

    # Verify the service name was mapped correctly
    mock_boto3_client.assert_called_once_with('ce', region_name='us-east-1')


@pytest.mark.unit
@pytest.mark.asyncio
@patch('boto3.client')
async def test_generic_handler_parameter_transformation(mock_boto3_client):
    """Test that the generic_handler transforms parameters for cost_explorer."""
    # Create a registry
    registry = Boto3ToolRegistry()

    # Create a Boto3ToolInfo object
    tool_info = Boto3ToolInfo(
        service='cost_explorer', method='test_method', docstring='Test docstring'
    )

    # Register a tool
    registry.register_tool(tool_info)

    # Get the shortened tool name
    tool_name = next(
        name
        for name, info in registry.tools.items()
        if info.service == 'cost_explorer' and info.method == 'test_method'
    )

    # Mock the boto3 client and its method
    mock_client = MagicMock()
    mock_boto3_client.return_value = mock_client
    mock_client.test_method.return_value = {'result': 'success'}

    # Call the generic_handler with camelCase parameters
    await registry.generic_handler(
        tool_name,
        timePeriod={'start': '2023-01-01', 'end': '2023-01-31'},
        granularity='MONTHLY',
    )

    # Verify the parameters were transformed to PascalCase
    mock_client.test_method.assert_called_once_with(
        TimePeriod={'start': '2023-01-01', 'end': '2023-01-31'}, Granularity='MONTHLY'
    )


@pytest.mark.unit
@pytest.mark.asyncio
@patch('boto3.client')
async def test_generic_handler_error_handling(mock_boto3_client):
    """Test that the generic_handler handles errors properly."""
    # Create a registry
    registry = Boto3ToolRegistry()

    # Create a Boto3ToolInfo object
    tool_info = Boto3ToolInfo(
        service='test_service', method='test_method', docstring='Test docstring'
    )

    # Register a tool
    registry.register_tool(tool_info)

    # Mock the boto3 client and its method to raise an exception
    mock_client = MagicMock()
    mock_boto3_client.return_value = mock_client
    mock_client.test_method.side_effect = Exception('Test error')

    # Call the generic_handler
    result = await registry.generic_handler('test_service_test_method')

    # Verify the error was handled
    assert 'error' in result
    assert result['error'] == 'Test error'


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generic_handler_tool_not_found():
    """Test that the generic_handler handles non-existent tools."""
    # Create a registry
    registry = Boto3ToolRegistry()

    # Call the generic_handler with a non-existent tool
    result = await registry.generic_handler('non_existent_tool')

    # Verify the error was handled
    assert 'error' in result
    assert result['error'] == 'Tool non_existent_tool not found in registry'
