# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Additional tests for create cache cluster tool to improve coverage."""

import pytest
from awslabs.elasticache_mcp_server.tools.cc.create import (
    CreateCacheClusterRequest,
    create_cache_cluster,
)
from unittest.mock import MagicMock, patch


def create_test_request(
    cache_cluster_id: str = 'test-cluster',
    **kwargs,
) -> CreateCacheClusterRequest:
    """Create a test request with the given parameters."""
    request_data = {
        'cache_cluster_id': cache_cluster_id,
        **kwargs,
    }
    return CreateCacheClusterRequest(**request_data)


@pytest.mark.asyncio
async def test_readonly_mode():
    """Test that readonly mode prevents cluster creation."""
    # Set readonly mode to True
    with patch('awslabs.elasticache_mcp_server.context.Context.readonly_mode', return_value=True):
        request = create_test_request()
        result = await create_cache_cluster(request)
        assert 'error' in result
        assert 'readonly mode' in result['error']


@pytest.mark.asyncio
async def test_create_cache_cluster_all_optional_params():
    """Test cache cluster creation with all optional parameters."""
    mock_client = MagicMock()
    mock_client.create_cache_cluster.return_value = {
        'CacheCluster': {'CacheClusterId': 'test-cluster', 'CacheClusterStatus': 'creating'}
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        request = create_test_request(
            cache_cluster_id='test-cluster',
            cache_node_type='cache.t3.micro',
            engine='redis',
            engine_version='6.0',
            num_cache_nodes=3,
            preferred_availability_zone='us-west-2a',
            preferred_availability_zones=['us-west-2a', 'us-west-2b', 'us-west-2c'],
            cache_parameter_group_name='default.redis6.x',
            cache_subnet_group_name='subnet-group-1',
            cache_security_group_names=['security-group-1', 'security-group-2'],
            security_group_ids=['sg-12345', 'sg-67890'],
            snapshot_arns=['arn:aws:s3:::my-bucket/snapshot1.rdb'],
            snapshot_name='snapshot-1',
            preferred_maintenance_window='sun:05:00-sun:09:00',
            port=6379,
            notification_topic_arn='arn:aws:sns:us-west-2:123456789012:my-topic',
            auto_minor_version_upgrade=True,
            snapshot_retention_limit=7,
            snapshot_window='00:00-03:00',
            auth_token='password123',
            outpost_mode='single-outpost',
            preferred_outpost_arn='arn:aws:outposts:us-west-2:123456789012:outpost/op-1234567890abcdef0',
            preferred_outpost_arns=[
                'arn:aws:outposts:us-west-2:123456789012:outpost/op-1234567890abcdef0'
            ],
        )
        result = await create_cache_cluster(request)

    assert result['CacheCluster']['CacheClusterId'] == 'test-cluster'
    mock_client.create_cache_cluster.assert_called_once_with(
        CacheClusterId='test-cluster',
        CacheNodeType='cache.t3.micro',
        Engine='redis',
        EngineVersion='6.0',
        NumCacheNodes=3,
        PreferredAvailabilityZone='us-west-2a',
        PreferredAvailabilityZones=['us-west-2a', 'us-west-2b', 'us-west-2c'],
        CacheParameterGroupName='default.redis6.x',
        CacheSubnetGroupName='subnet-group-1',
        CacheSecurityGroupNames=['security-group-1', 'security-group-2'],
        SecurityGroupIds=['sg-12345', 'sg-67890'],
        SnapshotArns=['arn:aws:s3:::my-bucket/snapshot1.rdb'],
        SnapshotName='snapshot-1',
        PreferredMaintenanceWindow='sun:05:00-sun:09:00',
        Port=6379,
        NotificationTopicArn='arn:aws:sns:us-west-2:123456789012:my-topic',
        AutoMinorVersionUpgrade=True,
        SnapshotRetentionLimit=7,
        SnapshotWindow='00:00-03:00',
        AuthToken='password123',
        OutpostMode='single-outpost',
        PreferredOutpostArn='arn:aws:outposts:us-west-2:123456789012:outpost/op-1234567890abcdef0',
        PreferredOutpostArns=[
            'arn:aws:outposts:us-west-2:123456789012:outpost/op-1234567890abcdef0'
        ],
    )


@pytest.mark.asyncio
async def test_create_cache_cluster_with_tags_list():
    """Test cache cluster creation with tags in list format."""
    mock_client = MagicMock()
    mock_client.create_cache_cluster.return_value = {
        'CacheCluster': {'CacheClusterId': 'test-cluster', 'CacheClusterStatus': 'creating'}
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        # Test list format tags
        request = create_test_request(
            cache_cluster_id='test-cluster',
            tags=[{'Key': 'Key1', 'Value': 'Value1'}, {'Key': 'Key2', 'Value': 'Value2'}],
        )
        result = await create_cache_cluster(request)
        assert result['CacheCluster']['CacheClusterId'] == 'test-cluster'
        mock_client.create_cache_cluster.assert_called_with(
            CacheClusterId='test-cluster',
            Tags=[{'Key': 'Key1', 'Value': 'Value1'}, {'Key': 'Key2', 'Value': 'Value2'}],
        )


@pytest.mark.asyncio
async def test_create_cache_cluster_with_tags_null_value():
    """Test cache cluster creation with tags that have null values."""
    mock_client = MagicMock()
    mock_client.create_cache_cluster.return_value = {
        'CacheCluster': {'CacheClusterId': 'test-cluster', 'CacheClusterStatus': 'creating'}
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        # Test string format tags with null value
        request = create_test_request(cache_cluster_id='test-cluster', tags='Key1=Value1,Key2=')
        result = await create_cache_cluster(request)
        assert result['CacheCluster']['CacheClusterId'] == 'test-cluster'
        mock_client.create_cache_cluster.assert_called_with(
            CacheClusterId='test-cluster',
            Tags=[{'Key': 'Key1', 'Value': 'Value1'}, {'Key': 'Key2', 'Value': None}],
        )


@pytest.mark.asyncio
async def test_create_cache_cluster_invalid_tag_formats():
    """Test cache cluster creation with various invalid tag formats."""
    mock_client = MagicMock()

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        # Test invalid tag format with no equals sign
        request = create_test_request(tags='InvalidFormat')
        result = await create_cache_cluster(request)
        assert 'error' in result
        assert 'Invalid tag format' in result['error']

        # Test empty key
        request = create_test_request(tags='=Value')
        result = await create_cache_cluster(request)
        assert 'error' in result
        assert 'Tag key cannot be empty' in result['error']

        # Test list with empty key
        request = create_test_request(tags=[{'Key': '', 'Value': 'Value'}])
        result = await create_cache_cluster(request)
        assert 'error' in result
        assert 'Tag key cannot be empty' in result['error']

        # Test list with missing Key
        request = create_test_request(tags=[{'NotKey': 'Value'}])
        result = await create_cache_cluster(request)
        assert 'error' in result
        assert 'Each tag must be a dictionary with a Key' in result['error']


@pytest.mark.asyncio
async def test_create_cache_cluster_with_shorthand_log_delivery():
    """Test cache cluster creation with log delivery configuration in shorthand format."""
    mock_client = MagicMock()
    mock_client.create_cache_cluster.return_value = {
        'CacheCluster': {'CacheClusterId': 'test-cluster', 'CacheClusterStatus': 'creating'}
    }

    log_config_shorthand = (
        'LogType=slow-log,DestinationType=cloudwatch-logs,'
        "DestinationDetails={'CloudWatchLogsDetails':{'LogGroup':'/aws/elasticache/test'}},"
        'LogFormat=json,Enabled=true'
    )

    expected_log_config = [
        {
            'LogType': 'slow-log',
            'DestinationType': 'cloudwatch-logs',
            'DestinationDetails': {'CloudWatchLogsDetails': {'LogGroup': '/aws/elasticache/test'}},
            'LogFormat': 'json',
            'Enabled': True,
        }
    ]

    with (
        patch(
            'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
            return_value=mock_client,
        ),
        patch(
            'awslabs.elasticache_mcp_server.tools.cc.create.process_log_delivery_configurations',
            return_value=expected_log_config,
        ) as mock_process,
    ):
        request = create_test_request(
            cache_cluster_id='test-cluster', log_delivery_configurations=log_config_shorthand
        )
        result = await create_cache_cluster(request)

        assert result['CacheCluster']['CacheClusterId'] == 'test-cluster'
        mock_process.assert_called_once_with(log_config_shorthand)
        mock_client.create_cache_cluster.assert_called_once_with(
            CacheClusterId='test-cluster', LogDeliveryConfigurations=expected_log_config
        )


@pytest.mark.asyncio
async def test_create_cache_cluster_with_invalid_log_delivery():
    """Test cache cluster creation with invalid log delivery configuration."""
    mock_client = MagicMock()

    with (
        patch(
            'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
            return_value=mock_client,
        ),
        patch(
            'awslabs.elasticache_mcp_server.tools.cc.create.process_log_delivery_configurations',
            side_effect=ValueError(
                'Invalid log delivery shorthand syntax: Invalid format. Each parameter must be in key=value format: invalid'
            ),
        ),
    ):
        request = create_test_request(
            cache_cluster_id='test-cluster', log_delivery_configurations='invalid'
        )
        result = await create_cache_cluster(request)

    assert 'error' in result
    assert 'Invalid format. Each parameter must be in key=value format: invalid' in result['error']
    mock_client.create_cache_cluster.assert_not_called()
