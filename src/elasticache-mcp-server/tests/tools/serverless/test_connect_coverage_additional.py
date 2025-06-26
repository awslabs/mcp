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

"""Additional coverage tests for serverless cache connection tools to achieve 100% coverage."""

import pytest
from awslabs.elasticache_mcp_server.tools.serverless.connect import (
    _configure_security_groups,
    connect_jump_host_serverless,
    create_jump_host_serverless,
    get_ssh_tunnel_command_serverless,
)
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_configure_security_groups_no_clients_provided():
    """Test _configure_security_groups when no clients are provided (lines 43, 45)."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock responses
    mock_elasticache.describe_serverless_caches.return_value = {
        'ServerlessCaches': [
            {
                'SecurityGroupIds': ['sg-cache'],
                'SubnetIds': ['subnet-123'],
                'Engine': 'redis',
                'Endpoint': {'Port': 6379},
            }
        ]
    }

    mock_ec2.describe_subnets.return_value = {'Subnets': [{'VpcId': 'vpc-123'}]}

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
        result = await _configure_security_groups('serverless-test', 'i-123')

        assert result[0] is True  # success
        assert result[1] == 'vpc-123'  # vpc_id
        assert result[2] == 6379  # cache_port


@pytest.mark.asyncio
async def test_configure_security_groups_memcached_engine():
    """Test _configure_security_groups with memcached engine (line 366->372)."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock responses with memcached engine
    mock_elasticache.describe_serverless_caches.return_value = {
        'ServerlessCaches': [
            {
                'SecurityGroupIds': ['sg-cache'],
                'SubnetIds': ['subnet-123'],
                'Engine': 'memcached',  # Memcached engine - line 366->372
                # No Endpoint provided to test default port logic
            }
        ]
    }

    mock_ec2.describe_subnets.return_value = {'Subnets': [{'VpcId': 'vpc-123'}]}

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

    result = await _configure_security_groups(
        'serverless-test', 'i-123', mock_ec2, mock_elasticache
    )

    assert result[0] is True  # success
    assert result[1] == 'vpc-123'  # vpc_id
    assert result[2] == 11211  # memcached default port


@pytest.mark.asyncio
async def test_configure_security_groups_redis_default_port():
    """Test _configure_security_groups with redis engine default port (line 367->366)."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock responses with redis engine but no endpoint port
    mock_elasticache.describe_serverless_caches.return_value = {
        'ServerlessCaches': [
            {
                'SecurityGroupIds': ['sg-cache'],
                'SubnetIds': ['subnet-123'],
                'Engine': 'redis',  # Redis engine - line 367->366
                # No Endpoint provided to test default port logic
            }
        ]
    }

    mock_ec2.describe_subnets.return_value = {'Subnets': [{'VpcId': 'vpc-123'}]}

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

    result = await _configure_security_groups(
        'serverless-test', 'i-123', mock_ec2, mock_elasticache
    )

    assert result[0] is True  # success
    assert result[1] == 'vpc-123'  # vpc_id
    assert result[2] == 6379  # redis default port


@pytest.mark.asyncio
async def test_create_jump_host_serverless_no_main_route_table():
    """Test create_jump_host_serverless when no explicit route table association exists (line 381->385)."""
    mock_ec2 = MagicMock()
    mock_elasticache = MagicMock()

    # Mock responses
    mock_ec2.describe_key_pairs.return_value = {'KeyPairs': [{'KeyName': 'test-key'}]}

    mock_elasticache.describe_serverless_caches.return_value = {
        'ServerlessCaches': [
            {
                'SecurityGroupIds': ['sg-cache'],
                'SubnetIds': ['subnet-123'],
                'Engine': 'redis',
            }
        ]
    }

    mock_ec2.describe_subnets.return_value = {
        'Subnets': [{'VpcId': 'vpc-123', 'MapPublicIpOnLaunch': True}]
    }

    mock_ec2.describe_vpcs.return_value = {'Vpcs': [{'IsDefault': False}]}

    # Mock no explicit route table association, then main route table
    mock_ec2.describe_route_tables.side_effect = [
        {'RouteTables': []},  # No explicit association
        {
            'RouteTables': [{'Routes': [{'GatewayId': 'igw-123'}]}]
        },  # Main route table with IGW - line 381->385
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
            'awslabs.elasticache_mcp_server.tools.serverless.connect._configure_security_groups',
            return_value=(True, 'vpc-123', 6379),
        ),
        patch('awslabs.elasticache_mcp_server.context.Context.readonly_mode', return_value=False),
    ):
        result = await create_jump_host_serverless(
            'serverless-test', 'test-key', 'subnet-123', 'sg-123'
        )

    # Debug: Print the actual result
    print(f'Actual result: {result}')

    # Verify successful creation
    assert result['InstanceId'] == 'i-new'
    assert result['PublicIpAddress'] == '1.2.3.4'


@pytest.mark.asyncio
async def test_connect_jump_host_serverless_readonly_mode():
    """Test connect_jump_host_serverless in readonly mode."""
    with patch('awslabs.elasticache_mcp_server.context.Context.readonly_mode', return_value=True):
        result = await connect_jump_host_serverless('serverless-test', 'i-123')
        assert 'error' in result
        assert 'You have configured this tool in readonly mode' in result['error']


@pytest.mark.asyncio
async def test_get_ssh_tunnel_command_serverless_memcached_default_port():
    """Test get_ssh_tunnel_command_serverless with memcached engine default port."""
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

    # Mock serverless cache with memcached engine
    mock_elasticache.describe_serverless_caches.return_value = {
        'ServerlessCaches': [
            {
                'Engine': 'memcached',
                'Endpoint': {'Address': 'cache.abc123.cache.amazonaws.com'},
                # No Port in Endpoint to test default port logic
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
        result = await get_ssh_tunnel_command_serverless('serverless-test', 'i-123')

    # Verify response uses memcached default port
    assert result['keyName'] == 'test-key'
    assert result['user'] == 'ec2-user'
    assert result['localPort'] == 11211  # memcached default port
    assert result['cachePort'] == 11211
    assert '11211' in result['command']


@pytest.mark.asyncio
async def test_get_ssh_tunnel_command_serverless_redis_default_port():
    """Test get_ssh_tunnel_command_serverless with redis engine default port."""
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

    # Mock serverless cache with redis engine
    mock_elasticache.describe_serverless_caches.return_value = {
        'ServerlessCaches': [
            {
                'Engine': 'redis',
                'Endpoint': {'Address': 'cache.abc123.cache.amazonaws.com'},
                # No Port in Endpoint to test default port logic
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
        result = await get_ssh_tunnel_command_serverless('serverless-test', 'i-123')

    # Verify response uses redis default port
    assert result['keyName'] == 'test-key'
    assert result['user'] == 'ec2-user'
    assert result['localPort'] == 6379  # redis default port
    assert result['cachePort'] == 6379
    assert '6379' in result['command']


@pytest.mark.asyncio
async def test_create_jump_host_serverless_readonly_mode():
    """Test create_jump_host_serverless in readonly mode."""
    with patch('awslabs.elasticache_mcp_server.context.Context.readonly_mode', return_value=True):
        result = await create_jump_host_serverless('serverless-test', 'test-key')
        assert 'error' in result
        assert 'You have configured this tool in readonly mode' in result['error']
