"""Test to improve coverage for server.py - one test case at a time."""

from awslabs.openapi_mcp_server.api.config import Config
from awslabs.openapi_mcp_server.server import create_mcp_server
from unittest.mock import MagicMock, patch


class TestServerCoverageBoost:
    """Tests to improve coverage for server.py - adding one test at a time."""

    @patch('awslabs.openapi_mcp_server.auth.register.register_provider_by_type')
    @patch('awslabs.openapi_mcp_server.server.load_openapi_spec')
    @patch('awslabs.openapi_mcp_server.server.validate_openapi_spec')
    @patch('awslabs.openapi_mcp_server.server.FastMCP')
    def test_create_mcp_server_with_auth_type_registration(
        self, mock_fastmcp, mock_validate, mock_load_spec, mock_register
    ):
        """Test create_mcp_server registers auth provider by type."""
        # Mock dependencies with a valid OpenAPI spec
        mock_load_spec.return_value = {
            'openapi': '3.0.0',
            'info': {'title': 'Test API', 'version': '1.0.0'},
            'paths': {
                '/test': {
                    'get': {
                        'summary': 'Test endpoint',
                        'responses': {'200': {'description': 'Success'}},
                    }
                }
            },
        }
        mock_validate.return_value = True
        mock_server_instance = MagicMock()
        mock_fastmcp.return_value = mock_server_instance

        # Create a config with auth_type
        config = Config(
            api_name='test_api',
            api_base_url='https://api.example.com',
            api_spec_url='https://api.example.com/openapi.json',
            auth_type='bearer',
        )

        # Mock FastMCPOpenAPI to avoid the validation error
        with patch('awslabs.openapi_mcp_server.server.FastMCPOpenAPI') as mock_fastmcp_openapi:
            mock_openapi_server = MagicMock()
            mock_fastmcp_openapi.return_value = mock_openapi_server

            # Call create_mcp_server
            server = create_mcp_server(config)

            # Verify register_provider_by_type was called with the auth_type
            mock_register.assert_called_once_with('bearer')

            # Verify server was created
            assert server == mock_openapi_server
