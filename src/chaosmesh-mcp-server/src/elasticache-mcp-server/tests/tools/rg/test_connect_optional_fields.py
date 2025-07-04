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

"""Tests for optional fields in replication group create_jump_host_rg function."""

import pytest
from awslabs.elasticache_mcp_server.tools.rg.connect import create_jump_host_rg
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_create_jump_host_rg_auto_select_subnet_default_vpc():
    """Test auto-selection of subnet when not provided in default VPC."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock responses for auto-selection scenario
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
        'CacheSubnetGroups': [{'VpcId': 'vpc-default'}]
    }

    # Mock VPC as default VPC
    mock_ec2.describe_vpcs.return_value = {'Vpcs': [{'IsDefault': True}]}

    # Mock subnet response for auto-selection (default VPC)
    mock_ec2.describe_subnets.side_effect = [
        {
            'Subnets': [
                {'SubnetId': 'subnet-default-1', 'DefaultForAz': True, 'MapPublicIpOnLaunch': True}
            ]
        },  # Default subnets lookup
        {
            'Subnets': [
                {'VpcId': 'vpc-default', 'DefaultForAz': True, 'MapPublicIpOnLaunch': True}
            ]
        },  # Selected subnet details
    ]

    # Mock security groups for default VPC
    mock_ec2.describe_security_groups.side_effect = [
        {
            'SecurityGroups': [{'GroupId': 'sg-default', 'GroupName': 'default'}]
        },  # Default security group lookup
        {'SecurityGroups': [{'IpPermissions': []}]},  # Security group details for SSH rule check
    ]

    mock_ec2.describe_route_tables.return_value = {'RouteTables': [{'Routes': []}]}
    mock_ec2.describe_images.return_value = {
        'Images': [{'ImageId': 'ami-123', 'CreationDate': '2023-01-01'}]
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
            return_value=(True, 'vpc-default', 6379),
        ),
    ):
        # Call without subnet_id and security_group_id (should auto-select)
        result = await create_jump_host_rg(
            replication_group_id='rg-test',
            key_name='test-key',
            # subnet_id not provided - should auto-select
            # security_group_id not provided - should auto-select
            instance_type='t3.micro',  # Custom instance type
        )

        # Verify successful creation with auto-selected values
        assert result['InstanceId'] == 'i-new'
        assert result['PublicIpAddress'] == '1.2.3.4'
        assert result['InstanceType'] == 't3.micro'
        assert result['SubnetId'] == 'subnet-default-1'  # Auto-selected
        assert result['SecurityGroupId'] == 'sg-default'  # Auto-selected
        assert result['ReplicationGroupId'] == 'rg-test'


@pytest.mark.asyncio
async def test_create_jump_host_rg_auto_select_fallback_public_subnet():
    """Test auto-selection fallback to public subnet when no default subnets."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock responses for fallback scenario
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
        'CacheSubnetGroups': [{'VpcId': 'vpc-default'}]
    }

    # Mock VPC as default VPC
    mock_ec2.describe_vpcs.return_value = {'Vpcs': [{'IsDefault': True}]}

    # Mock subnet response for fallback scenario (default VPC)
    mock_ec2.describe_subnets.side_effect = [
        {'Subnets': []},  # No default subnets found
        {
            'Subnets': [
                {'SubnetId': 'subnet-public-1', 'MapPublicIpOnLaunch': True},
                {'SubnetId': 'subnet-private-1', 'MapPublicIpOnLaunch': False},
            ]
        },  # All subnets lookup for fallback
        {
            'Subnets': [{'VpcId': 'vpc-default', 'MapPublicIpOnLaunch': True}]
        },  # Selected subnet details
    ]

    # Mock security groups for default VPC
    mock_ec2.describe_security_groups.side_effect = [
        {
            'SecurityGroups': [{'GroupId': 'sg-default', 'GroupName': 'default'}]
        },  # Default security group lookup
        {'SecurityGroups': [{'IpPermissions': []}]},  # Security group details for SSH rule check
    ]

    mock_ec2.describe_route_tables.return_value = {'RouteTables': [{'Routes': []}]}
    mock_ec2.describe_images.return_value = {
        'Images': [{'ImageId': 'ami-123', 'CreationDate': '2023-01-01'}]
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
            return_value=(True, 'vpc-default', 6379),
        ),
    ):
        # Call without subnet_id and security_group_id (should auto-select)
        result = await create_jump_host_rg(
            replication_group_id='rg-test',
            key_name='test-key',
            # subnet_id not provided - should fallback to public subnet
            # security_group_id not provided - should auto-select
        )

        # Verify successful creation with fallback subnet
        assert result['InstanceId'] == 'i-new'
        assert result['SubnetId'] == 'subnet-public-1'  # Fallback to public subnet
        assert result['SecurityGroupId'] == 'sg-default'  # Auto-selected


@pytest.mark.asyncio
async def test_create_jump_host_rg_non_default_vpc_requires_params():
    """Test that non-default VPC requires explicit subnet_id and security_group_id."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock responses for non-default VPC scenario
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
        # Call without subnet_id (should fail for non-default VPC)
        result = await create_jump_host_rg(
            replication_group_id='rg-test',
            key_name='test-key',
            # subnet_id not provided - should fail for non-default VPC
        )

        # Should fail with appropriate error message
        assert 'error' in result
        assert 'subnet_id is required' in result['error']
        assert 'ensure the replication group is in the default VPC' in result['error']


@pytest.mark.asyncio
async def test_create_jump_host_rg_non_default_vpc_requires_security_group():
    """Test that non-default VPC requires explicit security_group_id."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock responses for non-default VPC scenario
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
        # Call with subnet_id but without security_group_id (should fail for non-default VPC)
        result = await create_jump_host_rg(
            replication_group_id='rg-test',
            key_name='test-key',
            subnet_id='subnet-custom',
            # security_group_id not provided - should fail for non-default VPC
        )

        # Should fail with appropriate error message
        assert 'error' in result
        assert 'security_group_id is required' in result['error']
        assert 'ensure the replication group is in the default VPC' in result['error']


@pytest.mark.asyncio
async def test_create_jump_host_rg_custom_instance_type():
    """Test create_jump_host_rg with custom instance type."""
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

    mock_ec2.describe_subnets.return_value = {'Subnets': [{'VpcId': 'vpc-123'}]}
    mock_ec2.describe_route_tables.return_value = {
        'RouteTables': [{'Routes': [{'GatewayId': 'igw-123'}]}]
    }
    mock_ec2.describe_security_groups.return_value = {'SecurityGroups': [{'IpPermissions': []}]}
    mock_ec2.describe_images.return_value = {
        'Images': [{'ImageId': 'ami-123', 'CreationDate': '2023-01-01'}]
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
    ):
        # Test with custom instance type
        result = await create_jump_host_rg(
            replication_group_id='rg-test',
            key_name='test-key',
            subnet_id='subnet-123',
            security_group_id='sg-123',
            instance_type='t3.large',  # Custom instance type
        )

        # Verify custom instance type is used
        assert result['InstanceType'] == 't3.large'

        # Verify run_instances was called with correct instance type
        mock_ec2.run_instances.assert_called_once()
        call_args = mock_ec2.run_instances.call_args[1]
        assert call_args['InstanceType'] == 't3.large'


@pytest.mark.asyncio
async def test_create_jump_host_rg_default_instance_type():
    """Test create_jump_host_rg with default instance type."""
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

    mock_ec2.describe_subnets.return_value = {'Subnets': [{'VpcId': 'vpc-123'}]}
    mock_ec2.describe_route_tables.return_value = {
        'RouteTables': [{'Routes': [{'GatewayId': 'igw-123'}]}]
    }
    mock_ec2.describe_security_groups.return_value = {'SecurityGroups': [{'IpPermissions': []}]}
    mock_ec2.describe_images.return_value = {
        'Images': [{'ImageId': 'ami-123', 'CreationDate': '2023-01-01'}]
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
    ):
        # Test without specifying instance_type (should use default)
        result = await create_jump_host_rg(
            replication_group_id='rg-test',
            key_name='test-key',
            subnet_id='subnet-123',
            security_group_id='sg-123',
            # instance_type not provided - should use default 't3.small'
        )

        # Verify default instance type is used
        assert result['InstanceType'] == 't3.small'

        # Verify run_instances was called with default instance type
        mock_ec2.run_instances.assert_called_once()
        call_args = mock_ec2.run_instances.call_args[1]
        assert call_args['InstanceType'] == 't3.small'


@pytest.mark.asyncio
async def test_create_jump_host_rg_all_optional_params_provided():
    """Test create_jump_host_rg with all optional parameters explicitly provided."""
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

    mock_ec2.describe_subnets.return_value = {'Subnets': [{'VpcId': 'vpc-123'}]}
    mock_ec2.describe_route_tables.return_value = {
        'RouteTables': [{'Routes': [{'GatewayId': 'igw-123'}]}]
    }
    mock_ec2.describe_security_groups.return_value = {'SecurityGroups': [{'IpPermissions': []}]}
    mock_ec2.describe_images.return_value = {
        'Images': [{'ImageId': 'ami-123', 'CreationDate': '2023-01-01'}]
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
    ):
        # Test with all optional parameters explicitly provided
        result = await create_jump_host_rg(
            replication_group_id='rg-test',
            key_name='test-key',
            subnet_id='subnet-custom',
            security_group_id='sg-custom',
            instance_type='t3.xlarge',
        )

        # Verify all provided values are used
        assert result['InstanceId'] == 'i-new'
        assert result['SubnetId'] == 'subnet-custom'
        assert result['SecurityGroupId'] == 'sg-custom'
        assert result['InstanceType'] == 't3.xlarge'

        # Verify run_instances was called with provided values
        mock_ec2.run_instances.assert_called_once()
        call_args = mock_ec2.run_instances.call_args[1]
        assert call_args['InstanceType'] == 't3.xlarge'
        assert call_args['NetworkInterfaces'][0]['SubnetId'] == 'subnet-custom'
        assert call_args['NetworkInterfaces'][0]['Groups'] == ['sg-custom']


@pytest.mark.asyncio
async def test_create_jump_host_rg_main_route_table_check():
    """Test create_jump_host_rg with main route table check for public subnet."""
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

    mock_ec2.describe_subnets.return_value = {'Subnets': [{'VpcId': 'vpc-123'}]}

    # No explicit route table association, but main route table has IGW
    mock_ec2.describe_route_tables.side_effect = [
        {'RouteTables': []},  # First call for subnet-specific route table
        {
            'RouteTables': [{'Routes': [{'GatewayId': 'igw-123'}]}]
        },  # Second call for main route table with IGW
    ]

    mock_ec2.describe_security_groups.return_value = {'SecurityGroups': [{'IpPermissions': []}]}
    mock_ec2.describe_images.return_value = {
        'Images': [{'ImageId': 'ami-123', 'CreationDate': '2023-01-01'}]
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
    ):
        # Test with subnet that uses main route table
        result = await create_jump_host_rg(
            replication_group_id='rg-test',
            key_name='test-key',
            subnet_id='subnet-123',
            security_group_id='sg-123',
        )

        # Should succeed because main route table has IGW
        assert result['InstanceId'] == 'i-new'
        assert result['SubnetId'] == 'subnet-123'
        assert result['SecurityGroupId'] == 'sg-123'
