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

import pytest
import subprocess
import sys
import warnings
from awslabs.aws_serverless_mcp_server import server
from awslabs.aws_serverless_mcp_server.server import DEPRECATION_NOTICE, main
from mcp.server.mcpserver import MCPServer
from unittest import mock


EXPECTED_TOOLS = {
    'webapp_deployment_help',
    'deploy_serverless_app_help',
    'get_iac_guidance',
    'get_lambda_event_schemas',
    'get_lambda_guidance',
    'get_serverless_templates',
    'sam_build',
    'sam_deploy',
    'sam_init',
    'sam_local_invoke',
    'sam_logs',
    'list_registries',
    'search_schema',
    'describe_schema',
    'get_metrics',
    'configure_domain',
    'deploy_webapp',
    'update_webapp_frontend',
    'esm_guidance',
    'esm_kafka_troubleshoot',
    'esm_optimize',
    'secure_esm_msk_policy',
    'secure_esm_sqs_policy',
    'secure_esm_kinesis_policy',
    'secure_esm_dynamodb_policy',
}


def test_deprecation_notice_names_replacement_and_guide():
    """The notice names the package, the replacements, and the migration guide."""
    assert DEPRECATION_NOTICE.startswith('awslabs.aws-serverless-mcp-server')
    assert 'https://github.com/aws/agent-toolkit-for-aws' in DEPRECATION_NOTICE
    assert 'SAM CLI' in DEPRECATION_NOTICE
    assert (
        'https://github.com/awslabs/mcp/blob/main/docs/migration-aws-serverless.md'
        in DEPRECATION_NOTICE
    )


def _run_main(argv, target_mcp):
    """Run main() against target_mcp with argv, recording warnings seen before mcp.run()."""
    warnings_at_run = []

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')

        def record_run(*args, **kwargs):
            warnings_at_run.append(len(caught))

        with (
            mock.patch('sys.argv', ['awslabs.aws-serverless-mcp-server', *argv]),
            mock.patch.object(server, 'mcp', target_mcp),
            mock.patch.object(target_mcp, 'run', side_effect=record_run) as mock_run,
            mock.patch.object(server, 'logger'),
            mock.patch.object(server.os, 'makedirs'),
            mock.patch.dict(server.os.environ),
        ):
            result = main()

    return result, caught, warnings_at_run, mock_run


@pytest.mark.parametrize('argv', [[], ['--allow-write', '--allow-sensitive-data-access']])
def test_main_emits_one_future_warning_before_run(argv):
    """main() warns once with the notice, from the caller's line, before it starts the server."""
    result, caught, warnings_at_run, mock_run = _run_main(argv, MCPServer('test'))

    future_warnings = [w for w in caught if issubclass(w.category, FutureWarning)]
    assert result == 0
    assert len(future_warnings) == 1
    assert DEPRECATION_NOTICE in str(future_warnings[0].message)
    assert future_warnings[0].filename == __file__
    mock_run.assert_called_once()
    assert warnings_at_run == [len(caught)]


def test_importing_server_does_not_warn():
    """The warning comes from main(), not from importing the module."""
    completed = subprocess.run(
        [
            sys.executable,
            '-W',
            'error::FutureWarning',
            '-c',
            'import awslabs.aws_serverless_mcp_server.server',
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
    assert instructions.startswith(f'{DEPRECATION_NOTICE}\n\n')
    assert 'AWS Serverless MCP' in instructions[len(DEPRECATION_NOTICE) :]


@pytest.mark.parametrize('argv', [[], ['--allow-write', '--allow-sensitive-data-access']])
async def test_every_tool_description_is_marked_deprecated(argv):
    """Every tool main() registers carries the [DEPRECATED] prefix."""
    target = MCPServer('test')
    _run_main(argv, target)

    tools = await target.list_tools()

    assert {tool.name for tool in tools} == EXPECTED_TOOLS
    assert len(tools) == len(EXPECTED_TOOLS)
    for tool in tools:
        assert tool.description is not None
        assert tool.description.startswith('[DEPRECATED] '), tool.name
