"""Tests for the create serverless tool."""

import pytest  # type: ignore
from awslabs.elasticache_mcp_server.tools.serverless.create import create_serverless_cache
from awslabs.elasticache_mcp_server.tools.serverless.models import (
    CacheUsageLimits,
    CreateServerlessCacheRequest,
    DataStorageLimits,
    ECPULimits,
    Tag,
)
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_create_serverless_cache_basic():
    """Test basic creation of a serverless cache."""
    mock_client = MagicMock()

    mock_client.create_serverless_cache.return_value = {
        'ServerlessCache': {
            'ServerlessCacheName': 'test-cache',
            'ServerlessCacheStatus': 'creating',
        }
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        request = CreateServerlessCacheRequest(
            serverless_cache_name='test-cache',
            engine='redis',
            description=None,
            kms_key_id=None,
            major_engine_version=None,
            snapshot_arns_to_restore=None,
            subnet_ids=None,
            tags=None,
            vpc_security_group_ids=None,
            cache_usage_limits=None,
            user_group_id=None,
            snapshot_retention_limit=None,
            daily_snapshot_time=None,
        )
        result = await create_serverless_cache(request=request)

        mock_client.create_serverless_cache.assert_called_once_with(
            ServerlessCacheName='test-cache',
            Engine='redis',
        )
        assert result['ServerlessCache']['ServerlessCacheName'] == 'test-cache'


@pytest.mark.asyncio
async def test_create_serverless_cache_all_params():
    """Test creation with all parameters."""
    mock_client = MagicMock()

    mock_client.create_serverless_cache.return_value = {
        'ServerlessCache': {
            'ServerlessCacheName': 'test-cache',
            'ServerlessCacheStatus': 'creating',
        }
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        request = CreateServerlessCacheRequest(
            serverless_cache_name='Test Cache',
            engine='redis',
            description='Test serverless cache',
            kms_key_id='key-1',
            major_engine_version='7.x',
            snapshot_arns_to_restore=['arn:aws:s3:::bucket/snapshot1'],
            subnet_ids=['subnet-1', 'subnet-2'],
            tags=[Tag(Key='Environment', Value='Production')],
            vpc_security_group_ids=['sg-1', 'sg-2'],
            cache_usage_limits=CacheUsageLimits(
                DataStorage=DataStorageLimits(Maximum=1024, Minimum=1, Unit='GB'),
                ECPUPerSecond=ECPULimits(Maximum=100, Minimum=1),
            ),
            user_group_id='group-1',
            snapshot_retention_limit=7,
            daily_snapshot_time='04:00-05:00',
        )
        result = await create_serverless_cache(request=request)

        mock_client.create_serverless_cache.assert_called_once()
        call_args = mock_client.create_serverless_cache.call_args[1]

        assert call_args['ServerlessCacheName'] == 'Test Cache'
        assert call_args['Engine'] == 'redis'
        assert call_args['Description'] == 'Test serverless cache'
        assert call_args['KmsKeyId'] == 'key-1'
        assert call_args['MajorEngineVersion'] == '7.x'
        assert call_args['SnapshotArnsToRestore'] == ['arn:aws:s3:::bucket/snapshot1']
        assert call_args['SubnetIds'] == ['subnet-1', 'subnet-2']
        assert call_args['Tags'] == [{'Key': 'Environment', 'Value': 'Production'}]
        assert call_args['VpcSecurityGroupIds'] == ['sg-1', 'sg-2']
        assert call_args['CacheUsageLimits'] == {
            'DataStorage': {'Maximum': 1024, 'Minimum': 1, 'Unit': 'GB'},
            'ECPUPerSecond': {'Maximum': 100, 'Minimum': 1},
        }
        assert call_args['UserGroupId'] == 'group-1'
        assert call_args['SnapshotRetentionLimit'] == '7'
        assert call_args['DailySnapshotTime'] == '04:00-05:00'
        assert result['ServerlessCache']['ServerlessCacheName'] == 'test-cache'


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'exception_class, error_message, cache_params',
    [
        (
            'ServerlessCacheAlreadyExistsFault',
            "Serverless cache 'existing-cache' already exists",
            {
                'request': CreateServerlessCacheRequest(
                    serverless_cache_name='existing-cache',
                    engine='redis',
                    description=None,
                    kms_key_id=None,
                    major_engine_version=None,
                    snapshot_arns_to_restore=None,
                    subnet_ids=None,
                    tags=None,
                    vpc_security_group_ids=None,
                    cache_usage_limits=None,
                    user_group_id=None,
                    snapshot_retention_limit=None,
                    daily_snapshot_time=None,
                )
            },
        ),
        (
            'InvalidParameterValueException',
            'Invalid parameter value',
            {
                'request': CreateServerlessCacheRequest(
                    serverless_cache_name='test-cache',
                    engine='invalid-engine',
                    description=None,
                    kms_key_id=None,
                    major_engine_version=None,
                    snapshot_arns_to_restore=None,
                    subnet_ids=None,
                    tags=None,
                    vpc_security_group_ids=None,
                    cache_usage_limits=None,
                    user_group_id=None,
                    snapshot_retention_limit=None,
                    daily_snapshot_time=None,
                )
            },
        ),
    ],
)
async def test_create_serverless_cache_exceptions(exception_class, error_message, cache_params):
    """Test creation with various exception scenarios."""
    mock_client = MagicMock()

    class CustomException(Exception):
        def __init__(self):
            self.message = error_message

        def __str__(self):
            return self.message

    setattr(mock_client.exceptions, exception_class, CustomException)
    mock_client.create_serverless_cache.side_effect = getattr(
        mock_client.exceptions, exception_class
    )()

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await create_serverless_cache(**cache_params)

        assert isinstance(result, dict)
        assert 'error' in result
        assert error_message in result['error']
