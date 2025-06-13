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
"""Test for prompt registration with the server."""

import pytest
from awslabs.openapi_mcp_server.prompts import MCPPromptManager
from awslabs.openapi_mcp_server.prompts.generators.operation_prompts import create_operation_prompt
from awslabs.openapi_mcp_server.prompts.generators.workflow_prompts import create_workflow_prompt
from unittest.mock import MagicMock, patch


def test_operation_prompt_registration():
    """Test that operation prompts are registered correctly."""
    # Create a mock server with _prompt_manager.add_prompt_from_fn
    server = MagicMock()
    server._prompt_manager = MagicMock()
    server._prompt_manager.add_prompt = MagicMock()

    # Call create_operation_prompt
    result = create_operation_prompt(
        server=server,
        api_name='test-api',
        operation_id='testOperation',
        method='get',
        path='/test',
        summary='Test operation',
        description='',
        parameters=[],
        request_body=None,
        responses=None,
        security=None,
    )

    # Check that the prompt was registered
    assert result is True
    server._prompt_manager.add_prompt.assert_called_once()

    # Check the prompt data
    prompt = server._prompt_manager.add_prompt.call_args[0][0]
    name = prompt.name
    description = prompt.description

    assert name == 'testOperation'
    assert description == 'Test operation'

    # Test the function
    messages = prompt.fn()
    assert isinstance(messages, list)
    assert len(messages) > 0
    assert messages[0]['role'] == 'user'
    assert messages[0]['content']['type'] == 'text'
    assert 'testOperation' in messages[0]['content']['text']


def test_workflow_prompt_registration():
    """Test that workflow prompts are registered correctly."""
    # Create a mock server with _prompt_manager.add_prompt
    server = MagicMock()
    server._prompt_manager = MagicMock()
    server._prompt_manager.add_prompt = MagicMock()

    # Create a test workflow
    workflow = {
        'name': 'test_workflow',
        'type': 'list_get_update',
        'resource_type': 'test',
        'operations': {
            'list': {'operationId': 'listTests'},
            'get': {'operationId': 'getTest'},
            'update': {'operationId': 'updateTest'},
        },
    }

    # Call create_workflow_prompt
    result = create_workflow_prompt(server, workflow)

    # Check that the prompt was registered
    assert result is True
    server._prompt_manager.add_prompt.assert_called_once()

    # Check the prompt data
    prompt = server._prompt_manager.add_prompt.call_args[0][0]
    name = prompt.name
    description = prompt.description

    assert name == 'test_workflow'
    assert 'list_get_update' in description

    # Test the function
    messages = prompt.fn()
    assert isinstance(messages, list)
    assert len(messages) > 0
    assert messages[0]['role'] == 'user'
    assert messages[0]['content']['type'] == 'text'
    assert 'Test List Get Update Workflow' in messages[0]['content']['text']


def test_missing_add_prompt_method():
    """Test behavior when server doesn't have _prompt_manager."""

    # Create a server object without _prompt_manager
    class EmptyServer:
        pass

    server = EmptyServer()
    # No _prompt_manager attribute

    # Call create_operation_prompt
    result = create_operation_prompt(
        server=server,
        api_name='test-api',
        operation_id='testOperation',
        method='get',
        path='/test',
        summary='Test operation',
        description='',
        parameters=[],
        request_body=None,
        responses=None,
        security=None,
    )

    # Check that the function returned False
    assert result is False


@pytest.mark.asyncio
async def test_prompt_manager_generate_prompts():
    """Test the generate_prompts method."""
    # Create a mock server
    server = MagicMock()
    server._prompt_manager = MagicMock()
    server._prompt_manager.add_prompt = MagicMock()

    # Create a simple OpenAPI spec
    openapi_spec = {'paths': {'/test': {'get': {'operationId': 'getTest', 'summary': 'Get test'}}}}

    # Create a prompt manager
    prompt_manager = MCPPromptManager()

    # Mock the create_operation_prompt function to return True
    with patch(
        'awslabs.openapi_mcp_server.prompts.prompt_manager.create_operation_prompt',
        return_value=True,
    ):
        # Mock the identify_workflows function to return an empty list
        with patch(
            'awslabs.openapi_mcp_server.prompts.prompt_manager.identify_workflows', return_value=[]
        ):
            # Call generate_prompts
            result = await prompt_manager.generate_prompts(server, 'test-api', openapi_spec)

            # Check the result
            assert result['operation_prompts_generated'] is True
            assert result['workflow_prompts_generated'] is False
