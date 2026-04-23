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

"""Tests for server initialization and tool registration."""


class TestServerInitialization:
    """Test server module initialization."""

    def test_mcp_server_created(self):
        """Test that the FastMCP server instance is created."""
        from awslabs.aws_for_sap_management_mcp_server.server import mcp

        assert mcp is not None
        assert mcp.name == 'awslabs.aws-for-sap-management-mcp-server'

    async def test_tools_registered(self):
        """Test that all tool modules are registered on the server."""
        from awslabs.aws_for_sap_management_mcp_server.server import mcp

        tools = await mcp.list_tools()
        tool_names = [t.name for t in tools]
        # Application tools
        assert 'list_applications' in tool_names
        assert 'get_application' in tool_names
        assert 'get_component' in tool_names
        assert 'get_operation' in tool_names
        assert 'register_application' in tool_names
        assert 'start_application' in tool_names
        assert 'stop_application' in tool_names
        # Config check tools
        assert 'list_config_check_definitions' in tool_names
        assert 'start_config_checks' in tool_names
        assert 'get_config_check_summary' in tool_names
        assert 'get_config_check_operation' in tool_names
        assert 'list_sub_check_results' in tool_names
        assert 'list_sub_check_rule_results' in tool_names
        # Scheduling tools
        assert 'schedule_config_checks' in tool_names
        assert 'schedule_start_application' in tool_names
        assert 'schedule_stop_application' in tool_names
        assert 'list_app_schedules' in tool_names
        assert 'delete_schedule' in tool_names
        assert 'update_schedule_state' in tool_names
        assert 'get_schedule_details' in tool_names
        # Health tools
        assert 'get_sap_health_summary' in tool_names
        assert 'generate_health_report' in tool_names

    def test_server_exception_handler(self):
        """Test that server re-raises exceptions during tool registration (lines 165-167)."""
        from unittest.mock import patch

        # Patch one of the tool classes to raise during init
        with patch(
            'awslabs.aws_for_sap_management_mcp_server.ssm_sap_applications.tools.SSMSAPApplicationTools'
        ) as mock_app_tools:
            mock_app_tools.side_effect = RuntimeError('Registration failed')
            import importlib
            import pytest

            with pytest.raises(RuntimeError, match='Registration failed'):
                import awslabs.aws_for_sap_management_mcp_server.server as server_mod

                importlib.reload(server_mod)

    def test_main_function(self):
        """Test that main() calls mcp.run() (line 177)."""
        from awslabs.aws_for_sap_management_mcp_server.server import main
        from unittest.mock import patch

        with patch('awslabs.aws_for_sap_management_mcp_server.server.mcp') as mock_mcp:
            main()
            mock_mcp.run.assert_called_once()
