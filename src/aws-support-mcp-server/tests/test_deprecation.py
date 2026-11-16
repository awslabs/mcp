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
"""Tests for the deprecation signals of the AWS Support MCP Server."""

import pytest
import sys
import warnings
from awslabs.aws_support_mcp_server.server import DEPRECATION_NOTICE, main, mcp
from unittest.mock import patch


EXPECTED_TOOL_COUNT = 11


@patch('awslabs.aws_support_mcp_server.server.logger')
def test_main_emits_one_future_warning(mock_logger, monkeypatch: pytest.MonkeyPatch):
    """main() warns once with the deprecation notice before it starts the server."""
    monkeypatch.setattr(sys, 'argv', ['server.py'])
    with patch('awslabs.aws_support_mcp_server.server.mcp.run') as mock_run:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            main()

    future_warnings = [w for w in caught if issubclass(w.category, FutureWarning)]
    assert len(future_warnings) == 1
    assert DEPRECATION_NOTICE in str(future_warnings[0].message)
    mock_run.assert_called_once_with(transport='stdio')


def test_instructions_start_with_deprecation_notice():
    """The server instructions open with the deprecation notice and a blank line."""
    assert mcp.instructions is not None
    assert mcp.instructions.startswith(DEPRECATION_NOTICE + '\n\n')


async def test_every_tool_description_is_marked_deprecated():
    """Every registered tool has a description that starts with [DEPRECATED]."""
    tools = await mcp.list_tools()

    assert len(tools) == EXPECTED_TOOL_COUNT
    unmarked = [t.name for t in tools if not (t.description or '').startswith('[DEPRECATED]')]
    assert unmarked == []
