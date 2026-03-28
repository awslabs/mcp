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

"""Tests for server module."""

from awslabs.cross_account_cloudwatch_mcp_server.server import main, mcp
from unittest.mock import patch


class TestServer:
    """Tests for server initialization and main entry point."""

    def test_mcp_server_name(self):
        """Test that the MCP server has the correct name."""
        assert mcp.name == 'awslabs.cross-account-cloudwatch-mcp-server'

    def test_registered_tools(self):
        """Test that the expected MCP tools are registered."""
        tool_names = {tool.name for tool in mcp._tool_manager.list_tools()}
        assert 'list_cw_targets' in tool_names
        assert 'query_logs' in tool_names

    @patch('awslabs.cross_account_cloudwatch_mcp_server.server.mcp')
    def test_main_calls_run(self, mock_mcp):
        """Test that main() calls mcp.run()."""
        main()
        mock_mcp.run.assert_called_once()
