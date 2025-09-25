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

"""Tests for cache cluster connect tools."""

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
async def test_configure_security_groups_basic():
    """Test basic security group configuration."""
    # Mock clients
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
        'CacheSubnetGroups': [{'VpcId': 'vpc-1234'}]
    }

    mock_ec2.describe_instances.return_value = {
        'Reservations': [
            {
                'Instances': [
                    {
                        'VpcId': 'vpc-1234',
                        'SecurityGroups': [{'GroupId': 'sg-instance'}],
                    }
                ]
            }
        ]
    }
    mock_ec2.describe_security_groups.return_value = {'SecurityGroups': [{'IpPermissions': []}]}

    # Call function
    success, vpc_id, port = await _configure_security_groups(
        'cluster-1', 'i-1234', mock_ec2, mock_elasticache
    )

    # Verify results
    assert success is True
    assert vpc_id == 'vpc-1234'
    assert port == 6379

    # Verify security group rule was added
    mock_ec2.authorize_security_group_ingress.assert_called_once_with(
        GroupId='sg-cache',
        IpPermissions=[
            {
                'IpProtocol': 'tcp',
                'FromPort': 6379,
                'ToPort': 6379,
                'UserIdGroupPairs': [
                    {
                        'GroupId': 'sg-instance',
                        'Description': 'Allow access from jump host i-1234',
                    }
                ],
            }
        ],
    )


@pytest.mark.asyncio
async def test_configure_security_groups_existing_rule():
    """Test when security group rule already exists."""
    # Mock clients
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
        'CacheSubnetGroups': [{'VpcId': 'vpc-1234'}]
    }

    mock_ec2.describe_instances.return_value = {
        'Reservations': [
            {
                'Instances': [
                    {
                        'VpcId': 'vpc-1234',
                        'SecurityGroups': [{'GroupId': 'sg-instance'}],
                    }
                ]
            }
        ]
    }
    mock_ec2.describe_security_groups.return_value = {
        'SecurityGroups': [
            {
                'IpPermissions': [
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 6379,
                        'ToPort': 6379,
                        'UserIdGroupPairs': [{'GroupId': 'sg-instance'}],
                    }
                ]
            }
        ]
    }

    # Call function
    success, vpc_id, port = await _configure_security_groups(
        'cluster-1', 'i-1234', mock_ec2, mock_elasticache
    )

    # Verify results
    assert success is True
    assert vpc_id == 'vpc-1234'
    assert port == 6379

    # Verify no new rule was added
    mock_ec2.authorize_security_group_ingress.assert_not_called()


@pytest.mark.asyncio
async def test_configure_security_groups_vpc_mismatch():
    """Test when VPCs don't match."""
    # Mock clients
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
        'CacheSubnetGroups': [{'VpcId': 'vpc-1234'}]
    }

    mock_ec2.describe_instances.return_value = {
        'Reservations': [
            {'Instances': [{'VpcId': 'vpc-5678', 'SecurityGroups': [{'GroupId': 'sg-instance'}]}]}
        ]
    }

    # Call function and verify it raises error
    with pytest.raises(ValueError) as exc_info:
        await _configure_security_groups('cluster-1', 'i-1234', mock_ec2, mock_elasticache)

    assert 'VPC (vpc-5678) does not match cache cluster VPC (vpc-1234)' in str(exc_info.value)


@pytest.mark.asyncio
async def test_connect_jump_host_cc_success():
    """Test successful jump host connection."""
    with patch(
        'awslabs.elasticache_mcp_server.tools.cc.connect._configure_security_groups',
        return_value=(True, 'vpc-1234', 6379),
    ):
        result = await connect_jump_host_cc('cluster-1', 'i-1234')

        assert result['Status'] == 'Success'
        assert result['InstanceId'] == 'i-1234'
        assert result['CacheClusterId'] == 'cluster-1'
        assert result['CachePort'] == 6379
        assert result['VpcId'] == 'vpc-1234'
        assert result['SecurityGroupsConfigured'] is True


@pytest.mark.asyncio
async def test_get_ssh_tunnel_command_cc_success():
    """Test successful SSH tunnel command generation."""
    # Mock clients
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock responses
    mock_ec2.describe_instances.return_value = {
        'Reservations': [
            {
                'Instances': [
                    {
                        'KeyName': 'my-key',
                        'PublicDnsName': 'ec2-1-2-3-4.compute-1.amazonaws.com',
                        'Platform': '',  # Linux
                    }
                ]
            }
        ]
    }

    mock_elasticache.describe_cache_clusters.return_value = {
        'CacheClusters': [
            {
                'CacheNodes': [
                    {
                        'Endpoint': {
                            'Address': 'cluster.123456.cache.amazonaws.com',
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
        result = await get_ssh_tunnel_command_cc('cluster-1', 'i-1234')

        assert 'command' in result
        assert 'ssh -i "my-key.pem"' in result['command']
        assert 'ec2-user' in result['command']
        # Check that both the endpoint and port are in the command, but don't require a specific format
        assert 'cluster.123456.cache.amazonaws.com' in result['command']
        assert '6379' in result['command']
        assert result['keyName'] == 'my-key'
        assert result['user'] == 'ec2-user'
        assert result['localPort'] == 6379
        assert result['cacheEndpoint'] == 'cluster.123456.cache.amazonaws.com'
        assert result['jumpHostDns'] == 'ec2-1-2-3-4.compute-1.amazonaws.com'


@pytest.mark.asyncio
async def test_get_ssh_tunnel_command_cc_ubuntu():
    """Test SSH tunnel command generation for Ubuntu instance."""
    # Mock clients
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock responses with Ubuntu image
    mock_ec2.describe_instances.return_value = {
        'Reservations': [
            {
                'Instances': [
                    {
                        'KeyName': 'my-key',
                        'PublicDnsName': 'ec2-1-2-3-4.compute-1.amazonaws.com',
                        'Platform': '',
                        'ImageId': 'ami-ubuntu-123',
                    }
                ]
            }
        ]
    }

    mock_elasticache.describe_cache_clusters.return_value = {
        'CacheClusters': [
            {
                'CacheNodes': [
                    {
                        'Endpoint': {
                            'Address': 'cluster.123456.cache.amazonaws.com',
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
        result = await get_ssh_tunnel_command_cc('cluster-1', 'i-1234')

        assert 'ubuntu' in result['command']
        assert result['user'] == 'ubuntu'


@pytest.mark.asyncio
async def test_create_jump_host_cc_success():
    """Test successful jump host creation."""
    # Mock clients
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
        'CacheSubnetGroups': [{'VpcId': 'vpc-1234'}]
    }

    mock_ec2.describe_subnets.return_value = {'Subnets': [{'VpcId': 'vpc-1234'}]}
    mock_ec2.describe_route_tables.return_value = {
        'RouteTables': [{'Routes': [{'GatewayId': 'igw-1234'}]}]
    }
    mock_ec2.describe_security_groups.return_value = {'SecurityGroups': [{'IpPermissions': []}]}
    mock_ec2.describe_images.return_value = {
        'Images': [{'ImageId': 'ami-123', 'CreationDate': '2023-01-01'}]
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
            return_value=(True, 'vpc-1234', 6379),
        ),
    ):
        result = await create_jump_host_cc(
            'cluster-1',
            'my-key',
            'subnet-1234',
            'sg-1234',
            't3.micro',
        )

        assert result['InstanceId'] == 'i-new1234'
        assert result['PublicIpAddress'] == '1.2.3.4'
        assert result['InstanceType'] == 't3.micro'
        assert result['SubnetId'] == 'subnet-1234'
        assert result['SecurityGroupId'] == 'sg-1234'
        assert result['CacheClusterId'] == 'cluster-1'
        assert result['SecurityGroupsConfigured'] is True
        assert result['CachePort'] == 6379
        assert result['VpcId'] == 'vpc-1234'


@pytest.mark.asyncio
async def test_create_jump_host_cc_private_subnet():
    """Test jump host creation with private subnet."""
    # Mock clients
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
        'CacheSubnetGroups': [{'VpcId': 'vpc-1234'}]
    }

    mock_ec2.describe_subnets.return_value = {'Subnets': [{'VpcId': 'vpc-1234'}]}
    # No internet gateway route
    mock_ec2.describe_route_tables.return_value = {'RouteTables': [{'Routes': []}]}

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
        result = await create_jump_host_cc(
            'cluster-1',
            'my-key',
            'subnet-1234',
            'sg-1234',
        )

        assert 'error' in result
        assert 'Subnet subnet-1234 is not public' in result['error']


@pytest.mark.asyncio
async def test_create_jump_host_cc_invalid_key():
    """Test jump host creation with invalid key pair."""
    # Mock clients
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock key pair not found error
    mock_ec2.describe_key_pairs.side_effect = ClientError(
        {'Error': {'Code': 'InvalidKeyPair.NotFound', 'Message': 'Key pair not found'}},
        'DescribeKeyPairs',
    )

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
        result = await create_jump_host_cc(
            'cluster-1',
            'invalid-key',
            'subnet-1234',
            'sg-1234',
        )

        assert 'error' in result
        assert "Key pair 'invalid-key' not found" in result['error']


@pytest.mark.asyncio
async def test_create_jump_host_cc_default_vpc_default_subnet():
    """Test jump host creation with default subnet in default VPC."""
    # Mock clients
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
        'CacheSubnetGroups': [{'VpcId': 'vpc-1234'}]
    }

    # Mock subnet in default VPC with no IGW route (but is default subnet)
    mock_ec2.describe_subnets.return_value = {
        'Subnets': [
            {
                'VpcId': 'vpc-1234',
                'DefaultForAz': True,  # This is a default subnet
                'MapPublicIpOnLaunch': True,
            }
        ]
    }
    # No internet gateway route in route table
    mock_ec2.describe_route_tables.return_value = {'RouteTables': [{'Routes': []}]}

    # Mock VPC as default VPC
    mock_ec2.describe_vpcs.return_value = {
        'Vpcs': [{'IsDefault': True}]  # This is the default VPC
    }

    mock_ec2.describe_security_groups.return_value = {'SecurityGroups': [{'IpPermissions': []}]}
    mock_ec2.describe_images.return_value = {
        'Images': [{'ImageId': 'ami-123', 'CreationDate': '2023-01-01'}]
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
            return_value=(True, 'vpc-1234', 6379),
        ),
    ):
        result = await create_jump_host_cc(
            'cluster-1',
            'my-key',
            'subnet-1234',
            'sg-1234',
            't3.micro',
        )

        # Should succeed because it's a default subnet in default VPC
        assert result['InstanceId'] == 'i-new1234'
        assert result['PublicIpAddress'] == '1.2.3.4'
        assert result['InstanceType'] == 't3.micro'
        assert result['SubnetId'] == 'subnet-1234'
        assert result['SecurityGroupId'] == 'sg-1234'
        assert result['CacheClusterId'] == 'cluster-1'
        assert result['SecurityGroupsConfigured'] is True
        assert result['CachePort'] == 6379
        assert result['VpcId'] == 'vpc-1234'


@pytest.mark.asyncio
async def test_create_jump_host_cc_default_vpc_map_public_ip():
    """Test jump host creation with subnet that has MapPublicIpOnLaunch in default VPC."""
    # Mock clients
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
        'CacheSubnetGroups': [{'VpcId': 'vpc-1234'}]
    }

    # Mock subnet in default VPC with MapPublicIpOnLaunch but not DefaultForAz
    mock_ec2.describe_subnets.return_value = {
        'Subnets': [
            {
                'VpcId': 'vpc-1234',
                'DefaultForAz': False,  # Not a default subnet
                'MapPublicIpOnLaunch': True,  # But has MapPublicIpOnLaunch
            }
        ]
    }
    # No internet gateway route in route table
    mock_ec2.describe_route_tables.return_value = {'RouteTables': [{'Routes': []}]}

    # Mock VPC as default VPC
    mock_ec2.describe_vpcs.return_value = {
        'Vpcs': [{'IsDefault': True}]  # This is the default VPC
    }

    mock_ec2.describe_security_groups.return_value = {'SecurityGroups': [{'IpPermissions': []}]}
    mock_ec2.describe_images.return_value = {
        'Images': [{'ImageId': 'ami-123', 'CreationDate': '2023-01-01'}]
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
            return_value=(True, 'vpc-1234', 6379),
        ),
    ):
        result = await create_jump_host_cc(
            'cluster-1',
            'subnet-1234',
            'sg-1234',
            'my-key',
            't3.micro',
        )

        # Should succeed because MapPublicIpOnLaunch is True in default VPC
        assert result['InstanceId'] == 'i-new1234'
        assert result['PublicIpAddress'] == '1.2.3.4'


@pytest.mark.asyncio
async def test_create_jump_host_cc_non_default_vpc_private_subnet():
    """Test jump host creation with private subnet in non-default VPC."""
    # Mock clients
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
        'CacheSubnetGroups': [{'VpcId': 'vpc-1234'}]
    }

    # Mock subnet in non-default VPC
    mock_ec2.describe_subnets.return_value = {
        'Subnets': [
            {
                'VpcId': 'vpc-1234',
                'DefaultForAz': False,
                'MapPublicIpOnLaunch': False,
            }
        ]
    }
    # No internet gateway route
    mock_ec2.describe_route_tables.return_value = {'RouteTables': [{'Routes': []}]}

    # Mock VPC as non-default VPC
    mock_ec2.describe_vpcs.return_value = {
        'Vpcs': [{'IsDefault': False}]  # This is NOT the default VPC
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
        result = await create_jump_host_cc(
            'cluster-1',
            'my-key',
            'subnet-1234',
            'sg-1234',
        )

        # Should fail because it's not public and not in default VPC
        assert 'error' in result
        assert 'Subnet subnet-1234 is not public' in result['error']
        assert 'not a default subnet in default VPC' in result['error']


@pytest.mark.asyncio
async def test_create_jump_host_cc_default_vpc_non_default_subnet():
    """Test jump host creation with non-default subnet in default VPC."""
    # Mock clients
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
        'CacheSubnetGroups': [{'VpcId': 'vpc-1234'}]
    }

    # Mock non-default subnet in default VPC (should still fail)
    mock_ec2.describe_subnets.return_value = {
        'Subnets': [
            {
                'VpcId': 'vpc-1234',
                'DefaultForAz': False,  # Not a default subnet
                'MapPublicIpOnLaunch': False,  # No auto-assign public IP
            }
        ]
    }
    # No internet gateway route
    mock_ec2.describe_route_tables.return_value = {'RouteTables': [{'Routes': []}]}

    # Mock VPC as default VPC
    mock_ec2.describe_vpcs.return_value = {
        'Vpcs': [{'IsDefault': True}]  # This is the default VPC
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
        result = await create_jump_host_cc(
            'cluster-1',
            'my-key',
            'subnet-1234',
            'sg-1234',
        )

        # Should fail because it's not a default subnet (even though in default VPC)
        assert 'error' in result
        assert 'Subnet subnet-1234 is not public' in result['error']
        assert 'not a default subnet in default VPC' in result['error']


@pytest.mark.asyncio
async def test_create_jump_host_cc_auto_select_defaults():
    """Test jump host creation with auto-selection of subnet and security group in default VPC."""
    # Mock clients
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
        'CacheSubnetGroups': [{'VpcId': 'vpc-default'}]
    }

    # Mock VPC as default VPC
    mock_ec2.describe_vpcs.return_value = {
        'Vpcs': [{'IsDefault': True}]  # This is the default VPC
    }

    # Mock default subnets available
    mock_ec2.describe_subnets.side_effect = [
        # First call for auto-selecting default subnets
        {
            'Subnets': [
                {
                    'SubnetId': 'subnet-auto-selected',
                    'VpcId': 'vpc-default',
                    'DefaultForAz': True,
                    'MapPublicIpOnLaunch': True,
                }
            ]
        },
        # Second call for validating the selected subnet
        {
            'Subnets': [
                {
                    'SubnetId': 'subnet-auto-selected',
                    'VpcId': 'vpc-default',
                    'DefaultForAz': True,
                    'MapPublicIpOnLaunch': True,
                }
            ]
        },
    ]

    # Mock default security group available
    mock_ec2.describe_security_groups.side_effect = [
        # First call for auto-selecting default security group
        {
            'SecurityGroups': [
                {
                    'GroupId': 'sg-auto-selected',
                    'GroupName': 'default',
                    'VpcId': 'vpc-default',
                }
            ]
        },
        # Second call for validating the selected security group
        {
            'SecurityGroups': [
                {
                    'GroupId': 'sg-auto-selected',
                    'IpPermissions': [],
                }
            ]
        },
    ]

    # Mock route table shows it's public (has IGW route)
    mock_ec2.describe_route_tables.return_value = {
        'RouteTables': [{'Routes': [{'GatewayId': 'igw-1234'}]}]
    }

    mock_ec2.describe_images.return_value = {
        'Images': [{'ImageId': 'ami-123', 'CreationDate': '2023-01-01'}]
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
            return_value=(True, 'vpc-default', 6379),
        ),
    ):
        # Call without subnet_id and security_group_id - should auto-select
        result = await create_jump_host_cc(
            'cluster-1',
            'my-key',  # Only provide required key_name
        )

        # Should succeed with auto-selected values
        assert result['InstanceId'] == 'i-new1234'
        assert result['PublicIpAddress'] == '1.2.3.4'
        assert result['SubnetId'] == 'subnet-auto-selected'  # Auto-selected
        assert result['SecurityGroupId'] == 'sg-auto-selected'  # Auto-selected
        assert result['CacheClusterId'] == 'cluster-1'
        assert result['SecurityGroupsConfigured'] is True
        assert result['CachePort'] == 6379
        assert result['VpcId'] == 'vpc-default'
