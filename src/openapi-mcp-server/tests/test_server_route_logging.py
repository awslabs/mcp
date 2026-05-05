"""Tests for route logging in server.py."""

from awslabs.openapi_mcp_server.api.config import Config
from awslabs.openapi_mcp_server.server import create_mcp_server
from unittest.mock import MagicMock, patch


class TestServerRouteLogging:
    """Tests for route logging in server.py."""

    @patch('awslabs.openapi_mcp_server.server.logger')
    @patch('awslabs.openapi_mcp_server.auth.get_auth_provider')
    @patch('awslabs.openapi_mcp_server.server.load_openapi_spec')
    @patch('awslabs.openapi_mcp_server.server.validate_openapi_spec')
    @patch('awslabs.openapi_mcp_server.server.OpenAPIProvider')
    @patch('awslabs.openapi_mcp_server.server.FastMCP')
    @patch('awslabs.openapi_mcp_server.server.HttpClientFactory')
    def test_create_server_with_openapi_provider(
        self,
        mock_http_factory,
        mock_openapi_provider,
        mock_fastmcp,
        mock_validate,
        mock_load,
        mock_get_auth,
        mock_logger,
    ):
        """Test that create_mcp_server creates server with OpenAPIProvider."""
        # Set up mocks
        mock_auth = MagicMock()
        mock_auth.is_configured.return_value = True  # This is crucial to prevent sys.exit(1)
        mock_auth.get_auth_headers.return_value = {}
        mock_auth.get_auth_params.return_value = {}
        mock_auth.get_auth_cookies.return_value = {}
        mock_auth.get_httpx_auth.return_value = None
        mock_auth.provider_name = 'test_auth'  # Add provider_name attribute
        mock_get_auth.return_value = mock_auth

        mock_spec = {
            'openapi': '3.0.0',
            'paths': {},
            'info': {'title': 'Test API', 'version': '1.0.0'},
        }
        mock_load.return_value = mock_spec
        mock_validate.return_value = True

        # Mock HTTP client factory
        mock_client = MagicMock()
        mock_http_factory.create_client.return_value = mock_client

        # Create a mock server
        mock_server = MagicMock()
        mock_fastmcp.return_value = mock_server

        # Set logger.level to DEBUG
        mock_logger.level = 'DEBUG'

        # Create config
        config = Config(
            api_name='test',
            api_base_url='https://api.example.com',
            api_spec_url='https://api.example.com/spec.json',
        )

        # Call create_mcp_server
        create_mcp_server(config)

        # Verify that the server was created successfully
        mock_fastmcp.assert_called_once()
        mock_openapi_provider.assert_called_once()

    @patch('awslabs.openapi_mcp_server.server.logger')
    @patch('awslabs.openapi_mcp_server.auth.get_auth_provider')
    @patch('awslabs.openapi_mcp_server.server.load_openapi_spec')
    @patch('awslabs.openapi_mcp_server.server.validate_openapi_spec')
    @patch('awslabs.openapi_mcp_server.server.OpenAPIProvider')
    @patch('awslabs.openapi_mcp_server.server.FastMCP')
    @patch('awslabs.openapi_mcp_server.server.HttpClientFactory')
    def test_create_server_no_debug_logging(
        self,
        mock_http_factory,
        mock_openapi_provider,
        mock_fastmcp,
        mock_validate,
        mock_load,
        mock_get_auth,
        mock_logger,
    ):
        """Test that create_mcp_server does not log route-level debug messages."""
        # Set up mocks
        mock_auth = MagicMock()
        mock_auth.is_configured.return_value = True
        mock_auth.get_auth_headers.return_value = {}
        mock_auth.get_auth_params.return_value = {}
        mock_auth.get_auth_cookies.return_value = {}
        mock_auth.get_httpx_auth.return_value = None
        mock_auth.provider_name = 'test_auth'
        mock_get_auth.return_value = mock_auth

        mock_spec = {
            'openapi': '3.0.0',
            'paths': {},
            'info': {'title': 'Test API', 'version': '1.0.0'},
        }
        mock_load.return_value = mock_spec
        mock_validate.return_value = True

        mock_client = MagicMock()
        mock_http_factory.create_client.return_value = mock_client
        mock_fastmcp.return_value = MagicMock()

        config = Config(
            api_name='test',
            api_base_url='https://api.example.com',
            api_spec_url='https://api.example.com/spec.json',
        )

        create_mcp_server(config)

        # Route-level debug logging was removed in fastmcp 3.x migration
        debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
        route_debug_messages = [
            call for call in debug_calls if 'Route 0:' in call or 'Route 1:' in call
        ]
        assert len(route_debug_messages) == 0
