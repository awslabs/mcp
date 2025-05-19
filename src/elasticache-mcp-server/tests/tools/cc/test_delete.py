"""Tests for delete cache cluster tool."""

import pytest
from awslabs.elasticache_mcp_server.tools.cc.delete import delete_cache_cluster
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_delete_cache_cluster_minimal():
    """Test deleting a cache cluster with minimal parameters."""
    mock_client = MagicMock()
    mock_client.delete_cache_cluster.return_value = {
        'CacheCluster': {'CacheClusterId': 'test-cluster'}
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await delete_cache_cluster(cache_cluster_id='test-cluster')

    assert result == {'CacheCluster': {'CacheClusterId': 'test-cluster'}}
    mock_client.delete_cache_cluster.assert_called_once_with(CacheClusterId='test-cluster')


@pytest.mark.asyncio
async def test_delete_cache_cluster_with_snapshot():
    """Test deleting a cache cluster with final snapshot."""
    mock_client = MagicMock()
    mock_client.delete_cache_cluster.return_value = {
        'CacheCluster': {'CacheClusterId': 'test-cluster'}
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await delete_cache_cluster(
            cache_cluster_id='test-cluster', final_snapshot_identifier='final-snapshot'
        )

    assert result == {'CacheCluster': {'CacheClusterId': 'test-cluster'}}
    mock_client.delete_cache_cluster.assert_called_once_with(
        CacheClusterId='test-cluster', FinalSnapshotIdentifier='final-snapshot'
    )


@pytest.mark.asyncio
async def test_delete_cache_cluster_not_found():
    """Test error handling when cache cluster is not found."""
    mock_client = MagicMock()
    exception_class = 'CacheClusterNotFoundFault'
    error_message = 'Cache cluster test-cluster not found'
    mock_exception = type(exception_class, (Exception,), {})
    setattr(mock_client.exceptions, exception_class, mock_exception)
    mock_client.delete_cache_cluster.side_effect = mock_exception(error_message)

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await delete_cache_cluster(cache_cluster_id='test-cluster')

        assert 'error' in result
        assert error_message in result['error']
