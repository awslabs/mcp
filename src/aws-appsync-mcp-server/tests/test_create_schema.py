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

"""Tests for the create_schema operation and tool."""

import pytest
from awslabs.aws_appsync_mcp_server.decorators import set_write_allowed
from awslabs.aws_appsync_mcp_server.operations.create_schema import create_schema_operation
from awslabs.aws_appsync_mcp_server.tools.create_schema import register_create_schema_tool
from mcp.server.fastmcp import FastMCP
from typing import Any, Callable
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_create_schema_success_immediate():
    """Test create_schema tool with immediate success."""
    mock_client = MagicMock()
    mock_start_response = {'status': 'PROCESSING'}
    mock_status_response = {'status': 'SUCCESS', 'details': 'Schema created successfully'}

    mock_client.start_schema_creation.return_value = mock_start_response
    mock_client.get_schema_creation_status.return_value = mock_status_response

    with (
        patch(
            'awslabs.aws_appsync_mcp_server.operations.create_schema.get_appsync_client',
            return_value=mock_client,
        ),
        patch('asyncio.sleep', new_callable=AsyncMock),
    ):
        result = await create_schema_operation(
            api_id='abcdefghijklmnopqrstuvwxyz', definition='type Query { hello: String }'
        )

        mock_client.start_schema_creation.assert_called_once_with(
            apiId='abcdefghijklmnopqrstuvwxyz', definition='type Query { hello: String }'
        )
        mock_client.get_schema_creation_status.assert_called_once_with(
            apiId='abcdefghijklmnopqrstuvwxyz'
        )
        assert result == {'status': 'SUCCESS', 'details': 'Schema created successfully'}


@pytest.mark.asyncio
async def test_create_schema_success_after_polling():
    """Test create_schema tool with success after polling."""
    mock_client = MagicMock()
    mock_start_response = {'status': 'PROCESSING'}
    mock_status_responses = [
        {'status': 'PROCESSING'},
        {'status': 'PROCESSING'},
        {'status': 'SUCCESS', 'details': 'Schema created successfully'},
    ]

    mock_client.start_schema_creation.return_value = mock_start_response
    mock_client.get_schema_creation_status.side_effect = mock_status_responses

    with (
        patch(
            'awslabs.aws_appsync_mcp_server.operations.create_schema.get_appsync_client',
            return_value=mock_client,
        ),
        patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep,
    ):
        result = await create_schema_operation(
            api_id='abcdefghijklmnopqrstuvwxyz', definition='type Query { hello: String }'
        )

        mock_client.start_schema_creation.assert_called_once_with(
            apiId='abcdefghijklmnopqrstuvwxyz', definition='type Query { hello: String }'
        )
        assert mock_client.get_schema_creation_status.call_count == 3
        assert mock_sleep.call_count == 2  # Called twice before final success
        assert result == {'status': 'SUCCESS', 'details': 'Schema created successfully'}


@pytest.mark.asyncio
async def test_create_schema_failure():
    """Test create_schema tool with failure."""
    mock_client = MagicMock()
    mock_start_response = {'status': 'PROCESSING'}
    mock_status_response = {'status': 'FAILED', 'details': 'Invalid schema definition'}

    mock_client.start_schema_creation.return_value = mock_start_response
    mock_client.get_schema_creation_status.return_value = mock_status_response

    with (
        patch(
            'awslabs.aws_appsync_mcp_server.operations.create_schema.get_appsync_client',
            return_value=mock_client,
        ),
        patch('asyncio.sleep', new_callable=AsyncMock),
    ):
        result = await create_schema_operation(
            api_id='abcdefghijklmnopqrstuvwxyz', definition='invalid schema'
        )

        mock_client.start_schema_creation.assert_called_once_with(
            apiId='abcdefghijklmnopqrstuvwxyz', definition='invalid schema'
        )
        mock_client.get_schema_creation_status.assert_called_once_with(
            apiId='abcdefghijklmnopqrstuvwxyz'
        )
        assert result == {'status': 'FAILED', 'details': 'Invalid schema definition'}


@pytest.mark.asyncio
async def test_create_schema_failure_after_polling():
    """Test create_schema tool with failure after polling."""
    mock_client = MagicMock()
    mock_start_response = {'status': 'PROCESSING'}
    mock_status_responses = [
        {'status': 'PROCESSING'},
        {'status': 'PROCESSING'},
        {'status': 'FAILED', 'details': 'Schema validation failed'},
    ]

    mock_client.start_schema_creation.return_value = mock_start_response
    mock_client.get_schema_creation_status.side_effect = mock_status_responses

    with (
        patch(
            'awslabs.aws_appsync_mcp_server.operations.create_schema.get_appsync_client',
            return_value=mock_client,
        ),
        patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep,
    ):
        result = await create_schema_operation(
            api_id='abcdefghijklmnopqrstuvwxyz', definition='type Query { invalid: InvalidType }'
        )

        mock_client.start_schema_creation.assert_called_once_with(
            apiId='abcdefghijklmnopqrstuvwxyz', definition='type Query { invalid: InvalidType }'
        )
        assert mock_client.get_schema_creation_status.call_count == 3
        assert mock_sleep.call_count == 2  # Called twice before final failure
        assert result == {'status': 'FAILED', 'details': 'Schema validation failed'}


@pytest.mark.asyncio
async def test_create_schema_complex_definition():
    """Test create_schema tool with complex schema definition."""
    mock_client = MagicMock()
    mock_start_response = {'status': 'PROCESSING'}
    mock_status_response = {'status': 'SUCCESS', 'details': 'Schema created successfully'}

    mock_client.start_schema_creation.return_value = mock_start_response
    mock_client.get_schema_creation_status.return_value = mock_status_response

    complex_schema = """
    type User {
        id: ID!
        name: String!
        email: String!
        posts: [Post]
    }

    type Post {
        id: ID!
        title: String!
        content: String!
        author: User!
    }

    type Query {
        getUser(id: ID!): User
        listUsers: [User]
        getPost(id: ID!): Post
        listPosts: [Post]
    }

    type Mutation {
        createUser(input: CreateUserInput!): User
        updateUser(id: ID!, input: UpdateUserInput!): User
        deleteUser(id: ID!): Boolean
        createPost(input: CreatePostInput!): Post
        updatePost(id: ID!, input: UpdatePostInput!): Post
        deletePost(id: ID!): Boolean
    }

    input CreateUserInput {
        name: String!
        email: String!
    }

    input UpdateUserInput {
        name: String
        email: String
    }

    input CreatePostInput {
        title: String!
        content: String!
        authorId: ID!
    }

    input UpdatePostInput {
        title: String
        content: String
    }
    """

    with (
        patch(
            'awslabs.aws_appsync_mcp_server.operations.create_schema.get_appsync_client',
            return_value=mock_client,
        ),
        patch('asyncio.sleep', new_callable=AsyncMock),
    ):
        result = await create_schema_operation(
            api_id='abcdefghijklmnopqrstuvwxyz', definition=complex_schema
        )

        mock_client.start_schema_creation.assert_called_once_with(
            apiId='abcdefghijklmnopqrstuvwxyz', definition=complex_schema
        )
        mock_client.get_schema_creation_status.assert_called_once_with(
            apiId='abcdefghijklmnopqrstuvwxyz'
        )
        assert result == {'status': 'SUCCESS', 'details': 'Schema created successfully'}


@pytest.mark.asyncio
async def test_create_schema_with_subscriptions():
    """Test create_schema tool with subscription types."""
    mock_client = MagicMock()
    mock_start_response = {'status': 'PROCESSING'}
    mock_status_response = {
        'status': 'SUCCESS',
        'details': 'Schema with subscriptions created successfully',
    }

    mock_client.start_schema_creation.return_value = mock_start_response
    mock_client.get_schema_creation_status.return_value = mock_status_response

    schema_with_subscriptions = """
    type User {
        id: ID!
        name: String!
        status: String!
    }

    type Query {
        getUser(id: ID!): User
    }

    type Mutation {
        updateUserStatus(id: ID!, status: String!): User
    }

    type Subscription {
        onUserStatusChanged(id: ID!): User
            @aws_subscribe(mutations: ["updateUserStatus"])
    }
    """

    with (
        patch(
            'awslabs.aws_appsync_mcp_server.operations.create_schema.get_appsync_client',
            return_value=mock_client,
        ),
        patch('asyncio.sleep', new_callable=AsyncMock),
    ):
        result = await create_schema_operation(
            api_id='abcdefghijklmnopqrstuvwxyz', definition=schema_with_subscriptions
        )

        mock_client.start_schema_creation.assert_called_once_with(
            apiId='abcdefghijklmnopqrstuvwxyz', definition=schema_with_subscriptions
        )
        mock_client.get_schema_creation_status.assert_called_once_with(
            apiId='abcdefghijklmnopqrstuvwxyz'
        )
        assert result == {
            'status': 'SUCCESS',
            'details': 'Schema with subscriptions created successfully',
        }


@pytest.mark.asyncio
async def test_create_schema_empty_details():
    """Test create_schema tool with empty details in response."""
    mock_client = MagicMock()
    mock_start_response = {'status': 'PROCESSING'}
    mock_status_response = {
        'status': 'SUCCESS'
        # No 'details' field
    }

    mock_client.start_schema_creation.return_value = mock_start_response
    mock_client.get_schema_creation_status.return_value = mock_status_response

    with (
        patch(
            'awslabs.aws_appsync_mcp_server.operations.create_schema.get_appsync_client',
            return_value=mock_client,
        ),
        patch('asyncio.sleep', new_callable=AsyncMock),
    ):
        result = await create_schema_operation(
            api_id='abcdefghijklmnopqrstuvwxyz', definition='type Query { hello: String }'
        )

        mock_client.start_schema_creation.assert_called_once_with(
            apiId='abcdefghijklmnopqrstuvwxyz', definition='type Query { hello: String }'
        )
        mock_client.get_schema_creation_status.assert_called_once_with(
            apiId='abcdefghijklmnopqrstuvwxyz'
        )
        assert result == {'status': 'SUCCESS', 'details': None}


@pytest.mark.asyncio
async def test_create_schema_long_polling():
    """Test create_schema tool with extended polling period."""
    mock_client = MagicMock()
    mock_start_response = {'status': 'PROCESSING'}
    mock_status_responses = [
        {'status': 'PROCESSING'},
        {'status': 'PROCESSING'},
        {'status': 'PROCESSING'},
        {'status': 'PROCESSING'},
        {'status': 'PROCESSING'},
        {'status': 'SUCCESS', 'details': 'Schema created after long processing'},
    ]

    mock_client.start_schema_creation.return_value = mock_start_response
    mock_client.get_schema_creation_status.side_effect = mock_status_responses

    with (
        patch(
            'awslabs.aws_appsync_mcp_server.operations.create_schema.get_appsync_client',
            return_value=mock_client,
        ),
        patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep,
    ):
        result = await create_schema_operation(
            api_id='abcdefghijklmnopqrstuvwxyz',
            definition='type Query { complexOperation: String }',
        )

        mock_client.start_schema_creation.assert_called_once_with(
            apiId='abcdefghijklmnopqrstuvwxyz',
            definition='type Query { complexOperation: String }',
        )
        assert mock_client.get_schema_creation_status.call_count == 6
        assert mock_sleep.call_count == 5  # Called 5 times before final success
        # Verify sleep was called with 2 seconds each time
        for call in mock_sleep.call_args_list:
            assert call[0][0] == 2
        assert result == {'status': 'SUCCESS', 'details': 'Schema created after long processing'}


# Tool registration and functionality tests


@pytest.fixture
def mock_mcp():
    """Create a mock FastMCP instance."""
    return MagicMock(spec=FastMCP)


def test_register_create_schema_tool(mock_mcp):
    """Test that create_schema tool is registered correctly."""
    register_create_schema_tool(mock_mcp)

    # Verify tool was registered
    mock_mcp.tool.assert_called_once()

    # Get the decorator call arguments
    call_args = mock_mcp.tool.call_args
    assert call_args[1]['name'] == 'create_schema'
    assert 'Creates a GraphQL schema' in call_args[1]['description']

    # Verify annotations
    annotations = call_args[1]['annotations']
    assert annotations.title == 'Create Schema'
    assert annotations.readOnlyHint is False
    assert annotations.destructiveHint is False
    assert annotations.openWorldHint is False


@pytest.mark.asyncio
async def test_create_schema_tool_write_protection():
    """Test that create_schema tool respects write protection."""
    mock_mcp = MagicMock(spec=FastMCP)

    # Capture the decorated function
    decorated_func: Callable[..., Any] | None = None

    def capture_tool(**kwargs):
        def decorator(func):
            nonlocal decorated_func
            decorated_func = func
            return func

        return decorator

    mock_mcp.tool = capture_tool

    # Register the tool
    register_create_schema_tool(mock_mcp)

    # Disable write operations
    set_write_allowed(False)

    # Test that the tool raises an error when write is disabled
    assert decorated_func is not None
    with pytest.raises(
        ValueError, match='Operation not permitted: Server is configured in read-only mode'
    ):
        await decorated_func(api_id='test-api-id', definition='type Query { hello: String }')


@pytest.mark.asyncio
async def test_create_schema_tool_success():
    """Test create_schema tool successful execution."""
    mock_mcp = MagicMock(spec=FastMCP)

    # Capture the decorated function
    decorated_func: Callable[..., Any] | None = None

    def capture_tool(**kwargs):
        def decorator(func):
            nonlocal decorated_func
            decorated_func = func
            return func

        return decorator

    mock_mcp.tool = capture_tool

    # Register the tool
    register_create_schema_tool(mock_mcp)

    # Enable write operations
    set_write_allowed(True)

    # Mock the operation
    with patch(
        'awslabs.aws_appsync_mcp_server.tools.create_schema.create_schema_operation'
    ) as mock_op:
        mock_op.return_value = {'status': 'SUCCESS', 'details': 'Schema created successfully'}

        assert decorated_func is not None
        result = await decorated_func(
            api_id='test-api-id', definition='type Query { hello: String }'
        )

        mock_op.assert_called_once_with('test-api-id', 'type Query { hello: String }')
        assert result == {'status': 'SUCCESS', 'details': 'Schema created successfully'}


@pytest.mark.asyncio
async def test_create_schema_tool_with_complex_schema():
    """Test create_schema tool with complex GraphQL schema."""
    mock_mcp = MagicMock(spec=FastMCP)

    # Capture the decorated function
    decorated_func: Callable[..., Any] | None = None

    def capture_tool(**kwargs):
        def decorator(func):
            nonlocal decorated_func
            decorated_func = func
            return func

        return decorator

    mock_mcp.tool = capture_tool

    # Register the tool
    register_create_schema_tool(mock_mcp)

    # Enable write operations
    set_write_allowed(True)

    complex_schema = """
    type User {
        id: ID!
        name: String!
        email: String!
        posts: [Post]
    }

    type Post {
        id: ID!
        title: String!
        content: String!
        author: User!
    }

    type Query {
        getUser(id: ID!): User
        listUsers: [User]
    }

    type Mutation {
        createUser(input: CreateUserInput!): User
    }

    input CreateUserInput {
        name: String!
        email: String!
    }
    """

    # Mock the operation
    with patch(
        'awslabs.aws_appsync_mcp_server.tools.create_schema.create_schema_operation'
    ) as mock_op:
        mock_op.return_value = {
            'status': 'SUCCESS',
            'details': 'Complex schema created successfully',
        }

        assert decorated_func is not None
        result = await decorated_func(api_id='complex-api-id', definition=complex_schema)

        mock_op.assert_called_once_with('complex-api-id', complex_schema)
        assert result == {'status': 'SUCCESS', 'details': 'Complex schema created successfully'}


def teardown_function():
    """Reset write allowed state after each test."""
    set_write_allowed(False)
