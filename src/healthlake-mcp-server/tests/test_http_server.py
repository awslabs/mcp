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

"""Tests for HTTP server (Streamable HTTP transport) functionality."""

import pytest
import sys
from unittest.mock import AsyncMock, Mock, patch

from awslabs.healthlake_mcp_server.http_server import (
    MCPASGIApp,
    create_app,
    parse_args,
)
from awslabs.healthlake_mcp_server.server import ALL_TOOLS


class TestParseArgs:
    """Test argument parsing functionality for HTTP server."""

    def test_parse_args_defaults(self):
        """Test default argument values."""
        with patch.object(sys, 'argv', ['test']):
            args = parse_args()
            assert args.readonly is False
            assert args.host == '0.0.0.0'
            assert args.port == 8080
            assert args.stateless is False
            assert args.allowed_origins == ''
            assert args.allowed_tools == ''

    def test_parse_args_readonly_flag(self):
        """Test parsing --readonly flag."""
        with patch.object(sys, 'argv', ['test', '--readonly']):
            args = parse_args()
            assert args.readonly is True

    def test_parse_args_host(self):
        """Test parsing --host argument."""
        with patch.object(sys, 'argv', ['test', '--host', '127.0.0.1']):
            args = parse_args()
            assert args.host == '127.0.0.1'

    def test_parse_args_port(self):
        """Test parsing --port argument."""
        with patch.object(sys, 'argv', ['test', '--port', '3000']):
            args = parse_args()
            assert args.port == 3000

    def test_parse_args_stateless(self):
        """Test parsing --stateless flag."""
        with patch.object(sys, 'argv', ['test', '--stateless']):
            args = parse_args()
            assert args.stateless is True

    def test_parse_args_allowed_origins(self):
        """Test parsing --allowed-origins argument."""
        with patch.object(sys, 'argv', ['test', '--allowed-origins', 'https://example.com']):
            args = parse_args()
            assert args.allowed_origins == 'https://example.com'

    def test_parse_args_allowed_tools(self):
        """Test parsing --allowed-tools argument."""
        with patch.object(
            sys, 'argv', ['test', '--allowed-tools', 'read_fhir_resource,search_fhir_resources']
        ):
            args = parse_args()
            assert args.allowed_tools == 'read_fhir_resource,search_fhir_resources'

    def test_parse_args_env_host(self):
        """Test MCP_HOST environment variable."""
        with patch.object(sys, 'argv', ['test']):
            with patch.dict('os.environ', {'MCP_HOST': '192.168.1.1'}):
                # Need to reimport to pick up env var
                from awslabs.healthlake_mcp_server import http_server
                import importlib

                importlib.reload(http_server)
                args = http_server.parse_args()
                assert args.host == '192.168.1.1'

    def test_parse_args_env_port(self):
        """Test MCP_PORT environment variable."""
        with patch.object(sys, 'argv', ['test']):
            with patch.dict('os.environ', {'MCP_PORT': '9000'}):
                from awslabs.healthlake_mcp_server import http_server
                import importlib

                importlib.reload(http_server)
                args = http_server.parse_args()
                assert args.port == 9000

    def test_parse_args_combined(self):
        """Test multiple arguments together."""
        with patch.object(
            sys,
            'argv',
            [
                'test',
                '--host',
                '127.0.0.1',
                '--port',
                '3000',
                '--readonly',
                '--stateless',
                '--allowed-origins',
                'https://example.com',
                '--allowed-tools',
                'read_fhir_resource',
            ],
        ):
            args = parse_args()
            assert args.host == '127.0.0.1'
            assert args.port == 3000
            assert args.readonly is True
            assert args.stateless is True
            assert args.allowed_origins == 'https://example.com'
            assert args.allowed_tools == 'read_fhir_resource'


class TestMCPASGIApp:
    """Test the ASGI wrapper for MCP session manager."""

    async def test_asgi_app_calls_session_manager(self):
        """Test that MCPASGIApp delegates to session manager."""
        mock_session_manager = Mock()
        mock_session_manager.handle_request = AsyncMock()

        app = MCPASGIApp(mock_session_manager)

        scope = {'type': 'http'}
        receive = AsyncMock()
        send = AsyncMock()

        await app(scope, receive, send)

        mock_session_manager.handle_request.assert_called_once_with(scope, receive, send)


class TestCreateApp:
    """Test Starlette application creation."""

    @patch('awslabs.healthlake_mcp_server.http_server.create_healthlake_server')
    @patch('awslabs.healthlake_mcp_server.http_server.StreamableHTTPSessionManager')
    def test_create_app_default(self, mock_session_manager, mock_create_server):
        """Test creating app with default settings."""
        mock_server = Mock()
        mock_create_server.return_value = mock_server

        app = create_app()

        assert app is not None
        mock_create_server.assert_called_once_with(read_only=False, allowed_tools=None)
        mock_session_manager.assert_called_once()

    @patch('awslabs.healthlake_mcp_server.http_server.create_healthlake_server')
    @patch('awslabs.healthlake_mcp_server.http_server.StreamableHTTPSessionManager')
    def test_create_app_readonly(self, mock_session_manager, mock_create_server):
        """Test creating app in read-only mode."""
        mock_server = Mock()
        mock_create_server.return_value = mock_server

        app = create_app(read_only=True)

        assert app is not None
        mock_create_server.assert_called_once_with(read_only=True, allowed_tools=None)

    @patch('awslabs.healthlake_mcp_server.http_server.create_healthlake_server')
    @patch('awslabs.healthlake_mcp_server.http_server.StreamableHTTPSessionManager')
    def test_create_app_stateless(self, mock_session_manager, mock_create_server):
        """Test creating app in stateless mode."""
        mock_server = Mock()
        mock_create_server.return_value = mock_server

        app = create_app(stateless=True)

        assert app is not None
        call_kwargs = mock_session_manager.call_args.kwargs
        assert call_kwargs['stateless'] is True

    @patch('awslabs.healthlake_mcp_server.http_server.create_healthlake_server')
    @patch('awslabs.healthlake_mcp_server.http_server.StreamableHTTPSessionManager')
    def test_create_app_allowed_tools(self, mock_session_manager, mock_create_server):
        """Test creating app with allowed tools."""
        mock_server = Mock()
        mock_create_server.return_value = mock_server

        allowed = {'read_fhir_resource', 'search_fhir_resources'}
        app = create_app(allowed_tools=allowed)

        assert app is not None
        mock_create_server.assert_called_once_with(read_only=False, allowed_tools=allowed)

    @patch('awslabs.healthlake_mcp_server.http_server.create_healthlake_server')
    @patch('awslabs.healthlake_mcp_server.http_server.StreamableHTTPSessionManager')
    @patch('awslabs.healthlake_mcp_server.http_server.TransportSecuritySettings')
    def test_create_app_allowed_origins(
        self, mock_security_settings, mock_session_manager, mock_create_server
    ):
        """Test creating app with allowed origins."""
        mock_server = Mock()
        mock_create_server.return_value = mock_server

        origins = ['https://example.com', 'https://trusted.com']
        app = create_app(allowed_origins=origins)

        assert app is not None
        mock_security_settings.assert_called_once_with(allowed_origins=origins)


class TestAppRoutes:
    """Test HTTP routes in the application."""

    @patch('awslabs.healthlake_mcp_server.http_server.create_healthlake_server')
    @patch('awslabs.healthlake_mcp_server.http_server.StreamableHTTPSessionManager')
    def test_routes_exist(self, mock_session_manager, mock_create_server):
        """Test that expected routes are configured."""
        mock_server = Mock()
        mock_create_server.return_value = mock_server

        app = create_app()

        # Get route paths
        route_paths = [route.path for route in app.routes]

        assert '/health' in route_paths
        assert '/ready' in route_paths
        assert '/mcp' in route_paths


class TestHealthEndpoints:
    """Test health check endpoints."""

    @patch('awslabs.healthlake_mcp_server.http_server.create_healthlake_server')
    @patch('awslabs.healthlake_mcp_server.http_server.StreamableHTTPSessionManager')
    async def test_health_endpoint(self, mock_session_manager, mock_create_server):
        """Test /health endpoint returns correct response."""
        from starlette.testclient import TestClient

        mock_server = Mock()
        mock_create_server.return_value = mock_server

        # Mock the session manager's run method
        mock_session_manager_instance = Mock()
        mock_session_manager_instance.run = AsyncMock()
        mock_session_manager.return_value = mock_session_manager_instance

        app = create_app()

        # Note: TestClient doesn't trigger lifespan, so we test the endpoint directly
        # by finding the route handler
        for route in app.routes:
            if hasattr(route, 'path') and route.path == '/health':
                from starlette.requests import Request
                from starlette.responses import JSONResponse

                # Create a mock request
                mock_request = Mock(spec=Request)

                # Get the endpoint function
                endpoint = route.endpoint
                response = await endpoint(mock_request)

                assert isinstance(response, JSONResponse)
                break

    @patch('awslabs.healthlake_mcp_server.http_server.create_healthlake_server')
    @patch('awslabs.healthlake_mcp_server.http_server.StreamableHTTPSessionManager')
    async def test_ready_endpoint(self, mock_session_manager, mock_create_server):
        """Test /ready endpoint returns correct response."""
        mock_server = Mock()
        mock_create_server.return_value = mock_server

        app = create_app()

        for route in app.routes:
            if hasattr(route, 'path') and route.path == '/ready':
                from starlette.requests import Request
                from starlette.responses import JSONResponse

                mock_request = Mock(spec=Request)
                endpoint = route.endpoint
                response = await endpoint(mock_request)

                assert isinstance(response, JSONResponse)
                break


class TestMainFunction:
    """Test the main entry point function."""

    @patch('uvicorn.run')
    @patch('awslabs.healthlake_mcp_server.http_server.create_app')
    @patch('awslabs.healthlake_mcp_server.http_server.parse_args')
    def test_main_basic(self, mock_parse_args, mock_create_app, mock_uvicorn_run):
        """Test main function with basic arguments."""
        from awslabs.healthlake_mcp_server.http_server import main

        mock_args = Mock()
        mock_args.host = '0.0.0.0'
        mock_args.port = 8080
        mock_args.readonly = False
        mock_args.stateless = False
        mock_args.allowed_origins = ''
        mock_args.allowed_tools = ''
        mock_parse_args.return_value = mock_args

        mock_app = Mock()
        mock_create_app.return_value = mock_app

        main()

        mock_create_app.assert_called_once_with(
            read_only=False, stateless=False, allowed_origins=None, allowed_tools=None
        )
        mock_uvicorn_run.assert_called_once()

    @patch('uvicorn.run')
    @patch('awslabs.healthlake_mcp_server.http_server.create_app')
    @patch('awslabs.healthlake_mcp_server.http_server.parse_args')
    def test_main_with_allowed_tools(self, mock_parse_args, mock_create_app, mock_uvicorn_run):
        """Test main function with allowed tools."""
        from awslabs.healthlake_mcp_server.http_server import main

        mock_args = Mock()
        mock_args.host = '0.0.0.0'
        mock_args.port = 8080
        mock_args.readonly = False
        mock_args.stateless = False
        mock_args.allowed_origins = ''
        mock_args.allowed_tools = 'read_fhir_resource,search_fhir_resources'
        mock_parse_args.return_value = mock_args

        mock_app = Mock()
        mock_create_app.return_value = mock_app

        main()

        call_kwargs = mock_create_app.call_args.kwargs
        assert call_kwargs['allowed_tools'] == {'read_fhir_resource', 'search_fhir_resources'}

    @patch('uvicorn.run')
    @patch('awslabs.healthlake_mcp_server.http_server.create_app')
    @patch('awslabs.healthlake_mcp_server.http_server.parse_args')
    def test_main_with_allowed_origins(self, mock_parse_args, mock_create_app, mock_uvicorn_run):
        """Test main function with allowed origins."""
        from awslabs.healthlake_mcp_server.http_server import main

        mock_args = Mock()
        mock_args.host = '0.0.0.0'
        mock_args.port = 8080
        mock_args.readonly = False
        mock_args.stateless = False
        mock_args.allowed_origins = 'https://example.com,https://trusted.com'
        mock_args.allowed_tools = ''
        mock_parse_args.return_value = mock_args

        mock_app = Mock()
        mock_create_app.return_value = mock_app

        main()

        call_kwargs = mock_create_app.call_args.kwargs
        assert call_kwargs['allowed_origins'] == ['https://example.com', 'https://trusted.com']

    @patch('uvicorn.run')
    @patch('awslabs.healthlake_mcp_server.http_server.create_app')
    @patch('awslabs.healthlake_mcp_server.http_server.parse_args')
    def test_main_invalid_tool_exits(self, mock_parse_args, mock_create_app, mock_uvicorn_run):
        """Test main function exits with invalid tool name."""
        from awslabs.healthlake_mcp_server.http_server import main

        mock_args = Mock()
        mock_args.host = '0.0.0.0'
        mock_args.port = 8080
        mock_args.readonly = False
        mock_args.stateless = False
        mock_args.allowed_origins = ''
        mock_args.allowed_tools = 'invalid_tool_name'
        mock_parse_args.return_value = mock_args

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1


class TestAllToolsConstant:
    """Test the ALL_TOOLS constant is properly defined."""

    def test_all_tools_contains_expected_tools(self):
        """Test ALL_TOOLS contains all expected tool names."""
        expected_tools = {
            'list_datastores',
            'get_datastore_details',
            'read_fhir_resource',
            'search_fhir_resources',
            'patient_everything',
            'list_fhir_jobs',
            'create_fhir_resource',
            'update_fhir_resource',
            'delete_fhir_resource',
            'start_fhir_import_job',
            'start_fhir_export_job',
        }
        assert ALL_TOOLS == expected_tools

    def test_all_tools_count(self):
        """Test ALL_TOOLS has 11 tools."""
        assert len(ALL_TOOLS) == 11

