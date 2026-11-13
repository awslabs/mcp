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

"""Tests for the deprecation signals the server sends at startup and to clients."""

import subprocess
import sys
import warnings
from unittest import mock

import pytest

from awslabs.well_architected_security_mcp_server import server
from awslabs.well_architected_security_mcp_server.consts import INSTRUCTIONS
from awslabs.well_architected_security_mcp_server.server import DEPRECATION_NOTICE, main

EXPECTED_TOOLS = {
    "CheckSecurityServices",
    "GetSecurityFindings",
    "GetStoredSecurityContext",
    "CheckStorageEncryption",
    "ListServicesInRegion",
    "CheckNetworkSecurity",
}


def test_deprecation_notice_names_replacement_and_guide():
    """The notice names the package, the replacement, and the migration guide."""
    assert DEPRECATION_NOTICE.startswith("awslabs.well-architected-security-mcp-server")
    assert "https://github.com/aws/agent-toolkit-for-aws" in DEPRECATION_NOTICE
    assert (
        "https://github.com/awslabs/mcp/blob/main/docs/migration-well-architected-security.md"
        in DEPRECATION_NOTICE
    )


@pytest.mark.parametrize("argv", [[], ["--sse", "--port", "9999"]])
def test_main_emits_one_future_warning_before_run(argv):
    """main() warns once with the notice, before it starts the server."""
    warnings_at_run = []

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")

        def record_run(*args, **kwargs):
            warnings_at_run.append(len(caught))

        with (
            mock.patch("sys.argv", ["awslabs.well-architected-security-mcp-server", *argv]),
            mock.patch.object(server.mcp, "run", side_effect=record_run) as mock_run,
        ):
            main()

    future_warnings = [w for w in caught if issubclass(w.category, FutureWarning)]
    assert len(future_warnings) == 1
    assert DEPRECATION_NOTICE in str(future_warnings[0].message)
    mock_run.assert_called_once()
    assert warnings_at_run == [1]


def test_importing_server_does_not_warn():
    """The warning comes from main(), not from importing the module."""
    completed = subprocess.run(
        [
            sys.executable,
            "-W",
            "always",
            "-c",
            "import awslabs.well_architected_security_mcp_server.server",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert DEPRECATION_NOTICE not in completed.stderr


def test_instructions_start_with_deprecation_notice():
    """The server instructions lead with the notice, then the original text."""
    instructions = server.mcp.instructions
    assert instructions is not None
    assert instructions.startswith(DEPRECATION_NOTICE)
    assert instructions == f"{DEPRECATION_NOTICE}\n\n{INSTRUCTIONS}"


@pytest.mark.asyncio
async def test_every_tool_description_is_marked_deprecated():
    """Every registered tool carries the [DEPRECATED] prefix."""
    tools = await server.mcp.list_tools()

    assert {tool.name for tool in tools} == EXPECTED_TOOLS
    assert len(tools) == len(EXPECTED_TOOLS)
    for tool in tools:
        assert tool.description is not None
        assert tool.description.startswith("[DEPRECATED] "), tool.name
