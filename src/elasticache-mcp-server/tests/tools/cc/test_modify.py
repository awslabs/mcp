"""Tests for modify cache cluster tool."""

import pytest
from awslabs.elasticache_mcp_server.context import Context
from awslabs.elasticache_mcp_server.tools.cc.modify import (
    ModifyCacheClusterRequest,
    modify_cache_cluster,
)
from typing import Any, Dict, List, Optional, TypedDict, Union
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_modify_cache_cluster_readonly_mode():
    """Test modifying a cache cluster in readonly mode."""
    with patch.object(Context, 'readonly_mode', return_value=True):
        request = ModifyCacheClusterRequest(
            cache_cluster_id='test-cluster',
            apply_immediately=True,
        )
        result = await modify_cache_cluster(request)
        assert 'error' in result
        assert 'readonly mode' in result['error']


class ModifyRequestKwargs(TypedDict, total=False):
    """Type definition for modify request kwargs."""

    cache_cluster_id: str
    num_cache_nodes: Optional[int]
    cache_node_ids_to_remove: Optional[List[str]]
    az_mode: Optional[str]
    new_availability_zones: Optional[List[str]]
    cache_security_group_names: Optional[List[str]]
    security_group_ids: Optional[List[str]]
    preferred_maintenance_window: Optional[str]
    notification_topic_arn: Optional[str]
    cache_parameter_group_name: Optional[str]
    notification_topic_status: Optional[str]
    apply_immediately: Optional[bool]
    engine_version: Optional[str]
    auto_minor_version_upgrade: Optional[bool]
    snapshot_retention_limit: Optional[int]
    snapshot_window: Optional[str]
    cache_node_type: Optional[str]
    auth_token: Optional[str]
    auth_token_update_strategy: Optional[str]
    log_delivery_configurations: Optional[Union[str, List[Dict[str, Any]]]]
    scale_config: Optional[Union[str, Dict[str, Any]]]


def create_test_request(
    cache_cluster_id: str = 'test-cluster',
    num_cache_nodes: Optional[int] = None,
    cache_node_ids_to_remove: Optional[List[str]] = None,
    az_mode: Optional[str] = None,
    new_availability_zones: Optional[List[str]] = None,
    cache_security_group_names: Optional[List[str]] = None,
    security_group_ids: Optional[List[str]] = None,
    preferred_maintenance_window: Optional[str] = None,
    notification_topic_arn: Optional[str] = None,
    cache_parameter_group_name: Optional[str] = None,
    notification_topic_status: Optional[str] = None,
    apply_immediately: Optional[bool] = None,
    engine_version: Optional[str] = None,
    auto_minor_version_upgrade: Optional[bool] = None,
    snapshot_retention_limit: Optional[int] = None,
    snapshot_window: Optional[str] = None,
    cache_node_type: Optional[str] = None,
    auth_token: Optional[str] = None,
    auth_token_update_strategy: Optional[str] = None,
    log_delivery_configurations: Optional[Union[str, List[Dict[str, Any]]]] = None,
    scale_config: Optional[Union[str, Dict[str, Any]]] = None,
) -> ModifyCacheClusterRequest:
    """Create a test request with minimal required values."""
    request_data = {
        'cache_cluster_id': cache_cluster_id,
        **{k: v for k, v in locals().items() if k != 'cache_cluster_id' and v is not None},
    }
    return ModifyCacheClusterRequest(**request_data)


@pytest.mark.asyncio
async def test_modify_cache_cluster_basic():
    """Test basic modification of a cache cluster."""
    mock_client = MagicMock()
    mock_client.modify_cache_cluster.return_value = {
        'CacheCluster': {'CacheClusterId': 'test-cluster', 'NumCacheNodes': 3}
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        request = create_test_request(
            cache_cluster_id='test-cluster', num_cache_nodes=3, apply_immediately=True
        )
        result = await modify_cache_cluster(request)

    assert result['CacheCluster']['CacheClusterId'] == 'test-cluster'
    mock_client.modify_cache_cluster.assert_called_once_with(
        CacheClusterId='test-cluster', NumCacheNodes=3, ApplyImmediately=True
    )


@pytest.mark.asyncio
async def test_modify_cache_cluster_all_params():
    """Test modification with all parameters."""
    mock_client = MagicMock()
    mock_client.modify_cache_cluster.return_value = {
        'CacheCluster': {'CacheClusterId': 'test-cluster', 'Status': 'modifying'}
    }

    log_config = [
        {
            'LogType': 'slow-log',
            'DestinationType': 'cloudwatch-logs',
            'DestinationDetails': {'CloudWatchLogsDetails': {'LogGroup': '/aws/elasticache'}},
            'LogFormat': 'json',
            'Enabled': True,
        }
    ]

    scale_config = {
        'ReplicasPerNodeGroup': 2,
        'AutomaticFailoverEnabled': True,
        'ScaleOutEnabled': True,
        'ScaleInEnabled': True,
        'TargetCapacity': 4,
        'MinCapacity': 2,
        'MaxCapacity': 6,
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        request = create_test_request(
            cache_cluster_id='test-cluster',
            num_cache_nodes=3,
            cache_node_ids_to_remove=['0001', '0002'],
            az_mode='single-az',
            new_availability_zones=['us-west-2a'],
            cache_security_group_names=['sg-1'],
            security_group_ids=['sg-123'],
            preferred_maintenance_window='sun:05:00-sun:09:00',
            notification_topic_arn='arn:aws:sns:region:account:topic',
            cache_parameter_group_name='default.redis6.x',
            notification_topic_status='active',
            apply_immediately=True,
            engine_version='6.x',
            auto_minor_version_upgrade=True,
            snapshot_retention_limit=5,
            snapshot_window='05:00-09:00',
            cache_node_type='cache.t3.micro',
            auth_token='secret',
            auth_token_update_strategy='ROTATE',
            log_delivery_configurations=log_config,
            scale_config=scale_config,
        )
        result = await modify_cache_cluster(request)

    assert result['CacheCluster']['CacheClusterId'] == 'test-cluster'
    mock_client.modify_cache_cluster.assert_called_once_with(
        CacheClusterId='test-cluster',
        NumCacheNodes=3,
        CacheNodeIdsToRemove=['0001', '0002'],
        AZMode='single-az',
        NewAvailabilityZones=['us-west-2a'],
        CacheSecurityGroupNames=['sg-1'],
        SecurityGroupIds=['sg-123'],
        PreferredMaintenanceWindow='sun:05:00-sun:09:00',
        NotificationTopicArn='arn:aws:sns:region:account:topic',
        CacheParameterGroupName='default.redis6.x',
        NotificationTopicStatus='active',
        ApplyImmediately=True,
        EngineVersion='6.x',
        AutoMinorVersionUpgrade=True,
        SnapshotRetentionLimit=5,
        SnapshotWindow='05:00-09:00',
        CacheNodeType='cache.t3.micro',
        AuthToken='secret',
        AuthTokenUpdateStrategy='ROTATE',
        LogDeliveryConfigurations=log_config,
        ScaleConfig=scale_config,
    )


@pytest.mark.asyncio
async def test_modify_cache_cluster_shorthand_configs():
    """Test modification with shorthand configurations."""
    mock_client = MagicMock()
    mock_client.modify_cache_cluster.return_value = {
        'CacheCluster': {'CacheClusterId': 'test-cluster', 'Status': 'modifying'}
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        request = create_test_request(
            cache_cluster_id='test-cluster',
            log_delivery_configurations=(
                'LogType=slow-log,DestinationType=cloudwatch-logs,'
                'DestinationDetails={"CloudWatchLogsDetails":{"LogGroup":"/aws/elasticache"}},'
                'LogFormat=json,Enabled=true'
            ),
            scale_config=(
                'ReplicasPerNodeGroup=2,AutomaticFailoverEnabled=true,'
                'ScaleOutEnabled=true,ScaleInEnabled=true,'
                'TargetCapacity=4,MinCapacity=2,MaxCapacity=6'
            ),
        )
        result = await modify_cache_cluster(request)

    assert result['CacheCluster']['CacheClusterId'] == 'test-cluster'
    assert 'LogDeliveryConfigurations' in mock_client.modify_cache_cluster.call_args[1]
    assert 'ScaleConfig' in mock_client.modify_cache_cluster.call_args[1]


@pytest.mark.asyncio
async def test_modify_cache_cluster_scale_config_validation():
    """Test scale configuration validation."""
    mock_client = MagicMock()

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        # Test invalid capacity values
        request = create_test_request(
            cache_cluster_id='test-cluster',
            scale_config={'MinCapacity': 6, 'MaxCapacity': 4, 'TargetCapacity': 5},
        )
        result = await modify_cache_cluster(request)
        assert 'error' in result
        assert 'MinCapacity cannot be greater than MaxCapacity' in result['error']

        # Test invalid target capacity
        request = create_test_request(
            cache_cluster_id='test-cluster',
            scale_config={'MinCapacity': 2, 'MaxCapacity': 6, 'TargetCapacity': 8},
        )
        result = await modify_cache_cluster(request)
        assert 'error' in result
        assert 'TargetCapacity must be between MinCapacity and MaxCapacity' in result['error']
