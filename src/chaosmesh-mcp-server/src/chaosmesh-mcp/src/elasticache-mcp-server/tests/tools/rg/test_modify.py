"""Tests for modify replication group tool."""

import pytest
from awslabs.elasticache_mcp_server.context import Context
from awslabs.elasticache_mcp_server.tools.rg import (
    modify_replication_group,
    modify_replication_group_shard_configuration,
)
from awslabs.elasticache_mcp_server.tools.rg.modify import ModifyReplicationGroupRequest
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_modify_replication_group_readonly_mode():
    """Test modifying a replication group in readonly mode."""
    with patch.object(Context, 'readonly_mode', return_value=True):
        request = ModifyReplicationGroupRequest(
            replication_group_id='test-group',
            apply_immediately=True,
        )
        result = await modify_replication_group(request)
        assert 'error' in result
        assert 'readonly mode' in result['error']


@pytest.mark.asyncio
async def test_modify_replication_group_shard_configuration_readonly_mode():
    """Test modifying a replication group shard configuration in readonly mode."""
    with patch.object(Context, 'readonly_mode', return_value=True):
        result = await modify_replication_group_shard_configuration(
            replication_group_id='test-group',
            node_group_count=2,
        )
        assert 'error' in result
        assert 'readonly mode' in result['error']


@pytest.mark.asyncio
async def test_modify_replication_group_basic():
    """Test basic modification of a replication group."""
    mock_client = MagicMock()
    mock_client.modify_replication_group.return_value = {
        'ReplicationGroup': {'ReplicationGroupId': 'test-group'}
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        request = ModifyReplicationGroupRequest(
            replication_group_id='test-group',
            apply_immediately=True,
            automatic_failover_enabled=True,
        )
        result = await modify_replication_group(request)

    assert result['ReplicationGroup']['ReplicationGroupId'] == 'test-group'
    mock_client.modify_replication_group.assert_called_once_with(
        ReplicationGroupId='test-group',
        ApplyImmediately=True,
        AutomaticFailoverEnabled=True,
    )


@pytest.mark.asyncio
async def test_modify_replication_group_all_params():
    """Test modification with all parameters."""
    mock_client = MagicMock()
    mock_client.modify_replication_group.return_value = {
        'ReplicationGroup': {'ReplicationGroupId': 'test-group'}
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        request = ModifyReplicationGroupRequest(
            replication_group_id='test-group',
            apply_immediately=True,
            auto_minor_version_upgrade=True,
            automatic_failover_enabled=True,
            cache_node_type='cache.t3.micro',
            cache_parameter_group_name='default.redis6.x',
            cache_security_group_names=['sg-1'],
            engine_version='6.x',
            log_delivery_configurations=[
                {
                    'LogType': 'slow-log',
                    'DestinationType': 'cloudwatch-logs',
                    'DestinationDetails': {
                        'CloudWatchLogsDetails': {'LogGroup': '/aws/elasticache'}
                    },
                    'LogFormat': 'json',
                    'Enabled': True,
                }
            ],
            maintenance_window='sun:05:00-sun:09:00',
            multi_az_enabled=True,
            notification_topic_arn='arn:aws:sns:region:account:topic',
            notification_topic_status='active',
            num_node_groups=3,
            preferred_node_groups_to_remove=[1, 2],
            primary_cluster_id='primary-cluster',
            replicas_per_node_group=2,
            replication_group_description='Updated test group',
            security_group_ids=['sg-123'],
            snapshot_retention_limit=5,
            snapshot_window='05:00-09:00',
            user_group_ids_to_add=['user-group-1'],
            user_group_ids_to_remove=['user-group-2'],
            node_group_id='node-group-1',
            remove_user_groups=False,
            auth_token='secret',
            auth_token_update_strategy='ROTATE',
        )
        result = await modify_replication_group(request)

    assert result['ReplicationGroup']['ReplicationGroupId'] == 'test-group'
    call_args = mock_client.modify_replication_group.call_args[1]

    # Verify all parameters were passed correctly
    assert call_args['ReplicationGroupId'] == 'test-group'
    assert call_args['ApplyImmediately'] is True
    assert call_args['AutoMinorVersionUpgrade'] is True
    assert call_args['AutomaticFailoverEnabled'] is True
    assert call_args['CacheNodeType'] == 'cache.t3.micro'
    assert call_args['CacheParameterGroupName'] == 'default.redis6.x'
    assert call_args['CacheSecurityGroupNames'] == ['sg-1']
    assert call_args['EngineVersion'] == '6.x'
    assert call_args['LogDeliveryConfigurations'] == [
        {
            'LogType': 'slow-log',
            'DestinationType': 'cloudwatch-logs',
            'DestinationDetails': {'CloudWatchLogsDetails': {'LogGroup': '/aws/elasticache'}},
            'LogFormat': 'json',
            'Enabled': True,
        }
    ]


@pytest.mark.asyncio
async def test_modify_replication_group_shorthand_configs():
    """Test modification with shorthand configurations."""
    mock_client = MagicMock()
    mock_client.modify_replication_group.return_value = {
        'ReplicationGroup': {'ReplicationGroupId': 'test-group'}
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        request = ModifyReplicationGroupRequest(
            replication_group_id='test-group',
            log_delivery_configurations=(
                'LogType=slow-log,DestinationType=cloudwatch-logs,'
                'DestinationDetails={"CloudWatchLogsDetails":{"LogGroup":"/aws/elasticache"}},'
                'LogFormat=json,Enabled=true'
            ),
        )
        result = await modify_replication_group(request)

    assert result['ReplicationGroup']['ReplicationGroupId'] == 'test-group'
    call_args = mock_client.modify_replication_group.call_args[1]
    assert 'LogDeliveryConfigurations' in call_args


@pytest.mark.asyncio
async def test_modify_replication_group_node_groups():
    """Test modification of node groups."""
    mock_client = MagicMock()
    mock_client.modify_replication_group.return_value = {
        'ReplicationGroup': {'ReplicationGroupId': 'test-group'}
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        # Test adding node groups
        request = ModifyReplicationGroupRequest(
            replication_group_id='test-group',
            num_node_groups=4,
            replicas_per_node_group=2,
        )
        result = await modify_replication_group(request)
        assert result['ReplicationGroup']['ReplicationGroupId'] == 'test-group'
        call_args = mock_client.modify_replication_group.call_args[1]
        assert call_args['NodeGroupCount'] == 4
        assert call_args['ReplicasPerNodeGroup'] == 2

        # Test removing node groups
        mock_client.reset_mock()
        request = ModifyReplicationGroupRequest(
            replication_group_id='test-group',
            num_node_groups=2,
            preferred_node_groups_to_remove=[2, 3],
        )
        result = await modify_replication_group(request)
        assert result['ReplicationGroup']['ReplicationGroupId'] == 'test-group'
        call_args = mock_client.modify_replication_group.call_args[1]
        assert call_args['NodeGroupCount'] == 2
        assert call_args['NodeGroupsToRemove'] == [2, 3]


@pytest.mark.asyncio
async def test_modify_replication_group_user_groups():
    """Test modification of user groups."""
    mock_client = MagicMock()
    mock_client.modify_replication_group.return_value = {
        'ReplicationGroup': {'ReplicationGroupId': 'test-group'}
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        # Test adding and removing user groups
        request = ModifyReplicationGroupRequest(
            replication_group_id='test-group',
            user_group_ids_to_add=['new-group-1', 'new-group-2'],
            user_group_ids_to_remove=['old-group-1'],
        )
        result = await modify_replication_group(request)
        assert result['ReplicationGroup']['ReplicationGroupId'] == 'test-group'
        call_args = mock_client.modify_replication_group.call_args[1]
        assert call_args['UserGroupIdsToAdd'] == ['new-group-1', 'new-group-2']
        assert call_args['UserGroupIdsToRemove'] == ['old-group-1']

        # Test removing all user groups
        mock_client.reset_mock()
        request = ModifyReplicationGroupRequest(
            replication_group_id='test-group',
            remove_user_groups=True,
        )
        result = await modify_replication_group(request)
        assert result['ReplicationGroup']['ReplicationGroupId'] == 'test-group'
        call_args = mock_client.modify_replication_group.call_args[1]
        assert call_args['RemoveUserGroups'] is True


@pytest.mark.asyncio
async def test_modify_replication_group_none_values():
    """Test that None values are not passed in the request."""
    mock_client = MagicMock()
    mock_client.modify_replication_group.return_value = {
        'ReplicationGroup': {'ReplicationGroupId': 'test-group'}
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        request = ModifyReplicationGroupRequest(
            replication_group_id='test-group',
            apply_immediately=True,
            auto_minor_version_upgrade=None,  # Should not be included in request
            cache_node_type=None,  # Should not be included in request
            num_node_groups=3,
        )
        result = await modify_replication_group(request)

    assert result['ReplicationGroup']['ReplicationGroupId'] == 'test-group'
    call_args = mock_client.modify_replication_group.call_args[1]
    assert 'AutoMinorVersionUpgrade' not in call_args
    assert 'CacheNodeType' not in call_args
    assert call_args['NodeGroupCount'] == 3


@pytest.mark.asyncio
async def test_modify_replication_group_shard_configuration_basic():
    """Test basic modification of replication group shard configuration."""
    result = await modify_replication_group_shard_configuration(
        replication_group_id='test-group',
        node_group_count=2,
        apply_immediately=True,
        resharding_configuration=[
            {
                'NodeGroupId': 'ng-1',
                'NewShardConfiguration': {
                    'NewReplicaCount': 2,
                    'PreferredAvailabilityZones': ['us-west-2a', 'us-west-2b'],
                },
            }
        ],
    )
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_modify_replication_group_shard_configuration_shorthand():
    """Test modification with shorthand resharding configuration."""
    result = await modify_replication_group_shard_configuration(
        replication_group_id='test-group',
        node_group_count=2,
        apply_immediately=True,
        resharding_configuration=(
            'NodeGroupId=ng-1,NewShardConfiguration={NewReplicaCount=2,'
            'PreferredAvailabilityZones=us-west-2a,us-west-2b}'
        ),
    )
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_modify_replication_group_shard_configuration_multiple():
    """Test modification with multiple resharding configurations."""
    result = await modify_replication_group_shard_configuration(
        replication_group_id='test-group',
        node_group_count=3,
        apply_immediately=True,
        resharding_configuration=[
            {
                'NodeGroupId': 'ng-1',
                'NewShardConfiguration': {
                    'NewReplicaCount': 2,
                    'PreferredAvailabilityZones': ['us-west-2a', 'us-west-2b'],
                },
            },
            {
                'NodeGroupId': 'ng-2',
                'NewShardConfiguration': {
                    'NewReplicaCount': 3,
                    'PreferredAvailabilityZones': ['us-west-2c', 'us-west-2d', 'us-west-2e'],
                },
            },
        ],
    )
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_modify_replication_group_shard_configuration_multiple_shorthand():
    """Test modification with multiple shorthand resharding configurations."""
    result = await modify_replication_group_shard_configuration(
        replication_group_id='test-group',
        node_group_count=3,
        apply_immediately=True,
        resharding_configuration=(
            'NodeGroupId=ng-1,NewShardConfiguration={NewReplicaCount=2,'
            'PreferredAvailabilityZones=us-west-2a,us-west-2b} '
            'NodeGroupId=ng-2,NewShardConfiguration={NewReplicaCount=3,'
            'PreferredAvailabilityZones=us-west-2c,us-west-2d,us-west-2e}'
        ),
    )
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_modify_replication_group_shard_configuration_invalid_params():
    """Test modification with invalid parameters."""
    # Test missing NodeGroupId
    result = await modify_replication_group_shard_configuration(
        replication_group_id='test-group',
        node_group_count=2,
        resharding_configuration=[{'NewShardConfiguration': {'NewReplicaCount': 2}}],
    )
    assert 'error' in result

    # Test missing NewShardConfiguration
    result = await modify_replication_group_shard_configuration(
        replication_group_id='test-group',
        node_group_count=2,
        resharding_configuration=[{'NodeGroupId': 'ng-1'}],
    )
    assert 'error' in result

    # Test missing NewReplicaCount
    result = await modify_replication_group_shard_configuration(
        replication_group_id='test-group',
        node_group_count=2,
        resharding_configuration=[
            {
                'NodeGroupId': 'ng-1',
                'NewShardConfiguration': {'PreferredAvailabilityZones': ['us-west-2a']},
            }
        ],
    )
    assert 'error' in result

    # Test invalid NewReplicaCount
    result = await modify_replication_group_shard_configuration(
        replication_group_id='test-group',
        node_group_count=2,
        resharding_configuration=[
            {'NodeGroupId': 'ng-1', 'NewShardConfiguration': {'NewReplicaCount': -1}}
        ],
    )
    assert 'error' in result


@pytest.mark.asyncio
async def test_modify_replication_group_invalid_params():
    """Test modification with invalid parameters."""
    mock_client = MagicMock()

    class MockException(Exception):
        def __str__(self):
            return 'Invalid parameter value'

    mock_client.modify_replication_group.side_effect = MockException()

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        # Test invalid node group count
        request = ModifyReplicationGroupRequest(
            replication_group_id='test-group',
            num_node_groups=-1,
        )
        result = await modify_replication_group(request)
        assert 'error' in result

        # Test invalid replicas per node group
        mock_client.reset_mock()
        request = ModifyReplicationGroupRequest(
            replication_group_id='test-group',
            replicas_per_node_group=-1,
        )
        result = await modify_replication_group(request)
        assert 'error' in result

        # Test invalid auth token update strategy
        mock_client.reset_mock()
        request = ModifyReplicationGroupRequest(
            replication_group_id='test-group',
            auth_token='secret',
            auth_token_update_strategy='INVALID',
        )
        result = await modify_replication_group(request)
        assert 'error' in result
