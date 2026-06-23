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

"""Registry-style eval tests for the dynamic instrumentation MCP tools."""

import pytest
from awslabs.cloudwatch_applicationsignals_mcp_server.dynamic_instrumentation.registration import (
    register_tools,
)
from mcp.server.fastmcp import FastMCP


DYNAMIC_INSTRUMENTATION_TOOLS = [
    'create_instrumentation',
    'list_instrumentations',
    'get_instrumentation',
    'delete_instrumentation',
    'batch_delete_instrumentations_by_scope',
    'batch_delete_instrumentations_by_arns',
    'get_instrumentation_configuration_status',
    'check_instrumentation_status',
    'search_snapshots_for_status_event',
    'get_sample_snapshot_for_breakpoint',
]

_REQUIRED_PARAMS = [
    ('create_instrumentation', 'instrumentation_type'),
    ('create_instrumentation', 'service'),
    ('create_instrumentation', 'environment'),
    ('batch_delete_instrumentations_by_arns', 'resource_arns'),
    ('check_instrumentation_status', 'location_hash'),
    ('check_instrumentation_status', 'start_time'),
    ('check_instrumentation_status', 'end_time'),
    ('search_snapshots_for_status_event', 'status_timestamp'),
    ('get_sample_snapshot_for_breakpoint', 'status_timestamp'),
]

_PARAM_DEFAULTS = [
    ('search_snapshots_for_status_event', 'limit', 10),
    ('search_snapshots_for_status_event', 'max_timeout', 30),
    ('get_sample_snapshot_for_breakpoint', 'max_timeout', 30),
]

_DYNAMIC_MCP = None


def _get_dynamic_mcp():
    """Build a local MCP registry for the dynamic instrumentation feature package."""
    global _DYNAMIC_MCP
    if _DYNAMIC_MCP is None:
        mcp = FastMCP('DynamicInstrumentationTest')
        register_tools(mcp)
        _DYNAMIC_MCP = mcp
    return _DYNAMIC_MCP


def _get_tools_by_name() -> dict:
    """Return {name: Tool} for every registered dynamic instrumentation tool."""
    return {tool.name: tool for tool in _get_dynamic_mcp()._tool_manager.list_tools()}


def _get_tool_params(tool) -> dict:
    """Return the 'properties' dict from a tool's JSON Schema parameters."""
    return tool.parameters.get('properties', {})


def _get_tool_required(tool) -> list:
    """Return the list of required parameter names for a tool."""
    return tool.parameters.get('required', [])


@pytest.mark.eval
class TestDynamicInstrumentationToolRegistry:
    """Validate dynamic instrumentation MCP registration and schema metadata."""

    def test_all_dynamic_instrumentation_tools_registered(self):
        """Every dynamic instrumentation tool name resolves to a registered tool."""
        registered = _get_tools_by_name()
        for name in DYNAMIC_INSTRUMENTATION_TOOLS:
            assert name in registered, (
                f"Dynamic instrumentation tool '{name}' not registered. "
                f'Registered: {sorted(registered.keys())}'
            )

    @pytest.mark.parametrize('tool_name', DYNAMIC_INSTRUMENTATION_TOOLS)
    def test_tool_has_description(self, tool_name):
        """Each tool carries a non-trivial description for the LLM to read."""
        tool = _get_tools_by_name()[tool_name]
        assert len(tool.description) > 20, (
            f"Tool '{tool_name}' description too short ({len(tool.description)} chars)"
        )

    @pytest.mark.parametrize('tool_name', DYNAMIC_INSTRUMENTATION_TOOLS)
    def test_tool_has_valid_schema(self, tool_name):
        """Each tool exposes a JSON Schema object for its parameters."""
        tool = _get_tools_by_name()[tool_name]
        schema = tool.parameters
        assert isinstance(schema, dict)
        assert schema.get('type') == 'object'

    def test_no_duplicate_tool_names(self):
        """No two registered tools share a name."""
        names = [tool.name for tool in _get_dynamic_mcp()._tool_manager.list_tools()]
        assert len(names) == len(set(names)), (
            f'Duplicates: {[name for name in names if names.count(name) > 1]}'
        )

    @pytest.mark.parametrize('tool_name,param_name', _REQUIRED_PARAMS)
    def test_required_param(self, tool_name, param_name):
        """Parameters that must be supplied are marked required in the schema."""
        tool = _get_tools_by_name()[tool_name]
        assert param_name in _get_tool_required(tool), (
            f"'{param_name}' must be required for {tool_name}"
        )

    @pytest.mark.parametrize('tool_name,param_name,default_value', _PARAM_DEFAULTS)
    def test_param_default(self, tool_name, param_name, default_value):
        """Optional parameters expose the expected default value."""
        tool = _get_tools_by_name()[tool_name]
        params = _get_tool_params(tool)
        assert param_name in params, f"'{param_name}' not in {tool_name} params"
        assert params[param_name].get('default') == default_value, (
            f'{tool_name}.{param_name} default should be {default_value!r}, '
            f'got {params[param_name].get("default")!r}'
        )
