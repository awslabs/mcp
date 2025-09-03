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

"""Tests for the server module."""

import pytest
from awslabs.aws_appsync_mcp_server.decorators import is_write_allowed, set_write_allowed
from awslabs.aws_appsync_mcp_server.server import main
from unittest.mock import MagicMock, patch


def test_main_with_allow_write():
    """Test main function with --allow-write flag."""
    with (
        patch('sys.argv', ['server.py', '--allow-write']),
        patch('awslabs.aws_appsync_mcp_server.server.mcp') as mock_mcp,
        patch('awslabs.aws_appsync_mcp_server.server.logger') as mock_logger,
    ):
        mock_mcp.run = MagicMock()

        main()

        assert is_write_allowed() is True
        mock_logger.info.assert_called_once_with(
            'Starting AWS AppSync MCP Server (write operations: enabled).'
        )
        mock_mcp.run.assert_called_once()


def test_main_without_allow_write():
    """Test main function without --allow-write flag."""
    with (
        patch('sys.argv', ['server.py']),
        patch('awslabs.aws_appsync_mcp_server.server.mcp') as mock_mcp,
        patch('awslabs.aws_appsync_mcp_server.server.logger') as mock_logger,
    ):
        mock_mcp.run = MagicMock()

        main()

        assert is_write_allowed() is False
        mock_logger.info.assert_called_once_with(
            'Starting AWS AppSync MCP Server (write operations: disabled).'
        )
        mock_mcp.run.assert_called_once()


def test_main_registers_all_tools():
    """Test that main function registers all expected tools."""
    with (
        patch('sys.argv', ['server.py']),
        patch('awslabs.aws_appsync_mcp_server.server.mcp') as mock_mcp,
        patch('awslabs.aws_appsync_mcp_server.server.register_create_api_tool') as mock_api,
        patch(
            'awslabs.aws_appsync_mcp_server.server.register_create_graphql_api_tool'
        ) as mock_graphql,
        patch('awslabs.aws_appsync_mcp_server.server.register_create_api_key_tool') as mock_key,
        patch(
            'awslabs.aws_appsync_mcp_server.server.register_create_api_cache_tool'
        ) as mock_cache,
        patch('awslabs.aws_appsync_mcp_server.server.register_create_datasource_tool') as mock_ds,
        patch('awslabs.aws_appsync_mcp_server.server.register_create_function_tool') as mock_func,
        patch(
            'awslabs.aws_appsync_mcp_server.server.register_create_channel_namespace_tool'
        ) as mock_channel,
        patch(
            'awslabs.aws_appsync_mcp_server.server.register_create_domain_name_tool'
        ) as mock_domain,
        patch(
            'awslabs.aws_appsync_mcp_server.server.register_create_resolver_tool'
        ) as mock_resolver,
        patch('awslabs.aws_appsync_mcp_server.server.register_create_schema_tool') as mock_schema,
    ):
        mock_mcp.run = MagicMock()

        main()

        # Verify all tools are registered
        mock_api.assert_called_once_with(mock_mcp)
        mock_graphql.assert_called_once_with(mock_mcp)
        mock_key.assert_called_once_with(mock_mcp)
        mock_cache.assert_called_once_with(mock_mcp)
        mock_ds.assert_called_once_with(mock_mcp)
        mock_func.assert_called_once_with(mock_mcp)
        mock_channel.assert_called_once_with(mock_mcp)
        mock_domain.assert_called_once_with(mock_mcp)
        mock_resolver.assert_called_once_with(mock_mcp)
        mock_schema.assert_called_once_with(mock_mcp)


def test_main_with_help_flag():
    """Test main function with --help flag."""
    with patch('sys.argv', ['server.py', '--help']), pytest.raises(SystemExit):
        main()


def teardown_function():
    """Reset write allowed state after each test."""
    set_write_allowed(False)
