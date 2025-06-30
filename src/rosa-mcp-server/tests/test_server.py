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

"""Tests for the ROSA MCP Server."""

import pytest
from awslabs.rosa_mcp_server.server import create_server


def test_server_creation():
    """Test that the server can be created."""
    mcp = create_server()
    assert mcp is not None
    assert mcp.name == 'awslabs.rosa-mcp-server'


@pytest.mark.asyncio
async def test_server_has_tools():
    """Test that the server has tools registered."""
    mcp = create_server()
    
    # Initialize handlers to register tools
    from awslabs.rosa_mcp_server.rosa_cluster_handler import ROSAClusterHandler
    from awslabs.rosa_mcp_server.rosa_auth_handler import ROSAAuthHandler
    
    ROSAClusterHandler(mcp, allow_write=False)
    ROSAAuthHandler(mcp, allow_write=False)
    
    # Check that tools are registered
    tools = await mcp.list_tools()
    assert len(tools) > 0
    
    # Check for specific tools
    tool_names = [tool.name for tool in tools]
    assert 'list_rosa_clusters' in tool_names
    assert 'create_rosa_cluster' in tool_names
    assert 'setup_rosa_account_roles' in tool_names