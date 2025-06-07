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
"""Tests for the server module's httpx version handling."""

import pytest
from awslabs.openapi_mcp_server.api.config import Config
from awslabs.openapi_mcp_server.server import create_mcp_server
from unittest.mock import MagicMock, PropertyMock, patch


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
@patch('awslabs.openapi_mcp_server.server.logger')
@patch('awslabs.openapi_mcp_server.server.httpx')
def test_create_mcp_server_httpx_version_error(
    mock_httpx,
    mock_logger,
    mock_create_client,
    mock_validate,
    mock_load_spec,
    mock_fastmcp,
    mock_fastmcp_openapi,
    mock_config,
):
    """Test handling of missing httpx.__version__ attribute."""
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

    # Explicitly configure mock_httpx to raise AttributeError when __version__ is accessed
    type(mock_httpx).__version__ = PropertyMock(
        side_effect=AttributeError("'module' object has no attribute '__version__'")
    )

    # Call the function
    result = create_mcp_server(mock_config)

    # Verify the result
    assert result == mock_server

    # Verify that the logger.debug was called with the fallback message
    mock_logger.debug.assert_any_call('HTTPX version: unknown')
