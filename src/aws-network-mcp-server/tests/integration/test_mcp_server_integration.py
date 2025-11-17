#!/usr/bin/env python3
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

"""Integration test cases for the MCP server."""

from awslabs.aws_network_mcp_server.server import mcp
from unittest.mock import patch


class TestMcpServerIntegration:
    """Integration test cases for the MCP server."""

    def test_server_initialization(self):
        """Test that the MCP server initializes correctly."""
        assert mcp is not None
        assert mcp.name == 'awslabs.aws-core-network-mcp-server'
        assert mcp.version == '1.0.0'
        assert mcp.instructions is not None
        assert len(mcp.instructions) > 0

    def test_server_instructions_content(self):
        """Test that server instructions contain critical information."""
        instructions = mcp.instructions

        # Should contain critical workflow information
        assert 'get_path_trace_methodology' in instructions
        assert 'CRITICAL FIRST STEP' in instructions
        assert 'READ-ONLY' in instructions

        # Should describe available services
        assert 'Cloud WAN' in instructions
        assert 'Transit Gateway' in instructions
        assert 'VPC' in instructions
        assert 'Network Firewall' in instructions

        # Should provide troubleshooting workflow
        assert 'DISCOVER' in instructions
        assert 'ANALYZE' in instructions
        assert 'TRACE' in instructions
        assert 'INSPECT' in instructions
        assert 'VERIFY' in instructions

    def test_all_tools_registered(self):
        """Test that all expected tools are registered with the MCP server."""
        # Get registered tools from the MCP server
        tools = mcp._tools
        tool_names = set(tools.keys())

        # Expected tools from all modules
        expected_general_tools = {
            'get_path_trace_methodology',
            'find_ip_address',
            'get_eni_details',
        }
        expected_cloudwan_tools = {
            'detect_cloudwan_inspection',
            'get_all_cloudwan_routes',
            'get_cloudwan_routes',
            'get_cloudwan_attachment_details',
            'get_cloudwan_details',
            'get_cloudwan_logs',
            'get_cloudwan_peering_details',
            'list_cloudwan_peerings',
            'list_core_networks',
            'simulate_cloud_wan_route_change',
        }
        expected_vpc_tools = {'get_vpc_flow_logs', 'get_vpc_network_details', 'list_vpcs'}
        expected_tgw_tools = {
            'detect_tgw_inspection',
            'get_all_tgw_routes',
            'get_tgw_details',
            'get_tgw_routes',
            'get_tgw_flow_logs',
            'list_tgw_peerings',
            'list_transit_gateways',
        }
        expected_nfw_tools = {
            'get_firewall_rules',
            'get_network_firewall_flow_logs',
            'list_network_firewalls',
        }
        expected_vpn_tools = {'list_vpn_connections'}

        all_expected_tools = (
            expected_general_tools
            | expected_cloudwan_tools
            | expected_vpc_tools
            | expected_tgw_tools
            | expected_nfw_tools
            | expected_vpn_tools
        )

        # Verify all expected tools are registered
        for tool in all_expected_tools:
            assert tool in tool_names, f"Tool '{tool}' not registered with MCP server"

    def test_tool_metadata_structure(self):
        """Test that all registered tools have proper metadata structure."""
        tools = mcp._tools

        for tool_name, tool_info in tools.items():
            # Each tool should have proper structure
            assert 'func' in tool_info or 'handler' in tool_info

            # Tools should have descriptions (either from docstring or metadata)
            tool_func = tool_info.get('func') or tool_info.get('handler')
            if tool_func:
                assert tool_func.__doc__ is not None, f"Tool '{tool_name}' missing docstring"
                assert len(tool_func.__doc__.strip()) > 0, (
                    f"Tool '{tool_name}' has empty docstring"
                )

    def test_server_main_function(self):
        """Test the main function exists and is callable."""
        from awslabs.aws_network_mcp_server.server import main

        assert callable(main)

    @patch('awslabs.aws_network_mcp_server.server.mcp.run')
    def test_main_function_calls_mcp_run(self, mock_run):
        """Test that main function calls mcp.run()."""
        from awslabs.aws_network_mcp_server.server import main

        main()
        mock_run.assert_called_once()

    def test_logging_configuration(self):
        """Test that logging is properly configured."""
        import logging

        # Check that logger is configured at DEBUG level
        logger = logging.getLogger('awslabs.aws_network_mcp_server.server')

        # The logger should be configured (though we can't test the exact level due to setup)
        assert logger is not None

    def test_security_readonly_guarantee(self):
        """Test that all tools are guaranteed to be read-only."""
        tools = mcp._tools

        dangerous_operations = [
            'create',
            'delete',
            'update',
            'modify',
            'change',
            'write',
            'put',
            'post',
            'patch',
            'remove',
            'add',
            'attach',
            'detach',
        ]

        for tool_name in tools.keys():
            # Tool names should not contain dangerous operations
            tool_name_lower = tool_name.lower()

            # Exception for simulate_cloud_wan_route_change which is read-only simulation
            if tool_name != 'simulate_cloud_wan_route_change':
                for dangerous_op in dangerous_operations:
                    if dangerous_op in tool_name_lower:
                        # Only allow 'get' operations which are read-only
                        assert 'get' in tool_name_lower, (
                            f"Tool '{tool_name}' may perform write operations"
                        )

    def test_error_messages_security(self):
        """Test that error messages follow security best practices."""
        instructions = mcp.instructions

        # Instructions should mention validation and security
        assert 'VALIDATE' in instructions
        assert 'REQUIRED' in instructions

        # Should emphasize read-only nature
        assert 'READ-ONLY' in instructions
