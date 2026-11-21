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

"""Tests for the deprecation signals of the AWS AppSync MCP Server."""

import pytest
import subprocess
import sys
import warnings
from awslabs.aws_appsync_mcp_server.decorators import set_write_allowed
from awslabs.aws_appsync_mcp_server.server import DEPRECATION_NOTICE, main, mcp
from mcp.server.mcpserver import MCPServer
from unittest.mock import patch


EXPECTED_TOOLS = {
    'create_api',
    'create_api_cache',
    'create_api_key',
    'create_channel_namespace',
    'create_datasource',
    'create_domain_name',
    'create_function',
    'create_graphql_api',
    'create_resolver',
    'create_schema',
}


@pytest.fixture
def fresh_server():
    """Patch in a fresh MCPServer so main() registers its tools on a clean instance."""
    server = MCPServer('awslabs.aws-appsync-mcp-server')
    with (
        patch('awslabs.aws_appsync_mcp_server.server.mcp', server),
        patch.object(server, 'run') as mock_run,
    ):
        yield server, mock_run
    set_write_allowed(False)


def test_deprecation_notice_names_replacement_and_guide():
    """The notice names the package, the replacement, and the migration guide."""
    assert DEPRECATION_NOTICE.startswith('awslabs.aws-appsync-mcp-server is deprecated')
    assert 'https://github.com/aws/agent-toolkit-for-aws' in DEPRECATION_NOTICE
    assert (
        'https://github.com/awslabs/mcp/blob/main/docs/migration-appsync.md' in DEPRECATION_NOTICE
    )


@pytest.mark.parametrize('argv', [['server.py'], ['server.py', '--allow-write']])
def test_main_emits_one_future_warning_before_run(fresh_server, argv):
    """main() emits exactly one FutureWarning with the notice, before the server starts."""
    _, mock_run = fresh_server
    warnings_at_run = []
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        mock_run.side_effect = lambda *args, **kwargs: warnings_at_run.extend(caught)
        with patch('sys.argv', argv):
            main()
    future_warnings = [w for w in caught if issubclass(w.category, FutureWarning)]
    assert len(future_warnings) == 1
    assert DEPRECATION_NOTICE in str(future_warnings[0].message)
    assert future_warnings[0] in warnings_at_run
    mock_run.assert_called_once()


def test_import_does_not_warn():
    """Importing the server module emits no FutureWarning; only main() warns."""
    result = subprocess.run(
        [
            sys.executable,
            '-W',
            'error::FutureWarning',
            '-c',
            'import awslabs.aws_appsync_mcp_server.server',
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
    assert instructions.startswith(DEPRECATION_NOTICE + '\n\n')
    existing = instructions[len(DEPRECATION_NOTICE) :].lstrip()
    assert existing.startswith('AWS AppSync MCP Server provides tools')


async def test_every_tool_description_is_marked_deprecated(fresh_server):
    """Every tool main() registers has a description that starts with [DEPRECATED]."""
    server, _ = fresh_server
    with patch('sys.argv', ['server.py']), pytest.warns(FutureWarning):
        main()
    tools = await server.list_tools()
    assert len(tools) == len(EXPECTED_TOOLS)
    assert {tool.name for tool in tools} == EXPECTED_TOOLS
    for tool in tools:
        assert tool.description is not None
        assert tool.description.startswith('[DEPRECATED] '), tool.name
