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

"""Additional coverage tests for replication group connection tools to achieve 100% coverage."""

import pytest
from awslabs.elasticache_mcp_server.tools.rg.connect import (
    _configure_security_groups,
    connect_jump_host_rg,
    create_jump_host_rg,
    get_ssh_tunnel_command_rg,
)
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_configure_security_groups_no_clients_provided():
    """Test _configure_security_groups when no clients are provided (lines 43, 45)."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock responses
    mock_elasticache.describe_replication_groups.return_value = {
        'ReplicationGroups': [
            {
                'MemberClusters': ['cluster-1', 'cluster-2'],
            }
        ]
    }
    first_cluster_response = {
        'CacheClusters': [
            {
                'CacheSubnetGroupName': 'subnet-group-1',
                'SecurityGroups': [{'SecurityGroupId': 'sg-123'}],
                'CacheNodes': [{'Endpoint': {'Port': 6379}}],
            }
        ]
    }
    mock_elasticache.describe_cache_clusters.side_effect = [
        first_cluster_response,  # First call to get first cluster details
        first_cluster_response,  # Second call in final loop (cluster-1)
        first_cluster_response,  # Third call in final loop (cluster-2)
    ]
    mock_elasticache.describe_cache_subnet_groups.return_value = {
        'CacheSubnetGroups': [{'VpcId': 'vpc-123'}]
    }

    mock_ec2.describe_instances.return_value = {
        'Reservations': [
            {
                'Instances': [
                    {
                        'VpcId': 'vpc-123',
                        'SecurityGroups': [{'GroupId': 'sg-instance'}],
                    }
                ]
            }
        ]
    }

    mock_ec2.describe_security_groups.return_value = {'SecurityGroups': [{'IpPermissions': []}]}

    with (
        patch(
            'awslabs.elasticache_mcp_server.common.connection.EC2ConnectionManager.get_connection',
            return_value=mock_ec2,
        ),
        patch(
            'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
            return_value=mock_elasticache,
        ),
    ):
        # Call without providing clients - should use connection managers (lines 43, 45)
        result = await _configure_security_groups('rg-test', 'i-123')

        assert result[0] is True  # success
        assert result[1] == 'vpc-123'  # vpc_id
        assert result[2] == 6379  # cache_port


@pytest.mark.asyncio
async def test_create_jump_host_rg_no_main_route_table():
    """Test create_jump_host_rg when no explicit route table association exists (line 376->375)."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock responses
    mock_ec2.describe_key_pairs.return_value = {'KeyPairs': [{'KeyName': 'test-key'}]}

    mock_elasticache.describe_replication_groups.return_value = {
        'ReplicationGroups': [{'MemberClusters': ['cluster-1']}]
    }
    mock_elasticache.describe_cache_clusters.return_value = {
        'CacheClusters': [
            {
                'CacheSubnetGroupName': 'subnet-group-1',
            }
        ]
    }
    mock_elasticache.describe_cache_subnet_groups.return_value = {
        'CacheSubnetGroups': [{'VpcId': 'vpc-123'}]
    }

    mock_ec2.describe_subnets.return_value = {
        'Subnets': [{'VpcId': 'vpc-123', 'MapPublicIpOnLaunch': True}]
    }

    # Mock no explicit route table association, then main route table
    mock_ec2.describe_route_tables.side_effect = [
        {'RouteTables': []},  # No explicit association
        {'RouteTables': [{'Routes': [{'GatewayId': 'igw-123'}]}]},  # Main route table with IGW
    ]

    mock_ec2.describe_images.return_value = {
        'Images': [{'ImageId': 'ami-123', 'CreationDate': '2023-01-01'}]
    }
    mock_ec2.describe_security_groups.return_value = {'SecurityGroups': [{'IpPermissions': []}]}
    mock_ec2.run_instances.return_value = {'Instances': [{'InstanceId': 'i-new'}]}
    mock_ec2.describe_instances.return_value = {
        'Reservations': [{'Instances': [{'PublicIpAddress': '1.2.3.4'}]}]
    }

    with (
        patch(
            'awslabs.elasticache_mcp_server.common.connection.EC2ConnectionManager.get_connection',
            return_value=mock_ec2,
        ),
        patch(
            'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
            return_value=mock_elasticache,
        ),
        patch(
            'awslabs.elasticache_mcp_server.tools.rg.connect._configure_security_groups',
            return_value=(True, 'vpc-123', 6379),
        ),
        patch('awslabs.elasticache_mcp_server.context.Context.readonly_mode', return_value=False),
    ):
        result = await create_jump_host_rg('rg-test', 'test-key', 'subnet-123', 'sg-123')

    # Verify successful creation
    assert result['InstanceId'] == 'i-new'
    assert result['PublicIpAddress'] == '1.2.3.4'


@pytest.mark.asyncio
async def test_create_jump_host_rg_igw_route_found():
    """Test create_jump_host_rg when IGW route is found in route table (line 390->394)."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock responses
    mock_ec2.describe_key_pairs.return_value = {'KeyPairs': [{'KeyName': 'test-key'}]}

    mock_elasticache.describe_replication_groups.return_value = {
        'ReplicationGroups': [{'MemberClusters': ['cluster-1']}]
    }
    mock_elasticache.describe_cache_clusters.return_value = {
        'CacheClusters': [
            {
                'CacheSubnetGroupName': 'subnet-group-1',
            }
        ]
    }
    mock_elasticache.describe_cache_subnet_groups.return_value = {
        'CacheSubnetGroups': [{'VpcId': 'vpc-123'}]
    }

    mock_ec2.describe_subnets.return_value = {
        'Subnets': [{'VpcId': 'vpc-123', 'MapPublicIpOnLaunch': True}]
    }

    # Mock route table with IGW route
    mock_ec2.describe_route_tables.return_value = {
        'RouteTables': [
            {
                'Routes': [
                    {'GatewayId': 'local'},
                    {'GatewayId': 'igw-123'},  # IGW route found - line 390->394
                ]
            }
        ]
    }

    mock_ec2.describe_images.return_value = {
        'Images': [{'ImageId': 'ami-123', 'CreationDate': '2023-01-01'}]
    }
    mock_ec2.describe_security_groups.return_value = {'SecurityGroups': [{'IpPermissions': []}]}
    mock_ec2.run_instances.return_value = {'Instances': [{'InstanceId': 'i-new'}]}
    mock_ec2.describe_instances.return_value = {
        'Reservations': [{'Instances': [{'PublicIpAddress': '1.2.3.4'}]}]
    }

    with (
        patch(
            'awslabs.elasticache_mcp_server.common.connection.EC2ConnectionManager.get_connection',
            return_value=mock_ec2,
        ),
        patch(
            'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
            return_value=mock_elasticache,
        ),
        patch(
            'awslabs.elasticache_mcp_server.tools.rg.connect._configure_security_groups',
            return_value=(True, 'vpc-123', 6379),
        ),
        patch('awslabs.elasticache_mcp_server.context.Context.readonly_mode', return_value=False),
    ):
        result = await create_jump_host_rg('rg-test', 'test-key', 'subnet-123', 'sg-123')

    # Verify successful creation
    assert result['InstanceId'] == 'i-new'
    assert result['PublicIpAddress'] == '1.2.3.4'


@pytest.mark.asyncio
async def test_create_jump_host_rg_ssh_rule_already_exists():
    """Test create_jump_host_rg when SSH rule already exists in security group (line 449->452)."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock responses
    mock_ec2.describe_key_pairs.return_value = {'KeyPairs': [{'KeyName': 'test-key'}]}

    mock_elasticache.describe_replication_groups.return_value = {
        'ReplicationGroups': [{'MemberClusters': ['cluster-1']}]
    }
    mock_elasticache.describe_cache_clusters.return_value = {
        'CacheClusters': [
            {
                'CacheSubnetGroupName': 'subnet-group-1',
            }
        ]
    }
    mock_elasticache.describe_cache_subnet_groups.return_value = {
        'CacheSubnetGroups': [{'VpcId': 'vpc-123'}]
    }

    mock_ec2.describe_subnets.return_value = {
        'Subnets': [{'VpcId': 'vpc-123', 'MapPublicIpOnLaunch': True}]
    }

    mock_ec2.describe_route_tables.return_value = {
        'RouteTables': [{'Routes': [{'GatewayId': 'igw-123'}]}]
    }

    mock_ec2.describe_images.return_value = {
        'Images': [{'ImageId': 'ami-123', 'CreationDate': '2023-01-01'}]
    }

    # Mock security group with existing SSH rule
    mock_ec2.describe_security_groups.return_value = {
        'SecurityGroups': [
            {
                'IpPermissions': [
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 22,
                        'ToPort': 22,
                        'IpRanges': [
                            {'CidrIp': '0.0.0.0/0'}
                        ],  # SSH rule already exists - line 449->452
                    }
                ]
            }
        ]
    }

    mock_ec2.run_instances.return_value = {'Instances': [{'InstanceId': 'i-new'}]}
    mock_ec2.describe_instances.return_value = {
        'Reservations': [{'Instances': [{'PublicIpAddress': '1.2.3.4'}]}]
    }

    with (
        patch(
            'awslabs.elasticache_mcp_server.common.connection.EC2ConnectionManager.get_connection',
            return_value=mock_ec2,
        ),
        patch(
            'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
            return_value=mock_elasticache,
        ),
        patch(
            'awslabs.elasticache_mcp_server.tools.rg.connect._configure_security_groups',
            return_value=(True, 'vpc-123', 6379),
        ),
        patch('awslabs.elasticache_mcp_server.context.Context.readonly_mode', return_value=False),
    ):
        result = await create_jump_host_rg('rg-test', 'test-key', 'subnet-123', 'sg-123')

    # Verify successful creation and that SSH rule was not added again
    assert result['InstanceId'] == 'i-new'
    assert result['PublicIpAddress'] == '1.2.3.4'

    # Verify authorize_security_group_ingress was not called since rule already exists
    mock_ec2.authorize_security_group_ingress.assert_not_called()


@pytest.mark.asyncio
async def test_connect_jump_host_rg_readonly_mode():
    """Test connect_jump_host_rg in readonly mode."""
    with patch('awslabs.elasticache_mcp_server.context.Context.readonly_mode', return_value=True):
        result = await connect_jump_host_rg('rg-test', 'i-123')
        assert 'error' in result
        assert 'You have configured this tool in readonly mode' in result['error']


@pytest.mark.asyncio
async def test_get_ssh_tunnel_command_rg_no_configuration_endpoint():
    """Test get_ssh_tunnel_command_rg when no ConfigurationEndpoint is found."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock EC2 responses
    mock_ec2.describe_instances.return_value = {
        'Reservations': [
            {
                'Instances': [
                    {
                        'KeyName': 'test-key',
                        'PublicDnsName': 'ec2-1-2-3-4.compute-1.amazonaws.com',
                        'Platform': '',
                    }
                ]
            }
        ]
    }

    # Mock ElastiCache responses without ConfigurationEndpoint
    mock_elasticache.describe_replication_groups.return_value = {
        'ReplicationGroups': [
            {
                'MemberClusters': ['cluster-1', 'cluster-2'],
                # No ConfigurationEndpoint
            }
        ]
    }

    with (
        patch(
            'awslabs.elasticache_mcp_server.common.connection.EC2ConnectionManager.get_connection',
            return_value=mock_ec2,
        ),
        patch(
            'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
            return_value=mock_elasticache,
        ),
    ):
        result = await get_ssh_tunnel_command_rg('rg-test', 'i-123')
        assert 'error' in result
        assert 'No ConfigurationEndpoint found for replication group rg-test' in result['error']


@pytest.mark.asyncio
async def test_create_jump_host_rg_readonly_mode():
    """Test create_jump_host_rg in readonly mode."""
    with patch('awslabs.elasticache_mcp_server.context.Context.readonly_mode', return_value=True):
        result = await create_jump_host_rg('rg-test', 'test-key')
        assert 'error' in result
        assert 'You have configured this tool in readonly mode' in result['error']
