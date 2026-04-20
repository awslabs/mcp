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

"""Unit tests for Identity resource policy tools."""

import json
import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.identity.models import (
    DeleteResourcePolicyResponse,
    ErrorResponse,
    ResourcePolicyResponse,
)
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.identity.resource_policy import (
    ResourcePolicyTools,
)
from botocore.exceptions import ClientError


_SAMPLE_POLICY = {
    'Version': '2012-10-17',
    'Statement': [
        {
            'Effect': 'Allow',
            'Principal': {'AWS': 'arn:aws:iam::123456789012:role/invoker'},
            'Action': 'bedrock-agentcore:InvokeAgentRuntime',
            'Resource': '*',
        }
    ],
}


class TestIdentityPutResourcePolicy:
    """Tests for identity_put_resource_policy tool."""

    @pytest.mark.asyncio
    async def test_success_serializes_policy_to_json(
        self, mock_ctx, client_factory, mock_boto3_client
    ):
        """Serializes the dict policy to a JSON string before the API call."""
        mock_boto3_client.put_resource_policy.return_value = {
            'resourceArn': 'arn:aws:bedrock-agentcore:us-east-1:123:agent-runtime/my-agent',
            'policy': json.dumps(_SAMPLE_POLICY),
        }
        tools = ResourcePolicyTools(client_factory)
        result = await tools.identity_put_resource_policy(
            ctx=mock_ctx,
            resource_arn='arn:aws:bedrock-agentcore:us-east-1:123:agent-runtime/my-agent',
            policy_document=_SAMPLE_POLICY,
        )
        assert isinstance(result, ResourcePolicyResponse)
        assert result.status == 'success'
        assert result.resource_arn == (
            'arn:aws:bedrock-agentcore:us-east-1:123:agent-runtime/my-agent'
        )
        # The stored policy is parsed back into a dict in the response
        assert result.policy == _SAMPLE_POLICY
        # Confirm the API was called with the serialized JSON string
        kw = mock_boto3_client.put_resource_policy.call_args.kwargs
        assert kw['resourceArn'] == (
            'arn:aws:bedrock-agentcore:us-east-1:123:agent-runtime/my-agent'
        )
        assert isinstance(kw['policy'], str)
        assert json.loads(kw['policy']) == _SAMPLE_POLICY

    @pytest.mark.asyncio
    async def test_response_without_policy_field(
        self, mock_ctx, client_factory, mock_boto3_client
    ):
        """Falls back to the input policy_document when response lacks 'policy'."""
        mock_boto3_client.put_resource_policy.return_value = {
            'resourceArn': 'arn:aws:bedrock-agentcore:...:my-agent',
        }
        tools = ResourcePolicyTools(client_factory)
        result = await tools.identity_put_resource_policy(
            ctx=mock_ctx,
            resource_arn='arn:aws:bedrock-agentcore:...:my-agent',
            policy_document=_SAMPLE_POLICY,
        )
        assert isinstance(result, ResourcePolicyResponse)
        assert result.policy == _SAMPLE_POLICY

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError (e.g. malformed policy)."""
        mock_boto3_client.put_resource_policy.side_effect = ClientError(
            {
                'Error': {'Code': 'ValidationException', 'Message': 'bad policy'},
                'ResponseMetadata': {'HTTPStatusCode': 400},
            },
            'PutResourcePolicy',
        )
        tools = ResourcePolicyTools(client_factory)
        result = await tools.identity_put_resource_policy(
            ctx=mock_ctx,
            resource_arn='arn:aws:bedrock-agentcore:...:x',
            policy_document={'Version': '2012-10-17'},
        )
        assert isinstance(result, ErrorResponse)
        assert result.error_type == 'ValidationException'


class TestIdentityGetResourcePolicy:
    """Tests for identity_get_resource_policy tool."""

    @pytest.mark.asyncio
    async def test_success_parses_policy_json(self, mock_ctx, client_factory, mock_boto3_client):
        """Parses the JSON-string policy back into a dict."""
        mock_boto3_client.get_resource_policy.return_value = {
            'resourceArn': 'arn:aws:bedrock-agentcore:...:my-agent',
            'policy': json.dumps(_SAMPLE_POLICY),
        }
        tools = ResourcePolicyTools(client_factory)
        result = await tools.identity_get_resource_policy(
            ctx=mock_ctx,
            resource_arn='arn:aws:bedrock-agentcore:...:my-agent',
        )
        assert isinstance(result, ResourcePolicyResponse)
        assert result.status == 'success'
        assert result.policy == _SAMPLE_POLICY

    @pytest.mark.asyncio
    async def test_no_policy_attached(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns success with empty policy when resource has none attached."""
        mock_boto3_client.get_resource_policy.return_value = {
            'resourceArn': 'arn:aws:bedrock-agentcore:...:my-agent',
        }
        tools = ResourcePolicyTools(client_factory)
        result = await tools.identity_get_resource_policy(
            ctx=mock_ctx,
            resource_arn='arn:aws:bedrock-agentcore:...:my-agent',
        )
        assert isinstance(result, ResourcePolicyResponse)
        assert result.status == 'success'
        assert result.policy == {}
        assert 'No resource policy' in result.message

    @pytest.mark.asyncio
    async def test_invalid_json_surfaces_as_error(
        self, mock_ctx, client_factory, mock_boto3_client
    ):
        """Corrupted JSON in response surfaces as an error via the generic handler."""
        mock_boto3_client.get_resource_policy.return_value = {
            'resourceArn': 'arn:aws:bedrock-agentcore:...:my-agent',
            'policy': 'not-valid-json{',
        }
        tools = ResourcePolicyTools(client_factory)
        result = await tools.identity_get_resource_policy(
            ctx=mock_ctx,
            resource_arn='arn:aws:bedrock-agentcore:...:my-agent',
        )
        assert isinstance(result, ErrorResponse)
        # JSONDecodeError -> falls into generic Exception branch
        assert result.error_type == 'JSONDecodeError'

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.get_resource_policy.side_effect = ClientError(
            {
                'Error': {'Code': 'ResourceNotFoundException', 'Message': 'no resource'},
                'ResponseMetadata': {'HTTPStatusCode': 404},
            },
            'GetResourcePolicy',
        )
        tools = ResourcePolicyTools(client_factory)
        result = await tools.identity_get_resource_policy(
            ctx=mock_ctx, resource_arn='arn:aws:bedrock-agentcore:...:missing'
        )
        assert isinstance(result, ErrorResponse)
        assert result.error_type == 'ResourceNotFoundException'


class TestIdentityDeleteResourcePolicy:
    """Tests for identity_delete_resource_policy tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Deletes a resource policy."""
        mock_boto3_client.delete_resource_policy.return_value = {}
        tools = ResourcePolicyTools(client_factory)
        result = await tools.identity_delete_resource_policy(
            ctx=mock_ctx,
            resource_arn='arn:aws:bedrock-agentcore:...:my-agent',
        )
        assert isinstance(result, DeleteResourcePolicyResponse)
        assert result.status == 'success'
        assert result.resource_arn == 'arn:aws:bedrock-agentcore:...:my-agent'
        mock_boto3_client.delete_resource_policy.assert_called_once_with(
            resourceArn='arn:aws:bedrock-agentcore:...:my-agent'
        )

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.delete_resource_policy.side_effect = ClientError(
            {
                'Error': {'Code': 'ResourceNotFoundException', 'Message': 'no policy'},
                'ResponseMetadata': {'HTTPStatusCode': 404},
            },
            'DeleteResourcePolicy',
        )
        tools = ResourcePolicyTools(client_factory)
        result = await tools.identity_delete_resource_policy(
            ctx=mock_ctx, resource_arn='arn:aws:bedrock-agentcore:...:missing'
        )
        assert isinstance(result, ErrorResponse)
        assert result.error_type == 'ResourceNotFoundException'
