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
from awslabs.openapi_mcp_server.api.config import Config
from awslabs.openapi_mcp_server.server import create_mcp_server
from unittest.mock import MagicMock, patch


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
@patch('awslabs.openapi_mcp_server.server.FastMCP')
@patch('awslabs.openapi_mcp_server.server.load_openapi_spec')
@patch('awslabs.openapi_mcp_server.server.validate_openapi_spec', return_value=True)
@patch('awslabs.openapi_mcp_server.server.HttpClientFactory.create_client')
def test_create_mcp_server_basic(
    mock_create_client,
    mock_validate,
    mock_load_spec,
    mock_fastmcp,
    mock_fastmcp_openapi,
    mock_config,
):
    """Test creating an MCP server with basic configuration."""
    # Setup mocks
    mock_server = MagicMock()
    mock_fastmcp.return_value = MagicMock()
    mock_fastmcp_openapi.return_value = mock_server
    mock_load_spec.return_value = {
        'openapi': '3.0.0',
        'info': {'title': 'Test API', 'version': '1.0.0'},
        'paths': {},
    }
    mock_client = MagicMock()
    mock_create_client.return_value = mock_client

    # Call the function
    result = create_mcp_server(mock_config)

    # Verify the result
    assert result == mock_server
    mock_fastmcp.assert_called_once()
    mock_load_spec.assert_called_once_with(
        url=mock_config.api_spec_url, path=mock_config.api_spec_path
    )
    mock_validate.assert_called_once()
    mock_create_client.assert_called_once()
    mock_fastmcp_openapi.assert_called_once()


@patch('awslabs.openapi_mcp_server.server.FastMCP')
@patch('awslabs.openapi_mcp_server.server.load_openapi_spec')
@patch('awslabs.openapi_mcp_server.server.logger')
@patch('awslabs.openapi_mcp_server.server.sys.exit')
def test_create_mcp_server_missing_spec(
    mock_exit, mock_logger, mock_load_spec, mock_fastmcp, mock_config
):
    """Test creating an MCP server with missing API spec."""
    # Setup mocks
    mock_server = MagicMock()
    mock_fastmcp.return_value = mock_server

    # Set both URL and path to None
    mock_config.api_spec_url = None
    mock_config.api_spec_path = None

    # Call the function - it will try to exit but we've patched sys.exit
    _ = create_mcp_server(mock_config)

    # Verify that the logger.error was called with the right message
    mock_logger.error.assert_any_call('No API spec URL or path provided')
    # Verify other expected behaviors
    mock_fastmcp.assert_called_once()
    mock_load_spec.assert_not_called()
    # Verify that sys.exit was called with exit code 1
    mock_exit.assert_called_once_with(1)


@patch('awslabs.openapi_mcp_server.server.FastMCP')
@patch('awslabs.openapi_mcp_server.server.load_openapi_spec')
@patch('awslabs.openapi_mcp_server.server.validate_openapi_spec', return_value=True)
@patch('awslabs.openapi_mcp_server.server.logger')
@patch('awslabs.openapi_mcp_server.server.sys.exit')
def test_create_mcp_server_missing_base_url(
    mock_exit, mock_logger, mock_validate, mock_load_spec, mock_fastmcp, mock_config
):
    """Test creating an MCP server with missing API base URL."""
    # Setup mocks
    mock_server = MagicMock()
    mock_fastmcp.return_value = mock_server
    mock_load_spec.return_value = {
        'openapi': '3.0.0',
        'info': {'title': 'Test API', 'version': '1.0.0'},
        'paths': {},
    }

    # Set base URL to None
    mock_config.api_base_url = None

    # Call the function - it will try to exit but we've patched sys.exit
    _ = create_mcp_server(mock_config)

    # Verify that the logger.error was called with the right message
    mock_logger.error.assert_any_call('No API base URL provided')
    # Verify other expected behaviors
    mock_fastmcp.assert_called_once()
    mock_load_spec.assert_called_once()
    mock_validate.assert_called_once()
    # Verify that sys.exit was called with exit code 1
    mock_exit.assert_called_once_with(1)


@patch('awslabs.openapi_mcp_server.server.FastMCPOpenAPI')
@patch('awslabs.openapi_mcp_server.server.FastMCP')
@patch('awslabs.openapi_mcp_server.server.load_openapi_spec')
@patch('awslabs.openapi_mcp_server.server.validate_openapi_spec', return_value=False)
@patch('awslabs.openapi_mcp_server.server.HttpClientFactory.create_client')
def test_create_mcp_server_invalid_spec(
    mock_create_client,
    mock_validate,
    mock_load_spec,
    mock_fastmcp,
    mock_fastmcp_openapi,
    mock_config,
):
    """Test creating an MCP server with an invalid OpenAPI spec."""
    # Setup mocks
    mock_server = MagicMock()
    mock_fastmcp.return_value = MagicMock()
    mock_fastmcp_openapi.return_value = mock_server
    mock_load_spec.return_value = {
        'info': {'title': 'Test API', 'version': '1.0.0'},
        'paths': {},
    }  # Missing openapi field
    mock_client = MagicMock()
    mock_create_client.return_value = mock_client

    # Call the function
    result = create_mcp_server(mock_config)

    # Verify the result - should continue despite validation failure
    assert result == mock_server
    mock_fastmcp.assert_called_once()
    mock_load_spec.assert_called_once()
    mock_validate.assert_called_once()
    mock_create_client.assert_called_once()
    mock_fastmcp_openapi.assert_called_once()
