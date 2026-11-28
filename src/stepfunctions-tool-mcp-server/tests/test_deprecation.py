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

import os
import pytest
import subprocess
import sys
import warnings
from mcp.server.mcpserver import MCPServer
from unittest.mock import MagicMock, patch


with pytest.MonkeyPatch().context() as CTX:
    CTX.setattr('boto3.Session', MagicMock)
    from awslabs.stepfunctions_tool_mcp_server import server
    from awslabs.stepfunctions_tool_mcp_server.server import (
        DEPRECATION_NOTICE,
        INSTRUCTIONS,
        main,
    )


STATE_MACHINE_ARN = 'arn:aws:states:us-east-1:123456789012:stateMachine:order-workflow'
SCHEMA_ARN = 'arn:aws:schemas:us-east-1:123456789012:schema/my-registry/order-input'


def test_deprecation_notice_names_replacement_and_guide():
    """The notice names the package, the replacement, and the migration guide."""
    assert DEPRECATION_NOTICE.startswith('awslabs.stepfunctions-tool-mcp-server')
    assert 'will not receive further updates' in DEPRECATION_NOTICE
    assert 'https://github.com/aws/agent-toolkit-for-aws' in DEPRECATION_NOTICE
    assert (
        'https://github.com/awslabs/mcp/blob/main/docs/migration-stepfunctions-tool.md'
        in DEPRECATION_NOTICE
    )


@patch('awslabs.stepfunctions_tool_mcp_server.server.register_state_machines')
@patch('awslabs.stepfunctions_tool_mcp_server.server.mcp')
def test_main_emits_one_future_warning_before_run(mock_mcp, mock_register):
    """main() warns once, from the caller's line, before it registers tools and runs."""
    warnings_at_register = []

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        mock_register.side_effect = lambda: warnings_at_register.append(len(caught))
        main()

    future_warnings = [w for w in caught if issubclass(w.category, FutureWarning)]
    assert len(future_warnings) == 1
    assert DEPRECATION_NOTICE in str(future_warnings[0].message)
    assert future_warnings[0].filename == __file__
    assert warnings_at_register == [1]
    mock_register.assert_called_once_with()
    mock_mcp.run.assert_called_once_with()


def test_importing_server_does_not_warn():
    """The warning comes from main(), not from importing the module."""
    env = {k: v for k, v in os.environ.items() if k != 'AWS_PROFILE'}
    env['AWS_REGION'] = 'us-east-1'
    completed = subprocess.run(
        [
            sys.executable,
            '-W',
            'error::FutureWarning',
            '-c',
            'import awslabs.stepfunctions_tool_mcp_server.server',
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert completed.returncode == 0, completed.stderr
    assert DEPRECATION_NOTICE not in completed.stderr


def test_instructions_start_with_deprecation_notice():
    """The server instructions lead with the notice, then the original text."""
    instructions = server.mcp.instructions
    assert instructions is not None
    assert instructions.startswith(DEPRECATION_NOTICE)
    assert instructions == f'{DEPRECATION_NOTICE}\n\n{INSTRUCTIONS}'


@pytest.mark.parametrize(
    'describe_response, describe_error, schema_tag_key, expected_body',
    [
        (
            {
                'description': 'Processes an order',
                'definition': '{"Comment": "Order workflow", "StartAt": "A", "States": {}}',
            },
            None,
            None,
            'Processes an order\n\nWorkflow Description: Order workflow',
        ),
        (
            {'description': 'Processes an order', 'definition': '{}'},
            None,
            'input-schema-arn',
            'Processes an order\n\nInput Schema:\n{"type": "object"}',
        ),
        (
            None,
            Exception('AccessDenied'),
            None,
            'AWS Step Functions state machine: order-workflow',
        ),
    ],
    ids=['description-and-comment', 'with-input-schema', 'describe-fails'],
)
async def test_generated_tool_description_is_marked_deprecated(
    describe_response, describe_error, schema_tag_key, expected_body
):
    """A tool generated from a state machine carries the [DEPRECATED] prefix."""
    fresh_mcp = MCPServer('test-stepfunctions-tool-mcp-server')
    sfn_client = MagicMock()
    sfn_client.list_state_machines.return_value = {
        'stateMachines': [
            {'name': 'order-workflow', 'stateMachineArn': STATE_MACHINE_ARN, 'type': 'EXPRESS'}
        ]
    }
    sfn_client.describe_state_machine.return_value = describe_response
    sfn_client.describe_state_machine.side_effect = describe_error
    sfn_client.list_tags_for_resource.return_value = {
        'tags': [{'key': 'input-schema-arn', 'value': SCHEMA_ARN}]
    }
    schemas_client = MagicMock()
    schemas_client.describe_schema.return_value = {'Content': '{"type": "object"}'}

    with (
        patch.object(server, 'mcp', fresh_mcp),
        patch.object(server, 'sfn_client', sfn_client),
        patch.object(server, 'schemas_client', schemas_client),
        patch.object(server, 'STATE_MACHINE_PREFIX', ''),
        patch.object(server, 'STATE_MACHINE_LIST', []),
        patch.object(server, 'STATE_MACHINE_TAG_KEY', ''),
        patch.object(server, 'STATE_MACHINE_TAG_VALUE', ''),
        patch.object(server, 'STATE_MACHINE_INPUT_SCHEMA_ARN_TAG_KEY', schema_tag_key),
    ):
        server.register_state_machines()

    tools = await fresh_mcp.list_tools()
    assert [tool.name for tool in tools] == ['order_workflow']
    assert tools[0].description == f'[DEPRECATED] {expected_body}'
