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
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest


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

    mock_logs_client.describe_log_streams.return_value = {
        'logStreams': [{'logStreamName': 'stream1', 'lastEventTime': 1234567890}]
    }

    mock_logs_client.get_log_events.return_value = {
        'events': [
            {'timestamp': 1234567890000, 'message': 'Task started'},
            {'timestamp': 1234567891000, 'message': 'ERROR: Connection failed'},
        ]
    }

    with patch(
        'awslabs.aws_dms_troubleshoot_mcp_server.server.get_logs_client',
        return_value=mock_logs_client,
    ):
        result = await get_task_cloudwatch_logs(task_identifier='test-task-1', region='us-east-1')

        assert 'log_events' in result
        assert result['total_events'] == 2
        assert result['log_summary']['errors'] == 1


@pytest.mark.asyncio
async def test_get_task_cloudwatch_logs_not_found(mock_logs_client):
    """Test retrieving logs when log group doesn't exist."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import get_task_cloudwatch_logs

    mock_logs_client.describe_log_streams.side_effect = (
        mock_logs_client.exceptions.ResourceNotFoundException({}, 'ResourceNotFoundException')
    )

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
    assert any('credential' in rec.lower() or 'permission' in rec.lower() for rec in result['recommendations'])


@pytest.mark.asyncio
async def test_get_troubleshooting_recommendations_cdc():
    """Test getting recommendations for CDC issues."""
    from awslabs.aws_dms_troubleshoot_mcp_server.server import (
        get_troubleshooting_recommendations,
    )

    result = await get_troubleshooting_recommendations(error_pattern='binlog error')

    assert 'CDC/Replication Issues' in result['matched_patterns']
    assert any('binlog' in rec.lower() or 'cdc' in rec.lower() for rec in result['recommendations'])


@pytest.mark.asyncio
async def test_diagnose_replication_issue(mock_dms_client, sample_replication_task, sample_endpoint):
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