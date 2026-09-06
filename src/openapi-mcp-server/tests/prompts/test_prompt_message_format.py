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
"""Critical tests for prompt handler Message format compatibility with FastMCP 3.x.

These tests verify that prompt handlers return proper fastmcp.Message objects
that pass through FastMCP's convert_result pipeline without TypeError.
This is the exact bug scenario: returning list[dict] causes TypeError in
convert_result because dict is not Message or str.
"""

import pytest
from awslabs.openapi_mcp_server.prompts.generators.operation_prompts import (
    create_operation_prompt,
)
from awslabs.openapi_mcp_server.prompts.generators.workflow_prompts import (
    create_workflow_prompt,
)
from fastmcp.prompts import Message
from fastmcp.prompts.base import PromptResult
from mcp.types import EmbeddedResource
from unittest.mock import MagicMock


@pytest.fixture
def mock_server():
    """Create a mock MCP server with add_prompt capability."""
    server = MagicMock()
    server.add_prompt = MagicMock()
    return server


SIMPLE_PATHS = {
    '/pets': {
        'get': {
            'operationId': 'listPets',
            'summary': 'List all pets',
            'parameters': [],
            'responses': {'200': {'description': 'OK'}},
        },
    },
}


class TestOperationPromptMessageFormat:
    """Test that operation prompt handlers return valid Message objects."""

    def test_handler_returns_message_objects_not_dicts(self, mock_server):
        """CRITICAL: Handlers must return list[Message], not list[dict]."""
        create_operation_prompt(
            server=mock_server,
            api_name='test',
            operation_id='listPets',
            method='get',
            path='/pets',
            summary='List pets',
            description='',
            parameters=[],
            request_body=None,
            responses={'200': {'description': 'OK'}},
            security=[],
            paths=SIMPLE_PATHS,
        )

        prompt = mock_server.add_prompt.call_args[0][0]
        messages = prompt.fn()

        assert isinstance(messages, list)
        for msg in messages:
            assert isinstance(msg, Message), (
                f'Handler must return Message objects, got {type(msg).__name__}. '
                f'Returning dicts causes TypeError in FastMCP 3.x convert_result.'
            )

    def test_handler_message_has_correct_structure(self, mock_server):
        """Message objects must have role and content attributes."""
        create_operation_prompt(
            server=mock_server,
            api_name='test',
            operation_id='listPets',
            method='get',
            path='/pets',
            summary='List pets',
            description='',
            parameters=[],
            request_body=None,
            responses={'200': {'description': 'OK'}},
            security=[],
            paths=SIMPLE_PATHS,
        )

        prompt = mock_server.add_prompt.call_args[0][0]
        messages = prompt.fn()

        msg = messages[0]
        assert msg.role == 'user'
        assert hasattr(msg.content, 'type')
        assert msg.content.type == 'text'
        assert hasattr(msg.content, 'text')
        assert 'listPets' in msg.content.text

    def test_handler_passes_convert_result(self, mock_server):
        """CRITICAL: Handler output must survive FastMCP's convert_result pipeline."""
        create_operation_prompt(
            server=mock_server,
            api_name='test',
            operation_id='listPets',
            method='get',
            path='/pets',
            summary='List pets',
            description='',
            parameters=[],
            request_body=None,
            responses={'200': {'description': 'OK'}},
            security=[],
            paths=SIMPLE_PATHS,
        )

        prompt = mock_server.add_prompt.call_args[0][0]
        messages = prompt.fn()

        # This is exactly what FastMCP does internally — if it raises TypeError,
        # the prompt is broken for any MCP client
        result = prompt.convert_result(messages)
        assert isinstance(result, PromptResult)
        assert len(result.messages) >= 1
        assert result.messages[0].role == 'user'

    def test_resource_operation_returns_embedded_resource(self, mock_server):
        """Resource operations must use EmbeddedResource, not dict."""
        from awslabs.openapi_mcp_server.prompts.generators import operation_prompts

        original = operation_prompts.determine_operation_type
        operation_prompts.determine_operation_type = lambda *a, **kw: 'resource'
        try:
            create_operation_prompt(
                server=mock_server,
                api_name='petstore',
                operation_id='getPet',
                method='get',
                path='/pet/{petId}',
                summary='Get pet by ID',
                description='',
                parameters=[{'name': 'petId', 'in': 'path', 'required': True}],
                request_body=None,
                responses={
                    '200': {
                        'description': 'OK',
                        'content': {'application/json': {'schema': {'type': 'object'}}},
                    }
                },
                security=[],
                paths={'/pet/{petId}': {'get': {'operationId': 'getPet'}}},
            )

            prompt = mock_server.add_prompt.call_args[0][0]
            messages = prompt.fn('123')

            # Should have 2 messages: text + resource
            assert len(messages) == 2

            # Second message must use EmbeddedResource
            resource_msg = messages[1]
            assert isinstance(resource_msg, Message)
            assert resource_msg.content.type == 'resource'
            assert isinstance(resource_msg.content, EmbeddedResource)
            assert resource_msg.content.resource.mimeType == 'application/json'

        finally:
            operation_prompts.determine_operation_type = original

    def test_resource_operation_passes_convert_result(self, mock_server):
        """CRITICAL: Resource messages must also survive convert_result."""
        from awslabs.openapi_mcp_server.prompts.generators import operation_prompts

        original = operation_prompts.determine_operation_type
        operation_prompts.determine_operation_type = lambda *a, **kw: 'resource'
        try:
            create_operation_prompt(
                server=mock_server,
                api_name='petstore',
                operation_id='getPet',
                method='get',
                path='/pet/{petId}',
                summary='Get pet by ID',
                description='',
                parameters=[{'name': 'petId', 'in': 'path', 'required': True}],
                request_body=None,
                responses={
                    '200': {
                        'description': 'OK',
                        'content': {'application/json': {'schema': {'type': 'object'}}},
                    }
                },
                security=[],
                paths={'/pet/{petId}': {'get': {'operationId': 'getPet'}}},
            )

            prompt = mock_server.add_prompt.call_args[0][0]
            messages = prompt.fn('123')

            # This must NOT raise TypeError
            result = prompt.convert_result(messages)
            assert isinstance(result, PromptResult)
            assert len(result.messages) == 2

        finally:
            operation_prompts.determine_operation_type = original

    @pytest.mark.asyncio
    async def test_full_render_pipeline(self, mock_server):
        """CRITICAL: End-to-end render simulates what an MCP client triggers."""
        create_operation_prompt(
            server=mock_server,
            api_name='test',
            operation_id='listPets',
            method='get',
            path='/pets',
            summary='List pets',
            description='',
            parameters=[],
            request_body=None,
            responses={'200': {'description': 'OK'}},
            security=[],
            paths=SIMPLE_PATHS,
        )

        prompt = mock_server.add_prompt.call_args[0][0]

        # This is the exact call path an MCP client triggers via prompts/get
        result = await prompt.render(arguments={})
        assert isinstance(result, PromptResult)
        assert len(result.messages) >= 1


class TestWorkflowPromptMessageFormat:
    """Test that workflow prompt handlers return valid Message objects."""

    def test_workflow_handler_returns_message_objects(self, mock_server):
        """Workflow handlers must also return list[Message]."""
        workflow = {
            'name': 'test_workflow',
            'type': 'list_get_update',
            'resource_type': 'pets',
            'description': 'Test workflow',
            'operations': {
                'list': {'operationId': 'listPets'},
                'get': {'operationId': 'getPet'},
                'update': {'operationId': 'updatePet'},
            },
        }

        create_workflow_prompt(mock_server, workflow)
        prompt = mock_server.add_prompt.call_args[0][0]
        messages = prompt.fn()

        assert isinstance(messages, list)
        for msg in messages:
            assert isinstance(msg, Message)

    def test_workflow_handler_passes_convert_result(self, mock_server):
        """CRITICAL: Workflow output must survive convert_result."""
        workflow = {
            'name': 'test_workflow',
            'type': 'list_get_update',
            'resource_type': 'pets',
            'description': 'Test workflow',
            'operations': {
                'list': {'operationId': 'listPets'},
                'get': {'operationId': 'getPet'},
                'update': {'operationId': 'updatePet'},
            },
        }

        create_workflow_prompt(mock_server, workflow)
        prompt = mock_server.add_prompt.call_args[0][0]
        messages = prompt.fn()

        result = prompt.convert_result(messages)
        assert isinstance(result, PromptResult)

    @pytest.mark.asyncio
    async def test_workflow_full_render_pipeline(self, mock_server):
        """End-to-end render for workflow prompts."""
        workflow = {
            'name': 'test_workflow',
            'type': 'list_get_update',
            'resource_type': 'pets',
            'description': 'Test workflow',
            'operations': {
                'list': {'operationId': 'listPets'},
                'get': {'operationId': 'getPet'},
                'update': {'operationId': 'updatePet'},
            },
        }

        create_workflow_prompt(mock_server, workflow)
        prompt = mock_server.add_prompt.call_args[0][0]

        result = await prompt.render(arguments={})
        assert isinstance(result, PromptResult)


class TestMessageTypeRegression:
    """Regression tests to prevent reintroduction of dict-based messages."""

    def test_dict_message_would_fail_convert_result(self):
        """Demonstrate that dict messages cause TypeError (the original bug)."""
        from fastmcp.prompts.prompt import Prompt

        def bad_handler():
            return [{'role': 'user', 'content': {'type': 'text', 'text': 'hi'}}]

        prompt = Prompt.from_function(fn=bad_handler, name='bad', description='test')
        messages = prompt.fn()

        with pytest.raises(TypeError, match='must be Message or str, got dict'):
            prompt.convert_result(messages)

    def test_string_messages_are_acceptable(self):
        """Strings are also valid returns (wrapped to Message by convert_result)."""
        from fastmcp.prompts.prompt import Prompt

        def str_handler():
            return ['hello world']

        prompt = Prompt.from_function(fn=str_handler, name='str_test', description='test')
        messages = prompt.fn()

        result = prompt.convert_result(messages)
        assert isinstance(result, PromptResult)
        assert result.messages[0].content.text == 'hello world'
