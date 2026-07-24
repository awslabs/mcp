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

"""Tests that the MCP server initializes and registers the expected tools."""

import importlib
import pytest
from awslabs.amazon_connect_mcp_server import server
from unittest.mock import patch


@pytest.mark.asyncio
async def test_expected_tools_registered():
    """All discovery, realtime, and historical tools are registered."""
    tools = await server.mcp.list_tools()
    tool_names = {tool.name for tool in tools}

    expected = {
        'list_connect_instances',
        'list_queues',
        'list_agents',
        'list_routing_profiles',
        'get_current_metric_data',
        'get_current_agent_status',
        'get_historical_metric_data',
    }
    assert expected.issubset(tool_names)


def test_main_runs_server():
    """main() starts the FastMCP server via mcp.run()."""
    with patch.object(server.mcp, 'run') as run:
        server.main()
    run.assert_called_once()


def test_registration_failure_is_raised():
    """A failure while registering tools at import time is logged and re-raised."""
    with patch(
        'awslabs.amazon_connect_mcp_server.connect_admin.tools.ConnectAdminTools.register',
        side_effect=RuntimeError('boom'),
    ):
        with pytest.raises(RuntimeError):
            importlib.reload(server)

    # Reload once more without the patch so the module is left in a clean state
    # for any subsequent tests that import it.
    importlib.reload(server)
