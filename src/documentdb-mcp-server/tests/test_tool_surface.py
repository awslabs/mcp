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
"""Regression guard for the MCP tool surface.

The server connects only to the cluster the operator configures at startup.
These tests fail if any registered tool regains a parameter that could steer the
connection destination (the SSRF fixed in GHSA-v7wf-w8xc-2x3v), or if a tool is
added without updating EXPECTED_TOOLS, which forces a review of its parameters.
"""

from awslabs.documentdb_mcp_server.server import mcp
from mcp.server.mcpserver import MCPServer


# Parameter names that could influence where the client connects.
FORBIDDEN_PARAMS = {
    'connection_string',
    'connection_id',
    'uri',
    'host',
    'hostname',
    'port',
    'url',
    'endpoint',
    'tls',
    'tlscafile',
    'ssl',
}

EXPECTED_TOOLS = {
    'find',
    'aggregate',
    'insert',
    'update',
    'delete',
    'listDatabases',
    'createCollection',
    'listCollections',
    'dropCollection',
    'countDocuments',
    'getDatabaseStats',
    'getCollectionStats',
    'analyzeSchema',
    'explainOperation',
}


def destination_params(tools):
    """Return (tool, parameter) pairs whose parameter name is in FORBIDDEN_PARAMS."""
    return {
        (tool.name, param)
        for tool in tools
        for param in tool.input_schema.get('properties', {})
        if param.lower() in FORBIDDEN_PARAMS
    }


class TestToolSurface:
    """Tests for the registered tool surface."""

    async def test_no_connect_or_disconnect_tools(self):
        """The removed connect/disconnect tools must not come back."""
        names = {tool.name.lower() for tool in await mcp.list_tools()}
        assert names.isdisjoint({'connect', 'disconnect'})

    async def test_no_tool_can_influence_the_connection_destination(self):
        """No registered tool may take a destination-like parameter."""
        assert destination_params(await mcp.list_tools()) == set()

    async def test_tool_set_is_exactly_the_reviewed_set(self):
        """Adding or renaming a tool must update EXPECTED_TOOLS (and get reviewed)."""
        assert {tool.name for tool in await mcp.list_tools()} == EXPECTED_TOOLS

    async def test_guard_detects_a_reintroduced_destination_parameter(self):
        """Negative control: the guard flags a tool that takes a host parameter."""
        probe = MCPServer('probe')

        async def find(database: str, collection: str, host: str) -> list:
            return []

        probe.tool(name='find')(find)

        assert destination_params(await probe.list_tools()) == {('find', 'host')}
