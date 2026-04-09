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

"""Tests for lifecycle.py — create, get, update, delete, list runtimes."""

import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.runtime.lifecycle import (
    LifecycleTools,
)
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.runtime.models import (
    CreateRuntimeResponse,
    DeleteRuntimeResponse,
    ErrorResponse,
    GetRuntimeResponse,
    ListRuntimesResponse,
    ListRuntimeVersionsResponse,
    UpdateRuntimeResponse,
)
from botocore.exceptions import ClientError


def _client_error(code='ValidationException', message='bad request', status=400):
    """Create a ClientError for testing."""
    return ClientError(
        {
            'Error': {'Code': code, 'Message': message},
            'ResponseMetadata': {'HTTPStatusCode': status},
        },
        'TestOp',
    )


class TestCreateAgentRuntime:
    """Tests for create_agent_runtime."""

    @pytest.mark.asyncio
    async def test_success_container(self, mock_ctx, control_factory, mock_control_client):
        """Container-based creation returns CREATING status."""
        mock_control_client.create_agent_runtime.return_value = {
            'agentRuntimeArn': 'arn:aws:bedrock-agentcore:us-west-2:123:runtime/test',
            'agentRuntimeId': 'test-abc123',
            'agentRuntimeVersion': '1',
            'status': 'CREATING',
            'createdAt': '2025-01-01T00:00:00Z',
            'workloadIdentityDetails': {'workloadIdentityArn': 'arn:wid'},
        }
        tools = LifecycleTools(control_factory)
        result = await tools.create_agent_runtime(
            ctx=mock_ctx,
            agent_runtime_name='test_agent',
            role_arn='arn:aws:iam::123:role/TestRole',
            container_uri='123.dkr.ecr.us-west-2.amazonaws.com/test:latest',
        )
        assert isinstance(result, CreateRuntimeResponse)
        assert result.status == 'CREATING'
        assert result.agent_runtime_id == 'test-abc123'

    @pytest.mark.asyncio
    async def test_success_code_deploy(self, mock_ctx, control_factory, mock_control_client):
        """Code deploy sends codeConfiguration in the artifact."""
        mock_control_client.create_agent_runtime.return_value = {
            'agentRuntimeArn': 'arn:test',
            'agentRuntimeId': 'id-1',
            'agentRuntimeVersion': '1',
            'status': 'CREATING',
        }
        tools = LifecycleTools(control_factory)
        result = await tools.create_agent_runtime(
            ctx=mock_ctx,
            agent_runtime_name='code_agent',
            role_arn='arn:role',
            code_s3_bucket='my-bucket',
            code_s3_prefix='agent/code.zip',
            code_runtime='PYTHON_3_13',
            code_entry_point='main.py',
        )
        assert isinstance(result, CreateRuntimeResponse)
        assert result.status == 'CREATING'

    @pytest.mark.asyncio
    async def test_error_no_artifact(self, mock_ctx, control_factory):
        """Missing both container_uri and s3 fields returns error."""
        tools = LifecycleTools(control_factory)
        result = await tools.create_agent_runtime(
            ctx=mock_ctx,
            agent_runtime_name='bad',
            role_arn='arn:role',
        )
        assert isinstance(result, CreateRuntimeResponse)
        assert result.status == 'error'

    @pytest.mark.asyncio
    async def test_handles_client_error(self, mock_ctx, control_factory, mock_control_client):
        """ClientError is caught and returned as ErrorResponse."""
        mock_control_client.create_agent_runtime.side_effect = _client_error(
            'ValidationException',
            'Name is invalid',
            400,
        )
        tools = LifecycleTools(control_factory)
        result = await tools.create_agent_runtime(
            ctx=mock_ctx,
            agent_runtime_name='bad!',
            role_arn='arn:role',
            container_uri='uri',
        )
        assert isinstance(result, ErrorResponse)
        assert 'Name is invalid' in result.message

    @pytest.mark.asyncio
    async def test_vpc_mode(self, mock_ctx, control_factory, mock_control_client):
        """VPC mode passes subnets and security groups."""
        mock_control_client.create_agent_runtime.return_value = {
            'agentRuntimeArn': 'arn:vpc',
            'agentRuntimeId': 'vpc-1',
            'agentRuntimeVersion': '1',
            'status': 'CREATING',
        }
        tools = LifecycleTools(control_factory)
        await tools.create_agent_runtime(
            ctx=mock_ctx,
            agent_runtime_name='vpc_agent',
            role_arn='arn:role',
            container_uri='uri',
            network_mode='VPC',
            subnets='subnet-abc,subnet-def',
            security_groups='sg-123',
        )
        call_kwargs = mock_control_client.create_agent_runtime.call_args[1]
        net = call_kwargs['networkConfiguration']
        assert net['networkMode'] == 'VPC'
        assert 'subnet-abc' in net['networkModeConfig']['subnets']


class TestGetAgentRuntime:
    """Tests for get_agent_runtime."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, control_factory, mock_control_client):
        """Successful get returns runtime details."""
        mock_control_client.get_agent_runtime.return_value = {
            'agentRuntimeArn': 'arn:test',
            'agentRuntimeId': 'id-1',
            'agentRuntimeName': 'my_agent',
            'agentRuntimeVersion': '2',
            'status': 'READY',
            'protocolConfiguration': {'serverProtocol': 'HTTP'},
            'networkConfiguration': {'networkMode': 'PUBLIC'},
        }
        tools = LifecycleTools(control_factory)
        result = await tools.get_agent_runtime(ctx=mock_ctx, agent_runtime_id='id-1')
        assert isinstance(result, GetRuntimeResponse)
        assert result.status == 'success'

    @pytest.mark.asyncio
    async def test_not_found(self, mock_ctx, control_factory, mock_control_client):
        """ResourceNotFoundException is returned as ErrorResponse."""
        mock_control_client.get_agent_runtime.side_effect = _client_error(
            'ResourceNotFoundException',
            'Not found',
            404,
        )
        tools = LifecycleTools(control_factory)
        result = await tools.get_agent_runtime(ctx=mock_ctx, agent_runtime_id='x')
        assert isinstance(result, ErrorResponse)
        assert result.error_type == 'ResourceNotFoundException'


class TestUpdateAgentRuntime:
    """Tests for update_agent_runtime."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, control_factory, mock_control_client):
        """Successful update returns new version."""
        mock_control_client.update_agent_runtime.return_value = {
            'agentRuntimeArn': 'arn:test',
            'agentRuntimeId': 'id-1',
            'agentRuntimeVersion': '2',
            'status': 'UPDATING',
        }
        tools = LifecycleTools(control_factory)
        result = await tools.update_agent_runtime(
            ctx=mock_ctx,
            agent_runtime_id='id-1',
            role_arn='arn:role',
            container_uri='new-uri',
        )
        assert isinstance(result, UpdateRuntimeResponse)
        assert result.status == 'UPDATING'

    @pytest.mark.asyncio
    async def test_error_no_artifact(self, mock_ctx, control_factory):
        """Missing artifact fields returns error."""
        tools = LifecycleTools(control_factory)
        result = await tools.update_agent_runtime(
            ctx=mock_ctx,
            agent_runtime_id='id-1',
            role_arn='arn:role',
        )
        assert isinstance(result, UpdateRuntimeResponse)
        assert result.status == 'error'


class TestDeleteAgentRuntime:
    """Tests for delete_agent_runtime."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, control_factory, mock_control_client):
        """Successful delete returns DELETING status."""
        mock_control_client.delete_agent_runtime.return_value = {
            'agentRuntimeId': 'id-1',
            'status': 'DELETING',
        }
        tools = LifecycleTools(control_factory)
        result = await tools.delete_agent_runtime(ctx=mock_ctx, agent_runtime_id='id-1')
        assert isinstance(result, DeleteRuntimeResponse)
        assert result.runtime_status == 'DELETING'


class TestListAgentRuntimes:
    """Tests for list_agent_runtimes."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, control_factory, mock_control_client):
        """Lists runtimes with pagination token."""
        mock_control_client.list_agent_runtimes.return_value = {
            'agentRuntimes': [{'agentRuntimeId': 'id-1', 'status': 'READY'}],
            'nextToken': 'tok123',
        }
        tools = LifecycleTools(control_factory)
        result = await tools.list_agent_runtimes(ctx=mock_ctx)
        assert isinstance(result, ListRuntimesResponse)
        assert len(result.runtimes) == 1
        assert result.next_token == 'tok123'

    @pytest.mark.asyncio
    async def test_pagination(self, mock_ctx, control_factory, mock_control_client):
        """Pagination params are forwarded to the API."""
        mock_control_client.list_agent_runtimes.return_value = {'agentRuntimes': []}
        tools = LifecycleTools(control_factory)
        await tools.list_agent_runtimes(ctx=mock_ctx, max_results=10, next_token='p2')
        call_kwargs = mock_control_client.list_agent_runtimes.call_args[1]
        assert call_kwargs['maxResults'] == 10
        assert call_kwargs['nextToken'] == 'p2'


class TestListAgentRuntimeVersions:
    """Tests for list_agent_runtime_versions."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, control_factory, mock_control_client):
        """Lists multiple versions."""
        mock_control_client.list_agent_runtime_versions.return_value = {
            'agentRuntimes': [
                {'agentRuntimeVersion': '1', 'status': 'READY'},
                {'agentRuntimeVersion': '2', 'status': 'READY'},
            ]
        }
        tools = LifecycleTools(control_factory)
        result = await tools.list_agent_runtime_versions(
            ctx=mock_ctx,
            agent_runtime_id='id-1',
        )
        assert isinstance(result, ListRuntimeVersionsResponse)
        assert len(result.versions) == 2
