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
"""Tests for the OpenAPI MCP Server main function."""

from awslabs.openapi_mcp_server.server import main
from unittest.mock import MagicMock, patch


@patch('awslabs.openapi_mcp_server.server.create_mcp_server')
@patch('awslabs.openapi_mcp_server.server.load_config')
@patch('awslabs.openapi_mcp_server.server.argparse.ArgumentParser.parse_args')
@patch('awslabs.openapi_mcp_server.server.asyncio.run')
def test_main_function(mock_asyncio_run, mock_parse_args, mock_load_config, mock_create_mcp_server):
    """Test the main function."""
    # Setup mocks
    mock_args = MagicMock()
    # Properly set log_level to a string value to avoid TypeError
    mock_args.log_level = 'INFO'
    mock_parse_args.return_value = mock_args

    mock_config = MagicMock()
    mock_config.transport = 'sse'
    mock_config.port = 8888
    mock_load_config.return_value = mock_config

    mock_server = MagicMock()
    mock_create_mcp_server.return_value = mock_server

    # Mock the asyncio.run result
    mock_asyncio_run.return_value = (10, 5, 2, 1)  # prompts, tools, resources, resource_templates

    # Call main
    main()

    # Assert
    mock_parse_args.assert_called_once()
    mock_asyncio_run.assert_called_once()
