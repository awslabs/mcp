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

"""Tests for the Prometheus MCP Server."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_execute_query():
    """Test the execute_query function."""
    with (
        patch('awslabs.prometheus_mcp_server.server.make_prometheus_request') as mock_request,
        patch('awslabs.prometheus_mcp_server.server.config') as mock_config,
        patch('awslabs.prometheus_mcp_server.server.configure_workspace_for_request') as mock_configure,
    ):
        from awslabs.prometheus_mcp_server.server import execute_query

        # Setup
        mock_request.return_value = {'result': 'test_data'}
        mock_config.max_retries = 3
        ctx = AsyncMock()
        workspace_id = 'ws-12345678-abcd-1234-efgh-123456789012'

        # Execute
        result = await execute_query(ctx, workspace_id, 'up')

        # Assert
        # Don't check the exact arguments since the Field object is passed
        assert mock_configure.call_count == 1
        assert mock_configure.call_args[0][0] == ctx
        assert mock_configure.call_args[0][1] == workspace_id
        assert mock_request.call_args[0][0] == 'query'
        assert mock_request.call_args[0][1]['query'] == 'up'
        assert mock_request.call_args[0][2] == 3
        assert result == {'result': 'test_data'}


@pytest.mark.asyncio
async def test_execute_range_query():
    """Test the execute_range_query function."""
    with (
        patch('awslabs.prometheus_mcp_server.server.make_prometheus_request') as mock_request,
        patch('awslabs.prometheus_mcp_server.server.config') as mock_config,
        patch('awslabs.prometheus_mcp_server.server.configure_workspace_for_request') as mock_configure,
    ):
        from awslabs.prometheus_mcp_server.server import execute_range_query

        # Setup
        mock_request.return_value = {'result': 'test_range_data'}
        mock_config.max_retries = 3
        ctx = AsyncMock()
        workspace_id = 'ws-12345678-abcd-1234-efgh-123456789012'

        # Execute
        result = await execute_range_query(
            ctx,
            workspace_id,
            'rate(node_cpu_seconds_total[5m])',
            '2023-01-01T00:00:00Z',
            '2023-01-01T01:00:00Z',
            '5m',
        )

        # Assert
        # Don't check the exact arguments since the Field object is passed
        assert mock_configure.call_count == 1
        assert mock_configure.call_args[0][0] == ctx
        assert mock_configure.call_args[0][1] == workspace_id
        mock_request.assert_called_once_with(
            'query_range',
            {
                'query': 'rate(node_cpu_seconds_total[5m])',
                'start': '2023-01-01T00:00:00Z',
                'end': '2023-01-01T01:00:00Z',
                'step': '5m',
            },
            3,
        )
        assert result == {'result': 'test_range_data'}


@pytest.mark.asyncio
async def test_list_metrics():
    """Test the list_metrics function."""
    with (
        patch('awslabs.prometheus_mcp_server.server.make_prometheus_request') as mock_request,
        patch('awslabs.prometheus_mcp_server.server.config') as mock_config,
        patch('awslabs.prometheus_mcp_server.server.configure_workspace_for_request') as mock_configure,
    ):
        from awslabs.prometheus_mcp_server.models import MetricsList
        from awslabs.prometheus_mcp_server.server import list_metrics

        # Setup
        mock_request.return_value = ['metric1', 'metric2', 'metric3']
        mock_config.max_retries = 3
        ctx = AsyncMock()
        workspace_id = 'ws-12345678-abcd-1234-efgh-123456789012'

        # Execute
        result = await list_metrics(ctx, workspace_id)

        # Assert
        # Don't check the exact arguments since the Field object is passed
        assert mock_configure.call_count == 1
        assert mock_configure.call_args[0][0] == ctx
        assert mock_configure.call_args[0][1] == workspace_id
        mock_request.assert_called_once_with('label/__name__/values', params={}, max_retries=3)
        assert isinstance(result, MetricsList)
        assert result.metrics == ['metric1', 'metric2', 'metric3']


@pytest.mark.asyncio
async def test_get_server_info():
    """Test the get_server_info function."""
    with (
        patch('awslabs.prometheus_mcp_server.server.config') as mock_config,
        patch('awslabs.prometheus_mcp_server.server.configure_workspace_for_request') as mock_configure,
    ):
        from awslabs.prometheus_mcp_server.models import ServerInfo
        from awslabs.prometheus_mcp_server.server import get_server_info

        # Setup
        mock_config.prometheus_url = 'https://test-prometheus.amazonaws.com'
        mock_config.aws_region = 'us-east-1'
        mock_config.aws_profile = 'test-profile'
        mock_config.service_name = 'aps'
        ctx = AsyncMock()
        workspace_id = 'ws-12345678-abcd-1234-efgh-123456789012'

        # Execute
        result = await get_server_info(ctx, workspace_id)

        # Assert
        # Don't check the exact arguments since the Field object is passed
        assert mock_configure.call_count == 1
        assert mock_configure.call_args[0][0] == ctx
        assert mock_configure.call_args[0][1] == workspace_id
        assert isinstance(result, ServerInfo)
        assert result.prometheus_url == 'https://test-prometheus.amazonaws.com'
        assert result.aws_region == 'us-east-1'
        assert result.aws_profile == 'test-profile'
        assert result.service_name == 'aps'


@pytest.mark.asyncio
async def test_get_available_workspaces():
    """Test the get_available_workspaces function."""
    with (
        patch('awslabs.prometheus_mcp_server.server.boto3.Session') as mock_session,
        patch('awslabs.prometheus_mcp_server.server.config') as mock_config,
    ):
        from awslabs.prometheus_mcp_server.server import get_available_workspaces

        # Setup
        mock_config.aws_region = 'us-east-1'
        mock_config.aws_profile = 'test-profile'
        
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        
        # Use a MagicMock for createdAt to avoid the isoformat issue
        created_at = MagicMock()
        created_at.isoformat.return_value = '2023-01-01T00:00:00Z'
        
        mock_client.list_workspaces.return_value = {
            'workspaces': [
                {
                    'workspaceId': 'ws-12345',
                    'alias': 'Test Workspace',
                    'status': {'statusCode': 'ACTIVE'},
                    'createdAt': created_at,
                }
            ]
        }
        
        ctx = AsyncMock()

        # Execute
        result = await get_available_workspaces(ctx)

        # Assert
        mock_session.assert_called_once_with(region_name='us-east-1')
        mock_session.return_value.client.assert_called_once_with('amp')
        mock_client.list_workspaces.assert_called_once()
        
        assert result['count'] == 1
        assert result['region'] == 'us-east-1'
        assert len(result['workspaces']) == 1
        assert result['workspaces'][0]['workspace_id'] == 'ws-12345'
        assert result['workspaces'][0]['alias'] == 'Test Workspace'
        assert result['workspaces'][0]['status'] == 'ACTIVE'


@pytest.mark.asyncio
async def test_configure_workspace_for_request():
    """Test the configure_workspace_for_request function."""
    with (
        patch('awslabs.prometheus_mcp_server.server.config') as mock_config,
        patch('awslabs.prometheus_mcp_server.server.test_prometheus_connection') as mock_test_conn,
    ):
        from awslabs.prometheus_mcp_server.server import configure_workspace_for_request

        # Setup
        mock_test_conn.return_value = True
        ctx = AsyncMock()
        workspace_id = 'ws-12345678-abcd-1234-efgh-123456789012'
        region = 'us-west-2'

        # Execute
        await configure_workspace_for_request(ctx, workspace_id, region)

        # Assert
        assert mock_config.prometheus_url == f'https://aps-workspaces.{region}.amazonaws.com/workspaces/{workspace_id}'
        assert mock_config.aws_region == region
        mock_test_conn.assert_called_once()