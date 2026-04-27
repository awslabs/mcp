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

"""Unit tests for Memory control plane tools."""

import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.memory.controlplane import (
    ControlPlaneTools,
)
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.memory.models import (
    DeleteMemoryResponse,
    ErrorResponse,
    ListMemoriesResponse,
    MemoryResponse,
)
from botocore.exceptions import ClientError


class TestMemoryCreate:
    """Tests for memory_create tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Creates memory and returns ID and status."""
        mock_boto3_client.create_memory.return_value = {
            'memory': {
                'id': 'test-memory-abc1234567',
                'name': 'TestMemory',
                'status': 'CREATING',
                'arn': 'arn:aws:bedrock-agentcore:us-east-1:123:memory/t',
            }
        }
        tools = ControlPlaneTools(client_factory)
        result = await tools.memory_create(
            ctx=mock_ctx,
            name='TestMemory',
            event_expiry_duration=30,
        )
        assert isinstance(result, MemoryResponse)
        assert result.status == 'success'
        assert 'test-memory-abc1234567' in result.message
        assert result.memory['name'] == 'TestMemory'
        mock_boto3_client.create_memory.assert_called_once_with(
            name='TestMemory', eventExpiryDuration=30
        )

    @pytest.mark.asyncio
    async def test_with_all_params(self, mock_ctx, client_factory, mock_boto3_client):
        """Passes all optional params to the API."""
        mock_boto3_client.create_memory.return_value = {
            'memory': {'id': 'mem-id', 'status': 'CREATING'}
        }
        tools = ControlPlaneTools(client_factory)
        result = await tools.memory_create(
            ctx=mock_ctx,
            name='TestMemory',
            event_expiry_duration=90,
            description='A test memory',
            encryption_key_arn='arn:aws:kms:us-east-1:123:key/abc',
            memory_execution_role_arn='arn:aws:iam::123:role/test',
            memory_strategies=[{'semanticMemoryStrategy': {'name': 's1'}}],
            tags={'env': 'test'},
        )
        assert isinstance(result, MemoryResponse)
        assert result.status == 'success'
        kw = mock_boto3_client.create_memory.call_args.kwargs
        assert kw['description'] == 'A test memory'
        assert kw['encryptionKeyArn'] == 'arn:aws:kms:us-east-1:123:key/abc'
        assert kw['memoryStrategies'] == [{'semanticMemoryStrategy': {'name': 's1'}}]
        assert kw['tags'] == {'env': 'test'}

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.create_memory.side_effect = ClientError(
            {
                'Error': {'Code': 'ValidationException', 'Message': 'bad'},
                'ResponseMetadata': {'HTTPStatusCode': 400},
            },
            'CreateMemory',
        )
        tools = ControlPlaneTools(client_factory)
        result = await tools.memory_create(ctx=mock_ctx, name='bad!', event_expiry_duration=30)
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'
        assert 'bad' in result.message


class TestMemoryGet:
    """Tests for memory_get tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns memory details on success."""
        mock_boto3_client.get_memory.return_value = {
            'memory': {
                'id': 'mem-id',
                'status': 'ACTIVE',
                'name': 'Test',
                'strategies': [{'strategyId': 's1', 'type': 'SEMANTIC'}],
            }
        }
        tools = ControlPlaneTools(client_factory)
        result = await tools.memory_get(ctx=mock_ctx, memory_id='mem-id')
        assert isinstance(result, MemoryResponse)
        assert result.status == 'success'
        assert result.memory['status'] == 'ACTIVE'

    @pytest.mark.asyncio
    async def test_not_found(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse when memory not found."""
        mock_boto3_client.get_memory.side_effect = ClientError(
            {
                'Error': {'Code': 'ResourceNotFoundException', 'Message': 'x'},
                'ResponseMetadata': {'HTTPStatusCode': 404},
            },
            'GetMemory',
        )
        tools = ControlPlaneTools(client_factory)
        result = await tools.memory_get(ctx=mock_ctx, memory_id='nonexist')
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'


class TestMemoryUpdate:
    """Tests for memory_update tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Updates memory and returns updated details."""
        mock_boto3_client.update_memory.return_value = {
            'memory': {'id': 'mem-id', 'status': 'ACTIVE'}
        }
        tools = ControlPlaneTools(client_factory)
        result = await tools.memory_update(
            ctx=mock_ctx,
            memory_id='mem-id',
            description='Updated desc',
        )
        assert isinstance(result, MemoryResponse)
        assert result.status == 'success'
        mock_boto3_client.update_memory.assert_called_once_with(
            memoryId='mem-id', description='Updated desc'
        )

    @pytest.mark.asyncio
    async def test_with_all_params(self, mock_ctx, client_factory, mock_boto3_client):
        """Passes all optional params to the API."""
        mock_boto3_client.update_memory.return_value = {
            'memory': {'id': 'mem-id', 'status': 'ACTIVE'}
        }
        tools = ControlPlaneTools(client_factory)
        result = await tools.memory_update(
            ctx=mock_ctx,
            memory_id='mem-id',
            description='New desc',
            event_expiry_duration=60,
            memory_execution_role_arn='arn:aws:iam::123:role/new',
            memory_strategies={
                'addMemoryStrategies': [{'semanticMemoryStrategy': {'name': 's2'}}]
            },
        )
        assert isinstance(result, MemoryResponse)
        kw = mock_boto3_client.update_memory.call_args.kwargs
        assert kw['eventExpiryDuration'] == 60
        assert kw['memoryExecutionRoleArn'] == 'arn:aws:iam::123:role/new'
        assert 'addMemoryStrategies' in kw['memoryStrategies']

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.update_memory.side_effect = ClientError(
            {
                'Error': {'Code': 'ConflictException', 'Message': 'conflict'},
                'ResponseMetadata': {'HTTPStatusCode': 409},
            },
            'UpdateMemory',
        )
        tools = ControlPlaneTools(client_factory)
        result = await tools.memory_update(ctx=mock_ctx, memory_id='mem-id')
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'


class TestMemoryDelete:
    """Tests for memory_delete tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Deletes memory and returns DELETING status."""
        mock_boto3_client.delete_memory.return_value = {'memoryId': 'mem-id', 'status': 'DELETING'}
        tools = ControlPlaneTools(client_factory)
        result = await tools.memory_delete(ctx=mock_ctx, memory_id='mem-id')
        assert isinstance(result, DeleteMemoryResponse)
        assert result.status == 'success'
        assert result.memory_id == 'mem-id'
        assert result.memory_status == 'DELETING'

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.delete_memory.side_effect = ClientError(
            {
                'Error': {'Code': 'ResourceNotFoundException', 'Message': 'x'},
                'ResponseMetadata': {'HTTPStatusCode': 404},
            },
            'DeleteMemory',
        )
        tools = ControlPlaneTools(client_factory)
        result = await tools.memory_delete(ctx=mock_ctx, memory_id='bad')
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'


class TestMemoryList:
    """Tests for memory_list tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns list of memories with pagination token."""
        mock_boto3_client.list_memories.return_value = {
            'memories': [
                {'id': 'm1', 'status': 'ACTIVE'},
                {'id': 'm2', 'status': 'CREATING'},
            ],
            'nextToken': 'tok123',
        }
        tools = ControlPlaneTools(client_factory)
        result = await tools.memory_list(ctx=mock_ctx)
        assert isinstance(result, ListMemoriesResponse)
        assert result.status == 'success'
        assert len(result.memories) == 2
        assert result.next_token == 'tok123'

    @pytest.mark.asyncio
    async def test_with_pagination(self, mock_ctx, client_factory, mock_boto3_client):
        """Passes pagination params to API."""
        mock_boto3_client.list_memories.return_value = {'memories': [], 'nextToken': None}
        tools = ControlPlaneTools(client_factory)
        result = await tools.memory_list(ctx=mock_ctx, max_results=10, next_token='prev')
        assert isinstance(result, ListMemoriesResponse)
        assert result.status == 'success'
        mock_boto3_client.list_memories.assert_called_once_with(maxResults=10, nextToken='prev')

    @pytest.mark.asyncio
    async def test_empty(self, mock_ctx, client_factory, mock_boto3_client):
        """Handles empty memory list."""
        mock_boto3_client.list_memories.return_value = {'memories': []}
        tools = ControlPlaneTools(client_factory)
        result = await tools.memory_list(ctx=mock_ctx)
        assert isinstance(result, ListMemoriesResponse)
        assert result.status == 'success'
        assert len(result.memories) == 0

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.list_memories.side_effect = ClientError(
            {
                'Error': {'Code': 'ServiceException', 'Message': 'x'},
                'ResponseMetadata': {'HTTPStatusCode': 500},
            },
            'ListMemories',
        )
        tools = ControlPlaneTools(client_factory)
        result = await tools.memory_list(ctx=mock_ctx)
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'
