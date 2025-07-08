"""Tests for the Boto3ToolRegistry class."""

import pytest
from awslabs.aws_finops_mcp_server.boto3_tools import Boto3ToolRegistry
from unittest.mock import MagicMock, patch


@pytest.mark.unit
def test_register_tool():
    """Test registering a tool in the registry."""
    # Create a registry
    registry = Boto3ToolRegistry()

    # Register a tool
    registry.register_tool('test_service', 'test_method', 'Test docstring')

    # Verify the tool was registered
    assert 'test_service_test_method' in registry.tools
    assert registry.tools['test_service_test_method']['service'] == 'test_service'
    assert registry.tools['test_service_test_method']['method'] == 'test_method'
    assert registry.tools['test_service_test_method']['docstring'] == 'Test docstring'


@pytest.mark.unit
def test_register_all_tools(registry):
    """Test registering all tools from boto3_docstrings."""
    # Verify tools were registered
    assert len(registry.tools) > 0

    # Check for specific tools we know should be there
    assert 'cost_explorer_get_cost_and_usage' in registry.tools
    assert 'compute_optimizer_get_ec2_instance_recommendations' in registry.tools
    assert 'cost_optimization_hub_get_recommendation' in registry.tools


@pytest.mark.unit
@pytest.mark.asyncio
@patch('boto3.client')
async def test_generic_handler_service_name_mapping(mock_boto3_client):
    """Test that the generic_handler maps service names correctly."""
    # Create a registry
    registry = Boto3ToolRegistry()

    # Register a tool
    registry.register_tool('cost_explorer', 'test_method', 'Test docstring')

    # Mock the boto3 client and its method
    mock_client = MagicMock()
    mock_boto3_client.return_value = mock_client
    mock_client.test_method.return_value = {'result': 'success'}

    # Call the generic_handler
    await registry.generic_handler('cost_explorer_test_method')

    # Verify the service name was mapped correctly
    mock_boto3_client.assert_called_once_with('ce', region_name='us-east-1')


@pytest.mark.unit
@pytest.mark.asyncio
@patch('boto3.client')
async def test_generic_handler_parameter_transformation(mock_boto3_client):
    """Test that the generic_handler transforms parameters for cost_explorer."""
    # Create a registry
    registry = Boto3ToolRegistry()

    # Register a tool
    registry.register_tool('cost_explorer', 'test_method', 'Test docstring')

    # Mock the boto3 client and its method
    mock_client = MagicMock()
    mock_boto3_client.return_value = mock_client
    mock_client.test_method.return_value = {'result': 'success'}

    # Call the generic_handler with camelCase parameters
    await registry.generic_handler(
        'cost_explorer_test_method',
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

    # Register a tool
    registry.register_tool('test_service', 'test_method', 'Test docstring')

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
