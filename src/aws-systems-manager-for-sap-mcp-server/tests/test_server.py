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
        from awslabs.aws_systems_manager_for_sap_mcp_server.server import mcp

        assert mcp is not None
        assert mcp.name == 'awslabs.aws-systems-manager-for-sap-mcp-server'

    def test_tools_registered(self):
        """Test that all tool modules are registered on the server."""
        from awslabs.aws_systems_manager_for_sap_mcp_server.server import mcp

        tool_names = [t.name for t in mcp._tool_manager.list_tools()]
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
