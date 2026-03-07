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
"""Tests for the main function in server.py."""

from awslabs.mwaa_mcp_server.server import create_server, main
from unittest.mock import MagicMock, patch


class TestMain:
    """Tests for the main function."""

    @patch('awslabs.mwaa_mcp_server.server.AirflowTools')
    @patch('awslabs.mwaa_mcp_server.server.EnvironmentTools')
    @patch('awslabs.mwaa_mcp_server.server.create_server')
    @patch('sys.argv', ['awslabs.mwaa-mcp-server'])
    def test_main_default(self, mock_create_server, mock_env_tools, mock_airflow_tools):
        """Test main function with default arguments (read-only mode)."""
        mock_server = MagicMock()
        mock_create_server.return_value = mock_server

        main()

        mock_create_server.assert_called_once()
        mock_env_tools.assert_called_once_with(mock_server, False)
        mock_airflow_tools.assert_called_once_with(mock_server, False)
        mock_server.run.assert_called_once()

    @patch('awslabs.mwaa_mcp_server.server.AirflowTools')
    @patch('awslabs.mwaa_mcp_server.server.EnvironmentTools')
    @patch('awslabs.mwaa_mcp_server.server.create_server')
    @patch('sys.argv', ['awslabs.mwaa-mcp-server', '--allow-write'])
    def test_main_allow_write(self, mock_create_server, mock_env_tools, mock_airflow_tools):
        """Test main function with --allow-write flag."""
        mock_server = MagicMock()
        mock_create_server.return_value = mock_server

        main()

        mock_create_server.assert_called_once()
        mock_env_tools.assert_called_once_with(mock_server, True)
        mock_airflow_tools.assert_called_once_with(mock_server, True)
        mock_server.run.assert_called_once()

    def test_module_execution(self):
        """Test the module execution when run as __main__."""
        import inspect
        from awslabs.mwaa_mcp_server import server

        source = inspect.getsource(server)
        assert "if __name__ == '__main__':" in source
        assert 'main()' in source

    def test_create_server(self):
        """Test that create_server creates a FastMCP instance with correct parameters."""
        with patch('awslabs.mwaa_mcp_server.server.FastMCP') as mock_fastmcp:
            create_server()

            mock_fastmcp.assert_called_once()
            args, kwargs = mock_fastmcp.call_args
            assert args[0] == 'awslabs.mwaa-mcp-server'
            assert 'instructions' in kwargs
            assert 'dependencies' in kwargs
            assert 'MWAA MCP Server' in kwargs['instructions']
            assert 'boto3' in kwargs['dependencies']
