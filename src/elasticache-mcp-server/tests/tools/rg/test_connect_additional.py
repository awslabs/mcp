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

"""Additional tests for replication group connection tools to improve coverage."""

import pytest
from awslabs.elasticache_mcp_server.tools.rg.connect import (
    _configure_security_groups,
    connect_jump_host_rg,
    create_jump_host_rg,
    get_ssh_tunnel_command_rg,
)
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_configure_security_groups_no_cache_clusters():
    """Test when no cache clusters are found."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock ElastiCache responses
    mock_elasticache.describe_replication_groups.return_value = {
        'ReplicationGroups': [
            {
                'MemberClusters': [],  # Empty member clusters
            }
        ]
    }

    # Verify exception is raised
    with pytest.raises(ValueError) as excinfo:
        await _configure_security_groups(
            'rg-test',
            'i-123',
            ec2_client=mock_ec2,
            elasticache_client=mock_elasticache,
        )
    assert 'No clusters found in replication group' in str(excinfo.value)


@pytest.mark.asyncio
async def test_configure_security_groups_no_subnet_group():
    """Test when no subnet group is found."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock ElastiCache responses
    mock_elasticache.describe_replication_groups.return_value = {
        'ReplicationGroups': [
            {
                'MemberClusters': ['cluster-1'],
            }
        ]
    }
    # Cluster without subnet group
    mock_elasticache.describe_cache_clusters.return_value = {
        'CacheClusters': [
            {
                # No CacheSubnetGroupName
            }
        ]
    }

    # Verify exception is raised
    with pytest.raises(ValueError) as excinfo:
        await _configure_security_groups(
            'rg-test',
            'i-123',
            ec2_client=mock_ec2,
            elasticache_client=mock_elasticache,
        )
    assert 'No cache subnet group found' in str(excinfo.value)


@pytest.mark.asyncio
async def test_configure_security_groups_subnet_group_error():
    """Test when there's an error getting the subnet group."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock ElastiCache responses
    mock_elasticache.describe_replication_groups.return_value = {
        'ReplicationGroups': [
            {
                'MemberClusters': ['cluster-1'],
            }
        ]
    }
    mock_elasticache.describe_cache_clusters.return_value = {
        'CacheClusters': [
            {
                'CacheSubnetGroupName': 'subnet-group-1',
            }
        ]
    }
    # Error getting subnet group
    mock_elasticache.describe_cache_subnet_groups.side_effect = Exception('Subnet group not found')

    # Verify exception is raised
    with pytest.raises(ValueError) as excinfo:
        await _configure_security_groups(
            'rg-test',
            'i-123',
            ec2_client=mock_ec2,
            elasticache_client=mock_elasticache,
        )
    assert 'Failed to get cache subnet group' in str(excinfo.value)


@pytest.mark.asyncio
async def test_configure_security_groups_instance_not_found():
    """Test when EC2 instance is not found."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock ElastiCache responses
    mock_elasticache.describe_replication_groups.return_value = {
        'ReplicationGroups': [
            {
                'MemberClusters': ['cluster-1'],
            }
        ]
    }
    mock_elasticache.describe_cache_clusters.return_value = {
        'CacheClusters': [
            {
                'CacheClusterRole': 'PRIMARY',
                'CacheSubnetGroupName': 'subnet-group-1',
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
            'rg-test',
            'i-123',
            ec2_client=mock_ec2,
            elasticache_client=mock_elasticache,
        )
    assert 'EC2 instance i-123 not found' in str(excinfo.value)


@pytest.mark.asyncio
async def test_configure_security_groups_no_cache_security_groups():
    """Test when no security groups are found for the cache cluster."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock ElastiCache responses
    mock_elasticache.describe_replication_groups.return_value = {
        'ReplicationGroups': [
            {
                'MemberClusters': ['cluster-1'],
            }
        ]
    }
    mock_elasticache.describe_cache_clusters.return_value = {
        'CacheClusters': [
            {
                'CacheClusterRole': 'PRIMARY',
                'CacheSubnetGroupName': 'subnet-group-1',
                'SecurityGroups': [],  # Empty security groups
                'CacheNodes': [{'Endpoint': {'Port': 6379}}],
            }
        ]
    }
    mock_elasticache.describe_cache_subnet_groups.return_value = {
        'CacheSubnetGroups': [{'VpcId': 'vpc-123'}]
    }

    mock_ec2.describe_instances.return_value = {
        'Reservations': [
            {
                'Instances': [
                    {
                        'VpcId': 'vpc-123',
                        'SecurityGroups': [{'GroupId': 'sg-456'}],
                    }
                ]
            }
        ]
    }

    # Verify exception is raised
    with pytest.raises(ValueError) as excinfo:
        await _configure_security_groups(
            'rg-test',
            'i-123',
            ec2_client=mock_ec2,
            elasticache_client=mock_elasticache,
        )
    assert 'No security groups found for replication group' in str(excinfo.value)


@pytest.mark.asyncio
async def test_configure_security_groups_no_instance_security_groups():
    """Test when no security groups are found for the EC2 instance."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock ElastiCache responses
    mock_elasticache.describe_replication_groups.return_value = {
        'ReplicationGroups': [
            {
                'MemberClusters': ['cluster-1'],
            }
        ]
    }
    mock_elasticache.describe_cache_clusters.return_value = {
        'CacheClusters': [
            {
                'CacheClusterRole': 'PRIMARY',
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
            'rg-test',
            'i-123',
            ec2_client=mock_ec2,
            elasticache_client=mock_elasticache,
        )
    assert 'No security groups found for EC2 instance' in str(excinfo.value)


@pytest.mark.asyncio
async def test_connect_jump_host_rg_error():
    """Test error handling in connect_jump_host_rg."""
    # Mock an error in _configure_security_groups
    with patch(
        'awslabs.elasticache_mcp_server.tools.rg.connect._configure_security_groups',
        side_effect=ValueError('Test error'),
    ):
        result = await connect_jump_host_rg('rg-test', 'i-123')
        assert 'error' in result
        assert 'Test error' in result['error']


@pytest.mark.asyncio
async def test_get_ssh_tunnel_command_rg_instance_not_found():
    """Test get_ssh_tunnel_command_rg when instance is not found."""
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
        result = await get_ssh_tunnel_command_rg('rg-test', 'i-123')
        assert 'error' in result
        assert 'EC2 instance i-123 not found' in result['error']


@pytest.mark.asyncio
async def test_get_ssh_tunnel_command_rg_no_key_pair():
    """Test get_ssh_tunnel_command_rg when instance has no key pair."""
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
        result = await get_ssh_tunnel_command_rg('rg-test', 'i-123')
        assert 'error' in result
        assert 'No key pair associated with EC2 instance' in result['error']


@pytest.mark.asyncio
async def test_get_ssh_tunnel_command_rg_no_public_dns():
    """Test get_ssh_tunnel_command_rg when instance has no public DNS."""
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
        result = await get_ssh_tunnel_command_rg('rg-test', 'i-123')
        assert 'error' in result
        assert 'No public DNS name found for EC2 instance' in result['error']


@pytest.mark.asyncio
async def test_get_ssh_tunnel_command_rg_windows_instance():
    """Test get_ssh_tunnel_command_rg with Windows instance."""
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
        result = await get_ssh_tunnel_command_rg('rg-test', 'i-123')
        assert 'error' in result
        assert 'Windows instances are not supported for SSH tunneling' in result['error']


@pytest.mark.asyncio
async def test_get_ssh_tunnel_command_rg_no_configuration_endpoint():
    """Test get_ssh_tunnel_command_rg when replication group has no ConfigurationEndpoint."""
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

    # Mock ElastiCache responses with no ConfigurationEndpoint
    mock_elasticache.describe_replication_groups.return_value = {
        'ReplicationGroups': [
            {
                # No ConfigurationEndpoint
                'MemberClusters': ['cluster-1']
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
        assert 'No ConfigurationEndpoint found for replication group' in result['error']


@pytest.mark.asyncio
async def test_create_jump_host_rg_vpc_mismatch():
    """Test create_jump_host_rg with VPC mismatch."""
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
                'CacheClusterRole': 'PRIMARY',
                'CacheSubnetGroupName': 'subnet-group-1',
            }
        ]
    }
    mock_elasticache.describe_cache_subnet_groups.return_value = {
        'CacheSubnetGroups': [{'VpcId': 'vpc-123'}]
    }

    # VPC mismatch
    mock_ec2.describe_subnets.return_value = {'Subnets': [{'VpcId': 'vpc-456'}]}

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
        result = await create_jump_host_rg('rg-test', 'subnet-123', 'sg-123', 'test-key')
        assert 'error' in result
        assert (
            'Subnet VPC (vpc-456) does not match replication group VPC (vpc-123)'
            in result['error']
        )


@pytest.mark.asyncio
async def test_create_jump_host_rg_main_route_table():
    """Test create_jump_host_rg with main route table."""
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
                'CacheClusterRole': 'PRIMARY',
                'CacheSubnetGroupName': 'subnet-group-1',
            }
        ]
    }
    mock_elasticache.describe_cache_subnet_groups.return_value = {
        'CacheSubnetGroups': [{'VpcId': 'vpc-123'}]
    }

    mock_ec2.describe_subnets.return_value = {'Subnets': [{'VpcId': 'vpc-123'}]}

    # No explicit route table association, but main route table has IGW
    mock_ec2.describe_route_tables.side_effect = [
        {'RouteTables': []},  # First call for subnet-specific route table
        {
            'RouteTables': [{'Routes': [{'GatewayId': 'igw-123'}]}]
        },  # Second call for main route table
    ]

    mock_ec2.describe_images.return_value = {
        'Images': [{'ImageId': 'ami-123', 'CreationDate': '2023-01-01'}]
    }
    mock_ec2.describe_security_groups.return_value = {'SecurityGroups': [{'IpPermissions': []}]}
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
            'awslabs.elasticache_mcp_server.tools.rg.connect._configure_security_groups',
            return_value=(True, 'vpc-123', 6379),
        ),
    ):
        result = await create_jump_host_rg('rg-test', 'subnet-123', 'sg-123', 'test-key')

        # Should succeed because main route table has IGW
        assert 'InstanceId' in result
        assert result['InstanceId'] == 'i-new1234'


@pytest.mark.asyncio
async def test_create_jump_host_rg_existing_ssh_rule():
    """Test create_jump_host_rg with existing SSH rule."""
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
                'CacheClusterRole': 'PRIMARY',
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
            'awslabs.elasticache_mcp_server.tools.rg.connect._configure_security_groups',
            return_value=(True, 'vpc-123', 6379),
        ),
    ):
        result = await create_jump_host_rg('rg-test', 'subnet-123', 'sg-123', 'test-key')

        # Should succeed and not try to add SSH rule
        assert 'InstanceId' in result
        assert result['InstanceId'] == 'i-new1234'
        mock_ec2.authorize_security_group_ingress.assert_not_called()


@pytest.mark.asyncio
async def test_create_jump_host_rg_no_member_clusters():
    """Test create_jump_host_rg when replication group has no member clusters."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock responses
    mock_ec2.describe_key_pairs.return_value = {'KeyPairs': [{'KeyName': 'test-key'}]}

    # Replication group with no member clusters
    mock_elasticache.describe_replication_groups.return_value = {
        'ReplicationGroups': [{'MemberClusters': []}]
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
        result = await create_jump_host_rg('rg-test', 'subnet-123', 'sg-123', 'test-key')

        # Should fail with appropriate error message
        assert 'error' in result
        assert 'No clusters found in replication group rg-test' in result['error']


@pytest.mark.asyncio
async def test_get_ssh_tunnel_command_rg_no_member_clusters():
    """Test get_ssh_tunnel_command_rg when replication group has no member clusters."""
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

    # Replication group with no member clusters
    mock_elasticache.describe_replication_groups.return_value = {
        'ReplicationGroups': [
            {
                'ConfigurationEndpoint': {'Address': 'config.cache.amazonaws.com', 'Port': 6379},
                'MemberClusters': [],  # Empty member clusters
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
        # The function should still work since it doesn't directly use MemberClusters
        result = await get_ssh_tunnel_command_rg('rg-test', 'i-123')

        # Should succeed since get_ssh_tunnel_command_rg doesn't check MemberClusters
        assert 'command' in result
        assert 'ssh -i "test-key.pem"' in result['command']
        assert 'config.cache.amazonaws.com' in result['command']


@pytest.mark.asyncio
async def test_connect_jump_host_rg_no_member_clusters():
    """Test connect_jump_host_rg when replication group has no member clusters."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Replication group with no member clusters
    mock_elasticache.describe_replication_groups.return_value = {
        'ReplicationGroups': [{'MemberClusters': []}]
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
            side_effect=ValueError('No clusters found in replication group rg-test'),
        ),
    ):
        result = await connect_jump_host_rg('rg-test', 'i-123')

        # Should fail with appropriate error message
        assert 'error' in result
        assert 'No clusters found in replication group rg-test' in result['error']
