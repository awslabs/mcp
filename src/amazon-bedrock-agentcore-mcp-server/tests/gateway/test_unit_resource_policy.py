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

"""Unit tests for Gateway Resource Policy tools."""

import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.gateway.models import (
    DeleteResourcePolicyResponse,
    ErrorResponse,
    ResourcePolicyResponse,
)
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.gateway.resource_policy import (
    ResourcePolicyTools,
)
from botocore.exceptions import ClientError


RESOURCE_ARN = 'arn:aws:bedrock-agentcore:us-east-1:123456789012:gateway/gw1'
POLICY_DOC = (
    '{"Version":"2012-10-17","Statement":[{"Effect":"Allow",'
    '"Principal":{"AWS":"arn:aws:iam::123:root"},'
    '"Action":"bedrock-agentcore:InvokeGateway","Resource":"*"}]}'
)


class TestGatewayResourcePolicyPut:
    """Tests for gateway_resource_policy_put tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Puts policy and returns policy content."""
        mock_boto3_client.put_resource_policy.return_value = {'policy': POLICY_DOC}
        tools = ResourcePolicyTools(client_factory)
        result = await tools.gateway_resource_policy_put(
            ctx=mock_ctx, resource_arn=RESOURCE_ARN, policy=POLICY_DOC
        )
        assert isinstance(result, ResourcePolicyResponse)
        assert result.status == 'success'
        assert 'Allow' in result.policy
        mock_boto3_client.put_resource_policy.assert_called_once_with(
            resourceArn=RESOURCE_ARN, policy=POLICY_DOC
        )

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.put_resource_policy.side_effect = ClientError(
            {
                'Error': {'Code': 'ValidationException', 'Message': 'bad'},
                'ResponseMetadata': {'HTTPStatusCode': 400},
            },
            'PutResourcePolicy',
        )
        tools = ResourcePolicyTools(client_factory)
        result = await tools.gateway_resource_policy_put(
            ctx=mock_ctx, resource_arn=RESOURCE_ARN, policy='bad'
        )
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'


class TestGatewayResourcePolicyGet:
    """Tests for gateway_resource_policy_get tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns policy content on success."""
        mock_boto3_client.get_resource_policy.return_value = {'policy': POLICY_DOC}
        tools = ResourcePolicyTools(client_factory)
        result = await tools.gateway_resource_policy_get(ctx=mock_ctx, resource_arn=RESOURCE_ARN)
        assert isinstance(result, ResourcePolicyResponse)
        assert result.status == 'success'
        assert 'Allow' in result.policy

    @pytest.mark.asyncio
    async def test_not_found(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse when no policy attached."""
        mock_boto3_client.get_resource_policy.side_effect = ClientError(
            {
                'Error': {'Code': 'ResourceNotFoundException', 'Message': 'x'},
                'ResponseMetadata': {'HTTPStatusCode': 404},
            },
            'GetResourcePolicy',
        )
        tools = ResourcePolicyTools(client_factory)
        result = await tools.gateway_resource_policy_get(ctx=mock_ctx, resource_arn=RESOURCE_ARN)
        assert isinstance(result, ErrorResponse)


class TestGatewayResourcePolicyDelete:
    """Tests for gateway_resource_policy_delete tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Deletes policy and returns success."""
        mock_boto3_client.delete_resource_policy.return_value = {}
        tools = ResourcePolicyTools(client_factory)
        result = await tools.gateway_resource_policy_delete(
            ctx=mock_ctx, resource_arn=RESOURCE_ARN
        )
        assert isinstance(result, DeleteResourcePolicyResponse)
        assert result.status == 'success'
        assert result.resource_arn == RESOURCE_ARN
        mock_boto3_client.delete_resource_policy.assert_called_once_with(resourceArn=RESOURCE_ARN)

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.delete_resource_policy.side_effect = ClientError(
            {
                'Error': {'Code': 'AccessDeniedException', 'Message': 'x'},
                'ResponseMetadata': {'HTTPStatusCode': 403},
            },
            'DeleteResourcePolicy',
        )
        tools = ResourcePolicyTools(client_factory)
        result = await tools.gateway_resource_policy_delete(
            ctx=mock_ctx, resource_arn=RESOURCE_ARN
        )
        assert isinstance(result, ErrorResponse)
        assert result.error_type == 'AccessDeniedException'
