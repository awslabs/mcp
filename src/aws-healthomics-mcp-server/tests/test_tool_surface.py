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

"""Tool-surface preservation verification test.

Phase 1 of the remote-transport-multi-tenant feature is purely additive: it must not
alter any registered MCP tool's name, parameters, parameter types, or parameter
defaults. This module enumerates the live tool surface of the FastMCP server and
asserts it is byte-for-byte identical to a recorded baseline captured before Phase 1
work began.

The baseline lives at ``tests/fixtures/tool_surface_baseline.json`` and is committed to
the repository. Any change that adds, removes, or alters a tool signature will cause
this test to fail, which is the intended guard.

Validates: Requirements Behavior preservation in single-tenant mode (identical tool
names, parameter names, parameter types, and parameter defaults after Phase 1).
"""

import json
import os
from awslabs.aws_healthomics_mcp_server.server import mcp


BASELINE_PATH = os.path.join(os.path.dirname(__file__), 'fixtures', 'tool_surface_baseline.json')


def _normalize_type(schema: dict) -> object:
    """Return a deterministic JSON-schema type descriptor for a parameter.

    Handles both the simple ``type`` form and the ``anyOf`` form that Pydantic emits
    for optional parameters. Nested type lists are sorted so the descriptor is
    independent of declaration order.
    """
    if 'type' in schema:
        return schema['type']
    if 'anyOf' in schema:
        types = []
        for sub in schema['anyOf']:
            if 'type' in sub:
                types.append(sub['type'])
            else:
                # Preserve a stable, comparable marker for non-typed branches.
                types.append(json.dumps(sub, sort_keys=True))
        return {'anyOf': sorted(types)}
    return 'unknown'


def extract_tool_surface(tools) -> dict:
    """Build a deterministic mapping of tool name -> parameter surface.

    For each tool we capture, per parameter: the JSON-schema type, whether it is
    required, and its default value (when one is declared). Tool names and parameter
    names are emitted in sorted order so the snapshot is stable across runs.
    """
    surface: dict = {}
    for tool in tools:
        schema = tool.inputSchema or {}
        properties = schema.get('properties', {})
        required = set(schema.get('required', []))
        params: dict = {}
        for param_name in sorted(properties):
            param_schema = properties[param_name]
            entry: dict = {
                'type': _normalize_type(param_schema),
                'required': param_name in required,
            }
            if 'default' in param_schema:
                entry['default'] = param_schema['default']
            params[param_name] = entry
        surface[tool.name] = params
    return dict(sorted(surface.items()))


async def _current_surface() -> dict:
    tools = await mcp.list_tools()
    return extract_tool_surface(tools)


async def test_tool_surface_matches_baseline():
    """The live tool surface must equal the recorded Phase 1 baseline.

    Validates: Requirements Behavior preservation in single-tenant mode.
    """
    with open(BASELINE_PATH, encoding='utf-8') as handle:
        baseline = json.load(handle)

    current = await _current_surface()

    # Compare tool name sets first for a clearer failure message.
    assert set(current.keys()) == set(baseline.keys()), (
        'Registered tool names changed.\n'
        f'Added: {sorted(set(current) - set(baseline))}\n'
        f'Removed: {sorted(set(baseline) - set(current))}'
    )

    # Compare each tool's parameter surface (names, types, defaults, required).
    for tool_name in sorted(baseline):
        assert current[tool_name] == baseline[tool_name], (
            f"Parameter surface for tool '{tool_name}' changed.\n"
            f'Baseline: {json.dumps(baseline[tool_name], sort_keys=True)}\n'
            f'Current:  {json.dumps(current[tool_name], sort_keys=True)}'
        )

    # Full equality as a final guard.
    assert current == baseline
