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

"""Tool evaluation tests for the ServiceEvents MCP tools.

Two Bedrock-free sections (both ``@pytest.mark.eval``):

1. **Tool registry**:
   Validates that all core ServiceEvents tools are registered with proper
   schemas, descriptions, required parameters, and defaults.

2. **Predetermined eval**:
   Loads golden cases from ``eval_cases.json``, calls each tool as a plain
   Python function with mocked AWS dependencies, and validates the output
   against declarative assertions (key presence, value equality, type).

Neither section needs AWS credentials or an LLM. The LLM-based eval (tool
selection + output quality via Bedrock) lives in ``test_tool_eval_llm.py``,
which is intentionally kept out of the committed test suite.
"""

import inspect
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Tool registry: schema & registration checks
# ---------------------------------------------------------------------------

CORE_TOOLS = [
    'list_monitored_functions',
    'get_function_metrics',
    'search_functions_by_name',
    'get_endpoint_performance',
    'get_recent_incidents',
    'get_incident_root_cause',
    'get_service_health_overview',
    'find_deployment',
]


def _get_mcp():
    """Lazy-import the FastMCP instance to avoid collection-time ImportError."""
    from awslabs.cloudwatch_applicationsignals_mcp_server.server import mcp

    return mcp


def _get_tools_by_name() -> dict:
    """Return {name: Tool} for every registered tool."""
    return {t.name: t for t in _get_mcp()._tool_manager.list_tools()}


def _get_tool_params(tool) -> dict:
    """Return the 'properties' dict from a tool's JSON Schema parameters."""
    return tool.parameters.get('properties', {})


def _get_tool_required(tool) -> list:
    """Return the list of required parameter names for a tool."""
    return tool.parameters.get('required', [])


REQUIRED_PARAMS = [
    ('get_function_metrics', 'function_name'),
    ('search_functions_by_name', 'query'),
    ('get_incident_root_cause', 'snapshot_id'),
]

PARAM_DEFAULTS = [
    ('get_service_health_overview', 'detail', 'overview'),
    ('get_incident_root_cause', 'hours', 72),
    ('find_deployment', 'hours', 168),
]


@pytest.mark.eval
class TestToolRegistry:
    """Validate that all core tools are registered with adequate metadata."""

    def test_all_core_tools_registered(self):
        """Every core tool name resolves to a registered MCP tool."""
        registered = _get_tools_by_name()
        for name in CORE_TOOLS:
            assert name in registered, (
                f"Core tool '{name}' not registered. Registered: {sorted(registered.keys())}"
            )

    @pytest.mark.parametrize('tool_name', CORE_TOOLS)
    def test_tool_has_description(self, tool_name):
        """Each tool carries a non-trivial description for the LLM to read."""
        tool = _get_tools_by_name()[tool_name]
        assert len(tool.description) > 20, (
            f"Tool '{tool_name}' description too short ({len(tool.description)} chars)"
        )

    @pytest.mark.parametrize('tool_name', CORE_TOOLS)
    def test_tool_has_valid_schema(self, tool_name):
        """Each tool exposes a JSON Schema object for its parameters."""
        tool = _get_tools_by_name()[tool_name]
        schema = tool.parameters
        assert isinstance(schema, dict)
        assert schema.get('type') == 'object'

    def test_no_duplicate_tool_names(self):
        """No two registered tools share a name."""
        names = [t.name for t in _get_mcp()._tool_manager.list_tools()]
        assert len(names) == len(set(names)), (
            f'Duplicates: {[n for n in names if names.count(n) > 1]}'
        )

    @pytest.mark.parametrize('tool_name,param_name', REQUIRED_PARAMS)
    def test_required_param(self, tool_name, param_name):
        """Parameters that must be supplied are marked required in the schema."""
        tool = _get_tools_by_name()[tool_name]
        assert param_name in _get_tool_required(tool), (
            f"'{param_name}' must be required for {tool_name}"
        )

    @pytest.mark.parametrize('tool_name,param_name,default_value', PARAM_DEFAULTS)
    def test_param_default(self, tool_name, param_name, default_value):
        """Optional parameters expose the expected default value."""
        tool = _get_tools_by_name()[tool_name]
        params = _get_tool_params(tool)
        assert param_name in params, f"'{param_name}' not in {tool_name} params"
        assert params[param_name].get('default') == default_value, (
            f'{tool_name}.{param_name} default should be {default_value!r}, '
            f'got {params[param_name].get("default")!r}'
        )


# ---------------------------------------------------------------------------
# Predetermined eval: golden dataset
# ---------------------------------------------------------------------------

EVAL_CASES_PATH = Path(__file__).parent / 'eval_cases.json'
EVAL_CASES = json.loads(EVAL_CASES_PATH.read_text())

# Map tool name -> callable (imported from the service_events tools module)
_TOOL_FUNCS = {}


def _get_tool_funcs():
    """Lazy-load tool functions from the service_events tools module."""
    if not _TOOL_FUNCS:
        from awslabs.cloudwatch_applicationsignals_mcp_server.service_events import tools as t

        _TOOL_FUNCS['list_functions'] = t.list_functions
        _TOOL_FUNCS['get_function_details'] = t.get_function_details
        _TOOL_FUNCS['search_functions'] = t.search_functions
        _TOOL_FUNCS['get_endpoints'] = t.get_endpoints
        _TOOL_FUNCS['get_incidents'] = t.get_incidents
        _TOOL_FUNCS['get_incident_details'] = t.get_incident_details
        _TOOL_FUNCS['get_health_overview'] = t.get_health_overview
        _TOOL_FUNCS['find_deployment'] = t.find_deployment
    return _TOOL_FUNCS


# ---------------------------------------------------------------------------
# Mock factories
# ---------------------------------------------------------------------------


def _make_mock_function_metrics_patches():
    """Patch dict for function_metrics (CloudWatch Metrics V2 / PromQL) with empty data."""
    return {
        'fetch_function_records': MagicMock(return_value=[]),
        'search_function_names': MagicMock(return_value=[]),
    }


def _make_mock_cw_logs_patches():
    """Patch dict for cw_logs (CloudWatch Logs) query helpers with empty data."""
    return {
        'query_endpoint_summaries': MagicMock(return_value=[]),
        'query_incidents': MagicMock(return_value=[]),
        'query_incident_by_id': MagicMock(return_value=None),
        'query_deployments': MagicMock(return_value=[]),
    }


# ---------------------------------------------------------------------------
# Assertion helpers
# ---------------------------------------------------------------------------


def _check_assertions(output, assertions):
    """Validate ``output`` against a dict of declarative assertions."""
    if 'output_type' in assertions:
        expected_type = {'dict': dict, 'list': list, 'str': str, 'int': int}[
            assertions['output_type']
        ]
        assert isinstance(output, expected_type), (
            f'Expected type {assertions["output_type"]}, got {type(output).__name__}'
        )

    if 'output_contains_keys' in assertions:
        for key in assertions['output_contains_keys']:
            assert key in output, (
                f"Expected key '{key}' in output. Keys present: {list(output.keys())}"
            )

    if 'output_not_contains_keys' in assertions:
        for key in assertions['output_not_contains_keys']:
            assert key not in output, f"Key '{key}' should NOT be in output but was found"

    if 'output_value' in assertions:
        for key, expected in assertions['output_value'].items():
            assert key in output, f"Expected key '{key}' for value check, not found in output"
            assert output[key] == expected, (
                f"output['{key}'] = {output[key]!r}, expected {expected!r}"
            )

    if 'each_item_in_list' in assertions:
        spec = assertions['each_item_in_list']
        list_key = spec['list_key']
        must_have = spec['must_have_keys']
        items = output.get(list_key, [])
        for i, item in enumerate(items):
            for k in must_have:
                assert k in item, f"Item {i} in '{list_key}' missing key '{k}'"


# ---------------------------------------------------------------------------
# Predetermined eval tests
# ---------------------------------------------------------------------------


def _case_ids():
    return [c['id'] for c in EVAL_CASES]


@pytest.mark.eval
@pytest.mark.parametrize('case', EVAL_CASES, ids=_case_ids())
async def test_tool_eval(case):
    """Run a single predetermined eval case against the actual tool function."""
    tool_name = case['tool']
    params = case.get('params', {})
    assertions = case['assertions']

    funcs = _get_tool_funcs()
    assert tool_name in funcs, f'Unknown tool: {tool_name}'

    func = funcs[tool_name]

    fm_module = 'awslabs.cloudwatch_applicationsignals_mcp_server.service_events.function_metrics'
    cw_module = 'awslabs.cloudwatch_applicationsignals_mcp_server.service_events.cw_logs'

    with (
        patch.multiple(fm_module, **_make_mock_function_metrics_patches()),
        patch.multiple(cw_module, **_make_mock_cw_logs_patches()),
    ):
        if inspect.iscoroutinefunction(func):
            output = await func(**params)
        else:
            output = func(**params)

    _check_assertions(output, assertions)
