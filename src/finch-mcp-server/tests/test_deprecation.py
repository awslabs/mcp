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

"""Tests for the deprecation signals of the Finch MCP server."""

import subprocess
import sys
import warnings
from awslabs.finch_mcp_server.server import DEPRECATION_NOTICE, main, mcp
from unittest.mock import patch


KNOWN_TOOL_COUNT = 3


@patch('awslabs.finch_mcp_server.server.logger')
@patch('awslabs.finch_mcp_server.server.mcp')
def test_main_emits_one_future_warning(mock_mcp, mock_logger):
    """main() warns once, from the caller's line, before the server runs."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        main()

    future_warnings = [w for w in caught if issubclass(w.category, FutureWarning)]
    assert len(future_warnings) == 1
    assert DEPRECATION_NOTICE in str(future_warnings[0].message)
    assert future_warnings[0].filename == __file__
    mock_mcp.run.assert_called_once_with(transport='stdio')


def test_import_does_not_warn():
    """Importing the server module emits no FutureWarning."""
    result = subprocess.run(
        [
            sys.executable,
            '-W',
            'error::FutureWarning',
            '-c',
            'import awslabs.finch_mcp_server.server',
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_instructions_start_with_notice():
    """The server instructions start with the deprecation notice."""
    assert mcp.instructions is not None
    assert mcp.instructions.startswith(DEPRECATION_NOTICE)


async def test_every_tool_description_is_marked_deprecated():
    """Every registered tool's description starts with [DEPRECATED]."""
    tools = await mcp.list_tools()

    assert len(tools) == KNOWN_TOOL_COUNT
    for tool in tools:
        assert tool.description is not None
        assert tool.description.startswith('[DEPRECATED]'), tool.name
