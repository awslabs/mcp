"""Tests for the describe cache clusters tool."""

import pytest
from awslabs.elasticache_mcp_server.tools.cc.describe import describe_cache_clusters
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_describe_cache_clusters_basic():
    """Test basic describe cache clusters functionality."""
    mock_client = MagicMock()
    mock_client.describe_cache_clusters.return_value = {
        'CacheClusters': [{'CacheClusterId': 'test-cc', 'CacheClusterStatus': 'available'}]
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_cache_clusters()

        mock_client.describe_cache_clusters.assert_called_once_with()
        assert 'CacheClusters' in result
        assert len(result['CacheClusters']) == 1
        assert result['CacheClusters'][0]['CacheClusterId'] == 'test-cc'


@pytest.mark.asyncio
async def test_describe_cache_clusters_with_id():
    """Test describe cache clusters with specific ID."""
    mock_client = MagicMock()
    mock_client.describe_cache_clusters.return_value = {
        'CacheClusters': [{'CacheClusterId': 'specific-cc', 'CacheClusterStatus': 'available'}]
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_cache_clusters(cache_cluster_id='specific-cc')

        mock_client.describe_cache_clusters.assert_called_once_with(CacheClusterId='specific-cc')
        assert result['CacheClusters'][0]['CacheClusterId'] == 'specific-cc'


@pytest.mark.asyncio
async def test_describe_cache_clusters_with_pagination():
    """Test describe cache clusters with pagination parameters."""
    mock_client = MagicMock()
    mock_client.describe_cache_clusters.return_value = {
        'CacheClusters': [{'CacheClusterId': 'test-cc-1', 'CacheClusterStatus': 'available'}],
        'Marker': 'next-page',
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_cache_clusters(max_records=20, marker='current-page')

        mock_client.describe_cache_clusters.assert_called_once_with(
            MaxRecords=20, Marker='current-page'
        )
        assert 'Marker' in result
        assert result['Marker'] == 'next-page'


@pytest.mark.asyncio
async def test_describe_cache_clusters_with_node_info():
    """Test describe cache clusters with node info parameter."""
    mock_client = MagicMock()
    mock_client.describe_cache_clusters.return_value = {
        'CacheClusters': [
            {
                'CacheClusterId': 'test-cc',
                'CacheClusterStatus': 'available',
                'CacheNodes': [{'CacheNodeId': '0001', 'CacheNodeStatus': 'available'}],
            }
        ]
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_cache_clusters(show_cache_node_info=True)

        mock_client.describe_cache_clusters.assert_called_once_with(ShowCacheNodeInfo=True)
        assert 'CacheNodes' in result['CacheClusters'][0]


@pytest.mark.asyncio
async def test_describe_cache_clusters_not_found():
    """Test describe cache clusters when cluster is not found."""
    mock_client = MagicMock()
    exception_class = 'CacheClusterNotFoundFault'
    error_message = 'not found'
    mock_exception = type(exception_class, (Exception,), {})
    setattr(mock_client.exceptions, exception_class, mock_exception)
    mock_client.describe_cache_clusters.side_effect = mock_exception(error_message)

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_cache_clusters(cache_cluster_id='non-existent')

        assert 'error' in result
        assert error_message in result['error']
