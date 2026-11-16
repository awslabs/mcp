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

"""Tests for the deprecation signals of the amazon-qindex MCP Server."""

import pytest
import subprocess
import sys
import warnings
from awslabs.amazon_qindex_mcp_server.server import DEPRECATION_NOTICE, main, mcp
from unittest.mock import patch


EXPECTED_TOOL_COUNT = 4


class TestDeprecation:
    """Tests for the deprecation notice, warning, and tool descriptions."""

    @patch('awslabs.amazon_qindex_mcp_server.server.mcp.run')
    def test_main_emits_one_future_warning(self, mock_run):
        """main() emits exactly one FutureWarning that carries the notice."""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            main()

        future_warnings = [w for w in caught if issubclass(w.category, FutureWarning)]
        assert len(future_warnings) == 1
        assert DEPRECATION_NOTICE in str(future_warnings[0].message)
        mock_run.assert_called_once_with()

    def test_instructions_start_with_notice(self):
        """The server instructions start with the deprecation notice."""
        assert mcp.instructions is not None
        assert mcp.instructions.startswith(DEPRECATION_NOTICE + '\n\n')

    @pytest.mark.asyncio
    async def test_every_tool_description_is_marked_deprecated(self):
        """Every registered tool description starts with [DEPRECATED]."""
        tools = await mcp.list_tools()

        assert len(tools) == EXPECTED_TOOL_COUNT
        for tool in tools:
            assert (tool.description or '').startswith('[DEPRECATED] '), tool.name

    def test_server_starts_without_type_stubs(self):
        """The server module imports when mypy_boto3_qbusiness is not installed.

        The stubs are a dev dependency, so a PyPI install has to start without them
        for users to see the deprecation warning.
        """
        code = (
            'import sys\n'
            "sys.modules['mypy_boto3_qbusiness'] = None\n"
            'import awslabs.amazon_qindex_mcp_server.server\n'
        )
        result = subprocess.run(
            [sys.executable, '-c', code], capture_output=True, text=True, check=False
        )
        assert result.returncode == 0, result.stderr
