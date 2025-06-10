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

"""Tests for error handling in the Prometheus MCP Server."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_execute_query_error_handling():
    """Test error handling in execute_query function."""
    with (
        patch('awslabs.prometheus_mcp_server.server.make_prometheus_request') as mock_request,
        patch('awslabs.prometheus_mcp_server.server.logger') as mock_logger,
    ):
        from awslabs.prometheus_mcp_server.server import execute_query

        # Setup
        mock_request.side_effect = Exception("Test error")
        ctx = AsyncMock()

        # Execute and assert
        with pytest.raises(Exception, match="Test error"):
            await execute_query(ctx, "up")

        # Verify error was logged and reported to context
        mock_logger.error.assert_called_once()
        ctx.error.assert_called_once()


@pytest.mark.asyncio
async def test_execute_range_query_error_handling():
    """Test error handling in execute_range_query function."""
    with (
        patch('awslabs.prometheus_mcp_server.server.make_prometheus_request') as mock_request,
        patch('awslabs.prometheus_mcp_server.server.logger') as mock_logger,
    ):
        from awslabs.prometheus_mcp_server.server import execute_range_query

        # Setup
        mock_request.side_effect = Exception("Test error")
        ctx = AsyncMock()

        # Execute and assert
        with pytest.raises(Exception, match="Test error"):
            await execute_range_query(
                ctx,
                "rate(node_cpu_seconds_total[5m])",
                "2023-01-01T00:00:00Z",
                "2023-01-01T01:00:00Z",
                "5m",
            )

        # Verify error was logged and reported to context
        mock_logger.error.assert_called_once()
        ctx.error.assert_called_once()


@pytest.mark.asyncio
async def test_list_metrics_error_handling():
    """Test error handling in list_metrics function."""
    with (
        patch('awslabs.prometheus_mcp_server.server.make_prometheus_request') as mock_request,
        patch('awslabs.prometheus_mcp_server.server.logger') as mock_logger,
    ):
        from awslabs.prometheus_mcp_server.server import list_metrics

        # Setup
        mock_request.side_effect = Exception("Test error")
        ctx = AsyncMock()

        # Execute and assert
        with pytest.raises(Exception, match="Test error"):
            await list_metrics(ctx)

        # Verify error was logged and reported to context
        mock_logger.error.assert_called_once()
        ctx.error.assert_called_once()


@pytest.mark.asyncio
async def test_get_server_info_error_handling():
    """Test error handling in get_server_info function."""
    with (
        patch('awslabs.prometheus_mcp_server.server.logger'),
        patch('awslabs.prometheus_mcp_server.server.config', None),
    ):
        from awslabs.prometheus_mcp_server.models import ServerInfo
        from awslabs.prometheus_mcp_server.server import get_server_info

        # Setup
        ctx = AsyncMock()

        # Execute
        result = await get_server_info(ctx)

        # Assert
        assert isinstance(result, ServerInfo)
        assert result.prometheus_url == 'Not configured'
        assert result.aws_region == 'Not configured'
        assert result.aws_profile == 'Not configured'
        assert result.service_name == 'Not configured'


@pytest.mark.asyncio
async def test_get_server_info_with_exception():
    """Test error handling in get_server_info function when an exception occurs."""
    with (
        patch('awslabs.prometheus_mcp_server.server.logger') as mock_logger,
        patch('awslabs.prometheus_mcp_server.server.config') as mock_config,
    ):
        from awslabs.prometheus_mcp_server.server import get_server_info

        # Setup
        ctx = AsyncMock()

        # Configure the mock to raise an exception when prometheus_url is accessed
        mock_config.__bool__.return_value = True  # Make sure 'if not config' evaluates to False
        mock_config.prometheus_url = MagicMock(side_effect=Exception("Test error"))

        # Execute and assert
        with pytest.raises(Exception):
            await get_server_info(ctx)

        # Verify error was logged and reported to context
        mock_logger.error.assert_called_once()
        ctx.error.assert_called_once()
