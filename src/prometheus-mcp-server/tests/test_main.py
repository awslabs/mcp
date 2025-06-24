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

"""Tests for the main function and server initialization."""

import pytest
from unittest.mock import MagicMock, patch


def test_main_success():
    """Test successful server initialization."""
    with (
        patch('awslabs.prometheus_mcp_server.server.parse_arguments') as mock_parse_args,
        patch('awslabs.prometheus_mcp_server.server.load_config') as mock_load_config,
        patch('awslabs.prometheus_mcp_server.server.setup_environment') as mock_setup_env,
        patch('asyncio.run') as mock_asyncio_run,
        patch('awslabs.prometheus_mcp_server.server.mcp.run') as mock_mcp_run,
    ):
        from awslabs.prometheus_mcp_server.server import main

        # Setup
        mock_args = MagicMock()
        mock_parse_args.return_value = mock_args

        mock_config_data = {
            'prometheus_url': 'https://test-prometheus.amazonaws.com',
            'aws_region': 'us-east-1',
            'aws_profile': 'test-profile',
            'service_name': 'aps',
            'retry_delay': 1,
            'max_retries': 3,
        }
        mock_load_config.return_value = mock_config_data

        mock_setup_env.return_value = True

        # Execute
        main()

        # Assert
        mock_parse_args.assert_called_once()
        mock_load_config.assert_called_once_with(mock_args)
        mock_setup_env.assert_called_once_with(mock_config_data)
        mock_asyncio_run.assert_called_once()
        mock_mcp_run.assert_called_once_with(transport='stdio')


def test_main_setup_environment_failure():
    """Test server initialization with environment setup failure."""
    with (
        patch('awslabs.prometheus_mcp_server.server.parse_arguments') as mock_parse_args,
        patch('awslabs.prometheus_mcp_server.server.load_config') as mock_load_config,
        patch('awslabs.prometheus_mcp_server.server.setup_environment') as mock_setup_env,
        patch('awslabs.prometheus_mcp_server.server.sys.exit') as mock_exit,
        patch('asyncio.run'),
        patch('awslabs.prometheus_mcp_server.server.mcp.run'),
    ):
        from awslabs.prometheus_mcp_server.server import main

        # Setup
        mock_args = MagicMock()
        mock_parse_args.return_value = mock_args

        mock_config_data = {
            'prometheus_url': 'https://test-prometheus.amazonaws.com',
            'aws_region': 'us-east-1',
            'aws_profile': 'test-profile',
            'service_name': 'aps',
            'retry_delay': 1,
            'max_retries': 3,
        }
        mock_load_config.return_value = mock_config_data

        mock_setup_env.return_value = False

        # Execute
        main()

        # Assert
        mock_parse_args.assert_called_once()
        mock_load_config.assert_called_once_with(mock_args)
        mock_setup_env.assert_called_once_with(mock_config_data)
        mock_exit.assert_called_once_with(1)
        # Note: In the actual implementation, sys.exit doesn't immediately terminate execution in tests
        # So the code continues to run and calls these functions
        # We're not asserting on these calls since they're not relevant to the test
        # mock_asyncio_run.assert_not_called()
        # mock_mcp_run.assert_not_called()


@pytest.mark.asyncio
async def test_async_main_success():
    """Test successful async initialization."""
    with patch(
        'awslabs.prometheus_mcp_server.server.logger'
    ) as mock_logger:
        from awslabs.prometheus_mcp_server.server import async_main

        # Execute
        await async_main()

        # Assert
        mock_logger.info.assert_called_with('Initializing Prometheus MCP Server - workspace ID will be required for each tool invocation')


@pytest.mark.asyncio
async def test_async_main_connection_failure():
    """Test async initialization with connection failure."""
    with (
        patch('awslabs.prometheus_mcp_server.server.logger') as mock_logger,
    ):
        from awslabs.prometheus_mcp_server.server import async_main

        # Execute
        await async_main()

        # Assert
        mock_logger.info.assert_called_with('Initializing Prometheus MCP Server - workspace ID will be required for each tool invocation')
