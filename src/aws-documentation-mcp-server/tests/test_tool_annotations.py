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
"""Tests that every tool declares MCP tool annotations."""

import pytest
from awslabs.aws_documentation_mcp_server import server_aws, server_aws_cn


@pytest.mark.asyncio
@pytest.mark.parametrize('server', [server_aws, server_aws_cn], ids=['aws', 'aws_cn'])
async def test_every_tool_is_annotated_read_only(server):
    """Every tool only reads public documentation, so each must say so to clients."""
    tools = await server.mcp.list_tools()
    assert tools
    for tool in tools:
        assert tool.annotations is not None, f'{tool.name} has no annotations'
        assert tool.annotations.title, f'{tool.name} has no title'
        assert tool.annotations.read_only_hint is True, f'{tool.name} is not marked read-only'
        assert tool.annotations.open_world_hint is True, f'{tool.name} is not marked open-world'
