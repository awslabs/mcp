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

"""Additional coverage tests for cache cluster connection tools to achieve 100% coverage."""

import pytest
from awslabs.elasticache_mcp_server.tools.cc.connect import (
    _configure_security_groups,
    connect_jump_host_cc,
    create_jump_host_cc,
    get_ssh_tunnel_command_cc,
)
from botocore.exceptions import ClientError
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_configure_security_groups_no_clients_provided():
    """Test _configure_security_groups when no clients are provided (lines 43, 45)."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock responses
    mock_elasticache.describe_cache_clusters.return_value = {
        'CacheClusters': [
            {
                'CacheSubnetGroupName': 'subnet-group-1',
                'SecurityGroups': [{'SecurityGroupId': 'sg-cache'}],
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
        # Call without providing clients - should use connection managers
        result = await _configure_security_groups('cluster-1', 'i-123')

        assert result[0] is True  # success
        assert result[1] == 'vpc-123'  # vpc_id
        assert result[2] == 6379  # cache_port


@pytest.mark.asyncio
async def test_configure_security_groups_no_cache_security_groups():
    """Test _configure_security_groups when cache has no security groups (line ~57)."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock cache cluster with no security groups
    mock_elasticache.describe_cache_clusters.return_value = {
        'CacheClusters': [
            {
                'CacheSubnetGroupName': 'subnet-group-1',
                'SecurityGroups': [],  # No security groups
                'CacheNodes': [{'Endpoint': {'Port': 6379}}],
            }
        ]
    }
    mock_elasticache.describe_cache_subnet_groups.return_value = {
        'CacheSubnetGroups': [{'VpcId': 'vpc-123'}]
    }

    with pytest.raises(ValueError, match='No security groups found for cache cluster cluster-1'):
        await _configure_security_groups('cluster-1', 'i-123', mock_ec2, mock_elasticache)


@pytest.mark.asyncio
async def test_configure_security_groups_no_instance_found():
    """Test _configure_security_groups when EC2 instance is not found (line ~67)."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock cache cluster
    mock_elasticache.describe_cache_clusters.return_value = {
        'CacheClusters': [
            {
                'CacheSubnetGroupName': 'subnet-group-1',
                'SecurityGroups': [{'SecurityGroupId': 'sg-cache'}],
                'CacheNodes': [{'Endpoint': {'Port': 6379}}],
            }
        ]
    }
    mock_elasticache.describe_cache_subnet_groups.return_value = {
        'CacheSubnetGroups': [{'VpcId': 'vpc-123'}]
    }

    # Mock no instance found
    mock_ec2.describe_instances.return_value = {'Reservations': []}

    with pytest.raises(ValueError, match='EC2 instance i-123 not found'):
        await _configure_security_groups('cluster-1', 'i-123', mock_ec2, mock_elasticache)


@pytest.mark.asyncio
async def test_configure_security_groups_vpc_mismatch():
    """Test _configure_security_groups when VPCs don't match (line ~75)."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock cache cluster in vpc-123
    mock_elasticache.describe_cache_clusters.return_value = {
        'CacheClusters': [
            {
                'CacheSubnetGroupName': 'subnet-group-1',
                'SecurityGroups': [{'SecurityGroupId': 'sg-cache'}],
                'CacheNodes': [{'Endpoint': {'Port': 6379}}],
            }
        ]
    }
    mock_elasticache.describe_cache_subnet_groups.return_value = {
        'CacheSubnetGroups': [{'VpcId': 'vpc-123'}]
    }

    # Mock instance in different VPC
    mock_ec2.describe_instances.return_value = {
        'Reservations': [
            {
                'Instances': [
                    {
                        'VpcId': 'vpc-456',  # Different VPC
                        'SecurityGroups': [{'GroupId': 'sg-instance'}],
                    }
                ]
            }
        ]
    }

    with pytest.raises(
        ValueError,
        match='EC2 instance VPC \\(vpc-456\\) does not match cache cluster VPC \\(vpc-123\\)',
    ):
        await _configure_security_groups('cluster-1', 'i-123', mock_ec2, mock_elasticache)


@pytest.mark.asyncio
async def test_configure_security_groups_no_instance_security_groups():
    """Test _configure_security_groups when instance has no security groups (line ~82)."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock cache cluster
    mock_elasticache.describe_cache_clusters.return_value = {
        'CacheClusters': [
            {
                'CacheSubnetGroupName': 'subnet-group-1',
                'SecurityGroups': [{'SecurityGroupId': 'sg-cache'}],
                'CacheNodes': [{'Endpoint': {'Port': 6379}}],
            }
        ]
    }
    mock_elasticache.describe_cache_subnet_groups.return_value = {
        'CacheSubnetGroups': [{'VpcId': 'vpc-123'}]
    }

    # Mock instance with no security groups
    mock_ec2.describe_instances.return_value = {
        'Reservations': [
            {
                'Instances': [
                    {
                        'VpcId': 'vpc-123',
                        'SecurityGroups': [],  # No security groups
                    }
                ]
            }
        ]
    }

    with pytest.raises(ValueError, match='No security groups found for EC2 instance i-123'):
        await _configure_security_groups('cluster-1', 'i-123', mock_ec2, mock_elasticache)


@pytest.mark.asyncio
async def test_connect_jump_host_cc_readonly_mode():
    """Test connect_jump_host_cc in readonly mode (line 149)."""
    with patch('awslabs.elasticache_mcp_server.context.Context.readonly_mode', return_value=True):
        result = await connect_jump_host_cc('cluster-1', 'i-123')
        assert 'error' in result
        assert 'You have configured this tool in readonly mode' in result['error']


@pytest.mark.asyncio
async def test_get_ssh_tunnel_command_cc_no_instance_found():
    """Test get_ssh_tunnel_command_cc when instance is not found (line ~179)."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock no instance found
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
async def test_get_ssh_tunnel_command_cc_no_key_name():
    """Test get_ssh_tunnel_command_cc when instance has no key pair (line ~186)."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock instance without key name
    mock_ec2.describe_instances.return_value = {
        'Reservations': [
            {
                'Instances': [
                    {
                        'PublicDnsName': 'ec2-1-2-3-4.compute-1.amazonaws.com',
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
        assert 'No key pair associated with EC2 instance i-123' in result['error']


@pytest.mark.asyncio
async def test_get_ssh_tunnel_command_cc_no_public_dns():
    """Test get_ssh_tunnel_command_cc when instance has no public DNS (line ~191)."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock instance without public DNS
    mock_ec2.describe_instances.return_value = {
        'Reservations': [
            {
                'Instances': [
                    {
                        'KeyName': 'my-key',
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
        assert 'No public DNS name found for EC2 instance i-123' in result['error']


@pytest.mark.asyncio
async def test_get_ssh_tunnel_command_cc_windows_platform():
    """Test get_ssh_tunnel_command_cc with Windows platform (line ~197)."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock Windows instance
    mock_ec2.describe_instances.return_value = {
        'Reservations': [
            {
                'Instances': [
                    {
                        'KeyName': 'my-key',
                        'PublicDnsName': 'ec2-1-2-3-4.compute-1.amazonaws.com',
                        'Platform': 'Windows',
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
async def test_get_ssh_tunnel_command_cc_ubuntu_user():
    """Test get_ssh_tunnel_command_cc with Ubuntu AMI (line ~199)."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock Ubuntu instance
    mock_ec2.describe_instances.return_value = {
        'Reservations': [
            {
                'Instances': [
                    {
                        'KeyName': 'my-key',
                        'PublicDnsName': 'ec2-1-2-3-4.compute-1.amazonaws.com',
                        'ImageId': 'ami-ubuntu-123',  # Contains 'ubuntu'
                    }
                ]
            }
        ]
    }

    # Mock cache cluster
    mock_elasticache.describe_cache_clusters.return_value = {
        'CacheClusters': [
            {
                'CacheNodes': [
                    {
                        'Endpoint': {
                            'Address': 'cache.abc123.cache.amazonaws.com',
                            'Port': 6379,
                        }
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

        assert 'error' not in result
        assert result['user'] == 'ubuntu'
        assert 'ubuntu' in result['command']


@pytest.mark.asyncio
async def test_get_ssh_tunnel_command_cc_no_cache_nodes():
    """Test get_ssh_tunnel_command_cc when cache has no nodes (line ~210)."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock instance
    mock_ec2.describe_instances.return_value = {
        'Reservations': [
            {
                'Instances': [
                    {
                        'KeyName': 'my-key',
                        'PublicDnsName': 'ec2-1-2-3-4.compute-1.amazonaws.com',
                    }
                ]
            }
        ]
    }

    # Mock cache cluster with no nodes
    mock_elasticache.describe_cache_clusters.return_value = {
        'CacheClusters': [
            {
                'CacheNodes': []  # No cache nodes
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
async def test_create_jump_host_cc_readonly_mode():
    """Test create_jump_host_cc in readonly mode (line ~279)."""
    with patch('awslabs.elasticache_mcp_server.context.Context.readonly_mode', return_value=True):
        result = await create_jump_host_cc('cluster-1', 'my-key')
        assert 'error' in result
        assert 'You have configured this tool in readonly mode' in result['error']


@pytest.mark.asyncio
async def test_create_jump_host_cc_empty_key_name():
    """Test create_jump_host_cc with empty key_name (line ~290)."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    with (
        patch(
            'awslabs.elasticache_mcp_server.common.connection.EC2ConnectionManager.get_connection',
            return_value=mock_ec2,
        ),
        patch(
            'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
            return_value=mock_elasticache,
        ),
        patch('awslabs.elasticache_mcp_server.context.Context.readonly_mode', return_value=False),
    ):
        result = await create_jump_host_cc('cluster-1', '')  # Empty key name
        assert 'error' in result
        assert 'key_name is required' in result['error']


@pytest.mark.asyncio
async def test_create_jump_host_cc_key_pair_not_found():
    """Test create_jump_host_cc when key pair is not found (line ~297)."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock key pair not found
    mock_ec2.describe_key_pairs.return_value = {'KeyPairs': []}

    with (
        patch(
            'awslabs.elasticache_mcp_server.common.connection.EC2ConnectionManager.get_connection',
            return_value=mock_ec2,
        ),
        patch(
            'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
            return_value=mock_elasticache,
        ),
        patch('awslabs.elasticache_mcp_server.context.Context.readonly_mode', return_value=False),
    ):
        result = await create_jump_host_cc('cluster-1', 'nonexistent-key')

        assert 'error' in result
        assert "Key pair 'nonexistent-key' not found" in result['error']


@pytest.mark.asyncio
async def test_create_jump_host_cc_vpc_compatibility_error():
    """Test create_jump_host_cc when subnet VPC doesn't match cache VPC (line ~371)."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock responses
    mock_ec2.describe_key_pairs.return_value = {'KeyPairs': [{'KeyName': 'my-key'}]}

    mock_elasticache.describe_cache_clusters.return_value = {
        'CacheClusters': [
            {
                'CacheSubnetGroupName': 'subnet-group-1',
            }
        ]
    }
    mock_elasticache.describe_cache_subnet_groups.return_value = {
        'CacheSubnetGroups': [{'VpcId': 'vpc-cache'}]
    }

    # Mock subnet in different VPC
    mock_ec2.describe_subnets.return_value = {
        'Subnets': [{'VpcId': 'vpc-different'}]  # Different VPC
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
        patch('awslabs.elasticache_mcp_server.context.Context.readonly_mode', return_value=False),
    ):
        result = await create_jump_host_cc('cluster-1', 'my-key', 'subnet-123', 'sg-123')

        assert 'error' in result
        assert (
            'Subnet VPC (vpc-different) does not match cache cluster VPC (vpc-cache)'
            in result['error']
        )


@pytest.mark.asyncio
async def test_create_jump_host_cc_subnet_not_public():
    """Test create_jump_host_cc when subnet is not public (line ~427)."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock responses
    mock_ec2.describe_key_pairs.return_value = {'KeyPairs': [{'KeyName': 'my-key'}]}

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

    # Mock private subnet
    mock_ec2.describe_subnets.return_value = {
        'Subnets': [
            {
                'VpcId': 'vpc-123',
                'DefaultForAz': False,
                'MapPublicIpOnLaunch': False,  # Not public
            }
        ]
    }

    # Mock route tables with no IGW route
    mock_ec2.describe_route_tables.return_value = {
        'RouteTables': [
            {
                'Routes': [
                    {'GatewayId': 'local'}  # No IGW route
                ]
            }
        ]
    }

    # Mock VPC as non-default
    mock_ec2.describe_vpcs.return_value = {'Vpcs': [{'IsDefault': False}]}

    with (
        patch(
            'awslabs.elasticache_mcp_server.common.connection.EC2ConnectionManager.get_connection',
            return_value=mock_ec2,
        ),
        patch(
            'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
            return_value=mock_elasticache,
        ),
        patch('awslabs.elasticache_mcp_server.context.Context.readonly_mode', return_value=False),
    ):
        result = await create_jump_host_cc('cluster-1', 'my-key', 'subnet-123', 'sg-123')

        assert 'error' in result
        assert 'Subnet subnet-123 is not public' in result['error']


@pytest.mark.asyncio
async def test_create_jump_host_cc_client_error_invalid_keypair():
    """Test create_jump_host_cc with ClientError for invalid key pair (line ~510)."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock responses
    mock_ec2.describe_key_pairs.return_value = {'KeyPairs': [{'KeyName': 'my-key'}]}

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

    mock_ec2.describe_security_groups.return_value = {'SecurityGroups': [{'IpPermissions': []}]}

    # Mock ClientError for invalid key pair
    client_error = ClientError(
        error_response={
            'Error': {'Code': 'InvalidKeyPair.NotFound', 'Message': 'Key pair not found'}
        },
        operation_name='RunInstances',
    )
    mock_ec2.run_instances.side_effect = client_error

    with (
        patch(
            'awslabs.elasticache_mcp_server.common.connection.EC2ConnectionManager.get_connection',
            return_value=mock_ec2,
        ),
        patch(
            'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
            return_value=mock_elasticache,
        ),
        patch('awslabs.elasticache_mcp_server.context.Context.readonly_mode', return_value=False),
    ):
        result = await create_jump_host_cc('cluster-1', 'my-key', 'subnet-123', 'sg-123')

        assert 'error' in result
        assert "Key pair 'my-key' not found" in result['error']


@pytest.mark.asyncio
async def test_create_jump_host_cc_other_client_error():
    """Test create_jump_host_cc with other ClientError (line after 510)."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock responses
    mock_ec2.describe_key_pairs.return_value = {'KeyPairs': [{'KeyName': 'my-key'}]}

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

    mock_ec2.describe_security_groups.return_value = {'SecurityGroups': [{'IpPermissions': []}]}

    # Mock other ClientError
    client_error = ClientError(
        error_response={
            'Error': {'Code': 'InsufficientInstanceCapacity', 'Message': 'Insufficient capacity'}
        },
        operation_name='RunInstances',
    )
    mock_ec2.run_instances.side_effect = client_error

    with (
        patch(
            'awslabs.elasticache_mcp_server.common.connection.EC2ConnectionManager.get_connection',
            return_value=mock_ec2,
        ),
        patch(
            'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
            return_value=mock_elasticache,
        ),
        patch('awslabs.elasticache_mcp_server.context.Context.readonly_mode', return_value=False),
    ):
        result = await create_jump_host_cc('cluster-1', 'my-key', 'subnet-123', 'sg-123')

        assert 'error' in result
        assert 'InsufficientInstanceCapacity' in result['error']


@pytest.mark.asyncio
async def test_create_jump_host_cc_no_main_route_table():
    """Test create_jump_host_cc when no explicit route table association exists (main route table check)."""
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

    mock_ec2.describe_subnets.return_value = {
        'Subnets': [{'VpcId': 'vpc-123', 'MapPublicIpOnLaunch': True}]
    }

    mock_ec2.describe_vpcs.return_value = {'Vpcs': [{'IsDefault': False}]}

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

    # Mock the waiter
    mock_waiter = MagicMock()
    mock_ec2.get_waiter.return_value = mock_waiter

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
        patch('awslabs.elasticache_mcp_server.context.Context.readonly_mode', return_value=False),
    ):
        result = await create_jump_host_cc('cluster-1', 'test-key', 'subnet-123', 'sg-123')

    # Verify successful creation
    assert result['InstanceId'] == 'i-new'
    assert result['PublicIpAddress'] == '1.2.3.4'


@pytest.mark.asyncio
async def test_create_jump_host_cc_general_exception():
    """Test create_jump_host_cc with general exception (last line)."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock responses
    mock_ec2.describe_key_pairs.return_value = {'KeyPairs': [{'KeyName': 'my-key'}]}

    # Mock general exception
    mock_elasticache.describe_cache_clusters.side_effect = Exception('General error')

    with (
        patch(
            'awslabs.elasticache_mcp_server.common.connection.EC2ConnectionManager.get_connection',
            return_value=mock_ec2,
        ),
        patch(
            'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
            return_value=mock_elasticache,
        ),
        patch('awslabs.elasticache_mcp_server.context.Context.readonly_mode', return_value=False),
    ):
        result = await create_jump_host_cc('cluster-1', 'my-key')

        assert 'error' in result
        assert 'General error' in result['error']
