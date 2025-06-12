"""Tests for the describe service updates tool."""

import pytest
from awslabs.elasticache_mcp_server.tools.misc.describe_service_updates import (
    describe_service_updates,
)
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_describe_service_updates_basic():
    """Test basic describe service updates functionality."""
    mock_client = MagicMock()
    mock_client.describe_service_updates.return_value = {
        'ServiceUpdates': [
            {
                'ServiceUpdateName': 'update-1',
                'ServiceUpdateStatus': 'available',
                'ServiceUpdateDescription': 'Test update 1',
            },
            {
                'ServiceUpdateName': 'update-2',
                'ServiceUpdateStatus': 'complete',
                'ServiceUpdateDescription': 'Test update 2',
            },
        ]
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_service_updates()
        mock_client.describe_service_updates.assert_called_once_with()
        assert 'ServiceUpdates' in result
        assert len(result['ServiceUpdates']) == 2
        statuses = {update['ServiceUpdateStatus'] for update in result['ServiceUpdates']}
        assert statuses == {'available', 'complete'}


@pytest.mark.asyncio
async def test_describe_service_updates_with_name():
    """Test describe service updates with name filter."""
    mock_client = MagicMock()
    mock_client.describe_service_updates.return_value = {
        'ServiceUpdates': [
            {
                'ServiceUpdateName': 'update-1',
                'ServiceUpdateStatus': 'available',
                'ServiceUpdateDescription': 'Test update 1',
            }
        ]
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_service_updates(service_update_name='update-1')
        mock_client.describe_service_updates.assert_called_once_with(ServiceUpdateName='update-1')
        assert result['ServiceUpdates'][0]['ServiceUpdateName'] == 'update-1'


@pytest.mark.asyncio
async def test_describe_service_updates_with_status():
    """Test describe service updates with status filter."""
    mock_client = MagicMock()
    mock_client.describe_service_updates.return_value = {
        'ServiceUpdates': [
            {
                'ServiceUpdateName': 'update-1',
                'ServiceUpdateStatus': 'available',
                'ServiceUpdateDescription': 'Test update 1',
            }
        ]
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_service_updates(service_update_status=['available'])
        mock_client.describe_service_updates.assert_called_once_with(
            ServiceUpdateStatus=['available']
        )
        assert result['ServiceUpdates'][0]['ServiceUpdateStatus'] == 'available'


@pytest.mark.asyncio
async def test_describe_service_updates_with_pagination():
    """Test describe service updates with pagination parameters."""
    mock_client = MagicMock()
    mock_client.describe_service_updates.return_value = {
        'ServiceUpdates': [
            {
                'ServiceUpdateName': 'update-1',
                'ServiceUpdateStatus': 'available',
                'ServiceUpdateDescription': 'Test update 1',
            }
        ],
        'NextToken': 'next-page',
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_service_updates(
            starting_token='current-page', page_size=20, max_items=50
        )
        mock_client.describe_service_updates.assert_called_once_with(
            Marker='current-page', MaxRecords=20, MaxItems=50
        )
        assert 'NextToken' in result
        assert result['NextToken'] == 'next-page'


@pytest.mark.asyncio
async def test_describe_service_updates_invalid_parameter():
    """Test describe service updates with invalid parameter."""
    mock_client = MagicMock()
    exception_class = 'InvalidParameterValueException'
    error_message = 'Invalid parameter value'
    mock_exception = type(exception_class, (Exception,), {})
    setattr(mock_client.exceptions, exception_class, mock_exception)
    mock_client.describe_service_updates.side_effect = mock_exception(error_message)

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_service_updates(service_update_status=['invalid-status'])
        assert 'error' in result
        assert error_message in result['error']


@pytest.mark.asyncio
async def test_describe_service_updates_invalid_parameter_combination():
    """Test describe service updates with invalid parameter combination."""
    mock_client = MagicMock()
    exception_class = 'InvalidParameterCombinationException'
    error_message = 'Invalid parameter combination'
    mock_exception = type(exception_class, (Exception,), {})
    setattr(mock_client.exceptions, exception_class, mock_exception)
    mock_client.describe_service_updates.side_effect = mock_exception(error_message)

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_service_updates(
            service_update_name='update-1', service_update_status=['available']
        )
        assert 'error' in result
        assert error_message in result['error']


@pytest.mark.asyncio
async def test_describe_service_updates_empty_response():
    """Test describe service updates with empty response."""
    mock_client = MagicMock()
    mock_client.describe_service_updates.return_value = {'ServiceUpdates': []}

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_service_updates()
        mock_client.describe_service_updates.assert_called_once_with()
        assert 'ServiceUpdates' in result
        assert len(result['ServiceUpdates']) == 0


@pytest.mark.asyncio
async def test_describe_service_updates_multiple_filters():
    """Test describe service updates with multiple filters."""
    mock_client = MagicMock()
    mock_client.describe_service_updates.return_value = {
        'ServiceUpdates': [
            {
                'ServiceUpdateName': 'update-1',
                'ServiceUpdateStatus': 'available',
                'ServiceUpdateDescription': 'Test update 1',
            }
        ]
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_service_updates(
            service_update_name='update-1', service_update_status=['available'], page_size=10
        )
        mock_client.describe_service_updates.assert_called_once_with(
            ServiceUpdateName='update-1', ServiceUpdateStatus=['available'], MaxRecords=10
        )
        assert len(result['ServiceUpdates']) == 1
        assert result['ServiceUpdates'][0]['ServiceUpdateName'] == 'update-1'
        assert result['ServiceUpdates'][0]['ServiceUpdateStatus'] == 'available'


@pytest.mark.asyncio
async def test_describe_service_updates_pagination_edge_cases():
    """Test describe service updates with edge cases for pagination parameters."""
    mock_client = MagicMock()
    mock_client.describe_service_updates.return_value = {
        'ServiceUpdates': [
            {
                'ServiceUpdateName': 'update-1',
                'ServiceUpdateStatus': 'available',
                'ServiceUpdateDescription': 'Test update 1',
            }
        ]
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        # Test with zero page size
        await describe_service_updates(page_size=0)
        mock_client.describe_service_updates.assert_called_with()

        # Test with negative page size
        await describe_service_updates(page_size=-1)
        mock_client.describe_service_updates.assert_called_with(MaxRecords=-1)

        # Test with zero max items
        await describe_service_updates(max_items=0)
        mock_client.describe_service_updates.assert_called_with()

        # Test with negative max items
        await describe_service_updates(max_items=-1)
        mock_client.describe_service_updates.assert_called_with(MaxItems=-1)
