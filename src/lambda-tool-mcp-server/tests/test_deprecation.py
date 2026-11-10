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

"""Tests for the deprecation signals of the lambda-tool MCP Server."""

import pytest
import subprocess
import sys
import warnings
from mcp.server.mcpserver import MCPServer
from unittest.mock import MagicMock, patch


with pytest.MonkeyPatch().context() as CTX:
    CTX.setattr('boto3.Session', MagicMock)
    from awslabs.lambda_tool_mcp_server import server
    from awslabs.lambda_tool_mcp_server.server import DEPRECATION_NOTICE


SCHEMA_TAG_KEY = 'tool-input-schema-arn'
SCHEMA_ARN = 'arn:aws:schemas:us-east-1:123456789012:schema/registry/schema'

# One tool per function in the conftest mock_lambda_client fixture
EXPECTED_TOOLS = {
    'test_function_1',
    'test_function_2',
    'prefix_test_function_3',
    'other_function',
}


def test_deprecation_notice_names_replacement_and_guide():
    """The notice names the package, the replacement, and the migration guide."""
    assert DEPRECATION_NOTICE.startswith('awslabs.lambda-tool-mcp-server is deprecated')
    assert 'https://github.com/aws/agent-toolkit-for-aws' in DEPRECATION_NOTICE
    assert (
        'https://github.com/awslabs/mcp/blob/main/docs/migration-lambda-tool.md'
        in DEPRECATION_NOTICE
    )


def test_main_emits_one_future_warning_before_registering_tools():
    """main() emits one FutureWarning with the notice before it calls AWS."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')

        def future_warning_count():
            return len([w for w in caught if issubclass(w.category, FutureWarning)])

        warnings_seen_at_registration = []
        with (
            patch.object(
                server,
                'register_lambda_functions',
                side_effect=lambda: warnings_seen_at_registration.append(future_warning_count()),
            ),
            patch.object(server.mcp, 'run') as mock_run,
        ):
            server.main()

    future_warnings = [w for w in caught if issubclass(w.category, FutureWarning)]
    assert len(future_warnings) == 1
    assert DEPRECATION_NOTICE in str(future_warnings[0].message)
    assert warnings_seen_at_registration == [1]
    mock_run.assert_called_once()


def test_import_does_not_warn():
    """Importing the server module emits no FutureWarning; only main() warns."""
    result = subprocess.run(
        [
            sys.executable,
            '-W',
            'error::FutureWarning',
            '-c',
            'import boto3; from unittest.mock import MagicMock; boto3.Session = MagicMock; '
            'import awslabs.lambda_tool_mcp_server.server',
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_instructions_start_with_deprecation_notice():
    """The server instructions start with the notice, then a blank line."""
    instructions = server.mcp.instructions
    assert instructions is not None
    assert instructions.startswith(DEPRECATION_NOTICE + '\n\nUse AWS Lambda functions')


async def test_every_tool_description_is_marked_deprecated(mock_lambda_client):
    """Every tool main() registers has a description that starts with [DEPRECATED]."""
    lambda_client = mock_lambda_client
    # Give one function a schema tag so its tool takes the schema branch
    lambda_client.list_tags.side_effect = lambda Resource: (
        {'Tags': {SCHEMA_TAG_KEY: SCHEMA_ARN}} if Resource.endswith(':test-function-1') else {}
    )
    schemas_client = MagicMock()
    schemas_client.describe_schema.return_value = {'Content': '{"type": "object"}'}
    fresh_mcp = MCPServer('awslabs.lambda-tool-mcp-server')

    with (
        patch.object(server, 'mcp', fresh_mcp),
        patch.object(fresh_mcp, 'run') as mock_run,
        patch.object(server, 'lambda_client', lambda_client),
        patch.object(server, 'schemas_client', schemas_client),
        patch.object(server, 'FUNCTION_PREFIX', ''),
        patch.object(server, 'FUNCTION_LIST', []),
        patch.object(server, 'FUNCTION_TAG_KEY', ''),
        patch.object(server, 'FUNCTION_TAG_VALUE', ''),
        patch.object(server, 'FUNCTION_INPUT_SCHEMA_ARN_TAG_KEY', SCHEMA_TAG_KEY),
        pytest.warns(FutureWarning),
    ):
        server.main()

    mock_run.assert_called_once()
    tools = await fresh_mcp.list_tools()
    assert len(tools) == len(EXPECTED_TOOLS)
    assert {tool.name for tool in tools} == EXPECTED_TOOLS
    for tool in tools:
        assert tool.description is not None
        assert tool.description.startswith('[DEPRECATED] '), tool.name
    schema_tool = next(tool for tool in tools if tool.name == 'test_function_1')
    assert schema_tool.description is not None
    assert 'Input Schema:' in schema_tool.description
