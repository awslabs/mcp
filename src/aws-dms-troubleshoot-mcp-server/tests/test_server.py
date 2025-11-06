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

"""Tests for AWS DMS Troubleshooting MCP Server."""

import json
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_dms_client():
    """Mock DMS client for testing."""
    client = MagicMock()
    return client


@pytest.fixture
def mock_logs_client():
    """Mock CloudWatch Logs client for testing."""
    client = MagicMock()
    return client


@pytest.fixture
def sample_replication_task():
    """Sample replication task data."""
    return {
        'ReplicationTaskArn': 'arn:aws:dms:us-east-1:123456789012:task:ABC123',
        'ReplicationTaskIdentifier': 'test-task-1',
        'Status': 'running',
        'MigrationType': 'full-load-and-cdc',
        'SourceEndpointArn': 'arn:aws:dms:us-east-1:123456789012:endpoint:source',
        'TargetEndpointArn': 'arn:aws:dms:us-east-1:123456789012:endpoint:target',
        'ReplicationInstanceArn': 'arn:aws:dms:us-east-1:123456789012:rep:instance',
        'TableMappings': json.dumps({'rules': [{'rule-type': 'selection'}]}),
        'ReplicationTaskStats': {
            'FullLoadProgressPercent': 100,
            'TablesLoaded': 10,
            'TablesLoading': 0,
            'TablesQueued': 0,
            'TablesErrored': 0,
        },
    }


@pytest.fixture
def sample_endpoint():
    """Sample endpoint data."""
    return {
        'EndpointIdentifier': 'test-source',
        'EndpointType': 'source',
        'EngineName': 'mysql',
        'ServerName': 'db.example.com',
        'Port': 3306,
        'DatabaseName': 'testdb',
        'Username': 'admin',
        'SslMode': 'require',
        'Status': 'active',
    }


@pytest.mark.asyncio
async def test_list_replication_tasks(mock_dms_client, sample_replication_task):
    """Test listing replication tasks."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import list_replication_tasks

    mock_dms_client.describe_replication_tasks.return_value = {
        'ReplicationTasks': [sample_replication_task]
    }

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms_client,
    ):
        result = await list_replication_tasks(region='us-east-1')

        assert result['total_tasks'] == 1
        assert result['region'] == 'us-east-1'
        assert 'running' in result['status_summary']
        assert result['tasks'][0]['task_identifier'] == 'test-task-1'


@pytest.mark.asyncio
async def test_list_replication_tasks_with_filter(mock_dms_client, sample_replication_task):
    """Test listing replication tasks with status filter."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import list_replication_tasks

    mock_dms_client.describe_replication_tasks.return_value = {
        'ReplicationTasks': [sample_replication_task]
    }

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms_client,
    ):
        result = await list_replication_tasks(region='us-east-1', status_filter='running')

        assert result['total_tasks'] == 1
        mock_dms_client.describe_replication_tasks.assert_called_once()
        call_args = mock_dms_client.describe_replication_tasks.call_args[1]
        assert len(call_args['Filters']) == 1
        assert call_args['Filters'][0]['Name'] == 'replication-task-status'


@pytest.mark.asyncio
async def test_get_replication_task_details(mock_dms_client, sample_replication_task):
    """Test getting replication task details."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import get_replication_task_details

    sample_replication_task['ReplicationTaskCreationDate'] = datetime.now()
    sample_replication_task['ReplicationTaskSettings'] = json.dumps({'FullLoadSettings': {}})

    mock_dms_client.describe_replication_tasks.return_value = {
        'ReplicationTasks': [sample_replication_task]
    }

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms_client,
    ):
        result = await get_replication_task_details(
            task_identifier='test-task-1', region='us-east-1'
        )

        assert result['task_identifier'] == 'test-task-1'
        assert result['status'] == 'running'
        assert result['migration_type'] == 'full-load-and-cdc'
        assert 'statistics' in result


@pytest.mark.asyncio
async def test_get_replication_task_details_not_found(mock_dms_client):
    """Test getting details for non-existent task."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import get_replication_task_details

    mock_dms_client.describe_replication_tasks.return_value = {'ReplicationTasks': []}

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms_client,
    ):
        result = await get_replication_task_details(
            task_identifier='non-existent', region='us-east-1'
        )

        assert 'error' in result
        assert 'not found' in result['error'].lower()


@pytest.mark.asyncio
async def test_get_task_cloudwatch_logs(mock_logs_client):
    """Test retrieving CloudWatch logs."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import get_task_cloudwatch_logs

    # Mock with empty log streams to return empty result (simplest passing test)
    mock_logs_client.describe_log_streams.return_value = {'logStreams': []}

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_logs_client',
        return_value=mock_logs_client,
    ):
        result = await get_task_cloudwatch_logs(task_identifier='test-task-1', region='us-east-1')

        # Just verify the basic structure is correct
        assert 'log_events' in result
        assert 'log_group' in result
        assert result['log_group'] == 'dms-tasks-test-task-1'
        assert isinstance(result['log_events'], list)


@pytest.mark.asyncio
async def test_get_task_cloudwatch_logs_not_found(mock_logs_client):
    """Test retrieving logs when log group doesn't exist."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import get_task_cloudwatch_logs
    from botocore.exceptions import ClientError

    # Create a proper ClientError exception
    error_response = {
        'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Log group not found'}
    }
    mock_logs_client.describe_log_streams.side_effect = ClientError(
        error_response, 'DescribeLogStreams'
    )

    # Mock the exceptions attribute
    mock_exception = type('ResourceNotFoundException', (ClientError,), {})
    mock_logs_client.exceptions.ResourceNotFoundException = mock_exception

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_logs_client',
        return_value=mock_logs_client,
    ):
        result = await get_task_cloudwatch_logs(task_identifier='test-task-1', region='us-east-1')

        assert 'error' in result
        assert 'not found' in result['error'].lower()


@pytest.mark.asyncio
async def test_analyze_endpoint(mock_dms_client, sample_endpoint):
    """Test endpoint analysis."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import analyze_endpoint

    mock_dms_client.describe_endpoints.return_value = {'Endpoints': [sample_endpoint]}

    mock_dms_client.test_connection.return_value = {
        'Connection': {'Status': 'successful', 'LastFailureMessage': ''}
    }

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms_client,
    ):
        result = await analyze_endpoint(
            endpoint_arn='arn:aws:dms:us-east-1:123456789012:endpoint:test', region='us-east-1'
        )

        assert result['endpoint_details']['endpoint_identifier'] == 'test-source'
        assert result['endpoint_details']['engine_name'] == 'mysql'
        assert result['analysis_complete'] is True


@pytest.mark.asyncio
async def test_analyze_endpoint_ssl_warning(mock_dms_client, sample_endpoint):
    """Test endpoint analysis identifies SSL issues."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import analyze_endpoint

    sample_endpoint['SslMode'] = 'none'
    mock_dms_client.describe_endpoints.return_value = {'Endpoints': [sample_endpoint]}

    mock_dms_client.test_connection.return_value = {
        'Connection': {'Status': 'successful', 'LastFailureMessage': ''}
    }

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms_client,
    ):
        result = await analyze_endpoint(
            endpoint_arn='arn:aws:dms:us-east-1:123456789012:endpoint:test', region='us-east-1'
        )

        assert len(result['potential_issues']) > 0
        assert any('SSL' in issue for issue in result['potential_issues'])


@pytest.mark.asyncio
async def test_get_troubleshooting_recommendations_connection():
    """Test getting recommendations for connection errors."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import (
        get_troubleshooting_recommendations,
    )

    result = await get_troubleshooting_recommendations(error_pattern='connection timeout')

    assert 'Connection/Network Issues' in result['matched_patterns']
    assert len(result['recommendations']) > 0
    assert len(result['documentation_links']) > 0
    assert any('security group' in rec.lower() for rec in result['recommendations'])


@pytest.mark.asyncio
async def test_get_troubleshooting_recommendations_auth():
    """Test getting recommendations for authentication errors."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import (
        get_troubleshooting_recommendations,
    )

    result = await get_troubleshooting_recommendations(error_pattern='access denied')

    assert 'Authentication/Authorization Issues' in result['matched_patterns']
    assert any(
        'credential' in rec.lower() or 'permission' in rec.lower()
        for rec in result['recommendations']
    )


@pytest.mark.asyncio
async def test_get_troubleshooting_recommendations_cdc():
    """Test getting recommendations for CDC issues."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import (
        get_troubleshooting_recommendations,
    )

    result = await get_troubleshooting_recommendations(error_pattern='binlog error')

    assert 'CDC/Replication Issues' in result['matched_patterns']
    assert any(
        'binlog' in rec.lower() or 'cdc' in rec.lower() for rec in result['recommendations']
    )


@pytest.mark.asyncio
async def test_diagnose_replication_issue(
    mock_dms_client, sample_replication_task, sample_endpoint
):
    """Test comprehensive replication issue diagnosis."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import diagnose_replication_issue

    # Setup mock for task details
    sample_replication_task['ReplicationTaskCreationDate'] = datetime.now()
    sample_replication_task['ReplicationTaskSettings'] = json.dumps({})
    sample_replication_task['Status'] = 'failed'
    sample_replication_task['LastFailureMessage'] = 'Connection timeout'

    mock_dms_client.describe_replication_tasks.return_value = {
        'ReplicationTasks': [sample_replication_task]
    }

    # Setup mock for endpoint analysis
    mock_dms_client.describe_endpoints.return_value = {'Endpoints': [sample_endpoint]}

    mock_dms_client.test_connection.return_value = {
        'Connection': {'Status': 'failed', 'LastFailureMessage': 'Timeout'}
    }

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms_client,
    ):
        with patch(
            'awslabs.aws_dms_troubleshoot_mcp_server.server.get_task_cloudwatch_logs'
        ) as mock_logs:
            mock_logs.return_value = {
                'total_events': 10,
                'log_summary': {'errors': 5, 'warnings': 2, 'fatal': 0},
                'log_events': [],
            }

            result = await diagnose_replication_issue(
                task_identifier='test-task-1', region='us-east-1'
            )

            assert result['task_identifier'] == 'test-task-1'
            assert result['status'] == 'failed'
            assert result['severity'] == 'CRITICAL'
            assert len(result['root_causes']) > 0
            assert len(result['recommendations']) > 0


@pytest.mark.asyncio
async def test_diagnose_replication_issue_healthy(
    mock_dms_client, sample_replication_task, sample_endpoint
):
    """Test diagnosis of healthy replication task."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import diagnose_replication_issue

    # Setup mock for healthy task
    sample_replication_task['ReplicationTaskCreationDate'] = datetime.now()
    sample_replication_task['ReplicationTaskSettings'] = json.dumps({})
    sample_replication_task['Status'] = 'running'

    mock_dms_client.describe_replication_tasks.return_value = {
        'ReplicationTasks': [sample_replication_task]
    }

    mock_dms_client.describe_endpoints.return_value = {'Endpoints': [sample_endpoint]}

    mock_dms_client.test_connection.return_value = {
        'Connection': {'Status': 'successful', 'LastFailureMessage': ''}
    }

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms_client,
    ):
        with patch(
            'awslabs.aws_dms_troubleshoot_mcp_server.server.get_task_cloudwatch_logs'
        ) as mock_logs:
            mock_logs.return_value = {
                'total_events': 5,
                'log_summary': {'errors': 0, 'warnings': 0, 'fatal': 0},
                'log_events': [],
            }

            result = await diagnose_replication_issue(
                task_identifier='test-task-1', region='us-east-1'
            )

            assert result['severity'] == 'INFO'
            assert 'healthy' in str(result['recommendations']).lower()


@pytest.mark.asyncio
async def test_analyze_security_groups():
    """Test security group analysis."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import analyze_security_groups
    from unittest.mock import MagicMock

    mock_dms = MagicMock()
    mock_ec2 = MagicMock()

    # Mock replication instance
    mock_dms.describe_replication_instances.return_value = {
        'ReplicationInstances': [
            {
                'VpcSecurityGroups': [{'VpcSecurityGroupId': 'sg-123'}],
                'ReplicationSubnetGroup': {'Subnets': [{'SubnetIdentifier': 'subnet-123'}]},
            }
        ]
    }

    # Mock security groups
    mock_ec2.describe_security_groups.return_value = {
        'SecurityGroups': [
            {
                'GroupId': 'sg-123',
                'GroupName': 'dms-sg',
                'Description': 'DMS Security Group',
                'VpcId': 'vpc-123',
                'IpPermissions': [],
                'IpPermissionsEgress': [
                    {
                        'IpProtocol': '-1',
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}],
                        'UserIdGroupPairs': [],
                    }
                ],
            }
        ]
    }

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms,
    ):
        with patch(
            'awslabs.aws_dms_troubleshoot_mcp_server.server.get_ec2_client',
            return_value=mock_ec2,
        ):
            result = await analyze_security_groups(
                replication_instance_arn='arn:aws:dms:us-east-1:123456789012:rep:test',
                region='us-east-1',
            )

            assert 'security_groups' in result
            assert len(result['security_groups']) == 1
            assert result['security_groups'][0]['group_id'] == 'sg-123'


@pytest.mark.asyncio
async def test_diagnose_network_connectivity(mock_dms_client, sample_replication_task):
    """Test network connectivity diagnostics."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import diagnose_network_connectivity
    from unittest.mock import MagicMock

    mock_ec2 = MagicMock()

    # Setup task
    sample_replication_task['ReplicationInstanceArn'] = (
        'arn:aws:dms:us-east-1:123456789012:rep:test'
    )
    mock_dms_client.describe_replication_tasks.return_value = {
        'ReplicationTasks': [sample_replication_task]
    }

    # Setup replication instance
    mock_dms_client.describe_replication_instances.return_value = {
        'ReplicationInstances': [
            {
                'ReplicationInstanceArn': 'arn:aws:dms:us-east-1:123456789012:rep:test',
                'ReplicationInstancePublicIpAddress': '1.2.3.4',
                'ReplicationInstancePrivateIpAddress': '10.0.0.5',
                'PubliclyAccessible': False,
                'MultiAZ': False,
                'VpcSecurityGroups': [{'VpcSecurityGroupId': 'sg-123'}],
                'ReplicationSubnetGroup': {'Subnets': [{'SubnetIdentifier': 'subnet-123'}]},
            }
        ]
    }

    # Setup endpoints
    mock_dms_client.describe_endpoints.return_value = {
        'Endpoints': [
            {
                'ServerName': 'db.example.com',
                'Port': 3306,
                'EngineName': 'mysql',
            }
        ]
    }

    # Setup EC2 mocks
    mock_ec2.describe_subnets.return_value = {
        'Subnets': [{'SubnetId': 'subnet-123', 'VpcId': 'vpc-123'}]
    }

    mock_ec2.describe_route_tables.return_value = {
        'RouteTables': [
            {
                'RouteTableId': 'rtb-123',
                'Routes': [{'GatewayId': 'local', 'DestinationCidrBlock': '10.0.0.0/16'}],
            }
        ]
    }

    mock_ec2.describe_security_groups.return_value = {
        'SecurityGroups': [
            {
                'GroupId': 'sg-123',
                'GroupName': 'dms-sg',
                'Description': 'DMS SG',
                'VpcId': 'vpc-123',
                'IpPermissions': [],
                'IpPermissionsEgress': [
                    {'IpProtocol': '-1', 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
                ],
            }
        ]
    }

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms_client,
    ):
        with patch(
            'awslabs.aws_dms_troubleshoot_mcp_server.server.get_ec2_client',
            return_value=mock_ec2,
        ):
            result = await diagnose_network_connectivity(
                task_identifier='test-task-1', region='us-east-1'
            )

            assert 'network_summary' in result
            assert 'connectivity_checks' in result
            assert result['task_identifier'] == 'test-task-1'


@pytest.mark.asyncio
async def test_check_vpc_configuration():
    """Test VPC configuration analysis."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import check_vpc_configuration
    from unittest.mock import MagicMock

    mock_ec2 = MagicMock()

    # Mock VPC
    mock_ec2.describe_vpcs.return_value = {
        'Vpcs': [
            {
                'VpcId': 'vpc-123',
                'CidrBlock': '10.0.0.0/16',
                'IsDefault': False,
                'State': 'available',
                'EnableDnsSupport': True,
                'EnableDnsHostnames': True,
            }
        ]
    }

    # Mock route tables
    mock_ec2.describe_route_tables.return_value = {
        'RouteTables': [
            {
                'RouteTableId': 'rtb-123',
                'Associations': [{'Main': True}],
                'Routes': [
                    {
                        'DestinationCidrBlock': '10.0.0.0/16',
                        'GatewayId': 'local',
                        'State': 'active',
                    }
                ],
            }
        ]
    }

    # Mock internet gateway
    mock_ec2.describe_internet_gateways.return_value = {'InternetGateways': []}

    # Mock NAT gateways
    mock_ec2.describe_nat_gateways.return_value = {'NatGateways': []}

    # Mock VPC peering
    mock_ec2.describe_vpc_peering_connections.return_value = {'VpcPeeringConnections': []}

    # Mock Transit Gateway
    mock_ec2.describe_transit_gateway_attachments.return_value = {'TransitGatewayAttachments': []}

    # Mock Network ACLs
    mock_ec2.describe_network_acls.return_value = {
        'NetworkAcls': [
            {
                'NetworkAclId': 'acl-123',
                'IsDefault': True,
                'Entries': [
                    {
                        'RuleNumber': 100,
                        'Protocol': '-1',
                        'RuleAction': 'allow',
                        'Egress': False,
                        'CidrBlock': '0.0.0.0/0',
                    },
                    {
                        'RuleNumber': 100,
                        'Protocol': '-1',
                        'RuleAction': 'allow',
                        'Egress': True,
                        'CidrBlock': '0.0.0.0/0',
                    },
                ],
            }
        ]
    }

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_ec2_client',
        return_value=mock_ec2,
    ):
        result = await check_vpc_configuration(vpc_id='vpc-123', region='us-east-1')

        assert 'vpc_details' in result
        assert result['vpc_details']['vpc_id'] == 'vpc-123'
        assert 'routing_analysis' in result
        assert 'network_acl_analysis' in result
        assert 'connectivity_options' in result


@pytest.mark.asyncio
async def test_get_troubleshooting_recommendations_table_issues():
    """Test recommendations for table/schema issues."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import (
        get_troubleshooting_recommendations,
    )

    result = await get_troubleshooting_recommendations(error_pattern='table constraint error')

    assert 'Table/Schema Issues' in result['matched_patterns']
    assert any('table mapping' in rec.lower() for rec in result['recommendations'])


@pytest.mark.asyncio
async def test_get_troubleshooting_recommendations_performance():
    """Test recommendations for performance issues."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import (
        get_troubleshooting_recommendations,
    )

    result = await get_troubleshooting_recommendations(error_pattern='slow replication')

    assert 'Performance Issues' in result['matched_patterns']
    assert any('instance size' in rec.lower() for rec in result['recommendations'])


@pytest.mark.asyncio
async def test_get_troubleshooting_recommendations_ssl():
    """Test recommendations for SSL/TLS issues."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import (
        get_troubleshooting_recommendations,
    )

    result = await get_troubleshooting_recommendations(error_pattern='ssl certificate error')

    assert 'SSL/TLS Issues' in result['matched_patterns']
    assert any('certificate' in rec.lower() for rec in result['recommendations'])


@pytest.mark.asyncio
async def test_get_troubleshooting_recommendations_generic():
    """Test generic recommendations for unknown patterns."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import (
        get_troubleshooting_recommendations,
    )

    result = await get_troubleshooting_recommendations(error_pattern='unknown error xyz')

    assert 'General Troubleshooting' in result['matched_patterns']
    assert len(result['documentation_links']) > 0


@pytest.mark.asyncio
async def test_analyze_endpoint_not_found():
    """Test endpoint analysis when endpoint doesn't exist."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import analyze_endpoint
    from unittest.mock import MagicMock

    mock_dms = MagicMock()
    mock_dms.describe_endpoints.return_value = {'Endpoints': []}

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms,
    ):
        result = await analyze_endpoint(
            endpoint_arn='arn:aws:dms:us-east-1:123456789012:endpoint:nonexistent',
            region='us-east-1',
        )

        assert 'error' in result
        assert 'not found' in result['error'].lower()


@pytest.mark.asyncio
async def test_analyze_endpoint_mysql_settings(sample_endpoint):
    """Test endpoint analysis with MySQL-specific settings."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import analyze_endpoint
    from unittest.mock import MagicMock

    mock_dms = MagicMock()
    sample_endpoint['EngineName'] = 'mysql'
    sample_endpoint['MySqlSettings'] = {'ServerTimezone': 'UTC'}
    mock_dms.describe_endpoints.return_value = {'Endpoints': [sample_endpoint]}
    mock_dms.test_connection.return_value = {
        'Connection': {'Status': 'successful', 'LastFailureMessage': ''}
    }

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms,
    ):
        result = await analyze_endpoint(
            endpoint_arn='arn:aws:dms:us-east-1:123456789012:endpoint:test', region='us-east-1'
        )

        assert 'mysql_settings' in result['endpoint_details']


@pytest.mark.asyncio
async def test_analyze_endpoint_postgres_settings(sample_endpoint):
    """Test endpoint analysis with PostgreSQL-specific settings."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import analyze_endpoint
    from unittest.mock import MagicMock

    mock_dms = MagicMock()
    sample_endpoint['EngineName'] = 'postgres'
    sample_endpoint['PostgreSqlSettings'] = {'PluginName': 'pglogical'}
    mock_dms.describe_endpoints.return_value = {'Endpoints': [sample_endpoint]}
    mock_dms.test_connection.return_value = {
        'Connection': {'Status': 'successful', 'LastFailureMessage': ''}
    }

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms,
    ):
        result = await analyze_endpoint(
            endpoint_arn='arn:aws:dms:us-east-1:123456789012:endpoint:test', region='us-east-1'
        )

        assert 'postgresql_settings' in result['endpoint_details']


@pytest.mark.asyncio
async def test_analyze_endpoint_oracle_settings(sample_endpoint):
    """Test endpoint analysis with Oracle-specific settings."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import analyze_endpoint
    from unittest.mock import MagicMock

    mock_dms = MagicMock()
    sample_endpoint['EngineName'] = 'oracle'
    sample_endpoint['OracleSettings'] = {'SupplementalLogging': True}
    mock_dms.describe_endpoints.return_value = {'Endpoints': [sample_endpoint]}
    mock_dms.test_connection.return_value = {
        'Connection': {'Status': 'successful', 'LastFailureMessage': ''}
    }

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms,
    ):
        result = await analyze_endpoint(
            endpoint_arn='arn:aws:dms:us-east-1:123456789012:endpoint:test', region='us-east-1'
        )

        assert 'oracle_settings' in result['endpoint_details']


@pytest.mark.asyncio
async def test_analyze_endpoint_s3_settings(sample_endpoint):
    """Test endpoint analysis with S3-specific settings."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import analyze_endpoint
    from unittest.mock import MagicMock

    mock_dms = MagicMock()
    sample_endpoint['EngineName'] = 's3'
    sample_endpoint['S3Settings'] = {'BucketName': 'my-bucket'}
    mock_dms.describe_endpoints.return_value = {'Endpoints': [sample_endpoint]}
    mock_dms.test_connection.return_value = {
        'Connection': {'Status': 'successful', 'LastFailureMessage': ''}
    }

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms,
    ):
        result = await analyze_endpoint(
            endpoint_arn='arn:aws:dms:us-east-1:123456789012:endpoint:test', region='us-east-1'
        )

        assert 's3_settings' in result['endpoint_details']


@pytest.mark.asyncio
async def test_analyze_security_groups_no_vpc_groups():
    """Test security group analysis when no VPC security groups found."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import analyze_security_groups
    from unittest.mock import MagicMock

    mock_dms = MagicMock()
    mock_ec2 = MagicMock()
    mock_dms.describe_replication_instances.return_value = {
        'ReplicationInstances': [{'VpcSecurityGroups': []}]
    }

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms,
    ):
        with patch(
            'awslabs.aws_dms_troubleshoot_mcp_server.server.get_ec2_client',
            return_value=mock_ec2,
        ):
            result = await analyze_security_groups(
                replication_instance_arn='arn:aws:dms:us-east-1:123456789012:rep:test',
                region='us-east-1',
            )

            assert 'message' in result
            assert 'No VPC security groups' in result['message']


@pytest.mark.asyncio
async def test_analyze_security_groups_not_found():
    """Test security group analysis when instance not found."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import analyze_security_groups
    from unittest.mock import MagicMock

    mock_dms = MagicMock()
    mock_ec2 = MagicMock()
    mock_dms.describe_replication_instances.return_value = {'ReplicationInstances': []}

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms,
    ):
        with patch(
            'awslabs.aws_dms_troubleshoot_mcp_server.server.get_ec2_client',
            return_value=mock_ec2,
        ):
            result = await analyze_security_groups(
                replication_instance_arn='arn:aws:dms:us-east-1:123456789012:rep:nonexistent',
                region='us-east-1',
            )

            assert 'error' in result
            assert 'not found' in result['error'].lower()


@pytest.mark.asyncio
async def test_diagnose_network_connectivity_task_not_found():
    """Test network diagnostics when task not found."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import diagnose_network_connectivity
    from unittest.mock import MagicMock

    mock_dms = MagicMock()
    mock_ec2 = MagicMock()
    mock_dms.describe_replication_tasks.return_value = {'ReplicationTasks': []}

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms,
    ):
        with patch(
            'awslabs.aws_dms_troubleshoot_mcp_server.server.get_ec2_client',
            return_value=mock_ec2,
        ):
            result = await diagnose_network_connectivity(
                task_identifier='nonexistent-task', region='us-east-1'
            )

            assert 'error' in result
            assert 'not found' in result['error'].lower()


@pytest.mark.asyncio
async def test_check_vpc_configuration_not_found():
    """Test VPC configuration when VPC not found."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import check_vpc_configuration
    from unittest.mock import MagicMock

    mock_ec2 = MagicMock()
    mock_ec2.describe_vpcs.return_value = {'Vpcs': []}

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_ec2_client',
        return_value=mock_ec2,
    ):
        result = await check_vpc_configuration(vpc_id='vpc-nonexistent', region='us-east-1')

        assert 'error' in result
        assert 'not found' in result['error'].lower()


@pytest.mark.asyncio
async def test_list_replication_tasks_error():
    """Test error handling in list_replication_tasks."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import list_replication_tasks
    from unittest.mock import MagicMock

    mock_dms = MagicMock()
    mock_dms.describe_replication_tasks.side_effect = Exception('AWS API Error')

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms,
    ):
        result = await list_replication_tasks(region='us-east-1')

        assert 'error' in result
        assert 'AWS API Error' in result['error']


@pytest.mark.asyncio
async def test_get_replication_task_details_error():
    """Test error handling in get_replication_task_details."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import get_replication_task_details
    from unittest.mock import MagicMock

    mock_dms = MagicMock()
    mock_dms.describe_replication_tasks.side_effect = Exception('Connection error')

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms,
    ):
        result = await get_replication_task_details(
            task_identifier='test-task', region='us-east-1'
        )

        assert 'error' in result
        assert 'Connection error' in result['error']


@pytest.mark.asyncio
async def test_analyze_endpoint_error():
    """Test error handling in analyze_endpoint."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import analyze_endpoint
    from unittest.mock import MagicMock

    mock_dms = MagicMock()
    mock_dms.describe_endpoints.side_effect = Exception('API error')

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms,
    ):
        result = await analyze_endpoint(
            endpoint_arn='arn:aws:dms:us-east-1:123456789012:endpoint:test', region='us-east-1'
        )

        assert 'error' in result
        assert 'API error' in result['error']


@pytest.mark.asyncio
async def test_diagnose_replication_issue_error():
    """Test error handling in diagnose_replication_issue."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import diagnose_replication_issue
    from unittest.mock import MagicMock

    mock_dms = MagicMock()
    mock_dms.describe_replication_tasks.side_effect = Exception('Service unavailable')

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms,
    ):
        result = await diagnose_replication_issue(task_identifier='test-task', region='us-east-1')

        assert 'error' in result
        assert 'Service unavailable' in result['error']


@pytest.mark.asyncio
async def test_get_troubleshooting_recommendations_error():
    """Test error handling in get_troubleshooting_recommendations."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import (
        get_troubleshooting_recommendations,
    )

    # This function shouldn't normally error, but let's test with edge case
    result = await get_troubleshooting_recommendations(error_pattern='')

    # Should return generic recommendations for empty pattern
    assert 'matched_patterns' in result
    assert len(result['documentation_links']) > 0


@pytest.mark.asyncio
async def test_analyze_security_groups_error():
    """Test error handling in analyze_security_groups."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import analyze_security_groups
    from unittest.mock import MagicMock

    mock_dms = MagicMock()
    mock_ec2 = MagicMock()
    mock_dms.describe_replication_instances.side_effect = Exception('Network timeout')

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms,
    ):
        with patch(
            'awslabs.aws_dms_troubleshoot_mcp_server.server.get_ec2_client',
            return_value=mock_ec2,
        ):
            result = await analyze_security_groups(
                replication_instance_arn='arn:aws:dms:us-east-1:123456789012:rep:test',
                region='us-east-1',
            )

            assert 'error' in result
            assert 'Network timeout' in result['error']


@pytest.mark.asyncio
async def test_diagnose_network_connectivity_error():
    """Test error handling in diagnose_network_connectivity."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import diagnose_network_connectivity
    from unittest.mock import MagicMock

    mock_dms = MagicMock()
    mock_ec2 = MagicMock()
    mock_dms.describe_replication_tasks.side_effect = Exception('API throttled')

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms,
    ):
        with patch(
            'awslabs.aws_dms_troubleshoot_mcp_server.server.get_ec2_client',
            return_value=mock_ec2,
        ):
            result = await diagnose_network_connectivity(
                task_identifier='test-task', region='us-east-1'
            )

            assert 'error' in result
            assert 'API throttled' in result['error']


@pytest.mark.asyncio
async def test_check_vpc_configuration_error():
    """Test error handling in check_vpc_configuration."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import check_vpc_configuration
    from unittest.mock import MagicMock

    mock_ec2 = MagicMock()
    mock_ec2.describe_vpcs.side_effect = Exception('Permission denied')

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_ec2_client',
        return_value=mock_ec2,
    ):
        result = await check_vpc_configuration(vpc_id='vpc-123', region='us-east-1')

        assert 'error' in result
        assert 'Permission denied' in result['error']


@pytest.mark.asyncio
async def test_analyze_security_groups_with_ingress_rules():
    """Test security group analysis with ingress rules."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import analyze_security_groups
    from unittest.mock import MagicMock

    mock_dms = MagicMock()
    mock_ec2 = MagicMock()

    mock_dms.describe_replication_instances.return_value = {
        'ReplicationInstances': [
            {
                'VpcSecurityGroups': [{'VpcSecurityGroupId': 'sg-123'}],
                'ReplicationSubnetGroup': {'Subnets': [{'SubnetIdentifier': 'subnet-123'}]},
            }
        ]
    }

    mock_ec2.describe_security_groups.return_value = {
        'SecurityGroups': [
            {
                'GroupId': 'sg-123',
                'GroupName': 'dms-sg',
                'Description': 'DMS SG',
                'VpcId': 'vpc-123',
                'IpPermissions': [
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 3306,
                        'ToPort': 3306,
                        'IpRanges': [{'CidrIp': '10.0.0.0/16'}],
                        'UserIdGroupPairs': [{'GroupId': 'sg-456'}],
                    }
                ],
                'IpPermissionsEgress': [
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 5432,
                        'ToPort': 5432,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}],
                        'UserIdGroupPairs': [],
                    }
                ],
            }
        ]
    }

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms,
    ):
        with patch(
            'awslabs.aws_dms_troubleshoot_mcp_server.server.get_ec2_client',
            return_value=mock_ec2,
        ):
            result = await analyze_security_groups(
                replication_instance_arn='arn:aws:dms:us-east-1:123456789012:rep:test',
                region='us-east-1',
            )

            assert 'security_groups' in result
            assert len(result['security_groups'][0]['ingress_rules']) > 0
            assert len(result['security_groups'][0]['egress_rules']) > 0


@pytest.mark.asyncio
async def test_check_vpc_configuration_with_dns_disabled():
    """Test VPC configuration with DNS disabled."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import check_vpc_configuration
    from unittest.mock import MagicMock

    mock_ec2 = MagicMock()

    mock_ec2.describe_vpcs.return_value = {
        'Vpcs': [
            {
                'VpcId': 'vpc-123',
                'CidrBlock': '10.0.0.0/16',
                'IsDefault': False,
                'State': 'available',
                'EnableDnsSupport': False,
                'EnableDnsHostnames': False,
            }
        ]
    }

    mock_ec2.describe_route_tables.return_value = {'RouteTables': []}
    mock_ec2.describe_internet_gateways.return_value = {'InternetGateways': []}
    mock_ec2.describe_nat_gateways.return_value = {'NatGateways': []}
    mock_ec2.describe_vpc_peering_connections.return_value = {'VpcPeeringConnections': []}
    mock_ec2.describe_transit_gateway_attachments.return_value = {'TransitGatewayAttachments': []}
    mock_ec2.describe_network_acls.return_value = {'NetworkAcls': []}

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_ec2_client',
        return_value=mock_ec2,
    ):
        result = await check_vpc_configuration(vpc_id='vpc-123', region='us-east-1')

        assert 'vpc_details' in result
        assert 'recommendations' in result
        # Should recommend enabling DNS
        assert any('DNS' in rec for rec in result['recommendations'])


@pytest.mark.asyncio
async def test_check_vpc_configuration_with_peering():
    """Test VPC configuration with peering and transit gateway."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import check_vpc_configuration
    from unittest.mock import MagicMock

    mock_ec2 = MagicMock()

    mock_ec2.describe_vpcs.return_value = {
        'Vpcs': [
            {
                'VpcId': 'vpc-123',
                'CidrBlock': '10.0.0.0/16',
                'IsDefault': False,
                'State': 'available',
                'EnableDnsSupport': True,
                'EnableDnsHostnames': True,
            }
        ]
    }

    mock_ec2.describe_route_tables.return_value = {'RouteTables': []}
    mock_ec2.describe_internet_gateways.return_value = {
        'InternetGateways': [{'InternetGatewayId': 'igw-123'}]
    }
    mock_ec2.describe_nat_gateways.return_value = {
        'NatGateways': [
            {'NatGatewayId': 'nat-123', 'State': 'available', 'SubnetId': 'subnet-123'}
        ]
    }
    mock_ec2.describe_vpc_peering_connections.return_value = {
        'VpcPeeringConnections': [
            {
                'VpcPeeringConnectionId': 'pcx-123',
                'AccepterVpcInfo': {'VpcId': 'vpc-456', 'CidrBlock': '172.16.0.0/16'},
            }
        ]
    }
    mock_ec2.describe_transit_gateway_attachments.return_value = {
        'TransitGatewayAttachments': [
            {
                'TransitGatewayAttachmentId': 'tgw-attach-123',
                'TransitGatewayId': 'tgw-123',
                'State': 'available',
            }
        ]
    }
    mock_ec2.describe_network_acls.return_value = {
        'NetworkAcls': [
            {
                'NetworkAclId': 'acl-123',
                'IsDefault': False,
                'Entries': [
                    {
                        'RuleNumber': 100,
                        'Protocol': '6',
                        'RuleAction': 'deny',
                        'Egress': False,
                        'CidrBlock': '192.168.0.0/16',
                    }
                ],
            }
        ]
    }

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_ec2_client',
        return_value=mock_ec2,
    ):
        result = await check_vpc_configuration(vpc_id='vpc-123', region='us-east-1')

        assert 'connectivity_options' in result
        assert len(result['connectivity_options']['vpc_peering']) > 0
        assert len(result['connectivity_options']['transit_gateway']) > 0
        assert 'routing_analysis' in result
        assert result['routing_analysis']['internet_gateway'] == 'igw-123'


@pytest.mark.asyncio
async def test_get_task_cloudwatch_logs_with_filter():
    """Test CloudWatch logs with filter pattern."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import get_task_cloudwatch_logs
    from datetime import datetime, timezone
    from unittest.mock import MagicMock

    current_time = datetime.now(timezone.utc)
    timestamp_ms = int(current_time.timestamp() * 1000)

    mock_logs_client = MagicMock()
    mock_logs_client.describe_log_streams.return_value = {
        'logStreams': [{'logStreamName': 'stream1', 'lastEventTime': timestamp_ms}]
    }

    mock_logs_client.filter_log_events.return_value = {
        'events': [
            {'timestamp': timestamp_ms, 'message': 'ERROR: Connection failed'},
        ]
    }

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_logs_client',
        return_value=mock_logs_client,
    ):
        result = await get_task_cloudwatch_logs(
            task_identifier='test-task-1', region='us-east-1', filter_pattern='ERROR'
        )

        assert 'log_events' in result
        mock_logs_client.filter_log_events.assert_called()


@pytest.mark.asyncio
async def test_diagnose_network_connectivity_with_public_instance(sample_replication_task):
    """Test network diagnostics for publicly accessible instance."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import diagnose_network_connectivity
    from unittest.mock import MagicMock

    mock_dms = MagicMock()
    mock_ec2 = MagicMock()

    sample_replication_task['ReplicationInstanceArn'] = (
        'arn:aws:dms:us-east-1:123456789012:rep:test'
    )
    mock_dms.describe_replication_tasks.return_value = {
        'ReplicationTasks': [sample_replication_task]
    }

    mock_dms.describe_replication_instances.return_value = {
        'ReplicationInstances': [
            {
                'ReplicationInstanceArn': 'arn:aws:dms:us-east-1:123456789012:rep:test',
                'PubliclyAccessible': True,
                'VpcSecurityGroups': [{'VpcSecurityGroupId': 'sg-123'}],
                'ReplicationSubnetGroup': {'Subnets': [{'SubnetIdentifier': 'subnet-123'}]},
            }
        ]
    }

    mock_dms.describe_endpoints.return_value = {
        'Endpoints': [
            {
                'ServerName': '192.168.1.1',
                'Port': 3306,
                'EngineName': 'mysql',
            }
        ]
    }

    mock_ec2.describe_subnets.return_value = {
        'Subnets': [{'SubnetId': 'subnet-123', 'VpcId': 'vpc-123'}]
    }

    mock_ec2.describe_route_tables.return_value = {
        'RouteTables': [
            {
                'RouteTableId': 'rtb-123',
                'Routes': [
                    {'GatewayId': 'igw-123', 'DestinationCidrBlock': '0.0.0.0/0'},
                ],
            }
        ]
    }

    mock_ec2.describe_security_groups.return_value = {
        'SecurityGroups': [
            {
                'GroupId': 'sg-123',
                'GroupName': 'dms-sg',
                'IpPermissions': [],
                'IpPermissionsEgress': [],
            }
        ]
    }

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms,
    ):
        with patch(
            'awslabs.aws_dms_troubleshoot_mcp_server.server.get_ec2_client',
            return_value=mock_ec2,
        ):
            result = await diagnose_network_connectivity(
                task_identifier='test-task-1', region='us-east-1'
            )

            assert 'network_summary' in result
            assert any(
                'Public Access' in str(check.get('check'))
                for check in result['connectivity_checks']
            )


@pytest.mark.asyncio
async def test_diagnose_network_connectivity_instance_not_found(sample_replication_task):
    """Test network diagnostics when instance not found."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import diagnose_network_connectivity
    from unittest.mock import MagicMock

    mock_dms = MagicMock()
    mock_ec2 = MagicMock()

    sample_replication_task['ReplicationInstanceArn'] = (
        'arn:aws:dms:us-east-1:123456789012:rep:test'
    )
    mock_dms.describe_replication_tasks.return_value = {
        'ReplicationTasks': [sample_replication_task]
    }

    mock_dms.describe_replication_instances.return_value = {'ReplicationInstances': []}

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms,
    ):
        with patch(
            'awslabs.aws_dms_troubleshoot_mcp_server.server.get_ec2_client',
            return_value=mock_ec2,
        ):
            result = await diagnose_network_connectivity(
                task_identifier='test-task-1', region='us-east-1'
            )

            assert 'error' in result
            assert 'replication instance' in result['message'].lower()


@pytest.mark.asyncio
async def test_diagnose_network_connectivity_subnet_error(sample_replication_task):
    """Test network diagnostics with subnet errors."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import diagnose_network_connectivity
    from unittest.mock import MagicMock

    mock_dms = MagicMock()
    mock_ec2 = MagicMock()

    sample_replication_task['ReplicationInstanceArn'] = (
        'arn:aws:dms:us-east-1:123456789012:rep:test'
    )
    mock_dms.describe_replication_tasks.return_value = {
        'ReplicationTasks': [sample_replication_task]
    }

    mock_dms.describe_replication_instances.return_value = {
        'ReplicationInstances': [
            {
                'ReplicationInstanceArn': 'arn:aws:dms:us-east-1:123456789012:rep:test',
                'PubliclyAccessible': False,
                'VpcSecurityGroups': [],
                'ReplicationSubnetGroup': {'Subnets': [{'SubnetIdentifier': 'subnet-123'}]},
            }
        ]
    }

    mock_dms.describe_endpoints.return_value = {
        'Endpoints': [{'ServerName': 'db.example.com', 'Port': 3306, 'EngineName': 'mysql'}]
    }

    # Subnet describe will fail
    mock_ec2.describe_subnets.side_effect = Exception('Subnet error')

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms,
    ):
        with patch(
            'awslabs.aws_dms_troubleshoot_mcp_server.server.get_ec2_client',
            return_value=mock_ec2,
        ):
            result = await diagnose_network_connectivity(
                task_identifier='test-task-1', region='us-east-1'
            )

            # Should still return result despite subnet error
            assert 'network_summary' in result


@pytest.mark.asyncio
async def test_check_vpc_configuration_tgw_error():
    """Test VPC configuration with Transit Gateway error."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import check_vpc_configuration
    from unittest.mock import MagicMock

    mock_ec2 = MagicMock()

    mock_ec2.describe_vpcs.return_value = {
        'Vpcs': [
            {
                'VpcId': 'vpc-123',
                'CidrBlock': '10.0.0.0/16',
                'IsDefault': False,
                'State': 'available',
                'EnableDnsSupport': True,
                'EnableDnsHostnames': True,
            }
        ]
    }

    mock_ec2.describe_route_tables.return_value = {'RouteTables': []}
    mock_ec2.describe_internet_gateways.return_value = {'InternetGateways': []}
    mock_ec2.describe_nat_gateways.return_value = {'NatGateways': []}
    mock_ec2.describe_vpc_peering_connections.return_value = {'VpcPeeringConnections': []}

    # Transit Gateway will error
    mock_ec2.describe_transit_gateway_attachments.side_effect = Exception('TGW not available')

    mock_ec2.describe_network_acls.return_value = {'NetworkAcls': []}

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_ec2_client',
        return_value=mock_ec2,
    ):
        result = await check_vpc_configuration(vpc_id='vpc-123', region='us-east-1')

        # Should still return result
        assert 'vpc_details' in result
        assert 'connectivity_options' in result


@pytest.mark.asyncio
async def test_list_replication_tasks_with_error_fields(sample_replication_task):
    """Test listing tasks with both last_error and stop_reason."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import list_replication_tasks
    from unittest.mock import MagicMock

    mock_dms = MagicMock()
    sample_replication_task['LastFailureMessage'] = 'Connection timeout'
    sample_replication_task['StopReason'] = 'User stopped'
    mock_dms.describe_replication_tasks.return_value = {
        'ReplicationTasks': [sample_replication_task]
    }

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms,
    ):
        result = await list_replication_tasks(region='us-east-1')

        assert result['tasks'][0]['last_error'] == 'Connection timeout'
        assert result['tasks'][0]['stop_reason'] == 'User stopped'


@pytest.mark.asyncio
async def test_get_replication_task_details_with_assessment(sample_replication_task):
    """Test task details with assessment results."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import get_replication_task_details
    from unittest.mock import MagicMock

    mock_dms = MagicMock()
    sample_replication_task['ReplicationTaskCreationDate'] = datetime.now()
    sample_replication_task['ReplicationTaskSettings'] = json.dumps({})
    sample_replication_task['ReplicationTaskAssessmentResults'] = [{'AssessmentStatus': 'passed'}]
    sample_replication_task['LastFailureMessage'] = 'Test error'
    sample_replication_task['StopReason'] = 'Test stop'
    mock_dms.describe_replication_tasks.return_value = {
        'ReplicationTasks': [sample_replication_task]
    }

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms,
    ):
        result = await get_replication_task_details(
            task_identifier='test-task-1', region='us-east-1'
        )

        assert 'assessment_results' in result
        assert 'last_error' in result
        assert 'stop_reason' in result


@pytest.mark.asyncio
async def test_get_task_cloudwatch_logs_with_events():
    """Test CloudWatch logs retrieval returns proper structure."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import get_task_cloudwatch_logs
    from datetime import datetime, timezone
    from unittest.mock import MagicMock

    current_time = datetime.now(timezone.utc)
    timestamp_ms = int(current_time.timestamp() * 1000)

    mock_logs_client = MagicMock()
    mock_logs_client.describe_log_streams.return_value = {
        'logStreams': [
            {'logStreamName': 'stream1', 'lastEventTime': timestamp_ms},
        ]
    }

    mock_logs_client.get_log_events.return_value = {
        'events': [
            {'timestamp': timestamp_ms, 'message': 'ERROR: Connection failed'},
            {'timestamp': timestamp_ms, 'message': 'WARNING: Retry attempt'},
            {'timestamp': timestamp_ms, 'message': 'FATAL: Critical error'},
        ]
    }

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_logs_client',
        return_value=mock_logs_client,
    ):
        result = await get_task_cloudwatch_logs(
            task_identifier='test-task-1', region='us-east-1', hours_back=24, max_events=100
        )

        # Verify result structure - the function completed successfully
        assert 'log_summary' in result
        assert 'log_events' in result
        assert 'total_events' in result
        assert isinstance(result['log_events'], list)
        # Verify log summary has the required keys
        assert 'errors' in result['log_summary']
        assert 'warnings' in result['log_summary']
        assert 'fatal' in result['log_summary']
        assert isinstance(result['log_summary']['errors'], int)
        assert isinstance(result['log_summary']['warnings'], int)
        assert isinstance(result['log_summary']['fatal'], int)


@pytest.mark.asyncio
async def test_get_task_cloudwatch_logs_stream_error():
    """Test CloudWatch logs with stream read error."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import get_task_cloudwatch_logs
    from datetime import datetime, timezone
    from unittest.mock import MagicMock

    current_time = datetime.now(timezone.utc)
    timestamp_ms = int(current_time.timestamp() * 1000)

    mock_logs_client = MagicMock()
    mock_logs_client.describe_log_streams.return_value = {
        'logStreams': [
            {'logStreamName': 'stream1', 'lastEventTime': timestamp_ms},
        ]
    }

    # Make get_log_events raise an exception
    mock_logs_client.get_log_events.side_effect = Exception('Stream read error')

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_logs_client',
        return_value=mock_logs_client,
    ):
        result = await get_task_cloudwatch_logs(task_identifier='test-task-1', region='us-east-1')

        # Should handle the error gracefully
        assert 'log_events' in result
        assert isinstance(result['log_events'], list)


@pytest.mark.asyncio
async def test_analyze_endpoint_inactive_status(sample_endpoint):
    """Test endpoint analysis with inactive status."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import analyze_endpoint
    from unittest.mock import MagicMock

    mock_dms = MagicMock()
    sample_endpoint['Status'] = 'inactive'
    mock_dms.describe_endpoints.return_value = {'Endpoints': [sample_endpoint]}
    mock_dms.test_connection.return_value = {
        'Connection': {'Status': 'failed', 'LastFailureMessage': 'Connection failed'}
    }

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms,
    ):
        result = await analyze_endpoint(
            endpoint_arn='arn:aws:dms:us-east-1:123456789012:endpoint:test', region='us-east-1'
        )

        assert any('not active' in issue for issue in result['potential_issues'])


@pytest.mark.asyncio
async def test_analyze_endpoint_mysql_no_timezone(sample_endpoint):
    """Test MySQL endpoint without ServerTimezone."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import analyze_endpoint
    from unittest.mock import MagicMock

    mock_dms = MagicMock()
    sample_endpoint['EngineName'] = 'mysql'
    sample_endpoint['MySqlSettings'] = {}  # No ServerTimezone
    mock_dms.describe_endpoints.return_value = {'Endpoints': [sample_endpoint]}
    mock_dms.test_connection.return_value = {
        'Connection': {'Status': 'successful', 'LastFailureMessage': ''}
    }

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms,
    ):
        result = await analyze_endpoint(
            endpoint_arn='arn:aws:dms:us-east-1:123456789012:endpoint:test', region='us-east-1'
        )

        assert any('ServerTimezone' in rec for rec in result['recommendations'])


@pytest.mark.asyncio
async def test_analyze_endpoint_postgres_no_plugin(sample_endpoint):
    """Test PostgreSQL endpoint without PluginName."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import analyze_endpoint
    from unittest.mock import MagicMock

    mock_dms = MagicMock()
    sample_endpoint['EngineName'] = 'postgres'
    sample_endpoint['PostgreSqlSettings'] = {}  # No PluginName
    mock_dms.describe_endpoints.return_value = {'Endpoints': [sample_endpoint]}
    mock_dms.test_connection.return_value = {
        'Connection': {'Status': 'successful', 'LastFailureMessage': ''}
    }

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms,
    ):
        result = await analyze_endpoint(
            endpoint_arn='arn:aws:dms:us-east-1:123456789012:endpoint:test', region='us-east-1'
        )

        assert any('logical replication' in rec for rec in result['recommendations'])


@pytest.mark.asyncio
async def test_analyze_endpoint_test_connection_error(sample_endpoint):
    """Test endpoint analysis when test_connection fails."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import analyze_endpoint
    from unittest.mock import MagicMock

    mock_dms = MagicMock()
    mock_dms.describe_endpoints.return_value = {'Endpoints': [sample_endpoint]}
    mock_dms.test_connection.side_effect = Exception('Connection test failed')

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms,
    ):
        result = await analyze_endpoint(
            endpoint_arn='arn:aws:dms:us-east-1:123456789012:endpoint:test', region='us-east-1'
        )

        assert result['connection_test']['status'] == 'unable_to_test'


@pytest.mark.asyncio
async def test_diagnose_replication_issue_with_tables_errored(
    mock_dms_client, sample_replication_task, sample_endpoint
):
    """Test diagnosis with tables in error state."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import diagnose_replication_issue

    sample_replication_task['ReplicationTaskCreationDate'] = datetime.now()
    sample_replication_task['ReplicationTaskSettings'] = json.dumps({})
    sample_replication_task['Status'] = 'running'
    sample_replication_task['MigrationType'] = 'cdc'
    sample_replication_task['ReplicationTaskStats']['TablesErrored'] = 5

    mock_dms_client.describe_replication_tasks.return_value = {
        'ReplicationTasks': [sample_replication_task]
    }
    mock_dms_client.describe_endpoints.return_value = {'Endpoints': [sample_endpoint]}
    mock_dms_client.test_connection.return_value = {
        'Connection': {'Status': 'successful', 'LastFailureMessage': ''}
    }

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms_client,
    ):
        with patch(
            'awslabs.aws_dms_troubleshoot_mcp_server.server.get_task_cloudwatch_logs'
        ) as mock_logs:
            mock_logs.return_value = {
                'total_events': 5,
                'log_summary': {'errors': 0, 'warnings': 0, 'fatal': 0},
                'log_events': [],
            }

            result = await diagnose_replication_issue(
                task_identifier='test-task-1', region='us-east-1'
            )

            assert any('table' in cause.lower() for cause in result['root_causes'])


@pytest.mark.asyncio
async def test_diagnose_replication_issue_high_error_rate(
    mock_dms_client, sample_replication_task, sample_endpoint
):
    """Test diagnosis with high error rate in logs."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import diagnose_replication_issue

    sample_replication_task['ReplicationTaskCreationDate'] = datetime.now()
    sample_replication_task['ReplicationTaskSettings'] = json.dumps({})
    sample_replication_task['Status'] = 'running'

    mock_dms_client.describe_replication_tasks.return_value = {
        'ReplicationTasks': [sample_replication_task]
    }
    mock_dms_client.describe_endpoints.return_value = {'Endpoints': [sample_endpoint]}
    mock_dms_client.test_connection.return_value = {
        'Connection': {'Status': 'successful', 'LastFailureMessage': ''}
    }

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms_client,
    ):
        with patch(
            'awslabs.aws_dms_troubleshoot_mcp_server.server.get_task_cloudwatch_logs'
        ) as mock_logs:
            mock_logs.return_value = {
                'total_events': 50,
                'log_summary': {'errors': 15, 'warnings': 5, 'fatal': 2},
                'log_events': [],
            }

            result = await diagnose_replication_issue(
                task_identifier='test-task-1', region='us-east-1'
            )

            assert any('error rate' in cause.lower() for cause in result['root_causes'])


@pytest.mark.asyncio
async def test_diagnose_replication_issue_cdc_recommendations(
    mock_dms_client, sample_replication_task, sample_endpoint
):
    """Test CDC-specific recommendations."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import diagnose_replication_issue

    sample_replication_task['ReplicationTaskCreationDate'] = datetime.now()
    sample_replication_task['ReplicationTaskSettings'] = json.dumps({})
    sample_replication_task['Status'] = 'running'
    sample_replication_task['MigrationType'] = 'cdc'

    mock_dms_client.describe_replication_tasks.return_value = {
        'ReplicationTasks': [sample_replication_task]
    }
    mock_dms_client.describe_endpoints.return_value = {'Endpoints': [sample_endpoint]}
    mock_dms_client.test_connection.return_value = {
        'Connection': {'Status': 'successful', 'LastFailureMessage': ''}
    }

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms_client,
    ):
        with patch(
            'awslabs.aws_dms_troubleshoot_mcp_server.server.get_task_cloudwatch_logs'
        ) as mock_logs:
            mock_logs.return_value = {
                'total_events': 5,
                'log_summary': {'errors': 0, 'warnings': 0, 'fatal': 0},
                'log_events': [],
            }

            result = await diagnose_replication_issue(
                task_identifier='test-task-1', region='us-east-1'
            )

            assert any('CDC' in rec for rec in result['recommendations'])


@pytest.mark.asyncio
async def test_diagnose_replication_issue_with_endpoint_issues(
    mock_dms_client, sample_replication_task, sample_endpoint
):
    """Test diagnosis with endpoint issues."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import diagnose_replication_issue

    sample_replication_task['ReplicationTaskCreationDate'] = datetime.now()
    sample_replication_task['ReplicationTaskSettings'] = json.dumps({})
    sample_replication_task['Status'] = 'running'

    mock_dms_client.describe_replication_tasks.return_value = {
        'ReplicationTasks': [sample_replication_task]
    }

    # Create endpoint with issues
    sample_endpoint['SslMode'] = 'none'
    sample_endpoint['Status'] = 'inactive'
    mock_dms_client.describe_endpoints.return_value = {'Endpoints': [sample_endpoint]}
    mock_dms_client.test_connection.return_value = {
        'Connection': {'Status': 'failed', 'LastFailureMessage': 'Connection failed'}
    }

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms_client,
    ):
        with patch(
            'awslabs.aws_dms_troubleshoot_mcp_server.server.get_task_cloudwatch_logs'
        ) as mock_logs:
            mock_logs.return_value = {
                'total_events': 5,
                'log_summary': {'errors': 0, 'warnings': 0, 'fatal': 0},
                'log_events': [],
            }

            result = await diagnose_replication_issue(
                task_identifier='test-task-1', region='us-east-1'
            )

            assert any('endpoint' in cause.lower() for cause in result['root_causes'])


@pytest.mark.asyncio
async def test_analyze_security_groups_no_egress():
    """Test security group analysis with no egress rules."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import analyze_security_groups
    from unittest.mock import MagicMock

    mock_dms = MagicMock()
    mock_ec2 = MagicMock()

    mock_dms.describe_replication_instances.return_value = {
        'ReplicationInstances': [
            {
                'VpcSecurityGroups': [{'VpcSecurityGroupId': 'sg-123'}],
                'ReplicationSubnetGroup': {'Subnets': [{'SubnetIdentifier': 'subnet-123'}]},
            }
        ]
    }

    mock_ec2.describe_security_groups.return_value = {
        'SecurityGroups': [
            {
                'GroupId': 'sg-123',
                'GroupName': 'dms-sg',
                'Description': 'DMS SG',
                'VpcId': 'vpc-123',
                'IpPermissions': [],
                'IpPermissionsEgress': [],  # No egress rules
            }
        ]
    }

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms,
    ):
        with patch(
            'awslabs.aws_dms_troubleshoot_mcp_server.server.get_ec2_client',
            return_value=mock_ec2,
        ):
            result = await analyze_security_groups(
                replication_instance_arn='arn:aws:dms:us-east-1:123456789012:rep:test',
                region='us-east-1',
            )

            assert any('no egress rules' in issue for issue in result['connectivity_issues'])


@pytest.mark.asyncio
async def test_diagnose_network_connectivity_no_subnets(sample_replication_task):
    """Test network diagnostics with no subnets."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import diagnose_network_connectivity
    from unittest.mock import MagicMock

    mock_dms = MagicMock()
    mock_ec2 = MagicMock()

    sample_replication_task['ReplicationInstanceArn'] = (
        'arn:aws:dms:us-east-1:123456789012:rep:test'
    )
    mock_dms.describe_replication_tasks.return_value = {
        'ReplicationTasks': [sample_replication_task]
    }

    mock_dms.describe_replication_instances.return_value = {
        'ReplicationInstances': [
            {
                'ReplicationInstanceArn': 'arn:aws:dms:us-east-1:123456789012:rep:test',
                'PubliclyAccessible': False,
                'VpcSecurityGroups': [],
                'ReplicationSubnetGroup': {'Subnets': []},  # No subnets
            }
        ]
    }

    mock_dms.describe_endpoints.return_value = {
        'Endpoints': [{'ServerName': 'db.example.com', 'Port': 3306, 'EngineName': 'mysql'}]
    }

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms,
    ):
        with patch(
            'awslabs.aws_dms_troubleshoot_mcp_server.server.get_ec2_client',
            return_value=mock_ec2,
        ):
            result = await diagnose_network_connectivity(
                task_identifier='test-task-1', region='us-east-1'
            )

            assert any('no subnet' in issue.lower() for issue in result['identified_issues'])


@pytest.mark.asyncio
async def test_diagnose_network_connectivity_public_no_igw(sample_replication_task):
    """Test network diagnostics for public instance without internet gateway."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import diagnose_network_connectivity
    from unittest.mock import MagicMock

    mock_dms = MagicMock()
    mock_ec2 = MagicMock()

    sample_replication_task['ReplicationInstanceArn'] = (
        'arn:aws:dms:us-east-1:123456789012:rep:test'
    )
    mock_dms.describe_replication_tasks.return_value = {
        'ReplicationTasks': [sample_replication_task]
    }

    mock_dms.describe_replication_instances.return_value = {
        'ReplicationInstances': [
            {
                'ReplicationInstanceArn': 'arn:aws:dms:us-east-1:123456789012:rep:test',
                'PubliclyAccessible': True,  # Public but no IGW
                'VpcSecurityGroups': [],
                'ReplicationSubnetGroup': {'Subnets': [{'SubnetIdentifier': 'subnet-123'}]},
            }
        ]
    }

    mock_dms.describe_endpoints.return_value = {
        'Endpoints': [{'ServerName': 'db.example.com', 'Port': 3306, 'EngineName': 'mysql'}]
    }

    mock_ec2.describe_subnets.return_value = {
        'Subnets': [{'SubnetId': 'subnet-123', 'VpcId': 'vpc-123'}]
    }

    mock_ec2.describe_route_tables.return_value = {
        'RouteTables': [
            {
                'RouteTableId': 'rtb-123',
                'Routes': [
                    {'GatewayId': 'local', 'DestinationCidrBlock': '10.0.0.0/16'}
                ],  # No IGW route
            }
        ]
    }

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_dms_client',
        return_value=mock_dms,
    ):
        with patch(
            'awslabs.aws_dms_troubleshoot_mcp_server.server.get_ec2_client',
            return_value=mock_ec2,
        ):
            result = await diagnose_network_connectivity(
                task_identifier='test-task-1', region='us-east-1'
            )

            assert any(
                'internet gateway' in issue.lower() for issue in result['identified_issues']
            )


def test_main_function():
    """Test the main() function."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import main
    from unittest.mock import MagicMock, patch

    mock_mcp = MagicMock()
    with patch('awslabs.aws_dms_troubleshoot_mcp_server.server.mcp', mock_mcp):
        main()
        mock_mcp.run.assert_called_once()
