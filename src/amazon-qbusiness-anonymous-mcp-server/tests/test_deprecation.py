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

"""Tests for the deprecation signals of the amazon-qbusiness-anonymous MCP Server."""

import subprocess
import sys
import warnings
from awslabs.amazon_qbusiness_anonymous_mcp_server.server import DEPRECATION_NOTICE, main, mcp
from unittest.mock import patch


EXPECTED_TOOLS = {'QBusinessQueryTool'}


def test_deprecation_notice_names_replacement_and_guide():
    """The notice names the package, the replacement, and the migration guide."""
    assert DEPRECATION_NOTICE.startswith(
        'awslabs.amazon-qbusiness-anonymous-mcp-server is deprecated'
    )
    assert 'https://github.com/aws/agent-toolkit-for-aws' in DEPRECATION_NOTICE
    assert (
        'https://github.com/awslabs/mcp/blob/main/docs/migration-qbusiness-anonymous.md'
        in DEPRECATION_NOTICE
    )


@patch('awslabs.amazon_qbusiness_anonymous_mcp_server.server.mcp.run')
def test_main_emits_one_future_warning(mock_run):
    """main() emits exactly one FutureWarning carrying the deprecation notice."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        main()
    future_warnings = [w for w in caught if issubclass(w.category, FutureWarning)]
    assert len(future_warnings) == 1
    assert DEPRECATION_NOTICE in str(future_warnings[0].message)
    mock_run.assert_called_once()


def test_import_does_not_warn():
    """Importing the server module emits no FutureWarning; only main() warns."""
    result = subprocess.run(
        [
            sys.executable,
            '-W',
            'error::FutureWarning',
            '-c',
            'import awslabs.amazon_qbusiness_anonymous_mcp_server.server',
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_instructions_start_with_deprecation_notice():
    """The server instructions start with the notice, then a blank line."""
    instructions = mcp.instructions
    assert instructions is not None
    assert instructions.startswith(DEPRECATION_NOTICE + '\n\nUse this MCP server')


async def test_every_tool_description_is_marked_deprecated():
    """Every registered tool's description starts with [DEPRECATED]."""
    tools = await mcp.list_tools()
    assert len(tools) == len(EXPECTED_TOOLS)
    assert {tool.name for tool in tools} == EXPECTED_TOOLS
    for tool in tools:
        assert tool.description is not None
        assert tool.description.startswith('[DEPRECATED] '), tool.name
