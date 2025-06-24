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

"""Additional tests for RG connect to improve partial code coverage for specific code paths."""

import pytest
from awslabs.elasticache_mcp_server.tools.rg.connect import (
    create_jump_host_rg,
)
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_create_jump_host_rg_auto_select_subnet_with_map_public_ip():
    """Test create_jump_host_rg auto-selecting subnet with MapPublicIpOnLaunch=True.

    This test covers the specific code path:
    for subnet in all_subnets:
        if subnet.get('MapPublicIpOnLaunch', False):
    """
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

    # Mock VPC as default VPC
    mock_ec2.describe_vpcs.return_value = {'Vpcs': [{'IsDefault': True}]}

    # Mock no default subnets, but have subnets with MapPublicIpOnLaunch=True
    mock_ec2.describe_subnets.side_effect = [
        # First call for default subnets (returns empty)
        {'Subnets': []},
        # Second call for all subnets in VPC
        {
            'Subnets': [
                {'SubnetId': 'subnet-private', 'MapPublicIpOnLaunch': False},
                {
                    'SubnetId': 'subnet-public',
                    'MapPublicIpOnLaunch': True,
                },  # This should be selected
            ]
        },
        # Third call for the selected subnet details
        {
            'Subnets': [
                {
                    'SubnetId': 'subnet-public',
                    'VpcId': 'vpc-123',
                    'MapPublicIpOnLaunch': True,
                    'DefaultForAz': False,
                }
            ]
        },
    ]

    # Mock security groups
    mock_ec2.describe_security_groups.side_effect = [
        # First call for default security group
        {'SecurityGroups': [{'GroupId': 'sg-default'}]},
        # Second call for security group details
        {'SecurityGroups': [{'IpPermissions': []}]},
    ]

    mock_ec2.describe_route_tables.return_value = {
        'RouteTables': [{'Routes': [{'GatewayId': 'igw-123'}]}]
    }

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
        patch('awslabs.elasticache_mcp_server.context.Context.readonly_mode', return_value=False),
    ):
        # Call without subnet_id and security_group_id to trigger auto-selection
        result = await create_jump_host_rg('rg-test', 'test-key')

    # Verify successful creation with auto-selected subnet
    assert result['InstanceId'] == 'i-new'
    assert result['PublicIpAddress'] == '1.2.3.4'

    # Verify the run_instances call used the auto-selected subnet
    call_args = mock_ec2.run_instances.call_args[1]
    assert call_args['NetworkInterfaces'][0]['SubnetId'] == 'subnet-public'
    assert call_args['NetworkInterfaces'][0]['Groups'] == ['sg-default']


@pytest.mark.asyncio
async def test_create_jump_host_rg_auto_select_security_group():
    """Test create_jump_host_rg auto-selecting default security group.

    This test covers the specific code path:
    if security_groups:
        security_group_id = security_groups[0]['GroupId']
    """
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

    # Mock VPC as default VPC
    mock_ec2.describe_vpcs.return_value = {'Vpcs': [{'IsDefault': True}]}

    # Mock default subnets available
    mock_ec2.describe_subnets.side_effect = [
        # First call for default subnets
        {'Subnets': [{'SubnetId': 'subnet-default'}]},
        # Second call for the selected subnet details
        {
            'Subnets': [
                {
                    'SubnetId': 'subnet-default',
                    'VpcId': 'vpc-123',
                    'MapPublicIpOnLaunch': True,
                    'DefaultForAz': True,
                }
            ]
        },
    ]

    # Mock security groups - this covers the "if security_groups:" path
    mock_ec2.describe_security_groups.side_effect = [
        # First call for default security group (should find it)
        {'SecurityGroups': [{'GroupId': 'sg-default-found'}]},
        # Second call for security group details
        {'SecurityGroups': [{'IpPermissions': []}]},
    ]

    mock_ec2.describe_route_tables.return_value = {
        'RouteTables': [{'Routes': [{'GatewayId': 'igw-123'}]}]
    }

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
        patch('awslabs.elasticache_mcp_server.context.Context.readonly_mode', return_value=False),
    ):
        # Call without subnet_id and security_group_id to trigger auto-selection
        result = await create_jump_host_rg('rg-test', 'test-key')

    # Verify successful creation with auto-selected security group
    assert result['InstanceId'] == 'i-new'
    assert result['PublicIpAddress'] == '1.2.3.4'

    # Verify the run_instances call used the auto-selected security group
    call_args = mock_ec2.run_instances.call_args[1]
    assert call_args['NetworkInterfaces'][0]['SubnetId'] == 'subnet-default'
    assert call_args['NetworkInterfaces'][0]['Groups'] == ['sg-default-found']


@pytest.mark.asyncio
async def test_create_jump_host_rg_main_route_table_igw_check():
    """Test create_jump_host_rg checking main route table for IGW routes.

    This test covers the specific code path:
    for rt in main_route_tables:
        for route in rt.get('Routes', []):
            if route.get('GatewayId', '').startswith('igw-'):
                is_public = True
                break
        if is_public:
            break
    """
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
        'Subnets': [
            {
                'VpcId': 'vpc-123',
                'MapPublicIpOnLaunch': False,
                'DefaultForAz': False,
            }
        ]
    }

    # Mock route tables - first call returns empty (no explicit association),
    # second call returns main route table with IGW
    mock_ec2.describe_route_tables.side_effect = [
        # First call for explicit route table association (empty)
        {'RouteTables': []},
        # Second call for main route table
        {
            'RouteTables': [
                {
                    'Routes': [
                        {'GatewayId': 'local'},
                        {'GatewayId': 'igw-123456'},  # IGW route found in main route table
                    ]
                }
            ]
        },
    ]

    # Mock VPC as non-default
    mock_ec2.describe_vpcs.return_value = {'Vpcs': [{'IsDefault': False}]}

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

    # Verify successful creation (subnet is considered public due to IGW in main route table)
    assert result['InstanceId'] == 'i-new'
    assert result['PublicIpAddress'] == '1.2.3.4'

    # Verify both route table calls were made
    assert mock_ec2.describe_route_tables.call_count == 2

    # Verify the calls were for the right filters
    call_args_list = mock_ec2.describe_route_tables.call_args_list

    # First call should be for explicit association
    first_call_filters = call_args_list[0][1]['Filters']
    assert any(
        f['Name'] == 'association.subnet-id' and f['Values'] == ['subnet-123']
        for f in first_call_filters
    )

    # Second call should be for main route table
    second_call_filters = call_args_list[1][1]['Filters']
    assert any(f['Name'] == 'vpc-id' and f['Values'] == ['vpc-123'] for f in second_call_filters)
    assert any(
        f['Name'] == 'association.main' and f['Values'] == ['true'] for f in second_call_filters
    )


@pytest.mark.asyncio
async def test_create_jump_host_rg_main_route_table_break_on_igw_found():
    """Test create_jump_host_rg breaking out of loops when IGW is found in main route table.

    This test specifically covers the break statements in the nested loops:
    for rt in main_route_tables:
        for route in rt.get('Routes', []):
            if route.get('GatewayId', '').startswith('igw-'):
                is_public = True
                break  # Inner break
        if is_public:
            break  # Outer break
    """
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
        'Subnets': [
            {
                'VpcId': 'vpc-123',
                'MapPublicIpOnLaunch': False,
                'DefaultForAz': False,
            }
        ]
    }

    # Mock route tables - first call returns empty, second call returns multiple route tables
    # with IGW in the first one to test the break logic
    mock_ec2.describe_route_tables.side_effect = [
        # First call for explicit route table association (empty)
        {'RouteTables': []},
        # Second call for main route tables (multiple tables to test break logic)
        {
            'RouteTables': [
                {
                    'Routes': [
                        {'GatewayId': 'local'},
                        {'GatewayId': 'igw-first'},  # IGW found in first route table
                        {'GatewayId': 'nat-123'},
                    ]
                },
                {
                    'Routes': [
                        {'GatewayId': 'local'},
                        {'GatewayId': 'igw-second'},  # This shouldn't be processed due to break
                    ]
                },
            ]
        },
    ]

    # Mock VPC as non-default
    mock_ec2.describe_vpcs.return_value = {'Vpcs': [{'IsDefault': False}]}

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

    # Verify successful creation (subnet is considered public due to IGW found)
    assert result['InstanceId'] == 'i-new'
    assert result['PublicIpAddress'] == '1.2.3.4'

    # Verify both route table calls were made
    assert mock_ec2.describe_route_tables.call_count == 2
