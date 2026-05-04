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

"""Unit tests for Identity workload identity tools."""

import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.identity.models import (
    DeleteWorkloadIdentityResponse,
    ErrorResponse,
    ListWorkloadIdentitiesResponse,
    WorkloadIdentityResponse,
)
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.identity.workload_identity import (
    WorkloadIdentityTools,
)
from botocore.exceptions import ClientError


class TestIdentityCreateWorkloadIdentity:
    """Tests for identity_create_workload_identity tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Creates workload identity and returns ARN."""
        mock_boto3_client.create_workload_identity.return_value = {
            'name': 'my-agent',
            'workloadIdentityArn': (
                'arn:aws:bedrock-agentcore:us-east-1:123:workload-identity/'
                'directory/default/workload-identity/my-agent'
            ),
            'allowedResourceOauth2ReturnUrls': [],
            'ResponseMetadata': {'HTTPStatusCode': 201},
        }
        tools = WorkloadIdentityTools(client_factory)
        result = await tools.identity_create_workload_identity(
            ctx=mock_ctx,
            name='my-agent',
        )
        assert isinstance(result, WorkloadIdentityResponse)
        assert result.status == 'success'
        assert 'my-agent' in result.message
        assert result.workload_identity['name'] == 'my-agent'
        # ResponseMetadata is stripped
        assert 'ResponseMetadata' not in result.workload_identity
        mock_boto3_client.create_workload_identity.assert_called_once_with(name='my-agent')

    @pytest.mark.asyncio
    async def test_with_all_params(self, mock_ctx, client_factory, mock_boto3_client):
        """Passes optional params to the API."""
        mock_boto3_client.create_workload_identity.return_value = {
            'name': 'my-agent',
            'workloadIdentityArn': 'arn:aws:bedrock-agentcore:us-east-1:123:workload-identity/x',
        }
        tools = WorkloadIdentityTools(client_factory)
        result = await tools.identity_create_workload_identity(
            ctx=mock_ctx,
            name='my-agent',
            allowed_resource_oauth2_return_urls=['https://example.com/callback'],
            tags={'env': 'prod'},
        )
        assert isinstance(result, WorkloadIdentityResponse)
        kw = mock_boto3_client.create_workload_identity.call_args.kwargs
        assert kw['allowedResourceOauth2ReturnUrls'] == ['https://example.com/callback']
        assert kw['tags'] == {'env': 'prod'}

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.create_workload_identity.side_effect = ClientError(
            {
                'Error': {'Code': 'ValidationException', 'Message': 'invalid name'},
                'ResponseMetadata': {'HTTPStatusCode': 400},
            },
            'CreateWorkloadIdentity',
        )
        tools = WorkloadIdentityTools(client_factory)
        result = await tools.identity_create_workload_identity(ctx=mock_ctx, name='bad name!')
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'
        assert 'invalid name' in result.message


class TestIdentityGetWorkloadIdentity:
    """Tests for identity_get_workload_identity tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns workload identity details."""
        mock_boto3_client.get_workload_identity.return_value = {
            'name': 'my-agent',
            'workloadIdentityArn': 'arn:aws:bedrock-agentcore:us-east-1:123:workload-identity/x',
            'allowedResourceOauth2ReturnUrls': ['https://a.com/cb'],
            'createdTime': 1700000000,
            'lastUpdatedTime': 1700000001,
        }
        tools = WorkloadIdentityTools(client_factory)
        result = await tools.identity_get_workload_identity(ctx=mock_ctx, name='my-agent')
        assert isinstance(result, WorkloadIdentityResponse)
        assert result.status == 'success'
        assert result.workload_identity['name'] == 'my-agent'
        assert result.workload_identity['allowedResourceOauth2ReturnUrls'] == ['https://a.com/cb']

    @pytest.mark.asyncio
    async def test_not_found(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse when workload identity not found."""
        mock_boto3_client.get_workload_identity.side_effect = ClientError(
            {
                'Error': {'Code': 'ResourceNotFoundException', 'Message': 'not found'},
                'ResponseMetadata': {'HTTPStatusCode': 404},
            },
            'GetWorkloadIdentity',
        )
        tools = WorkloadIdentityTools(client_factory)
        result = await tools.identity_get_workload_identity(ctx=mock_ctx, name='nonexist')
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'
        assert result.error_type == 'ResourceNotFoundException'


class TestIdentityUpdateWorkloadIdentity:
    """Tests for identity_update_workload_identity tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Updates workload identity."""
        mock_boto3_client.update_workload_identity.return_value = {
            'name': 'my-agent',
            'workloadIdentityArn': 'arn:aws:bedrock-agentcore:us-east-1:123:workload-identity/x',
            'allowedResourceOauth2ReturnUrls': ['https://new.example.com/cb'],
        }
        tools = WorkloadIdentityTools(client_factory)
        result = await tools.identity_update_workload_identity(
            ctx=mock_ctx,
            name='my-agent',
            allowed_resource_oauth2_return_urls=['https://new.example.com/cb'],
        )
        assert isinstance(result, WorkloadIdentityResponse)
        assert result.status == 'success'
        kw = mock_boto3_client.update_workload_identity.call_args.kwargs
        assert kw['allowedResourceOauth2ReturnUrls'] == ['https://new.example.com/cb']

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.update_workload_identity.side_effect = ClientError(
            {
                'Error': {'Code': 'ValidationException', 'Message': 'bad url'},
                'ResponseMetadata': {'HTTPStatusCode': 400},
            },
            'UpdateWorkloadIdentity',
        )
        tools = WorkloadIdentityTools(client_factory)
        result = await tools.identity_update_workload_identity(ctx=mock_ctx, name='my-agent')
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'


class TestIdentityDeleteWorkloadIdentity:
    """Tests for identity_delete_workload_identity tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Deletes workload identity."""
        mock_boto3_client.delete_workload_identity.return_value = {}
        tools = WorkloadIdentityTools(client_factory)
        result = await tools.identity_delete_workload_identity(ctx=mock_ctx, name='my-agent')
        assert isinstance(result, DeleteWorkloadIdentityResponse)
        assert result.status == 'success'
        assert result.name == 'my-agent'
        mock_boto3_client.delete_workload_identity.assert_called_once_with(name='my-agent')

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.delete_workload_identity.side_effect = ClientError(
            {
                'Error': {'Code': 'ResourceNotFoundException', 'Message': 'missing'},
                'ResponseMetadata': {'HTTPStatusCode': 404},
            },
            'DeleteWorkloadIdentity',
        )
        tools = WorkloadIdentityTools(client_factory)
        result = await tools.identity_delete_workload_identity(ctx=mock_ctx, name='missing')
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'


class TestIdentityListWorkloadIdentities:
    """Tests for identity_list_workload_identities tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns list of workload identities with pagination token."""
        mock_boto3_client.list_workload_identities.return_value = {
            'workloadIdentities': [
                {'name': 'a', 'workloadIdentityArn': 'arn:aws:bedrock-agentcore:...:a'},
                {'name': 'b', 'workloadIdentityArn': 'arn:aws:bedrock-agentcore:...:b'},
            ],
            'nextToken': 'tok123',
        }
        tools = WorkloadIdentityTools(client_factory)
        result = await tools.identity_list_workload_identities(ctx=mock_ctx)
        assert isinstance(result, ListWorkloadIdentitiesResponse)
        assert result.status == 'success'
        assert len(result.workload_identities) == 2
        assert result.next_token == 'tok123'

    @pytest.mark.asyncio
    async def test_with_pagination(self, mock_ctx, client_factory, mock_boto3_client):
        """Passes pagination params to API."""
        mock_boto3_client.list_workload_identities.return_value = {
            'workloadIdentities': [],
        }
        tools = WorkloadIdentityTools(client_factory)
        result = await tools.identity_list_workload_identities(
            ctx=mock_ctx, max_results=5, next_token='prev'
        )
        assert isinstance(result, ListWorkloadIdentitiesResponse)
        mock_boto3_client.list_workload_identities.assert_called_once_with(
            maxResults=5, nextToken='prev'
        )

    @pytest.mark.asyncio
    async def test_empty(self, mock_ctx, client_factory, mock_boto3_client):
        """Handles empty result list."""
        mock_boto3_client.list_workload_identities.return_value = {'workloadIdentities': []}
        tools = WorkloadIdentityTools(client_factory)
        result = await tools.identity_list_workload_identities(ctx=mock_ctx)
        assert isinstance(result, ListWorkloadIdentitiesResponse)
        assert len(result.workload_identities) == 0

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.list_workload_identities.side_effect = ClientError(
            {
                'Error': {'Code': 'ServiceException', 'Message': 'x'},
                'ResponseMetadata': {'HTTPStatusCode': 500},
            },
            'ListWorkloadIdentities',
        )
        tools = WorkloadIdentityTools(client_factory)
        result = await tools.identity_list_workload_identities(ctx=mock_ctx)
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'
