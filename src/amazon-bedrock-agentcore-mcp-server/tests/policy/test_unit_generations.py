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

"""Unit tests for Policy generation tools."""

import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.policy.generations import (
    PolicyGenerationTools,
)
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.policy.models import (
    ErrorResponse,
    ListPolicyGenerationAssetsResponse,
    ListPolicyGenerationsResponse,
    PolicyGenerationResponse,
)
from botocore.exceptions import ClientError


CONTENT = {'rawText': 'Allow Admins to invoke all tools.'}
RESOURCE = {'arn': ('arn:aws:bedrock-agentcore:us-east-1:123:gateway/gw-abcdefghij')}


class TestPolicyGenerationStart:
    """Tests for policy_generation_start tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Starts generation and returns ID and status."""
        mock_boto3_client.start_policy_generation.return_value = {
            'policyGenerationId': 'gen-abcdefghij',
            'name': 'MyGen',
            'status': 'GENERATING',
        }
        tools = PolicyGenerationTools(client_factory)
        result = await tools.policy_generation_start(
            ctx=mock_ctx,
            policy_engine_id='eng-id',
            name='MyGen',
            content=CONTENT,
            resource=RESOURCE,
        )
        assert isinstance(result, PolicyGenerationResponse)
        assert result.status == 'success'
        assert 'gen-abcdefghij' in result.message
        kw = mock_boto3_client.start_policy_generation.call_args.kwargs
        assert kw['policyEngineId'] == 'eng-id'
        assert kw['name'] == 'MyGen'
        assert kw['content'] == CONTENT
        assert kw['resource'] == RESOURCE

    @pytest.mark.asyncio
    async def test_with_client_token(self, mock_ctx, client_factory, mock_boto3_client):
        """Passes client_token to the API."""
        mock_boto3_client.start_policy_generation.return_value = {
            'policyGenerationId': 'gen-id',
            'status': 'GENERATING',
        }
        tools = PolicyGenerationTools(client_factory)
        result = await tools.policy_generation_start(
            ctx=mock_ctx,
            policy_engine_id='eng-id',
            name='MyGen',
            content=CONTENT,
            resource=RESOURCE,
            client_token='a' * 33,
        )
        assert isinstance(result, PolicyGenerationResponse)
        kw = mock_boto3_client.start_policy_generation.call_args.kwargs
        assert kw['clientToken'] == 'a' * 33

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.start_policy_generation.side_effect = ClientError(
            {
                'Error': {
                    'Code': 'ServiceQuotaExceededException',
                    'Message': 'quota exceeded',
                },
                'ResponseMetadata': {'HTTPStatusCode': 402},
            },
            'StartPolicyGeneration',
        )
        tools = PolicyGenerationTools(client_factory)
        result = await tools.policy_generation_start(
            ctx=mock_ctx,
            policy_engine_id='eng-id',
            name='MyGen',
            content=CONTENT,
            resource=RESOURCE,
        )
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'
        assert 'quota exceeded' in result.message


class TestPolicyGenerationGet:
    """Tests for policy_generation_get tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns generation details on success."""
        mock_boto3_client.get_policy_generation.return_value = {
            'policyGenerationId': 'gen-id',
            'status': 'GENERATED',
            'findings': 'all good',
        }
        tools = PolicyGenerationTools(client_factory)
        result = await tools.policy_generation_get(
            ctx=mock_ctx,
            policy_engine_id='eng-id',
            policy_generation_id='gen-id',
        )
        assert isinstance(result, PolicyGenerationResponse)
        assert result.status == 'success'
        assert result.policy_generation['status'] == 'GENERATED'

    @pytest.mark.asyncio
    async def test_not_found(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse when generation not found."""
        mock_boto3_client.get_policy_generation.side_effect = ClientError(
            {
                'Error': {'Code': 'ResourceNotFoundException', 'Message': 'x'},
                'ResponseMetadata': {'HTTPStatusCode': 404},
            },
            'GetPolicyGeneration',
        )
        tools = PolicyGenerationTools(client_factory)
        result = await tools.policy_generation_get(
            ctx=mock_ctx,
            policy_engine_id='eng-id',
            policy_generation_id='nope',
        )
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'


class TestPolicyGenerationList:
    """Tests for policy_generation_list tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns list of generations with pagination token."""
        mock_boto3_client.list_policy_generations.return_value = {
            'policyGenerations': [
                {'policyGenerationId': 'g1', 'status': 'GENERATED'},
                {'policyGenerationId': 'g2', 'status': 'GENERATING'},
            ],
            'nextToken': 'tok',
        }
        tools = PolicyGenerationTools(client_factory)
        result = await tools.policy_generation_list(ctx=mock_ctx, policy_engine_id='eng-id')
        assert isinstance(result, ListPolicyGenerationsResponse)
        assert result.status == 'success'
        assert len(result.policy_generations) == 2
        assert result.next_token == 'tok'

    @pytest.mark.asyncio
    async def test_with_pagination(self, mock_ctx, client_factory, mock_boto3_client):
        """Passes pagination params to API."""
        mock_boto3_client.list_policy_generations.return_value = {
            'policyGenerations': [],
        }
        tools = PolicyGenerationTools(client_factory)
        result = await tools.policy_generation_list(
            ctx=mock_ctx,
            policy_engine_id='eng-id',
            max_results=50,
            next_token='prev',
        )
        assert isinstance(result, ListPolicyGenerationsResponse)
        kw = mock_boto3_client.list_policy_generations.call_args.kwargs
        assert kw['maxResults'] == 50
        assert kw['nextToken'] == 'prev'

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.list_policy_generations.side_effect = ClientError(
            {
                'Error': {'Code': 'ServiceException', 'Message': 'x'},
                'ResponseMetadata': {'HTTPStatusCode': 500},
            },
            'ListPolicyGenerations',
        )
        tools = PolicyGenerationTools(client_factory)
        result = await tools.policy_generation_list(ctx=mock_ctx, policy_engine_id='eng-id')
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'


class TestPolicyGenerationListAssets:
    """Tests for policy_generation_list_assets tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns list of assets with findings."""
        mock_boto3_client.list_policy_generation_assets.return_value = {
            'policyGenerationAssets': [
                {
                    'policyGenerationAssetId': 'asset-1',
                    'findings': [{'type': 'VALID'}],
                    'rawTextFragment': 'Allow Admins',
                },
                {
                    'policyGenerationAssetId': 'asset-2',
                    'findings': [{'type': 'NOT_TRANSLATABLE'}],
                    'rawTextFragment': 'Do something unclear',
                },
            ],
            'nextToken': None,
        }
        tools = PolicyGenerationTools(client_factory)
        result = await tools.policy_generation_list_assets(
            ctx=mock_ctx,
            policy_engine_id='eng-id',
            policy_generation_id='gen-id',
        )
        assert isinstance(result, ListPolicyGenerationAssetsResponse)
        assert result.status == 'success'
        assert len(result.policy_generation_assets) == 2
        assert result.next_token is None

    @pytest.mark.asyncio
    async def test_with_pagination(self, mock_ctx, client_factory, mock_boto3_client):
        """Passes pagination params to API."""
        mock_boto3_client.list_policy_generation_assets.return_value = {
            'policyGenerationAssets': [],
        }
        tools = PolicyGenerationTools(client_factory)
        result = await tools.policy_generation_list_assets(
            ctx=mock_ctx,
            policy_engine_id='eng-id',
            policy_generation_id='gen-id',
            max_results=5,
            next_token='tok',
        )
        assert isinstance(result, ListPolicyGenerationAssetsResponse)
        kw = mock_boto3_client.list_policy_generation_assets.call_args.kwargs
        assert kw['policyEngineId'] == 'eng-id'
        assert kw['policyGenerationId'] == 'gen-id'
        assert kw['maxResults'] == 5
        assert kw['nextToken'] == 'tok'

    @pytest.mark.asyncio
    async def test_empty(self, mock_ctx, client_factory, mock_boto3_client):
        """Handles empty asset list."""
        mock_boto3_client.list_policy_generation_assets.return_value = {
            'policyGenerationAssets': [],
        }
        tools = PolicyGenerationTools(client_factory)
        result = await tools.policy_generation_list_assets(
            ctx=mock_ctx,
            policy_engine_id='eng-id',
            policy_generation_id='gen-id',
        )
        assert isinstance(result, ListPolicyGenerationAssetsResponse)
        assert result.status == 'success'
        assert len(result.policy_generation_assets) == 0

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.list_policy_generation_assets.side_effect = ClientError(
            {
                'Error': {'Code': 'ResourceNotFoundException', 'Message': 'x'},
                'ResponseMetadata': {'HTTPStatusCode': 404},
            },
            'ListPolicyGenerationAssets',
        )
        tools = PolicyGenerationTools(client_factory)
        result = await tools.policy_generation_list_assets(
            ctx=mock_ctx,
            policy_engine_id='eng-id',
            policy_generation_id='nope',
        )
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'
