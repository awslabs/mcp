"""Tests for the describe cache engine versions tool."""

import pytest
from awslabs.elasticache_mcp_server.tools.misc.describe_cache_engine_versions import (
    describe_cache_engine_versions,
)
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_describe_cache_engine_versions_basic():
    """Test basic describe cache engine versions functionality."""
    mock_client = MagicMock()
    mock_client.describe_cache_engine_versions.return_value = {
        'CacheEngineVersions': [
            {'Engine': 'redis', 'EngineVersion': '7.x', 'CacheParameterGroupFamily': 'redis7.x'},
            {
                'Engine': 'memcached',
                'EngineVersion': '1.6.6',
                'CacheParameterGroupFamily': 'memcached1.6',
            },
            {'Engine': 'valkey', 'EngineVersion': '8.0', 'CacheParameterGroupFamily': 'valkey8.x'},
        ]
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_cache_engine_versions()

        mock_client.describe_cache_engine_versions.assert_called_once_with()
        assert 'CacheEngineVersions' in result
        assert len(result['CacheEngineVersions']) == 3
        engines = {version['Engine'] for version in result['CacheEngineVersions']}
        assert engines == {'redis', 'memcached', 'valkey'}


@pytest.mark.asyncio
async def test_describe_cache_engine_versions_redis():
    """Test describe cache engine versions with Redis engine."""
    mock_client = MagicMock()
    mock_client.describe_cache_engine_versions.return_value = {
        'CacheEngineVersions': [
            {'Engine': 'redis', 'EngineVersion': '6.x', 'CacheParameterGroupFamily': 'redis6.x'}
        ]
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_cache_engine_versions(engine='redis')

        mock_client.describe_cache_engine_versions.assert_called_once_with(Engine='redis')
        assert result['CacheEngineVersions'][0]['Engine'] == 'redis'


@pytest.mark.asyncio
async def test_describe_cache_engine_versions_memcached():
    """Test describe cache engine versions with Memcached engine."""
    mock_client = MagicMock()
    mock_client.describe_cache_engine_versions.return_value = {
        'CacheEngineVersions': [
            {
                'Engine': 'memcached',
                'EngineVersion': '1.6.6',
                'CacheParameterGroupFamily': 'memcached1.6',
            }
        ]
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_cache_engine_versions(engine='memcached')

        mock_client.describe_cache_engine_versions.assert_called_once_with(Engine='memcached')
        assert result['CacheEngineVersions'][0]['Engine'] == 'memcached'


@pytest.mark.asyncio
async def test_describe_cache_engine_versions_valkey():
    """Test describe cache engine versions with Valkey engine."""
    mock_client = MagicMock()
    mock_client.describe_cache_engine_versions.return_value = {
        'CacheEngineVersions': [
            {'Engine': 'valkey', 'EngineVersion': '8.0', 'CacheParameterGroupFamily': 'valkey8.x'}
        ]
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_cache_engine_versions(engine='valkey')

        mock_client.describe_cache_engine_versions.assert_called_once_with(Engine='valkey')
        assert result['CacheEngineVersions'][0]['Engine'] == 'valkey'


@pytest.mark.asyncio
async def test_describe_cache_engine_versions_with_pagination():
    """Test describe cache engine versions with pagination parameters."""
    mock_client = MagicMock()
    mock_client.describe_cache_engine_versions.return_value = {
        'CacheEngineVersions': [
            {'Engine': 'valkey', 'EngineVersion': '7.0', 'CacheParameterGroupFamily': 'valkey7.x'}
        ],
        'Marker': 'next-page',
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_cache_engine_versions(max_records=20, marker='current-page')

        mock_client.describe_cache_engine_versions.assert_called_once_with(
            MaxRecords=20, Marker='current-page'
        )
        assert 'Marker' in result
        assert result['Marker'] == 'next-page'


@pytest.mark.asyncio
async def test_describe_cache_engine_versions_with_parameter_group_family():
    """Test describe cache engine versions with parameter group family."""
    mock_client = MagicMock()
    mock_client.describe_cache_engine_versions.return_value = {
        'CacheEngineVersions': [
            {'Engine': 'valkey', 'EngineVersion': '8.0', 'CacheParameterGroupFamily': 'valkey8.x'}
        ]
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_cache_engine_versions(cache_parameter_group_family='valkey8.x')

        mock_client.describe_cache_engine_versions.assert_called_once_with(
            CacheParameterGroupFamily='valkey8.x'
        )
        assert result['CacheEngineVersions'][0]['CacheParameterGroupFamily'] == 'valkey8.x'


@pytest.mark.asyncio
async def test_describe_cache_engine_versions_with_default_only():
    """Test describe cache engine versions with default only flag."""
    mock_client = MagicMock()
    mock_client.describe_cache_engine_versions.return_value = {
        'CacheEngineVersions': [
            {
                'Engine': 'valkey',
                'EngineVersion': '8.0',
                'CacheParameterGroupFamily': 'valkey8.x',
                'IsDefault': True,
            }
        ]
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_cache_engine_versions(default_only=True)

        mock_client.describe_cache_engine_versions.assert_called_once_with(DefaultOnly=True)
        assert result['CacheEngineVersions'][0]['IsDefault']


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'exception_class, error_message',
    [
        ('InvalidParameterValueException', 'Invalid parameter value'),
    ],
)
async def test_describe_cache_engine_versions_invalid_parameter(exception_class, error_message):
    """Test describe cache engine versions with invalid parameter."""
    mock_client = MagicMock()
    mock_exception = type(exception_class, (Exception,), {})
    setattr(mock_client.exceptions, exception_class, mock_exception)
    mock_client.describe_cache_engine_versions.side_effect = mock_exception(error_message)

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_cache_engine_versions(engine='invalid-engine')

        assert 'error' in result
        assert error_message in result['error']


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'exception_class, error_message',
    [
        ('InvalidParameterCombinationException', 'Invalid parameter combination'),
    ],
)
async def test_describe_cache_engine_versions_invalid_parameter_combination(
    exception_class, error_message
):
    """Test describe cache engine versions with invalid parameter combination."""
    mock_client = MagicMock()
    mock_exception = type(exception_class, (Exception,), {})
    setattr(mock_client.exceptions, exception_class, mock_exception)
    mock_client.describe_cache_engine_versions.side_effect = mock_exception(error_message)

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_cache_engine_versions(
            engine='redis', cache_parameter_group_family='valkey8.x'
        )

        assert 'error' in result
        assert error_message in result['error']
