"""Tests for the batch apply update action tool."""

import pytest
from awslabs.elasticache_mcp_server.tools.misc.batch_apply_update_action import (
    batch_apply_update_action,
)
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_batch_apply_update_action_replication_groups():
    """Test batch apply update action with replication groups."""
    mock_client = MagicMock()
    mock_client.batch_apply_update_action.return_value = {
        'ProcessedItems': [
            {'ReplicationGroupId': 'rg-1', 'ServiceUpdateName': 'update-1', 'Status': 'pending'}
        ],
        'UnprocessedItems': [],
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await batch_apply_update_action(
            service_update_name='update-1', replication_group_ids=['rg-1']
        )

        mock_client.batch_apply_update_action.assert_called_once_with(
            ServiceUpdateName='update-1', ReplicationGroupIds=['rg-1']
        )
        assert 'ProcessedItems' in result
        assert len(result['ProcessedItems']) == 1
        assert result['ProcessedItems'][0]['ReplicationGroupId'] == 'rg-1'


@pytest.mark.asyncio
async def test_batch_apply_update_action_cache_clusters():
    """Test batch apply update action with cache clusters."""
    mock_client = MagicMock()
    mock_client.batch_apply_update_action.return_value = {
        'ProcessedItems': [
            {'CacheClusterId': 'cc-1', 'ServiceUpdateName': 'update-1', 'Status': 'pending'}
        ],
        'UnprocessedItems': [],
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await batch_apply_update_action(
            service_update_name='update-1', cache_cluster_ids=['cc-1']
        )

        mock_client.batch_apply_update_action.assert_called_once_with(
            ServiceUpdateName='update-1', CacheClusterIds=['cc-1']
        )
        assert 'ProcessedItems' in result
        assert len(result['ProcessedItems']) == 1
        assert result['ProcessedItems'][0]['CacheClusterId'] == 'cc-1'


@pytest.mark.asyncio
async def test_batch_apply_update_action_invalid_parameter():
    """Test batch apply update action with invalid parameter."""
    mock_client = MagicMock()
    exception_class = 'InvalidParameterValueException'
    error_message = 'Invalid parameter value'
    mock_exception = type(exception_class, (Exception,), {})
    setattr(mock_client.exceptions, exception_class, mock_exception)
    mock_client.batch_apply_update_action.side_effect = mock_exception(error_message)

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await batch_apply_update_action(
            service_update_name='invalid-update', replication_group_ids=['rg-1']
        )

        assert 'error' in result
        assert error_message in result['error']


@pytest.mark.asyncio
async def test_batch_apply_update_action_missing_targets():
    """Test batch apply update action with no targets specified."""
    mock_client = MagicMock()
    exception_class = 'InvalidParameterCombinationException'
    error_message = 'Must specify either replication groups or cache clusters'
    mock_exception = type(exception_class, (Exception,), {})
    setattr(mock_client.exceptions, exception_class, mock_exception)
    mock_client.batch_apply_update_action.side_effect = mock_exception(error_message)

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await batch_apply_update_action(service_update_name='update-1')

        assert 'error' in result
        assert error_message in result['error']
