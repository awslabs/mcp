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

"""Additional tests for cache cluster connection tools to improve coverage."""

import pytest
from awslabs.elasticache_mcp_server.tools.cc.connect import (
    _configure_security_groups,
    connect_jump_host_cc,
    create_jump_host_cc,
    get_ssh_tunnel_command_cc,
)
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_configure_security_groups_no_subnet_group():
    """Test when no subnet group is found."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock ElastiCache responses with missing subnet group
    mock_elasticache.describe_cache_clusters.return_value = {
        'CacheClusters': [
            {
                # No CacheSubnetGroupName
            }
        ]
    }

    # Verify exception is raised
    with pytest.raises(KeyError):
        await _configure_security_groups(
            'cluster-1',
            'i-123',
            ec2_client=mock_ec2,
            elasticache_client=mock_elasticache,
        )


@pytest.mark.asyncio
async def test_configure_security_groups_no_security_groups():
    """Test when no security groups are found for the cache cluster."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock ElastiCache responses
    mock_elasticache.describe_cache_clusters.return_value = {
        'CacheClusters': [
            {
                'CacheSubnetGroupName': 'subnet-group-1',
                # No SecurityGroups
                'CacheNodes': [{'Endpoint': {'Port': 6379}}],
            }
        ]
    }
    mock_elasticache.describe_cache_subnet_groups.return_value = {
        'CacheSubnetGroups': [{'VpcId': 'vpc-123'}]
    }

    # Verify exception is raised
    with pytest.raises(ValueError) as excinfo:
        await _configure_security_groups(
            'cluster-1',
            'i-123',
            ec2_client=mock_ec2,
            elasticache_client=mock_elasticache,
        )
    assert 'No security groups found for cache cluster' in str(excinfo.value)


@pytest.mark.asyncio
async def test_configure_security_groups_no_cache_nodes():
    """Test when no cache nodes are found for the cache cluster."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock ElastiCache responses
    mock_elasticache.describe_cache_clusters.return_value = {
        'CacheClusters': [
            {
                'CacheSubnetGroupName': 'subnet-group-1',
                'SecurityGroups': [{'SecurityGroupId': 'sg-123'}],
                'CacheNodes': [],  # Empty cache nodes
            }
        ]
    }
    mock_elasticache.describe_cache_subnet_groups.return_value = {
        'CacheSubnetGroups': [{'VpcId': 'vpc-123'}]
    }

    # Verify exception is raised
    with pytest.raises(IndexError):
        await _configure_security_groups(
            'cluster-1',
            'i-123',
            ec2_client=mock_ec2,
            elasticache_client=mock_elasticache,
        )


@pytest.mark.asyncio
async def test_configure_security_groups_instance_not_found():
    """Test when EC2 instance is not found."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock ElastiCache responses
    mock_elasticache.describe_cache_clusters.return_value = {
        'CacheClusters': [
            {
                'CacheSubnetGroupName': 'subnet-group-1',
                'SecurityGroups': [{'SecurityGroupId': 'sg-123'}],
                'CacheNodes': [{'Endpoint': {'Port': 6379}}],
            }
        ]
    }
    mock_elasticache.describe_cache_subnet_groups.return_value = {
        'CacheSubnetGroups': [{'VpcId': 'vpc-123'}]
    }

    # Instance not found
    mock_ec2.describe_instances.return_value = {'Reservations': []}

    # Verify exception is raised
    with pytest.raises(ValueError) as excinfo:
        await _configure_security_groups(
            'cluster-1',
            'i-123',
            ec2_client=mock_ec2,
            elasticache_client=mock_elasticache,
        )
    assert 'EC2 instance i-123 not found' in str(excinfo.value)


@pytest.mark.asyncio
async def test_configure_security_groups_no_instance_security_groups():
    """Test when no security groups are found for the EC2 instance."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock ElastiCache responses
    mock_elasticache.describe_cache_clusters.return_value = {
        'CacheClusters': [
            {
                'CacheSubnetGroupName': 'subnet-group-1',
                'SecurityGroups': [{'SecurityGroupId': 'sg-123'}],
                'CacheNodes': [{'Endpoint': {'Port': 6379}}],
            }
        ]
    }
    mock_elasticache.describe_cache_subnet_groups.return_value = {
        'CacheSubnetGroups': [{'VpcId': 'vpc-123'}]
    }

    # Instance with no security groups
    mock_ec2.describe_instances.return_value = {
        'Reservations': [
            {
                'Instances': [
                    {
                        'VpcId': 'vpc-123',
                        'SecurityGroups': [],  # Empty security groups
                    }
                ]
            }
        ]
    }

    # Verify exception is raised
    with pytest.raises(ValueError) as excinfo:
        await _configure_security_groups(
            'cluster-1',
            'i-123',
            ec2_client=mock_ec2,
            elasticache_client=mock_elasticache,
        )
    assert 'No security groups found for EC2 instance' in str(excinfo.value)


@pytest.mark.asyncio
async def test_connect_jump_host_cc_error():
    """Test error handling in connect_jump_host_cc."""
    # Mock an error in _configure_security_groups
    with patch(
        'awslabs.elasticache_mcp_server.tools.cc.connect._configure_security_groups',
        side_effect=ValueError('Test error'),
    ):
        result = await connect_jump_host_cc('cluster-1', 'i-123')
        assert 'error' in result
        assert 'Test error' in result['error']


@pytest.mark.asyncio
async def test_get_ssh_tunnel_command_cc_instance_not_found():
    """Test get_ssh_tunnel_command_cc when instance is not found."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Instance not found
    mock_ec2.describe_instances.return_value = {'Reservations': []}

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
        result = await get_ssh_tunnel_command_cc('cluster-1', 'i-123')
        assert 'error' in result
        assert 'EC2 instance i-123 not found' in result['error']


@pytest.mark.asyncio
async def test_get_ssh_tunnel_command_cc_no_key_pair():
    """Test get_ssh_tunnel_command_cc when instance has no key pair."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Instance with no key pair
    mock_ec2.describe_instances.return_value = {
        'Reservations': [
            {
                'Instances': [
                    {
                        # No KeyName
                    }
                ]
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
        result = await get_ssh_tunnel_command_cc('cluster-1', 'i-123')
        assert 'error' in result
        assert 'No key pair associated with EC2 instance' in result['error']


@pytest.mark.asyncio
async def test_get_ssh_tunnel_command_cc_no_public_dns():
    """Test get_ssh_tunnel_command_cc when instance has no public DNS."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Instance with no public DNS
    mock_ec2.describe_instances.return_value = {
        'Reservations': [
            {
                'Instances': [
                    {
                        'KeyName': 'test-key',
                        # No PublicDnsName
                    }
                ]
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
        result = await get_ssh_tunnel_command_cc('cluster-1', 'i-123')
        assert 'error' in result
        assert 'No public DNS name found for EC2 instance' in result['error']


@pytest.mark.asyncio
async def test_get_ssh_tunnel_command_cc_windows_instance():
    """Test get_ssh_tunnel_command_cc with Windows instance."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Windows instance
    mock_ec2.describe_instances.return_value = {
        'Reservations': [
            {
                'Instances': [
                    {
                        'KeyName': 'test-key',
                        'PublicDnsName': 'ec2-1-2-3-4.compute-1.amazonaws.com',
                        'Platform': 'windows',
                    }
                ]
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
        result = await get_ssh_tunnel_command_cc('cluster-1', 'i-123')
        assert 'error' in result
        assert 'Windows instances are not supported for SSH tunneling' in result['error']


@pytest.mark.asyncio
async def test_get_ssh_tunnel_command_cc_no_cache_nodes():
    """Test get_ssh_tunnel_command_cc when cluster has no cache nodes."""
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

    # Mock ElastiCache responses
    # Cluster with no cache nodes
    mock_elasticache.describe_cache_clusters.return_value = {
        'CacheClusters': [
            {
                'CacheNodes': [],  # Empty cache nodes
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
        result = await get_ssh_tunnel_command_cc('cluster-1', 'i-123')
        assert 'error' in result
        assert 'No cache nodes found for cluster cluster-1' in result['error']


@pytest.mark.asyncio
async def test_create_jump_host_cc_main_route_table():
    """Test create_jump_host_cc with main route table."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock responses
    mock_ec2.describe_key_pairs.return_value = {'KeyPairs': [{'KeyName': 'test-key'}]}

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

    mock_ec2.describe_subnets.return_value = {'Subnets': [{'VpcId': 'vpc-123'}]}

    # No explicit route table association, but main route table has no IGW
    mock_ec2.describe_route_tables.side_effect = [
        {'RouteTables': []},  # First call for subnet-specific route table
        {'RouteTables': [{'Routes': []}]},  # Second call for main route table with no IGW
    ]

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
        result = await create_jump_host_cc('cluster-1', 'subnet-123', 'sg-123', 'test-key')

        # Should fail because subnet is not public
        assert 'error' in result
        assert (
            'Subnet subnet-123 is not public (no route to internet gateway found)'
            in result['error']
        )


@pytest.mark.asyncio
async def test_create_jump_host_cc_existing_ssh_rule():
    """Test create_jump_host_cc with existing SSH rule."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock responses
    mock_ec2.describe_key_pairs.return_value = {'KeyPairs': [{'KeyName': 'test-key'}]}

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

    mock_ec2.describe_subnets.return_value = {'Subnets': [{'VpcId': 'vpc-123'}]}
    mock_ec2.describe_route_tables.return_value = {
        'RouteTables': [{'Routes': [{'GatewayId': 'igw-123'}]}]
    }
    mock_ec2.describe_images.return_value = {
        'Images': [{'ImageId': 'ami-123', 'CreationDate': '2023-01-01'}]
    }

    # Security group with existing SSH rule
    mock_ec2.describe_security_groups.return_value = {
        'SecurityGroups': [
            {
                'IpPermissions': [
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 22,
                        'ToPort': 22,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}],
                    }
                ]
            }
        ]
    }

    mock_ec2.run_instances.return_value = {'Instances': [{'InstanceId': 'i-new1234'}]}
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
            'awslabs.elasticache_mcp_server.tools.cc.connect._configure_security_groups',
            return_value=(True, 'vpc-123', 6379),
        ),
    ):
        result = await create_jump_host_cc('cluster-1', 'subnet-123', 'sg-123', 'test-key')

        # Should succeed and not try to add SSH rule
        assert 'InstanceId' in result
        assert result['InstanceId'] == 'i-new1234'
        mock_ec2.authorize_security_group_ingress.assert_not_called()
