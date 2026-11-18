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
"""Tests for the deprecation signals of the SageMaker AI MCP Server."""

import pytest
import re
import warnings
from awslabs.sagemaker_ai_mcp_server.server import DEPRECATION_NOTICE, main
from mcp.server.mcpserver import MCPServer
from unittest.mock import patch


EXPECTED_TOOLS = {
    'describe_hp_cluster',
    'manage_hyperpod_cluster_nodes',
    'manage_hyperpod_stacks',
    'update_hp_cluster',
}


def run_main() -> MCPServer:
    """Build the server through main() without starting it."""
    with (
        patch('sys.argv', ['awslabs.sagemaker-ai-mcp-server']),
        patch('awslabs.sagemaker_ai_mcp_server.server.logger'),
        patch.object(MCPServer, 'run') as mock_run,
    ):
        server = main()
    mock_run.assert_called_once_with()
    return server


def test_main_emits_one_future_warning():
    """main() warns once at startup with the deprecation notice."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        run_main()

    future_warnings = [w for w in caught if issubclass(w.category, FutureWarning)]
    assert len(future_warnings) == 1
    assert DEPRECATION_NOTICE in str(future_warnings[0].message)


def test_instructions_start_with_deprecation_notice():
    """The server instructions open with the deprecation notice and a blank line."""
    with pytest.warns(FutureWarning, match=re.escape(DEPRECATION_NOTICE)):
        server = run_main()

    assert server.instructions is not None
    assert server.instructions.startswith(DEPRECATION_NOTICE + '\n\n')


async def test_every_tool_description_is_marked_deprecated():
    """Every registered tool description starts with [DEPRECATED]."""
    with pytest.warns(FutureWarning, match=re.escape(DEPRECATION_NOTICE)):
        server = run_main()

    tools = await server.list_tools()

    assert {tool.name for tool in tools} == EXPECTED_TOOLS
    assert len(tools) == len(EXPECTED_TOOLS)
    for tool in tools:
        assert tool.description is not None
        assert tool.description.startswith('[DEPRECATED] '), tool.name
