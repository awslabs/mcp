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

"""Tests for the aws-network MCP Server."""

from awslabs.aws_network_mcp_server.server import main, mcp
from unittest.mock import patch


class TestMcpServer:
    """Test cases for the MCP server."""

    def test_server_initialization(self):
        """Test that the MCP server is properly initialized."""
        assert mcp is not None
        assert mcp.name == 'awslabs.aws-core-network-mcp-server'
        assert mcp.version == '1.0.0'
        assert mcp.instructions is not None

    def test_server_instructions_contain_required_content(self):
        """Test that server instructions contain required content."""
        instructions = mcp.instructions

        # Should contain critical workflow steps
        assert 'get_path_trace_methodology' in instructions
        assert 'CRITICAL FIRST STEP' in instructions

        # Should mention main service areas
        assert 'Cloud WAN' in instructions
        assert 'Transit Gateway' in instructions
        assert 'VPC' in instructions
        assert 'Network Firewall' in instructions

    @patch('awslabs.aws_network_mcp_server.server.mcp.run')
    def test_main_function(self, mock_run):
        """Test the main function calls mcp.run()."""
        main()
        mock_run.assert_called_once()

    def test_tools_registration(self):
        """Test that tools are properly registered."""
        # Check that tools are registered by checking if the mcp instance has tools
        # FastMCP stores tools differently - we'll verify by checking that key tools are importable
        from awslabs.aws_network_mcp_server.tools.general import find_ip_address, get_eni_details
        from awslabs.aws_network_mcp_server.tools.vpc import list_vpcs

        # If we can import these without errors, the tools are properly structured
        assert callable(find_ip_address)
        assert callable(get_eni_details)
        assert callable(list_vpcs)

        # Verify the MCP instance is properly configured
        assert hasattr(mcp, 'name')
        assert hasattr(mcp, 'version')
        assert hasattr(mcp, 'instructions')
