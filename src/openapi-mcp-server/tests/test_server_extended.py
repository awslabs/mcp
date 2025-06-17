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
"""Extended tests for the server module."""

import pytest
from awslabs.openapi_mcp_server.api.config import Config
from awslabs.openapi_mcp_server.server import create_mcp_server, setup_signal_handlers
from unittest.mock import MagicMock, call, patch


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    config = MagicMock(spec=Config)
    config.api_name = 'test-api'
    config.api_spec_url = 'https://example.com/openapi.json'
    config.api_spec_path = None
    config.api_base_url = 'https://example.com/api'
    config.auth_type = 'none'
    config.auth_username = None
    config.auth_password = None
    config.auth_token = None
    config.auth_api_key = None
    config.auth_api_key_name = 'api_key'
    config.auth_api_key_in = 'header'
    config.version = '1.0.0'
    config.transport = 'stdio'
    config.port = 8000
    return config


@patch('awslabs.openapi_mcp_server.server.FastMCPOpenAPI')
@patch('awslabs.openapi_mcp_server.server.load_openapi_spec')
@patch('awslabs.openapi_mcp_server.server.validate_openapi_spec', return_value=True)
@patch('awslabs.openapi_mcp_server.server.HttpClientFactory.create_client')
def test_create_mcp_server_with_query_params_routes(
    mock_create_client,
    mock_validate,
    mock_load_spec,
    mock_fastmcp_openapi,
    mock_config,
):
    """Test creating an MCP server with routes that have query parameters."""
    # Setup mocks
    mock_server = MagicMock()
    mock_fastmcp_openapi.return_value = mock_server

    # Create a mock OpenAPI spec with GET routes that have query parameters
    mock_load_spec.return_value = {
        'openapi': '3.0.0',
        'info': {'title': 'Test API', 'version': '1.0.0'},
        'paths': {
            '/pets': {
                'get': {
                    'operationId': 'listPets',
                    'parameters': [
                        {
                            'name': 'limit',
                            'in': 'query',
                            'description': 'How many items to return',
                            'schema': {'type': 'integer'},
                        },
                        {
                            'name': 'status',
                            'in': 'query',
                            'description': 'Status values to filter by',
                            'schema': {'type': 'string'},
                        },
                    ],
                }
            },
            '/users': {
                'get': {
                    'operationId': 'listUsers',
                    'parameters': [],  # No query parameters
                }
            },
        },
    }

    mock_client = MagicMock()
    mock_create_client.return_value = mock_client

    # Call the function
    result = create_mcp_server(mock_config)

    # Verify the result
    assert result == mock_server

    # Verify that FastMCPOpenAPI was called with custom route mappings
    # The first call args are the positional arguments
    call_args = mock_fastmcp_openapi.call_args[1]

    # Check that route_maps was included in the kwargs
    assert 'route_maps' in call_args


@patch('awslabs.openapi_mcp_server.server.FastMCPOpenAPI')
@patch('awslabs.openapi_mcp_server.server.load_openapi_spec')
@patch('awslabs.openapi_mcp_server.server.validate_openapi_spec', return_value=True)
@patch('awslabs.openapi_mcp_server.server.HttpClientFactory.create_client')
@patch('awslabs.openapi_mcp_server.server.asyncio.run')
def test_create_mcp_server_with_prompt_generation(
    mock_asyncio_run,
    mock_create_client,
    mock_validate,
    mock_load_spec,
    mock_fastmcp_openapi,
    mock_config,
):
    """Test creating an MCP server with prompt generation."""
    # Setup mocks
    mock_server = MagicMock()
    mock_server._prompt_manager = MagicMock()
    mock_server._prompt_manager._prompts = {
        'api_overview': 'API Overview Prompt',
        'operation_listPets': 'List Pets Operation Prompt',
        'mapping_reference': 'Mapping Reference Prompt',
    }
    mock_fastmcp_openapi.return_value = mock_server

    mock_load_spec.return_value = {
        'openapi': '3.0.0',
        'info': {'title': 'Test API', 'version': '1.0.0'},
        'paths': {'/pets': {'get': {'operationId': 'listPets', 'summary': 'List all pets'}}},
    }

    mock_client = MagicMock()
    mock_create_client.return_value = mock_client

    # Call the function
    result = create_mcp_server(mock_config)

    # Verify the result
    assert result == mock_server

    # Verify that asyncio.run was called
    mock_asyncio_run.assert_called()


@patch('awslabs.openapi_mcp_server.server.signal')
@patch('awslabs.openapi_mcp_server.server.logger')
@patch('awslabs.openapi_mcp_server.server.metrics')
@patch('awslabs.openapi_mcp_server.server.sys.exit')
def test_setup_signal_handlers(mock_exit, mock_metrics, mock_logger, mock_signal):
    """Test setting up signal handlers."""
    # Setup mocks
    mock_metrics.get_summary.return_value = {'api_calls': 10, 'errors': 2}
    mock_original_handler = MagicMock()
    mock_signal.getsignal.return_value = mock_original_handler

    # Call the function
    setup_signal_handlers()

    # Verify that signal handlers were registered
    mock_signal.getsignal.assert_called_once_with(mock_signal.SIGINT)
    mock_signal.signal.assert_has_calls(
        [
            call(mock_signal.SIGTERM, mock_signal.signal.call_args[0][1]),
            call(mock_signal.SIGINT, mock_signal.signal.call_args[0][1]),
        ]
    )

    # Get the signal handler function
    signal_handler = mock_signal.signal.call_args[0][1]

    # Call the signal handler with SIGTERM
    signal_handler(mock_signal.SIGTERM, None)

    # Verify that metrics were logged
    mock_metrics.get_summary.assert_called_once()
    mock_logger.info.assert_any_call("Final metrics: {'api_calls': 10, 'errors': 2}")

    # Reset mocks
    mock_metrics.reset_mock()
    mock_logger.reset_mock()

    # Call the signal handler with SIGINT
    signal_handler(mock_signal.SIGINT, None)

    # Verify that metrics were logged
    mock_metrics.get_summary.assert_called_once()
    mock_logger.info.assert_any_call('Process Interrupted, Shutting down gracefully...')
    mock_exit.assert_called_once_with(0)
