"""Tests for the modify serverless tool."""

import pytest
from awslabs.elasticache_mcp_server.tools.serverless.models import (
    CacheUsageLimits,
    DataStorageLimits,
    ECPULimits,
    ModifyServerlessCacheRequest,
)
from awslabs.elasticache_mcp_server.tools.serverless.modify import modify_serverless_cache
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_modify_serverless_cache_basic():
    """Test basic modification of a serverless cache."""
    mock_client = MagicMock()
    mock_client.modify_serverless_cache.return_value = {
        'ServerlessCache': {
            'ServerlessCacheName': 'test-cache',
            'ServerlessCacheStatus': 'modifying',
        }
    }

    request = ModifyServerlessCacheRequest(
        serverless_cache_name='test-cache',
        description='Updated Cache',
        major_engine_version=None,
        snapshot_retention_limit=None,
        daily_snapshot_time=None,
        cache_usage_limits=None,
        remove_user_group=None,
        user_group_id=None,
        security_group_ids=None,
    )

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await modify_serverless_cache(request)

        mock_client.modify_serverless_cache.assert_called_once_with(
            ServerlessCacheName='test-cache', Description='Updated Cache'
        )
        assert result['ServerlessCache']['ServerlessCacheName'] == 'test-cache'


@pytest.mark.asyncio
async def test_modify_serverless_cache_all_params():
    """Test modification with all parameters."""
    mock_client = MagicMock()
    mock_client.modify_serverless_cache.return_value = {
        'ServerlessCache': {
            'ServerlessCacheName': 'test-cache',
            'ServerlessCacheStatus': 'modifying',
        }
    }

    cache_usage_limits = CacheUsageLimits(
        DataStorage=DataStorageLimits(Maximum=100, Minimum=50, Unit='GB'),
        ECPUPerSecond=ECPULimits(Maximum=100, Minimum=50),
    )

    request = ModifyServerlessCacheRequest(
        serverless_cache_name='test-cache',
        description='Updated description',
        cache_usage_limits=cache_usage_limits,
        remove_user_group=True,
        user_group_id='group-1',
        security_group_ids=['sg-3', 'sg-4'],
        snapshot_retention_limit=14,
        daily_snapshot_time='05:00-06:00',
        major_engine_version='7.x',
    )

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await modify_serverless_cache(request)

        mock_client.modify_serverless_cache.assert_called_once()
        call_args = mock_client.modify_serverless_cache.call_args[1]

        # Verify all parameters were passed correctly
        expected_args = {
            'ServerlessCacheName': 'test-cache',
            'Description': 'Updated description',
            'CacheUsageLimits': cache_usage_limits.model_dump(),
            'RemoveUserGroup': 'true',
            'UserGroupId': 'group-1',
            'SecurityGroupIds': ['sg-3', 'sg-4'],
            'SnapshotRetentionLimit': 14,
            'DailySnapshotTime': '05:00-06:00',
            'MajorEngineVersion': '7.x',
        }
        for key, value in expected_args.items():
            assert call_args[key] == value
        assert result['ServerlessCache']['ServerlessCacheName'] == 'test-cache'


@pytest.mark.asyncio
async def test_modify_serverless_cache_none_values():
    """Test that None values are not passed in the request."""
    mock_client = MagicMock()
    mock_client.modify_serverless_cache.return_value = {
        'ServerlessCache': {
            'ServerlessCacheName': 'test-cache',
            'ServerlessCacheStatus': 'modifying',
        }
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        request = ModifyServerlessCacheRequest(
            serverless_cache_name='test-cache',
            description='Updated description',
            major_engine_version=None,  # Should not be included in request
            snapshot_retention_limit=14,
            daily_snapshot_time=None,  # Should not be included in request
            cache_usage_limits=None,  # Should not be included in request
            remove_user_group=True,
            user_group_id=None,  # Should not be included in request
            security_group_ids=['sg-1'],
        )
        result = await modify_serverless_cache(request)

    assert result['ServerlessCache']['ServerlessCacheName'] == 'test-cache'
    call_args = mock_client.modify_serverless_cache.call_args[1]

    # Verify None values were not included
    assert 'MajorEngineVersion' not in call_args
    assert 'DailySnapshotTime' not in call_args
    assert 'CacheUsageLimits' not in call_args
    assert 'UserGroupId' not in call_args

    # Verify non-None values were included
    assert call_args['ServerlessCacheName'] == 'test-cache'
    assert call_args['Description'] == 'Updated description'
    assert call_args['SnapshotRetentionLimit'] == 14
    assert call_args['RemoveUserGroup'] == 'true'
    assert call_args['SecurityGroupIds'] == ['sg-1']


@pytest.mark.asyncio
async def test_modify_serverless_cache_exceptions():
    """Test modification error handling for various exceptions."""
    mock_client = MagicMock()

    class MockException(Exception):
        def __str__(self):
            return 'Invalid parameter value'

    mock_client.modify_serverless_cache.side_effect = MockException()

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        # Test invalid snapshot retention limit
        request = ModifyServerlessCacheRequest(
            serverless_cache_name='test-cache',
            description=None,
            major_engine_version=None,
            snapshot_retention_limit=0,  # Invalid value
            daily_snapshot_time=None,
            cache_usage_limits=None,
            remove_user_group=None,
            user_group_id=None,
            security_group_ids=None,
        )
        result = await modify_serverless_cache(request)
        assert 'error' in result
