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

"""Tests for the RDS Control Plane MCP Server main module."""

from awslabs.rds_control_plane_mcp_server.main import main
from unittest.mock import MagicMock, patch


class TestMain:
    """Test main function."""

    @patch('awslabs.rds_control_plane_mcp_server.main.mcp')
    @patch('awslabs.rds_control_plane_mcp_server.main.RDSContext')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_with_default_args(self, mock_parse_args, mock_rds_context, mock_mcp):
        """Test main function with default arguments."""
        mock_args = MagicMock()
        mock_args.port = 8888
        mock_args.max_items = 100
        mock_args.readonly = True
        mock_parse_args.return_value = mock_args

        main()

        mock_rds_context.initialize.assert_called_once_with(True, 100)
        assert mock_mcp.settings.port == 8888
        mock_mcp.run.assert_called_once()

    @patch('awslabs.rds_control_plane_mcp_server.main.mcp')
    @patch('awslabs.rds_control_plane_mcp_server.main.RDSContext')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_with_custom_args(self, mock_parse_args, mock_rds_context, mock_mcp):
        """Test main function with custom arguments."""
        mock_args = MagicMock()
        mock_args.port = 9999
        mock_args.max_items = 50
        mock_args.readonly = False
        mock_parse_args.return_value = mock_args

        main()

        mock_rds_context.initialize.assert_called_once_with(False, 50)
        assert mock_mcp.settings.port == 9999
        mock_mcp.run.assert_called_once()

    @patch('awslabs.rds_control_plane_mcp_server.main.mcp')
    @patch('awslabs.rds_control_plane_mcp_server.main.RDSContext')
    @patch('sys.argv', ['main.py', '--port', '7777', '--max-items', '25', '--no-readonly'])
    def test_argument_parsing(self, mock_rds_context, mock_mcp):
        """Test argument parsing with specific values."""
        main()

        mock_rds_context.initialize.assert_called_once_with(False, 25)
        assert mock_mcp.settings.port == 7777
        mock_mcp.run.assert_called_once()


class TestImports:
    """Test module imports."""

    def test_resources_import(self):
        """Test resources module is imported."""
        import awslabs.rds_control_plane_mcp_server.resources

        assert awslabs.rds_control_plane_mcp_server.resources is not None

    def test_tools_import(self):
        """Test tools module is imported."""
        import awslabs.rds_control_plane_mcp_server.tools

        assert awslabs.rds_control_plane_mcp_server.tools is not None

    def test_mcp_server_import(self):
        """Test mcp server is imported."""
        from awslabs.rds_control_plane_mcp_server.common.server import mcp

        assert mcp is not None
        assert hasattr(mcp, 'run')
        assert callable(mcp.run)
