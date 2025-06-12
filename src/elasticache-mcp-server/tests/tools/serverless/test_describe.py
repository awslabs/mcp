"""Tests for the describe serverless tool."""

import pytest
from awslabs.elasticache_mcp_server.tools.serverless.describe import describe_serverless_caches
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_describe_serverless_caches_basic():
    """Test basic describe serverless caches functionality."""
    mock_client = MagicMock()
    mock_client.describe_serverless_caches.return_value = {
        'ServerlessCaches': [
            {
                'ServerlessCacheName': 'test-cache',
                'ServerlessCacheStatus': 'available',
                'Engine': 'valkey',
            }
        ]
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_serverless_caches()

        mock_client.describe_serverless_caches.assert_called_once_with()
        assert 'ServerlessCaches' in result
        assert len(result['ServerlessCaches']) == 1
        assert result['ServerlessCaches'][0]['ServerlessCacheName'] == 'test-cache'
        assert result['ServerlessCaches'][0]['Engine'] == 'valkey'


@pytest.mark.asyncio
async def test_describe_serverless_caches_with_name():
    """Test describe serverless caches with specific name."""
    mock_client = MagicMock()
    mock_client.describe_serverless_caches.return_value = {
        'ServerlessCaches': [
            {
                'ServerlessCacheName': 'specific-cache',
                'ServerlessCacheStatus': 'available',
                'Engine': 'redis',
            }
        ]
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_serverless_caches(serverless_cache_name='specific-cache')

        mock_client.describe_serverless_caches.assert_called_once_with(
            ServerlessCacheName='specific-cache'
        )
        assert result['ServerlessCaches'][0]['ServerlessCacheName'] == 'specific-cache'


@pytest.mark.asyncio
async def test_describe_serverless_caches_with_pagination():
    """Test describe serverless caches with pagination parameters."""
    mock_client = MagicMock()
    mock_client.describe_serverless_caches.return_value = {
        'ServerlessCaches': [
            {
                'ServerlessCacheName': 'test-cache-1',
                'ServerlessCacheStatus': 'available',
                'Engine': 'redis',
            }
        ],
        'NextToken': 'next-page',
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_serverless_caches(
            max_items=20, starting_token='current-page', page_size=10
        )

        mock_client.describe_serverless_caches.assert_called_once_with(
            MaxItems=20, StartingToken='current-page', PageSize=10
        )
        assert 'NextToken' in result
        assert result['NextToken'] == 'next-page'


@pytest.mark.asyncio
async def test_describe_serverless_caches_with_starting_token():
    """Test describe serverless caches with starting token."""
    mock_client = MagicMock()
    mock_client.describe_serverless_caches.return_value = {
        'ServerlessCaches': [
            {
                'ServerlessCacheName': 'test-cache-2',
                'ServerlessCacheStatus': 'available',
                'Engine': 'redis',
            }
        ],
        'NextToken': 'next-token',
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_serverless_caches(starting_token='current-token')

        mock_client.describe_serverless_caches.assert_called_once_with(
            StartingToken='current-token'
        )
        assert 'NextToken' in result
        assert result['NextToken'] == 'next-token'


@pytest.mark.asyncio
async def test_describe_serverless_caches_with_page_size():
    """Test describe serverless caches with page size."""
    mock_client = MagicMock()
    mock_client.describe_serverless_caches.return_value = {
        'ServerlessCaches': [
            {
                'ServerlessCacheName': 'test-cache-3',
                'ServerlessCacheStatus': 'available',
                'Engine': 'redis',
            }
        ]
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_serverless_caches(page_size=5)

        mock_client.describe_serverless_caches.assert_called_once_with(PageSize=5)
        assert len(result['ServerlessCaches']) == 1


@pytest.mark.asyncio
async def test_describe_serverless_caches_not_found():
    """Test describe serverless caches when cache is not found."""
    mock_client = MagicMock()

    class ServerlessCacheNotFoundFault(Exception):
        def __init__(self, cache_name):
            self.cache_name = cache_name

        def __str__(self):
            return f"Serverless cache '{self.cache_name}' not found"

    mock_client.exceptions.ServerlessCacheNotFoundFault = ServerlessCacheNotFoundFault
    mock_client.describe_serverless_caches.side_effect = ServerlessCacheNotFoundFault(
        'non-existent'
    )

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_serverless_caches(serverless_cache_name='non-existent')

        mock_client.describe_serverless_caches.assert_called_once_with(
            ServerlessCacheName='non-existent'
        )
        assert result == {'error': "Serverless cache 'non-existent' not found"}


@pytest.mark.asyncio
async def test_describe_serverless_caches_invalid_parameter():
    """Test describe serverless caches with invalid parameter."""
    mock_client = MagicMock()
    mock_client.exceptions.InvalidParameterValueException = Exception
    mock_client.describe_serverless_caches.side_effect = (
        mock_client.exceptions.InvalidParameterValueException()
    )

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_serverless_caches(max_records=-1)

        assert 'error' in result
        assert (
            str(getattr(mock_client.exceptions, 'InvalidParameterValueException')())
            in result['error']
        )
