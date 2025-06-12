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

"""Tests for create cache cluster tool."""

import pytest
from awslabs.elasticache_mcp_server.tools.cc.create import (
    CreateCacheClusterRequest,
    create_cache_cluster,
)
from typing import Any, Dict, List, Optional, TypedDict, Union
from unittest.mock import MagicMock, patch


class CreateRequestKwargs(TypedDict, total=False):
    """Type definition for create request kwargs."""

    cache_cluster_id: str
    cache_node_type: Optional[str]
    engine: Optional[str]
    engine_version: Optional[str]
    num_cache_nodes: Optional[int]
    preferred_availability_zone: Optional[str]
    preferred_availability_zones: Optional[List[str]]
    cache_parameter_group_name: Optional[str]
    cache_subnet_group_name: Optional[str]
    cache_security_group_names: Optional[List[str]]
    security_group_ids: Optional[List[str]]
    tags: Optional[Union[str, List[Dict[str, str]], Dict[str, str]]]
    snapshot_arns: Optional[List[str]]
    snapshot_name: Optional[str]
    preferred_maintenance_window: Optional[str]
    port: Optional[int]
    notification_topic_arn: Optional[str]
    auto_minor_version_upgrade: Optional[bool]
    snapshot_retention_limit: Optional[int]
    snapshot_window: Optional[str]
    auth_token: Optional[str]
    outpost_mode: Optional[str]
    preferred_outpost_arn: Optional[str]
    preferred_outpost_arns: Optional[List[str]]
    log_delivery_configurations: Optional[Union[str, List[Dict[str, Any]]]]


def create_test_request(
    cache_cluster_id: str = 'test-cluster',
    cache_node_type: Optional[str] = None,
    engine: Optional[str] = None,
    engine_version: Optional[str] = None,
    num_cache_nodes: Optional[int] = None,
    preferred_availability_zone: Optional[str] = None,
    preferred_availability_zones: Optional[List[str]] = None,
    cache_parameter_group_name: Optional[str] = None,
    cache_subnet_group_name: Optional[str] = None,
    cache_security_group_names: Optional[List[str]] = None,
    security_group_ids: Optional[List[str]] = None,
    tags: Optional[Union[str, List[Dict[str, str]], Dict[str, str]]] = None,
    snapshot_arns: Optional[List[str]] = None,
    snapshot_name: Optional[str] = None,
    preferred_maintenance_window: Optional[str] = None,
    port: Optional[int] = None,
    notification_topic_arn: Optional[str] = None,
    auto_minor_version_upgrade: Optional[bool] = None,
    snapshot_retention_limit: Optional[int] = None,
    snapshot_window: Optional[str] = None,
    auth_token: Optional[str] = None,
    outpost_mode: Optional[str] = None,
    preferred_outpost_arn: Optional[str] = None,
    preferred_outpost_arns: Optional[List[str]] = None,
    log_delivery_configurations: Optional[Union[str, List[Dict[str, Any]]]] = None,
) -> CreateCacheClusterRequest:
    """Create a test request with minimal required values."""
    request_data = {
        'cache_cluster_id': cache_cluster_id,
        **{k: v for k, v in locals().items() if k != 'cache_cluster_id' and v is not None},
    }
    return CreateCacheClusterRequest(**request_data)


@pytest.mark.asyncio
async def test_create_cache_cluster_basic():
    """Test basic cache cluster creation with required parameters."""
    mock_client = MagicMock()
    mock_client.create_cache_cluster.return_value = {
        'CacheCluster': {'CacheClusterId': 'test-cluster', 'CacheClusterStatus': 'creating'}
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        request = create_test_request()
        result = await create_cache_cluster(request)

    assert result['CacheCluster']['CacheClusterId'] == 'test-cluster'
    mock_client.create_cache_cluster.assert_called_once_with(CacheClusterId='test-cluster')


@pytest.mark.asyncio
async def test_create_memcached_cluster():
    """Test creating a memcached cluster with multiple nodes."""
    mock_client = MagicMock()
    mock_client.create_cache_cluster.return_value = {
        'CacheCluster': {'CacheClusterId': 'memProv', 'CacheClusterStatus': 'creating'}
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        request = create_test_request(
            cache_cluster_id='memProv',
            engine='memcached',
            num_cache_nodes=5,
            cache_node_type='cache.t3.micro',
        )
        result = await create_cache_cluster(request)

    assert result['CacheCluster']['CacheClusterId'] == 'memProv'
    mock_client.create_cache_cluster.assert_called_once_with(
        CacheClusterId='memProv',
        Engine='memcached',
        NumCacheNodes=5,
        CacheNodeType='cache.t3.micro',
    )


@pytest.mark.asyncio
async def test_create_cache_cluster_with_tags():
    """Test cache cluster creation with tags in different formats."""
    mock_client = MagicMock()
    mock_client.create_cache_cluster.return_value = {
        'CacheCluster': {'CacheClusterId': 'test-cluster', 'CacheClusterStatus': 'creating'}
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        # Test string format tags
        request = create_test_request(
            cache_cluster_id='test-cluster', tags='Key1=Value1,Key2=Value2'
        )
        result = await create_cache_cluster(request)
        assert result['CacheCluster']['CacheClusterId'] == 'test-cluster'
        mock_client.create_cache_cluster.assert_called_with(
            CacheClusterId='test-cluster',
            Tags=[{'Key': 'Key1', 'Value': 'Value1'}, {'Key': 'Key2', 'Value': 'Value2'}],
        )

        # Test dictionary format tags
        mock_client.reset_mock()
        request = create_test_request(
            cache_cluster_id='test-cluster', tags={'Key1': 'Value1', 'Key2': 'Value2'}
        )
        result = await create_cache_cluster(request)
        assert result['CacheCluster']['CacheClusterId'] == 'test-cluster'
        mock_client.create_cache_cluster.assert_called_with(
            CacheClusterId='test-cluster',
            Tags=[{'Key': 'Key1', 'Value': 'Value1'}, {'Key': 'Key2', 'Value': 'Value2'}],
        )


@pytest.mark.asyncio
async def test_create_cache_cluster_invalid_tags():
    """Test cache cluster creation with invalid tags."""
    mock_client = MagicMock()

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        # Test invalid tag format
        request = create_test_request(tags='InvalidFormat')
        result = await create_cache_cluster(request)
        assert 'error' in result
        assert 'Invalid tag format' in result['error']

        # Test empty key
        request = create_test_request(tags='=Value')
        result = await create_cache_cluster(request)
        assert 'error' in result
        assert 'Tag key cannot be empty' in result['error']


@pytest.mark.asyncio
async def test_create_cache_cluster_with_log_delivery():
    """Test cache cluster creation with log delivery configuration."""
    mock_client = MagicMock()
    mock_client.create_cache_cluster.return_value = {
        'CacheCluster': {'CacheClusterId': 'test-cluster', 'CacheClusterStatus': 'creating'}
    }

    log_config = [
        {
            'LogType': 'slow-log',
            'DestinationType': 'cloudwatch-logs',
            'DestinationDetails': {'CloudWatchLogsDetails': {'LogGroup': '/aws/elasticache/test'}},
            'LogFormat': 'json',
            'Enabled': True,
        }
    ]

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        request = create_test_request(
            cache_cluster_id='test-cluster', log_delivery_configurations=log_config
        )
        result = await create_cache_cluster(request)

    assert result['CacheCluster']['CacheClusterId'] == 'test-cluster'
    mock_client.create_cache_cluster.assert_called_once_with(
        CacheClusterId='test-cluster', LogDeliveryConfigurations=log_config
    )
