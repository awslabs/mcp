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

"""Unit tests for Gateway CRUD tools."""

import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.gateway.gateways import (
    GatewayTools,
)
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.gateway.models import (
    DeleteGatewayResponse,
    ErrorResponse,
    GatewayResponse,
    ListGatewaysResponse,
)
from botocore.exceptions import ClientError


class TestGatewayCreate:
    """Tests for gateway_create tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Creates gateway and returns ID and status."""
        mock_boto3_client.create_gateway.return_value = {
            'gatewayId': 'test-gateway-abc1234567',
            'name': 'TestGateway',
            'status': 'CREATING',
            'gatewayUrl': 'https://test-gateway-abc1234567.gateway...',
            'gatewayArn': 'arn:aws:bedrock-agentcore:us-east-1:123:gateway/t',
        }
        tools = GatewayTools(client_factory)
        result = await tools.gateway_create(
            ctx=mock_ctx,
            name='TestGateway',
            role_arn='arn:aws:iam::123:role/r',
            protocol_type='MCP',
            authorizer_type='AWS_IAM',
        )
        assert isinstance(result, GatewayResponse)
        assert result.status == 'success'
        assert 'test-gateway-abc1234567' in result.message
        mock_boto3_client.create_gateway.assert_called_once_with(
            name='TestGateway',
            roleArn='arn:aws:iam::123:role/r',
            protocolType='MCP',
            authorizerType='AWS_IAM',
        )

    @pytest.mark.asyncio
    async def test_with_all_params(self, mock_ctx, client_factory, mock_boto3_client):
        """Passes all optional params to the API."""
        mock_boto3_client.create_gateway.return_value = {
            'gatewayId': 'gw1',
            'status': 'CREATING',
        }
        tools = GatewayTools(client_factory)
        result = await tools.gateway_create(
            ctx=mock_ctx,
            name='TestGateway',
            role_arn='arn:aws:iam::123:role/r',
            protocol_type='MCP',
            authorizer_type='CUSTOM_JWT',
            authorizer_configuration={
                'customJWTAuthorizer': {
                    'discoveryUrl': 'https://idp.example.com/.well-known/openid-configuration',
                    'allowedClients': ['c1'],
                }
            },
            description='A gateway',
            kms_key_arn='arn:aws:kms:us-east-1:123:key/abc',
            exception_level='DEBUG',
            protocol_configuration={'mcp': {'searchType': 'SEMANTIC'}},
            policy_engine_configuration={'arn': 'arn:...', 'mode': 'LOG_ONLY'},
            interceptor_configurations=[
                {
                    'interceptor': {'lambda': {'arn': 'arn:aws:lambda:...'}},
                    'interceptionPoints': ['REQUEST'],
                }
            ],
            client_token='a' * 40,
            tags={'env': 'test'},
        )
        assert isinstance(result, GatewayResponse)
        assert result.status == 'success'
        kw = mock_boto3_client.create_gateway.call_args.kwargs
        assert kw['description'] == 'A gateway'
        assert kw['kmsKeyArn'].startswith('arn:aws:kms:')
        assert kw['exceptionLevel'] == 'DEBUG'
        assert kw['protocolConfiguration'] == {'mcp': {'searchType': 'SEMANTIC'}}
        assert kw['policyEngineConfiguration']['mode'] == 'LOG_ONLY'
        assert kw['interceptorConfigurations'][0]['interceptionPoints'] == ['REQUEST']
        assert kw['clientToken'] == 'a' * 40
        assert kw['tags'] == {'env': 'test'}

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.create_gateway.side_effect = ClientError(
            {
                'Error': {'Code': 'ValidationException', 'Message': 'bad'},
                'ResponseMetadata': {'HTTPStatusCode': 400},
            },
            'CreateGateway',
        )
        tools = GatewayTools(client_factory)
        result = await tools.gateway_create(
            ctx=mock_ctx,
            name='bad!',
            role_arn='arn:aws:iam::123:role/r',
            protocol_type='MCP',
            authorizer_type='NONE',
        )
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'


class TestGatewayGet:
    """Tests for gateway_get tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns gateway details on success."""
        mock_boto3_client.get_gateway.return_value = {
            'gatewayId': 'gw1',
            'status': 'READY',
            'name': 'Test',
            'gatewayUrl': 'https://...',
        }
        tools = GatewayTools(client_factory)
        result = await tools.gateway_get(ctx=mock_ctx, gateway_identifier='gw1')
        assert isinstance(result, GatewayResponse)
        assert result.status == 'success'
        assert result.gateway['status'] == 'READY'

    @pytest.mark.asyncio
    async def test_not_found(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse when gateway not found."""
        mock_boto3_client.get_gateway.side_effect = ClientError(
            {
                'Error': {'Code': 'ResourceNotFoundException', 'Message': 'x'},
                'ResponseMetadata': {'HTTPStatusCode': 404},
            },
            'GetGateway',
        )
        tools = GatewayTools(client_factory)
        result = await tools.gateway_get(ctx=mock_ctx, gateway_identifier='nope')
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'


class TestGatewayUpdate:
    """Tests for gateway_update tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Updates gateway and returns updated details."""
        mock_boto3_client.update_gateway.return_value = {
            'gatewayId': 'gw1',
            'status': 'UPDATING',
        }
        tools = GatewayTools(client_factory)
        result = await tools.gateway_update(
            ctx=mock_ctx,
            gateway_identifier='gw1',
            name='TestGateway',
            role_arn='arn:aws:iam::123:role/r',
            protocol_type='MCP',
            authorizer_type='AWS_IAM',
            description='Updated',
        )
        assert isinstance(result, GatewayResponse)
        assert result.status == 'success'
        kw = mock_boto3_client.update_gateway.call_args.kwargs
        assert kw['gatewayIdentifier'] == 'gw1'
        assert kw['description'] == 'Updated'

    @pytest.mark.asyncio
    async def test_with_all_params(self, mock_ctx, client_factory, mock_boto3_client):
        """Passes all optional params to the API."""
        mock_boto3_client.update_gateway.return_value = {
            'gatewayId': 'gw1',
            'status': 'UPDATING',
        }
        tools = GatewayTools(client_factory)
        result = await tools.gateway_update(
            ctx=mock_ctx,
            gateway_identifier='gw1',
            name='TestGateway',
            role_arn='arn:aws:iam::123:role/r',
            protocol_type='MCP',
            authorizer_type='CUSTOM_JWT',
            authorizer_configuration={'customJWTAuthorizer': {'discoveryUrl': 'x'}},
            description='D',
            kms_key_arn='arn:aws:kms:...',
            exception_level='DEBUG',
            protocol_configuration={'mcp': {}},
            policy_engine_configuration={'arn': 'a', 'mode': 'ENFORCE'},
            interceptor_configurations=[
                {
                    'interceptor': {'lambda': {'arn': 'a'}},
                    'interceptionPoints': ['RESPONSE'],
                }
            ],
        )
        assert isinstance(result, GatewayResponse)
        kw = mock_boto3_client.update_gateway.call_args.kwargs
        assert kw['kmsKeyArn'].startswith('arn:aws:kms:')
        assert kw['exceptionLevel'] == 'DEBUG'
        assert kw['policyEngineConfiguration']['mode'] == 'ENFORCE'

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.update_gateway.side_effect = ClientError(
            {
                'Error': {'Code': 'ConflictException', 'Message': 'c'},
                'ResponseMetadata': {'HTTPStatusCode': 409},
            },
            'UpdateGateway',
        )
        tools = GatewayTools(client_factory)
        result = await tools.gateway_update(
            ctx=mock_ctx,
            gateway_identifier='gw1',
            name='T',
            role_arn='r',
            protocol_type='MCP',
            authorizer_type='AWS_IAM',
        )
        assert isinstance(result, ErrorResponse)


class TestGatewayDelete:
    """Tests for gateway_delete tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Deletes gateway and returns DELETING status."""
        mock_boto3_client.delete_gateway.return_value = {
            'gatewayId': 'gw1',
            'status': 'DELETING',
        }
        tools = GatewayTools(client_factory)
        result = await tools.gateway_delete(ctx=mock_ctx, gateway_identifier='gw1')
        assert isinstance(result, DeleteGatewayResponse)
        assert result.status == 'success'
        assert result.gateway_id == 'gw1'
        assert result.gateway_status == 'DELETING'

    @pytest.mark.asyncio
    async def test_conflict_has_targets(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse when gateway still has targets."""
        mock_boto3_client.delete_gateway.side_effect = ClientError(
            {
                'Error': {'Code': 'ConflictException', 'Message': 'has targets'},
                'ResponseMetadata': {'HTTPStatusCode': 409},
            },
            'DeleteGateway',
        )
        tools = GatewayTools(client_factory)
        result = await tools.gateway_delete(ctx=mock_ctx, gateway_identifier='gw1')
        assert isinstance(result, ErrorResponse)
        assert result.error_type == 'ConflictException'


class TestGatewayList:
    """Tests for gateway_list tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns list of gateways with pagination token."""
        mock_boto3_client.list_gateways.return_value = {
            'items': [
                {'gatewayId': 'gw1', 'status': 'READY', 'name': 'A'},
                {'gatewayId': 'gw2', 'status': 'CREATING', 'name': 'B'},
            ],
            'nextToken': 'tok123',
        }
        tools = GatewayTools(client_factory)
        result = await tools.gateway_list(ctx=mock_ctx)
        assert isinstance(result, ListGatewaysResponse)
        assert result.status == 'success'
        assert len(result.gateways) == 2
        assert result.next_token == 'tok123'

    @pytest.mark.asyncio
    async def test_with_pagination(self, mock_ctx, client_factory, mock_boto3_client):
        """Passes pagination params to API."""
        mock_boto3_client.list_gateways.return_value = {'items': []}
        tools = GatewayTools(client_factory)
        result = await tools.gateway_list(ctx=mock_ctx, max_results=50, next_token='prev')
        assert isinstance(result, ListGatewaysResponse)
        mock_boto3_client.list_gateways.assert_called_once_with(maxResults=50, nextToken='prev')

    @pytest.mark.asyncio
    async def test_empty(self, mock_ctx, client_factory, mock_boto3_client):
        """Handles empty gateway list."""
        mock_boto3_client.list_gateways.return_value = {'items': []}
        tools = GatewayTools(client_factory)
        result = await tools.gateway_list(ctx=mock_ctx)
        assert isinstance(result, ListGatewaysResponse)
        assert len(result.gateways) == 0

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.list_gateways.side_effect = ClientError(
            {
                'Error': {'Code': 'ServiceException', 'Message': 'x'},
                'ResponseMetadata': {'HTTPStatusCode': 500},
            },
            'ListGateways',
        )
        tools = GatewayTools(client_factory)
        result = await tools.gateway_list(ctx=mock_ctx)
        assert isinstance(result, ErrorResponse)
