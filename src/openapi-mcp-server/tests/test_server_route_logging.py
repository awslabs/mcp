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
    @patch('awslabs.openapi_mcp_server.server.FastMCP')
    @patch('awslabs.openapi_mcp_server.server.FastMCPOpenAPI')
    @patch('awslabs.openapi_mcp_server.server.HttpClientFactory')
    def test_create_server_logs_routes(
        self,
        mock_http_factory,
        mock_fastmcp_openapi,
        mock_fastmcp,
        mock_validate,
        mock_load,
        mock_get_auth,
        mock_logger,
    ):
        """Test that create_mcp_server logs routes when debug is enabled."""
        # Set up mocks
        mock_auth = MagicMock()
        mock_auth.is_configured.return_value = True  # This is crucial to prevent sys.exit(1)
        mock_auth.get_auth_headers.return_value = {}
        mock_auth.get_auth_params.return_value = {}
        mock_auth.get_auth_cookies.return_value = {}
        mock_auth.get_httpx_auth.return_value = None
        mock_auth.provider_name = 'test_auth'  # Add provider_name attribute
        mock_get_auth.return_value = mock_auth

        mock_spec = {'openapi': '3.0.0', 'paths': {}, 'info': {'title': 'Test API'}}
        mock_load.return_value = mock_spec
        mock_validate.return_value = True

        # Mock HTTP client factory
        mock_client = MagicMock()
        mock_http_factory.create_client.return_value = mock_client

        # Create a mock server with routes
        mock_server = MagicMock()

        # Create mock routes
        mock_route1 = MagicMock()
        mock_route1.path = '/api/v1/pets'
        mock_route1.method = 'GET'
        mock_route1.route_type = 'resource'

        mock_route2 = MagicMock()
        mock_route2.path = '/api/v1/pets/{id}'
        mock_route2.method = 'POST'
        mock_route2.route_type = 'tool'

        # Set up the _openapi_router attribute with routes
        mock_openapi_router = MagicMock()
        mock_openapi_router._routes = [mock_route1, mock_route2]
        mock_server._openapi_router = mock_openapi_router

        mock_fastmcp_openapi.return_value = mock_server

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

        # Verify that logger.debug was called with the expected messages
        mock_logger.debug.assert_any_call('Server has 2 routes')
        mock_logger.debug.assert_any_call('Route 0: GET /api/v1/pets - Type: resource')
        mock_logger.debug.assert_any_call('Route 1: POST /api/v1/pets/{id} - Type: tool')

    @patch('awslabs.openapi_mcp_server.server.logger')
    @patch('awslabs.openapi_mcp_server.auth.get_auth_provider')
    @patch('awslabs.openapi_mcp_server.server.load_openapi_spec')
    @patch('awslabs.openapi_mcp_server.server.validate_openapi_spec')
    @patch('awslabs.openapi_mcp_server.server.FastMCP')
    @patch('awslabs.openapi_mcp_server.server.FastMCPOpenAPI')
    @patch('awslabs.openapi_mcp_server.server.HttpClientFactory')
    def test_create_server_no_debug_logging(
        self,
        mock_http_factory,
        mock_fastmcp_openapi,
        mock_fastmcp,
        mock_validate,
        mock_load,
        mock_get_auth,
        mock_logger,
    ):
        """Test that create_mcp_server doesn't log routes when debug is disabled."""
        # Set up mocks
        mock_auth = MagicMock()
        mock_auth.is_configured.return_value = True  # This is crucial to prevent sys.exit(1)
        mock_auth.get_auth_headers.return_value = {}
        mock_auth.get_auth_params.return_value = {}
        mock_auth.get_auth_cookies.return_value = {}
        mock_auth.get_httpx_auth.return_value = None
        mock_auth.provider_name = 'test_auth'  # Add provider_name attribute
        mock_get_auth.return_value = mock_auth

        mock_spec = {'openapi': '3.0.0', 'paths': {}, 'info': {'title': 'Test API'}}
        mock_load.return_value = mock_spec
        mock_validate.return_value = True

        # Mock HTTP client factory
        mock_client = MagicMock()
        mock_http_factory.create_client.return_value = mock_client

        # Create a mock server with routes
        mock_server = MagicMock()

        # Create mock routes
        mock_route1 = MagicMock()
        mock_route1.path = '/api/v1/pets'
        mock_route1.method = 'GET'
        mock_route1.route_type = 'resource'

        # Set up the _openapi_router attribute with routes
        mock_openapi_router = MagicMock()
        mock_openapi_router._routes = [mock_route1]
        mock_server._openapi_router = mock_openapi_router

        mock_fastmcp_openapi.return_value = mock_server

        # Set logger.level to INFO (not DEBUG)
        mock_logger.level = 'INFO'

        # Create config
        config = Config(
            api_name='test',
            api_base_url='https://api.example.com',
            api_spec_url='https://api.example.com/spec.json',
        )

        # Call create_mcp_server
        create_mcp_server(config)

        # Verify that logger.debug was not called with route information
        debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
        route_debug_messages = [
            call
            for call in debug_calls
            if 'routes' in call
            and (
                'Route 0:' in call
                or 'Route 1:' in call
                or 'Server has' in call
                and 'routes' in call
            )
        ]
        assert len(route_debug_messages) == 0, (
            f'Found unexpected route debug messages: {route_debug_messages}'
        )
