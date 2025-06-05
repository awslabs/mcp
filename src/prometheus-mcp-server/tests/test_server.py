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
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_execute_query():
    """Test the execute_query function."""
    with (
        patch('awslabs.prometheus_mcp_server.server.make_prometheus_request') as mock_request,
        patch('awslabs.prometheus_mcp_server.server.config') as mock_config,
    ):
        from awslabs.prometheus_mcp_server.server import execute_query

        # Setup
        mock_request.return_value = {'result': 'test_data'}
        mock_config.max_retries = 3
        ctx = AsyncMock()

        # Execute
        result = await execute_query(ctx, 'up')

        # Assert
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
    ):
        from awslabs.prometheus_mcp_server.server import execute_range_query

        # Setup
        mock_request.return_value = {'result': 'test_range_data'}
        mock_config.max_retries = 3
        ctx = AsyncMock()

        # Execute
        result = await execute_range_query(
            ctx,
            'rate(node_cpu_seconds_total[5m])',
            '2023-01-01T00:00:00Z',
            '2023-01-01T01:00:00Z',
            '5m',
        )

        # Assert
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
    ):
        from awslabs.prometheus_mcp_server.models import MetricsList
        from awslabs.prometheus_mcp_server.server import list_metrics

        # Setup
        mock_request.return_value = ['metric1', 'metric2', 'metric3']
        mock_config.max_retries = 3
        ctx = AsyncMock()

        # Execute
        result = await list_metrics(ctx)

        # Assert
        mock_request.assert_called_once_with('label/__name__/values', max_retries=3)
        assert isinstance(result, MetricsList)
        assert result.metrics == ['metric1', 'metric2', 'metric3']


@pytest.mark.asyncio
async def test_get_server_info():
    """Test the get_server_info function."""
    with patch('awslabs.prometheus_mcp_server.server.config') as mock_config:
        from awslabs.prometheus_mcp_server.models import ServerInfo
        from awslabs.prometheus_mcp_server.server import get_server_info

        # Setup
        mock_config.prometheus_url = 'https://test-prometheus.amazonaws.com'
        mock_config.aws_region = 'us-east-1'
        mock_config.aws_profile = 'test-profile'
        mock_config.service_name = 'aps'
        ctx = AsyncMock()

        # Execute
        result = await get_server_info(ctx)

        # Assert
        assert isinstance(result, ServerInfo)
        assert result.prometheus_url == 'https://test-prometheus.amazonaws.com'
        assert result.aws_region == 'us-east-1'
        assert result.aws_profile == 'test-profile'
        assert result.service_name == 'aps'
