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

"""Tests to ensure all MCP tools have descriptions."""

from awslabs.aws_msk_mcp_server.tools import (
    logs_and_telemetry,
    mutate_cluster,
    mutate_config,
    mutate_vpc,
    read_cluster,
    read_config,
    read_global,
    read_vpc,
    static_tools,
)
from unittest.mock import MagicMock


class TestToolDescriptions:
    """Test that all MCP tools have proper descriptions."""

    def test_all_tools_have_descriptions(self):
        """Test that all defined MCP tools have descriptions in their decorator."""
        # List of all modules that register MCP tools
        modules_to_test = [
            logs_and_telemetry,
            mutate_cluster,
            mutate_config,
            mutate_vpc,
            read_cluster,
            read_config,
            read_global,
            read_vpc,
            static_tools,
        ]

        tools_without_descriptions = []
        tools_with_descriptions = []

        for module in modules_to_test:
            module_name = module.__name__.split('.')[-1]

            # Create a mock MCP instance to capture tool calls
            mock_mcp = MagicMock()

            # Register the module's tools
            module.register_module(mock_mcp)

            # Check each tool decorator call
            for call in mock_mcp.tool.call_args_list:
                tool_name = call.kwargs.get('name')
                tool_description = call.kwargs.get('description')

                if tool_name:
                    if tool_description and tool_description.strip():
                        tools_with_descriptions.append(f'{module_name}.{tool_name}')
                    else:
                        tools_without_descriptions.append(f'{module_name}.{tool_name}')

        # Assert that all tools have descriptions
        if tools_without_descriptions:
            missing_tools_message = '\n'.join(f'  - {tool}' for tool in tools_without_descriptions)
            assert False, (
                f'The following tools are missing descriptions:\n{missing_tools_message}\n\n'
                f"All MCP tools must have a 'description' parameter in their @mcp.tool decorator. "
                f"This description helps Claude/q understand the tool's purpose."
            )

        # Verify we found some tools (sanity check)
        assert len(tools_with_descriptions) > 0, (
            'No tools with descriptions were found. This indicates a problem with the test.'
        )

        print(f'✅ All {len(tools_with_descriptions)} tools have descriptions:')
        for tool in sorted(tools_with_descriptions):
            print(f'  - {tool}')

    def test_tool_descriptions_are_meaningful(self):
        """Test that tool descriptions are meaningful (not just empty strings)."""
        modules_to_test = [
            logs_and_telemetry,
            mutate_cluster,
            mutate_config,
            mutate_vpc,
            read_cluster,
            read_config,
            read_global,
            read_vpc,
            static_tools,
        ]

        tools_with_poor_descriptions = []

        for module in modules_to_test:
            module_name = module.__name__.split('.')[-1]

            # Create a mock MCP instance to capture tool calls
            mock_mcp = MagicMock()

            # Register the module's tools
            module.register_module(mock_mcp)

            # Check each tool decorator call
            for call in mock_mcp.tool.call_args_list:
                tool_name = call.kwargs.get('name')
                tool_description = call.kwargs.get('description')

                if tool_name and tool_description:
                    # Check if description is meaningful (more than 10 characters, contains actual words)
                    if len(tool_description.strip()) < 10 or tool_description.strip().lower() in [
                        'todo',
                        'description',
                        'tbd',
                        'placeholder',
                    ]:
                        tools_with_poor_descriptions.append(
                            f"{module_name}.{tool_name}: '{tool_description}'"
                        )

        # Assert that all descriptions are meaningful
        if tools_with_poor_descriptions:
            poor_descriptions_message = '\n'.join(
                f'  - {tool}' for tool in tools_with_poor_descriptions
            )
            assert False, (
                f'The following tools have poor or placeholder descriptions:\n{poor_descriptions_message}\n\n'
                f'Tool descriptions should be clear, meaningful, and help Claude/q understand what the tool does.'
            )
