"""Tests for the delete serverless tool."""

import pytest
from awslabs.elasticache_mcp_server.tools.serverless.delete import delete_serverless_cache
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_delete_serverless_cache_basic():
    """Test basic deletion of a serverless cache."""
    mock_client = MagicMock()

    mock_client.delete_serverless_cache.return_value = {
        'ServerlessCache': {
            'ServerlessCacheName': 'test-cache',
            'ServerlessCacheStatus': 'deleting',
        }
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await delete_serverless_cache(serverless_cache_name='test-cache')

        mock_client.delete_serverless_cache.assert_called_once_with(
            ServerlessCacheName='test-cache'
        )
        assert result['ServerlessCache']['ServerlessCacheName'] == 'test-cache'


@pytest.mark.asyncio
async def test_delete_serverless_cache_with_final_snapshot():
    """Test deletion with final snapshot."""
    mock_client = MagicMock()

    mock_client.delete_serverless_cache.return_value = {
        'ServerlessCache': {
            'ServerlessCacheName': 'test-cache',
            'ServerlessCacheStatus': 'deleting',
        }
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await delete_serverless_cache(
            serverless_cache_name='test-cache',
            final_snapshot_name='final-snapshot',
        )

        mock_client.delete_serverless_cache.assert_called_once_with(
            ServerlessCacheName='test-cache',
            FinalSnapshotName='final-snapshot',
        )
        assert result['ServerlessCache']['ServerlessCacheName'] == 'test-cache'


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'exception_class, error_message',
    [
        ('ServerlessCacheNotFoundException', 'not found'),
        ('InvalidServerlessCacheStateException', 'Invalid state'),
        ('SnapshotAlreadyExistsException', 'Snapshot already exists'),
        ('SnapshotFeatureNotSupportedException', 'Snapshot feature not supported'),
    ],
)
async def test_delete_serverless_cache_exceptions(exception_class, error_message):
    """Test deletion with various exceptions."""
    mock_client = MagicMock()

    mock_exception = type(exception_class, (Exception,), {})
    setattr(mock_client.exceptions, exception_class, mock_exception)
    mock_client.delete_serverless_cache.side_effect = mock_exception(error_message)

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await delete_serverless_cache(
            serverless_cache_name='test-cache',
            final_snapshot_name='final-snapshot' if 'Snapshot' in exception_class else None,
        )

        assert 'error' in result
        assert error_message in result['error']
