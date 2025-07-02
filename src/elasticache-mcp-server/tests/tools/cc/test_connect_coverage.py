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

"""Coverage tests for cache cluster connection tools - specifically for auto-selection logic."""

import pytest
from awslabs.elasticache_mcp_server.tools.cc.connect import create_jump_host_cc
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_create_jump_host_cc_non_default_vpc_missing_params():
    """Test when cache is in non-default VPC and required parameters are missing."""
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
        'CacheSubnetGroups': [{'VpcId': 'vpc-custom'}]
    }

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
        # Call without subnet_id and security_group_id in non-default VPC - should fail
        result = await create_jump_host_cc(
            'cluster-1',
            'my-key',  # Only provide required key_name
        )

        # Should fail with subnet_id required error (first validation that fails)
        assert 'error' in result
        assert 'subnet_id is required' in result['error']
        assert (
            'ensure the cache cluster is in the default VPC with default subnets available'
            in result['error']
        )


@pytest.mark.asyncio
async def test_create_jump_host_cc_auto_select_subnets_with_public_ip():
    """Test auto-selection logic for subnets with MapPublicIpOnLaunch=True."""
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
    mock_ec2.describe_vpcs.return_value = {'Vpcs': [{'IsDefault': True}]}

    # Mock subnet calls - test the specific code that iterates through subnets
    mock_ec2.describe_subnets.side_effect = [
        # First call for auto-selecting default subnets (none found)
        {'Subnets': []},
        # Second call for fallback to any public subnet - tests the MapPublicIpOnLaunch logic
        {
            'Subnets': [
                {
                    'SubnetId': 'subnet-private-1',
                    'VpcId': 'vpc-default',
                    'MapPublicIpOnLaunch': False,  # This should be skipped
                    'DefaultForAz': False,
                },
                {
                    'SubnetId': 'subnet-public-found',
                    'VpcId': 'vpc-default',
                    'MapPublicIpOnLaunch': True,  # This should be selected
                    'DefaultForAz': False,
                },
                {
                    'SubnetId': 'subnet-private-2',
                    'VpcId': 'vpc-default',
                    'MapPublicIpOnLaunch': False,  # This should be skipped
                    'DefaultForAz': False,
                },
            ]
        },
        # Third call for validating the selected subnet
        {
            'Subnets': [
                {
                    'SubnetId': 'subnet-public-found',
                    'VpcId': 'vpc-default',
                    'MapPublicIpOnLaunch': True,
                    'DefaultForAz': False,
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
                    'GroupId': 'sg-default',
                    'GroupName': 'default',
                    'VpcId': 'vpc-default',
                }
            ]
        },
        # Second call for validating the selected security group
        {
            'SecurityGroups': [
                {
                    'GroupId': 'sg-default',
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
        # Call without subnet_id and security_group_id - should auto-select the public subnet
        result = await create_jump_host_cc(
            'cluster-1',
            'my-key',  # Only provide required key_name
        )

        # Should succeed with the correct subnet selected based on MapPublicIpOnLaunch=True
        assert result['InstanceId'] == 'i-new1234'
        assert (
            result['SubnetId'] == 'subnet-public-found'
        )  # The subnet with MapPublicIpOnLaunch=True
        assert result['SecurityGroupId'] == 'sg-default'


@pytest.mark.asyncio
async def test_create_jump_host_cc_auto_select_security_groups():
    """Test auto-selection logic for security groups when multiple exist."""
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
    mock_ec2.describe_vpcs.return_value = {'Vpcs': [{'IsDefault': True}]}

    # Mock default subnets available
    mock_ec2.describe_subnets.return_value = {
        'Subnets': [
            {
                'SubnetId': 'subnet-default',
                'VpcId': 'vpc-default',
                'DefaultForAz': True,
                'MapPublicIpOnLaunch': True,
            }
        ]
    }

    # Mock security group calls - the implementation uses filters to find the default security group
    mock_ec2.describe_security_groups.side_effect = [
        # First call for auto-selecting default security group (with filters)
        {
            'SecurityGroups': [
                {
                    'GroupId': 'sg-default-found',
                    'GroupName': 'default',  # This should be selected
                    'VpcId': 'vpc-default',
                }
            ]
        },
        # Second call for validating the selected security group
        {
            'SecurityGroups': [
                {
                    'GroupId': 'sg-default-found',
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
        # Call without security_group_id - should auto-select the 'default' security group
        result = await create_jump_host_cc(
            'cluster-1',
            'my-key',  # Only provide required key_name
        )

        # Should succeed with the correct security group selected
        assert result['InstanceId'] == 'i-new1234'
        assert (
            result['SecurityGroupId'] == 'sg-default-found'
        )  # The security group with GroupName='default'


@pytest.mark.asyncio
async def test_create_jump_host_cc_validation_errors():
    """Test the validation error messages for missing subnet_id and security_group_id."""
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
        'CacheSubnetGroups': [{'VpcId': 'vpc-custom'}]
    }

    # Mock VPC as non-default VPC
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
    ):
        # Test subnet_id validation error
        result = await create_jump_host_cc('cluster-1', 'my-key')
        assert 'error' in result
        assert 'subnet_id is required' in result['error']
        assert (
            'Either provide a subnet_id or ensure the cache cluster is in the default VPC with default subnets available'
            in result['error']
        )

        # Test with subnet_id provided but no security_group_id
        # Mock that we have a subnet but no default security groups
        mock_ec2.describe_subnets.return_value = {'Subnets': [{'VpcId': 'vpc-custom'}]}
        mock_ec2.describe_route_tables.return_value = {
            'RouteTables': [{'Routes': [{'GatewayId': 'igw-123'}]}]
        }
        mock_ec2.describe_security_groups.return_value = {'SecurityGroups': []}

        result = await create_jump_host_cc('cluster-1', 'my-key', 'subnet-123')
        assert 'error' in result
        assert 'security_group_id is required' in result['error']
        assert (
            'Either provide a security_group_id or ensure the cache cluster is in the default VPC'
            in result['error']
        )


@pytest.mark.asyncio
async def test_create_jump_host_cc_existing_ssh_rule():
    """Test create_jump_host_cc with existing SSH rule - should not add duplicate rule."""
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

    # Security group with existing SSH rule - this tests the specific logic that checks for existing rules
    mock_ec2.describe_security_groups.return_value = {
        'SecurityGroups': [
            {
                'IpPermissions': [
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 22,
                        'ToPort': 22,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}],  # Existing SSH rule
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
        result = await create_jump_host_cc('cluster-1', 'test-key', 'subnet-123', 'sg-123')

        # Should succeed and not try to add SSH rule since one already exists
        assert 'InstanceId' in result
        assert result['InstanceId'] == 'i-new1234'
        # Verify that authorize_security_group_ingress was NOT called for SSH rule
        mock_ec2.authorize_security_group_ingress.assert_not_called()
