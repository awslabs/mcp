"""Tests for the describe replication groups tool."""

import pytest
from awslabs.elasticache_mcp_server.tools.rg import describe_replication_groups
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_describe_replication_groups_basic():
    """Test basic describe replication groups functionality."""
    mock_client = MagicMock()

    mock_client.describe_replication_groups.return_value = {
        'ReplicationGroups': [
            {'ReplicationGroupId': 'test-rg', 'Description': 'Test replication group'}
        ]
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_replication_groups()

        mock_client.describe_replication_groups.assert_called_once_with()
        assert 'ReplicationGroups' in result
        assert len(result['ReplicationGroups']) == 1
        assert result['ReplicationGroups'][0]['ReplicationGroupId'] == 'test-rg'


@pytest.mark.asyncio
async def test_describe_replication_groups_with_id():
    """Test describe replication groups with specific ID."""
    mock_client = MagicMock()

    mock_client.describe_replication_groups.return_value = {
        'ReplicationGroups': [
            {'ReplicationGroupId': 'specific-rg', 'Description': 'Specific replication group'}
        ]
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_replication_groups(replication_group_id='specific-rg')

        mock_client.describe_replication_groups.assert_called_once_with(
            ReplicationGroupId='specific-rg'
        )
        assert result['ReplicationGroups'][0]['ReplicationGroupId'] == 'specific-rg'


@pytest.mark.asyncio
async def test_describe_replication_groups_with_pagination():
    """Test describe replication groups with pagination parameters."""
    mock_client = MagicMock()

    mock_client.describe_replication_groups.return_value = {
        'ReplicationGroups': [
            {'ReplicationGroupId': 'test-rg-1', 'Description': 'Test replication group 1'}
        ],
        'Marker': 'next-page',
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_replication_groups(max_records=20, marker='current-page')

        mock_client.describe_replication_groups.assert_called_once_with(
            MaxRecords=20, Marker='current-page'
        )
        assert 'Marker' in result
        assert result['Marker'] == 'next-page'


@pytest.mark.asyncio
async def test_describe_replication_groups_not_found():
    """Test describe replication groups when group is not found."""
    mock_client = MagicMock()

    mock_client.exceptions.ReplicationGroupNotFoundFault = Exception

    exception_class = 'ReplicationGroupNotFoundFault'
    error_message = 'An error occurred: ReplicationGroupNotFoundFault'
    mock_exception = type(exception_class, (Exception,), {})
    setattr(mock_client.exceptions, exception_class, mock_exception)
    mock_client.describe_replication_groups.side_effect = mock_exception(error_message)

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_replication_groups(replication_group_id='non-existent')

        assert 'error' in result
        assert error_message in result['error']


@pytest.mark.asyncio
async def test_describe_replication_groups_invalid_parameter():
    """Test describe replication groups with invalid parameter."""
    mock_client = MagicMock()

    mock_client.exceptions.ReplicationGroupNotFoundFault = Exception

    exception_class = 'InvalidParameterValueException'
    error_message = 'Invalid parameter value'
    mock_exception = type(exception_class, (Exception,), {})
    setattr(mock_client.exceptions, exception_class, mock_exception)
    mock_client.describe_replication_groups.side_effect = mock_exception(error_message)

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_replication_groups(max_records=-1)

        assert 'error' in result
        assert error_message in result['error']
