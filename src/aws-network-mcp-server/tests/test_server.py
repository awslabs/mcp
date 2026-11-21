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

import os
import subprocess
import sys
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

    def test_server_name(self):
        """Test server name and version are correct."""
        assert mcp.name == 'awslabs.aws-core-network-mcp-server'

    def test_server_instructions_contain_key_tools(self):
        """Test that instructions mention key tools."""
        instructions = mcp.instructions
        assert instructions is not None

        # Key tools should be mentioned
        key_tools = [
            'find_ip_address',
            'get_eni_details',
            'list_core_networks',
            'get_cloudwan_details',
            'list_transit_gateways',
            'get_tgw_details',
            'detect_tgw_inspection',
            'detect_cloudwan_inspection',
        ]

        for tool in key_tools:
            assert tool in instructions

    def test_server_instructions_contain_important_notes(self):
        """Test that instructions contain important operational notes."""
        instructions = mcp.instructions
        assert instructions is not None

        assert 'READ-ONLY' in instructions
        assert 'CloudWatch Logs' in instructions
        assert 'Network Manager registration' in instructions
        assert 'profile_name' in instructions

    @patch('awslabs.aws_network_mcp_server.server.mcp.run')
    def test_main_function_calls_mcp_run(self, mock_run):
        """Test the main function calls mcp.run()."""
        main()
        mock_run.assert_called_once()

    @patch('awslabs.aws_network_mcp_server.server.logger')
    @patch('awslabs.aws_network_mcp_server.server.mcp.run')
    def test_main_function_logs_startup(self, mock_run, mock_logger):
        """Test the main function logs startup message."""
        main()
        mock_logger.info.assert_called_with('Starting MCP server...')

    def test_tools_modules_importable(self):
        """Test that all tool modules can be imported."""
        from awslabs.aws_network_mcp_server.tools import (
            cloud_wan,
            general,
            network_firewall,
            transit_gateway,
            vpc,
            vpn,
        )

        # Verify modules exist
        assert cloud_wan is not None
        assert general is not None
        assert network_firewall is not None
        assert transit_gateway is not None
        assert vpc is not None
        assert vpn is not None

    def test_general_tools_available(self):
        """Test that general tools are available."""
        from awslabs.aws_network_mcp_server.tools.general import (
            find_ip_address,
            get_eni_details,
            get_path_trace_methodology,
        )

        assert callable(find_ip_address)
        assert callable(get_eni_details)
        assert callable(get_path_trace_methodology)

    def test_cloud_wan_tools_available(self):
        """Test that Cloud WAN tools are available."""
        from awslabs.aws_network_mcp_server.tools import cloud_wan

        # Check __all__ exists and contains expected tools
        assert hasattr(cloud_wan, '__all__')
        assert len(cloud_wan.__all__) > 0

    def test_vpc_tools_available(self):
        """Test that VPC tools are available."""
        from awslabs.aws_network_mcp_server.tools import vpc

        # Check __all__ exists and contains expected tools
        assert hasattr(vpc, '__all__')
        assert len(vpc.__all__) > 0

    def test_transit_gateway_tools_available(self):
        """Test that Transit Gateway tools are available."""
        from awslabs.aws_network_mcp_server.tools import transit_gateway

        # Check __all__ exists and contains expected tools
        assert hasattr(transit_gateway, '__all__')
        assert len(transit_gateway.__all__) > 0

    def test_network_firewall_tools_available(self):
        """Test that Network Firewall tools are available."""
        from awslabs.aws_network_mcp_server.tools import network_firewall

        # Check __all__ exists and contains expected tools
        assert hasattr(network_firewall, '__all__')
        assert len(network_firewall.__all__) > 0

    def test_vpn_tools_available(self):
        """Test that VPN tools are available."""
        from awslabs.aws_network_mcp_server.tools import vpn

        # Check __all__ exists and contains expected tools
        assert hasattr(vpn, '__all__')
        assert len(vpn.__all__) > 0

    def test_mcp_instance_has_required_attributes(self):
        """Test that MCP instance has all required attributes."""
        assert hasattr(mcp, 'name')
        assert hasattr(mcp, 'version')
        assert hasattr(mcp, 'instructions')
        assert hasattr(mcp, 'run')
        assert hasattr(mcp, 'tool')

    def test_logging_configuration(self):
        """Test that logging is properly configured."""
        import logging

        # Check that logging is configured at DEBUG level
        logger = logging.getLogger('awslabs.aws_network_mcp_server.server')
        assert logger.level <= logging.DEBUG

    def test_tool_registration_process(self):
        """Test that tools are registered with the MCP instance."""
        # Test that the mcp instance has tools registered by checking it has the tool method
        assert hasattr(mcp, 'tool')
        assert callable(mcp.tool)

        # Verify that tools from each module are accessible
        from awslabs.aws_network_mcp_server.tools import (
            cloud_wan,
            general,
            network_firewall,
            transit_gateway,
            vpc,
            vpn,
        )

        # Check that each module has __all__ defined with tools
        for module in [general, cloud_wan, vpc, transit_gateway, network_firewall, vpn]:
            assert hasattr(module, '__all__')
            assert len(module.__all__) > 0
            # Verify each tool in __all__ is callable
            for tool_name in module.__all__:
                assert hasattr(module, tool_name)
                assert callable(getattr(module, tool_name))

    def test_main_function_exists_and_callable(self):
        """Test that main function exists and is callable."""
        from awslabs.aws_network_mcp_server.server import main

        assert callable(main)

    @patch('awslabs.aws_network_mcp_server.server.mcp.run')
    def test_main_as_script_entry_point(self, mock_run):
        """Test main function works as script entry point."""
        # Simulate running as script
        with patch('awslabs.aws_network_mcp_server.server.__name__', '__main__'):
            # Import and run main
            from awslabs.aws_network_mcp_server.server import main

            main()
            mock_run.assert_called_once()


class TestLogging:
    """Test cases for log level configuration."""

    @staticmethod
    def _run(env_level):
        """Import the server in a fresh interpreter and emit one log per level."""
        env = {k: v for k, v in os.environ.items() if k != 'FASTMCP_LOG_LEVEL'}
        if env_level is not None:
            env['FASTMCP_LOG_LEVEL'] = env_level
        code = (
            'from awslabs.aws_network_mcp_server.server import logger;'
            "logger.debug('msg-debug');logger.info('msg-info');"
            "logger.warning('msg-warning');logger.error('msg-error')"
        )
        return subprocess.run(
            [sys.executable, '-c', code], env=env, capture_output=True, text=True, check=True
        )

    def test_default_level_is_warning(self):
        """Without FASTMCP_LOG_LEVEL only WARNING and above are logged."""
        result = self._run(None)
        assert 'msg-debug' not in result.stderr
        assert 'msg-info' not in result.stderr
        assert 'msg-warning' in result.stderr
        assert 'msg-error' in result.stderr

    def test_env_override_error(self):
        """FASTMCP_LOG_LEVEL=ERROR suppresses warnings."""
        result = self._run('ERROR')
        assert 'msg-warning' not in result.stderr
        assert 'msg-error' in result.stderr

    def test_env_override_debug(self):
        """FASTMCP_LOG_LEVEL=DEBUG enables debug output."""
        result = self._run('DEBUG')
        assert 'msg-debug' in result.stderr

    def test_logs_go_to_stderr_not_stdout(self):
        """Stdout carries the MCP transport and must stay free of log output."""
        result = self._run('DEBUG')
        assert result.stdout == ''
