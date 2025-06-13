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
"""Extended tests for the OpenAPI MCP Server main function."""

from awslabs.openapi_mcp_server.server import main
from unittest.mock import MagicMock, patch


@patch('awslabs.openapi_mcp_server.server.create_mcp_server')
@patch('awslabs.openapi_mcp_server.server.load_config')
@patch('awslabs.openapi_mcp_server.server.argparse.ArgumentParser.parse_args')
@patch('awslabs.openapi_mcp_server.server.asyncio.run')
@patch('awslabs.openapi_mcp_server.server.setup_signal_handlers')
@patch('awslabs.openapi_mcp_server.server.logger')
def test_main_with_stdio_transport(
    mock_logger,
    mock_setup_signal_handlers,
    mock_asyncio_run,
    mock_parse_args,
    mock_load_config,
    mock_create_mcp_server,
):
    """Test the main function with stdio transport."""
    # Setup mocks
    mock_args = MagicMock()
    mock_args.log_level = 'INFO'
    mock_parse_args.return_value = mock_args

    mock_config = MagicMock()
    mock_config.transport = 'stdio'
    mock_load_config.return_value = mock_config

    mock_server = MagicMock()
    mock_create_mcp_server.return_value = mock_server

    # Mock the asyncio.run result
    mock_asyncio_run.return_value = (5, 10, 3, 2)  # prompts, tools, resources, resource_templates

    # Call main
    main()

    # Assert
    mock_parse_args.assert_called_once()
    mock_load_config.assert_called_once_with(mock_args)
    mock_create_mcp_server.assert_called_once_with(mock_config)
    mock_setup_signal_handlers.assert_called_once()
    mock_server.run.assert_called_once_with()

    # Verify that the counts were logged
    mock_logger.info.assert_any_call(
        'Server components: 5 prompts, 10 tools, 3 resources, 2 resource templates'
    )


@patch('awslabs.openapi_mcp_server.server.create_mcp_server')
@patch('awslabs.openapi_mcp_server.server.load_config')
@patch('awslabs.openapi_mcp_server.server.argparse.ArgumentParser.parse_args')
@patch('awslabs.openapi_mcp_server.server.asyncio.run')
@patch('awslabs.openapi_mcp_server.server.setup_signal_handlers')
@patch('awslabs.openapi_mcp_server.server.logger')
def test_main_with_sse_transport(
    mock_logger,
    mock_setup_signal_handlers,
    mock_asyncio_run,
    mock_parse_args,
    mock_load_config,
    mock_create_mcp_server,
):
    """Test the main function with SSE transport."""
    # Setup mocks
    mock_args = MagicMock()
    mock_args.log_level = 'INFO'
    mock_parse_args.return_value = mock_args

    mock_config = MagicMock()
    mock_config.transport = 'sse'
    mock_config.port = 8000
    mock_load_config.return_value = mock_config

    mock_server = MagicMock()
    mock_create_mcp_server.return_value = mock_server

    # Mock the asyncio.run result
    mock_asyncio_run.return_value = (5, 10, 3, 2)  # prompts, tools, resources, resource_templates

    # Call main
    main()

    # Assert
    mock_parse_args.assert_called_once()
    mock_load_config.assert_called_once_with(mock_args)
    mock_create_mcp_server.assert_called_once_with(mock_config)
    mock_setup_signal_handlers.assert_called_once()

    # Verify that the server was configured with the correct port
    mock_server.settings.port = 8000  # Mock the port attribute
    assert mock_server.settings.port == 8000

    # Verify that the server was run with SSE transport
    mock_server.run.assert_called_once()


@patch('awslabs.openapi_mcp_server.server.create_mcp_server')
@patch('awslabs.openapi_mcp_server.server.load_config')
@patch('awslabs.openapi_mcp_server.server.argparse.ArgumentParser.parse_args')
@patch('awslabs.openapi_mcp_server.server.asyncio.run')
@patch('awslabs.openapi_mcp_server.server.setup_signal_handlers')
@patch('awslabs.openapi_mcp_server.server.logger')
@patch('awslabs.openapi_mcp_server.server.sys.exit')
def test_main_with_no_tools_or_resources(
    mock_exit,
    mock_logger,
    mock_setup_signal_handlers,
    mock_asyncio_run,
    mock_parse_args,
    mock_load_config,
    mock_create_mcp_server,
):
    """Test the main function when no tools or resources are registered."""
    # Setup mocks
    mock_args = MagicMock()
    mock_args.log_level = 'INFO'
    mock_parse_args.return_value = mock_args

    mock_config = MagicMock()
    mock_config.transport = 'stdio'
    mock_load_config.return_value = mock_config

    mock_server = MagicMock()
    mock_create_mcp_server.return_value = mock_server

    # Mock the asyncio.run result - no tools or resources
    mock_asyncio_run.return_value = (5, 0, 0, 0)  # prompts, tools, resources, resource_templates

    # Call main
    main()

    # Assert
    mock_parse_args.assert_called_once()
    mock_load_config.assert_called_once_with(mock_args)
    mock_create_mcp_server.assert_called_once_with(mock_config)
    mock_setup_signal_handlers.assert_called_once()

    # Verify that a warning was logged
    mock_logger.warning.assert_any_call(
        'No tools or resources were registered. This might indicate an issue with the API specification or authentication.'
    )


@patch('awslabs.openapi_mcp_server.server.create_mcp_server')
@patch('awslabs.openapi_mcp_server.server.load_config')
@patch('awslabs.openapi_mcp_server.server.argparse.ArgumentParser.parse_args')
@patch('awslabs.openapi_mcp_server.server.asyncio.run')
@patch('awslabs.openapi_mcp_server.server.setup_signal_handlers')
@patch('awslabs.openapi_mcp_server.server.logger')
@patch('awslabs.openapi_mcp_server.server.sys.exit')
def test_main_with_get_all_counts_error(
    mock_exit,
    mock_logger,
    mock_setup_signal_handlers,
    mock_asyncio_run,
    mock_parse_args,
    mock_load_config,
    mock_create_mcp_server,
):
    """Test the main function when get_all_counts raises an exception."""
    # Setup mocks
    mock_args = MagicMock()
    mock_args.log_level = 'INFO'
    mock_parse_args.return_value = mock_args

    mock_config = MagicMock()
    mock_config.transport = 'stdio'
    mock_load_config.return_value = mock_config

    mock_server = MagicMock()
    mock_create_mcp_server.return_value = mock_server

    # Mock the asyncio.run to raise an exception
    mock_asyncio_run.side_effect = Exception('Error counting tools and resources')

    # Call main
    main()

    # Assert
    mock_parse_args.assert_called_once()
    mock_load_config.assert_called_once_with(mock_args)
    mock_create_mcp_server.assert_called_once_with(mock_config)
    mock_setup_signal_handlers.assert_called_once()

    # Verify that an error was logged
    mock_logger.error.assert_any_call(
        'Error counting tools and resources: Error counting tools and resources'
    )
    mock_logger.error.assert_any_call(
        'Server shutting down due to error in tool/resource registration.'
    )

    # Verify that sys.exit was called
    mock_exit.assert_called_once_with(1)
