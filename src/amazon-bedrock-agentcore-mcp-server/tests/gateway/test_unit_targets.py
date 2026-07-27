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

"""Unit tests for Gateway Target tools."""

import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.gateway.models import (
    DeleteGatewayTargetResponse,
    ErrorResponse,
    GatewayTargetResponse,
    ListGatewayTargetsResponse,
    SynchronizeTargetsResponse,
)
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.gateway.targets import (
    GatewayTargetTools,
)
from botocore.exceptions import ClientError


class TestGatewayTargetCreate:
    """Tests for gateway_target_create tool."""

    @pytest.mark.asyncio
    async def test_success_mcp_server(self, mock_ctx, client_factory, mock_boto3_client):
        """Creates mcpServer target and returns ID and status."""
        mock_boto3_client.create_gateway_target.return_value = {
            'targetId': 'abc1234567',
            'name': 'MCPTarget',
            'status': 'CREATING',
        }
        tools = GatewayTargetTools(client_factory)
        result = await tools.gateway_target_create(
            ctx=mock_ctx,
            gateway_identifier='gw1',
            name='MCPTarget',
            target_configuration={
                'mcp': {'mcpServer': {'endpoint': 'https://mcp.example.com/mcp'}}
            },
        )
        assert isinstance(result, GatewayTargetResponse)
        assert result.status == 'success'
        assert 'abc1234567' in result.message

    @pytest.mark.asyncio
    async def test_success_lambda(self, mock_ctx, client_factory, mock_boto3_client):
        """Creates lambda target with credentials and all options."""
        mock_boto3_client.create_gateway_target.return_value = {
            'targetId': 'lam1234567',
            'status': 'CREATING',
        }
        tools = GatewayTargetTools(client_factory)
        result = await tools.gateway_target_create(
            ctx=mock_ctx,
            gateway_identifier='gw1',
            name='LambdaTarget',
            target_configuration={
                'mcp': {
                    'lambda': {
                        'lambdaArn': 'arn:aws:lambda:us-east-1:123:function:f',
                        'toolSchema': {'inlinePayload': []},
                    }
                }
            },
            credential_provider_configurations=[{'credentialProviderType': 'GATEWAY_IAM_ROLE'}],
            description='My lambda',
            metadata_configuration={
                'allowedRequestHeaders': ['x-correlation-id'],
            },
            client_token='a' * 40,
        )
        assert isinstance(result, GatewayTargetResponse)
        kw = mock_boto3_client.create_gateway_target.call_args.kwargs
        assert (
            kw['credentialProviderConfigurations'][0]['credentialProviderType']
            == 'GATEWAY_IAM_ROLE'
        )
        assert kw['metadataConfiguration']['allowedRequestHeaders'] == ['x-correlation-id']
        assert kw['clientToken'] == 'a' * 40

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.create_gateway_target.side_effect = ClientError(
            {
                'Error': {'Code': 'ValidationException', 'Message': 'bad'},
                'ResponseMetadata': {'HTTPStatusCode': 400},
            },
            'CreateGatewayTarget',
        )
        tools = GatewayTargetTools(client_factory)
        result = await tools.gateway_target_create(
            ctx=mock_ctx,
            gateway_identifier='gw1',
            name='T',
            target_configuration={'mcp': {}},
        )
        assert isinstance(result, ErrorResponse)


class TestGatewayTargetGet:
    """Tests for gateway_target_get tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns target details on success."""
        mock_boto3_client.get_gateway_target.return_value = {
            'targetId': 'abc1234567',
            'name': 'T',
            'status': 'READY',
        }
        tools = GatewayTargetTools(client_factory)
        result = await tools.gateway_target_get(
            ctx=mock_ctx, gateway_identifier='gw1', target_id='abc1234567'
        )
        assert isinstance(result, GatewayTargetResponse)
        assert result.target['status'] == 'READY'

    @pytest.mark.asyncio
    async def test_not_found(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse when target not found."""
        mock_boto3_client.get_gateway_target.side_effect = ClientError(
            {
                'Error': {'Code': 'ResourceNotFoundException', 'Message': 'x'},
                'ResponseMetadata': {'HTTPStatusCode': 404},
            },
            'GetGatewayTarget',
        )
        tools = GatewayTargetTools(client_factory)
        result = await tools.gateway_target_get(
            ctx=mock_ctx, gateway_identifier='gw1', target_id='nope123456'
        )
        assert isinstance(result, ErrorResponse)


class TestGatewayTargetUpdate:
    """Tests for gateway_target_update tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Updates target and returns updated details."""
        mock_boto3_client.update_gateway_target.return_value = {
            'targetId': 't1',
            'status': 'UPDATING',
        }
        tools = GatewayTargetTools(client_factory)
        result = await tools.gateway_target_update(
            ctx=mock_ctx,
            gateway_identifier='gw1',
            target_id='t1',
            name='UpdatedName',
            target_configuration={'mcp': {'mcpServer': {'endpoint': 'https://a'}}},
            description='updated',
            credential_provider_configurations=[{'credentialProviderType': 'GATEWAY_IAM_ROLE'}],
            metadata_configuration={'allowedRequestHeaders': ['x-h']},
        )
        assert isinstance(result, GatewayTargetResponse)
        kw = mock_boto3_client.update_gateway_target.call_args.kwargs
        assert kw['name'] == 'UpdatedName'
        assert kw['description'] == 'updated'
        assert kw['metadataConfiguration']['allowedRequestHeaders'] == ['x-h']

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.update_gateway_target.side_effect = ClientError(
            {
                'Error': {'Code': 'ConflictException', 'Message': 'c'},
                'ResponseMetadata': {'HTTPStatusCode': 409},
            },
            'UpdateGatewayTarget',
        )
        tools = GatewayTargetTools(client_factory)
        result = await tools.gateway_target_update(
            ctx=mock_ctx,
            gateway_identifier='gw1',
            target_id='t1',
            name='N',
            target_configuration={'mcp': {}},
        )
        assert isinstance(result, ErrorResponse)


class TestGatewayTargetDelete:
    """Tests for gateway_target_delete tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Deletes target and returns DELETING status."""
        mock_boto3_client.delete_gateway_target.return_value = {
            'targetId': 't1',
            'status': 'DELETING',
        }
        tools = GatewayTargetTools(client_factory)
        result = await tools.gateway_target_delete(
            ctx=mock_ctx, gateway_identifier='gw1', target_id='t1'
        )
        assert isinstance(result, DeleteGatewayTargetResponse)
        assert result.target_id == 't1'
        assert result.target_status == 'DELETING'

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.delete_gateway_target.side_effect = ClientError(
            {
                'Error': {'Code': 'ResourceNotFoundException', 'Message': 'x'},
                'ResponseMetadata': {'HTTPStatusCode': 404},
            },
            'DeleteGatewayTarget',
        )
        tools = GatewayTargetTools(client_factory)
        result = await tools.gateway_target_delete(
            ctx=mock_ctx, gateway_identifier='gw1', target_id='bad'
        )
        assert isinstance(result, ErrorResponse)


class TestGatewayTargetList:
    """Tests for gateway_target_list tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns list of targets with pagination token."""
        mock_boto3_client.list_gateway_targets.return_value = {
            'items': [
                {'targetId': 't1', 'status': 'READY', 'name': 'A'},
                {'targetId': 't2', 'status': 'CREATING', 'name': 'B'},
            ],
            'nextToken': 'tok',
        }
        tools = GatewayTargetTools(client_factory)
        result = await tools.gateway_target_list(ctx=mock_ctx, gateway_identifier='gw1')
        assert isinstance(result, ListGatewayTargetsResponse)
        assert len(result.targets) == 2
        assert result.next_token == 'tok'

    @pytest.mark.asyncio
    async def test_with_pagination(self, mock_ctx, client_factory, mock_boto3_client):
        """Passes pagination params to API."""
        mock_boto3_client.list_gateway_targets.return_value = {'items': []}
        tools = GatewayTargetTools(client_factory)
        result = await tools.gateway_target_list(
            ctx=mock_ctx, gateway_identifier='gw1', max_results=10, next_token='p'
        )
        assert isinstance(result, ListGatewayTargetsResponse)
        mock_boto3_client.list_gateway_targets.assert_called_once_with(
            gatewayIdentifier='gw1', maxResults=10, nextToken='p'
        )

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.list_gateway_targets.side_effect = ClientError(
            {
                'Error': {'Code': 'ValidationException', 'Message': 'x'},
                'ResponseMetadata': {'HTTPStatusCode': 400},
            },
            'ListGatewayTargets',
        )
        tools = GatewayTargetTools(client_factory)
        result = await tools.gateway_target_list(ctx=mock_ctx, gateway_identifier='bad')
        assert isinstance(result, ErrorResponse)


class TestGatewayTargetSynchronize:
    """Tests for gateway_target_synchronize tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Synchronizes targets and returns target list."""
        mock_boto3_client.synchronize_gateway_targets.return_value = {
            'targets': [{'targetId': 't1', 'status': 'SYNCHRONIZING'}]
        }
        tools = GatewayTargetTools(client_factory)
        result = await tools.gateway_target_synchronize(
            ctx=mock_ctx,
            gateway_identifier='gw1',
            target_id_list=['t123456789'],
        )
        assert isinstance(result, SynchronizeTargetsResponse)
        assert result.status == 'success'
        assert len(result.targets) == 1
        mock_boto3_client.synchronize_gateway_targets.assert_called_once_with(
            gatewayIdentifier='gw1', targetIdList=['t123456789']
        )

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.synchronize_gateway_targets.side_effect = ClientError(
            {
                'Error': {'Code': 'ConflictException', 'Message': 'x'},
                'ResponseMetadata': {'HTTPStatusCode': 409},
            },
            'SynchronizeGatewayTargets',
        )
        tools = GatewayTargetTools(client_factory)
        result = await tools.gateway_target_synchronize(
            ctx=mock_ctx, gateway_identifier='gw1', target_id_list=['t1']
        )
        assert isinstance(result, ErrorResponse)
