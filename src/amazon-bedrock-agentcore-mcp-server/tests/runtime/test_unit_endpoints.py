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

"""Tests for endpoints.py — CRUD on runtime endpoints."""

import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.runtime.endpoints import (
    EndpointTools,
)
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.runtime.models import (
    CreateEndpointResponse,
    DeleteEndpointResponse,
    ErrorResponse,
    GetEndpointResponse,
    ListEndpointsResponse,
    UpdateEndpointResponse,
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


class TestCreateEndpoint:
    """Tests for create_agent_runtime_endpoint."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, control_factory, mock_control_client):
        """Successful creation returns CREATING status."""
        mock_control_client.create_agent_runtime_endpoint.return_value = {
            'agentRuntimeEndpointArn': 'arn:ep',
            'agentRuntimeId': 'id-1',
            'endpointName': 'staging',
            'status': 'CREATING',
            'targetVersion': '2',
            'createdAt': '2025-01-01',
        }
        tools = EndpointTools(control_factory)
        result = await tools.create_agent_runtime_endpoint(
            ctx=mock_ctx,
            agent_runtime_id='id-1',
            name='staging',
            agent_runtime_version='2',
        )
        assert isinstance(result, CreateEndpointResponse)
        assert result.endpoint_name == 'staging'

    @pytest.mark.asyncio
    async def test_conflict(self, mock_ctx, control_factory, mock_control_client):
        """ConflictException is returned as ErrorResponse."""
        mock_control_client.create_agent_runtime_endpoint.side_effect = _client_error(
            'ConflictException', 'Already exists', 409
        )
        tools = EndpointTools(control_factory)
        result = await tools.create_agent_runtime_endpoint(
            ctx=mock_ctx,
            agent_runtime_id='id-1',
            name='dup',
        )
        assert isinstance(result, ErrorResponse)
        assert result.error_type == 'ConflictException'


class TestGetEndpoint:
    """Tests for get_agent_runtime_endpoint."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, control_factory, mock_control_client):
        """Successful get returns endpoint details."""
        mock_control_client.get_agent_runtime_endpoint.return_value = {
            'agentRuntimeEndpointArn': 'arn:ep',
            'name': 'DEFAULT',
            'status': 'READY',
            'liveVersion': '1',
            'targetVersion': '1',
        }
        tools = EndpointTools(control_factory)
        result = await tools.get_agent_runtime_endpoint(
            ctx=mock_ctx,
            agent_runtime_id='id-1',
            endpoint_name='DEFAULT',
        )
        assert isinstance(result, GetEndpointResponse)
        assert result.status == 'success'


class TestUpdateEndpoint:
    """Tests for update_agent_runtime_endpoint."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, control_factory, mock_control_client):
        """Successful update returns new target version."""
        mock_control_client.update_agent_runtime_endpoint.return_value = {
            'agentRuntimeEndpointArn': 'arn:ep',
            'status': 'UPDATING',
            'liveVersion': '1',
            'targetVersion': '3',
        }
        tools = EndpointTools(control_factory)
        result = await tools.update_agent_runtime_endpoint(
            ctx=mock_ctx,
            agent_runtime_id='id-1',
            endpoint_name='prod',
            agent_runtime_version='3',
        )
        assert isinstance(result, UpdateEndpointResponse)
        assert result.target_version == '3'


class TestDeleteEndpoint:
    """Tests for delete_agent_runtime_endpoint."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, control_factory, mock_control_client):
        """Successful delete returns DELETING status."""
        mock_control_client.delete_agent_runtime_endpoint.return_value = {
            'agentRuntimeId': 'id-1',
            'endpointName': 'staging',
            'status': 'DELETING',
        }
        tools = EndpointTools(control_factory)
        result = await tools.delete_agent_runtime_endpoint(
            ctx=mock_ctx,
            agent_runtime_id='id-1',
            endpoint_name='staging',
        )
        assert isinstance(result, DeleteEndpointResponse)
        assert result.status == 'success'


class TestListEndpoints:
    """Tests for list_agent_runtime_endpoints."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, control_factory, mock_control_client):
        """Lists multiple endpoints."""
        mock_control_client.list_agent_runtime_endpoints.return_value = {
            'runtimeEndpoints': [
                {'name': 'DEFAULT', 'status': 'READY', 'liveVersion': '1'},
                {'name': 'staging', 'status': 'READY', 'liveVersion': '2'},
            ]
        }
        tools = EndpointTools(control_factory)
        result = await tools.list_agent_runtime_endpoints(
            ctx=mock_ctx,
            agent_runtime_id='id-1',
        )
        assert isinstance(result, ListEndpointsResponse)
        assert len(result.endpoints) == 2

    @pytest.mark.asyncio
    async def test_empty(self, mock_ctx, control_factory, mock_control_client):
        """Empty list returns zero endpoints."""
        mock_control_client.list_agent_runtime_endpoints.return_value = {
            'runtimeEndpoints': [],
        }
        tools = EndpointTools(control_factory)
        result = await tools.list_agent_runtime_endpoints(
            ctx=mock_ctx,
            agent_runtime_id='id-1',
        )
        assert isinstance(result, ListEndpointsResponse)
        assert len(result.endpoints) == 0
