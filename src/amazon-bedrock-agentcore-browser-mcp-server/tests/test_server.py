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

"""Tests for the Amazon Bedrock AgentCore Browser MCP Server."""

import asyncio
from awslabs.amazon_bedrock_agentcore_browser_mcp_server.server import APP_NAME, mcp
from unittest.mock import patch


class TestServer:
    """Test cases for the MCP server setup."""

    def test_app_name(self):
        """Test that the app has the correct name."""
        assert mcp.name == APP_NAME
        assert APP_NAME == 'awslabs.amazon-bedrock-agentcore-browser-mcp-server'

    def test_all_tools_registered(self):
        """Test that all 9 tools are registered with the MCP app."""
        tools = asyncio.get_event_loop().run_until_complete(mcp.list_tools())
        tool_names = [tool.name for tool in tools]

        expected_tools = [
            'start_browser_session',
            'get_browser_session',
            'list_browser_sessions',
            'stop_browser_session',
            'get_automation_headers',
            'save_browser_session_profile',
            'list_browsers',
            'get_browser',
            'open_live_view',
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names, f'Tool {expected_tool} not registered'

        assert len(tool_names) == len(expected_tools), (
            f'Expected {len(expected_tools)} tools, found {len(tool_names)}'
        )

    @patch.object(mcp, 'run')
    def test_main_entry_point(self, mock_run):
        """Test that main() calls mcp.run()."""
        from awslabs.amazon_bedrock_agentcore_browser_mcp_server.server import main

        main()

        mock_run.assert_called_once()
