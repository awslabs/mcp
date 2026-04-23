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

"""Unit tests for Policy engine tools."""

import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.policy.engines import (
    PolicyEngineTools,
)
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.policy.models import (
    DeletePolicyEngineResponse,
    ErrorResponse,
    ListPolicyEnginesResponse,
    PolicyEngineResponse,
)
from botocore.exceptions import ClientError


class TestPolicyEngineCreate:
    """Tests for policy_engine_create tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Creates policy engine and returns ID and status."""
        mock_boto3_client.create_policy_engine.return_value = {
            'policyEngineId': 'ProdAuth-abcdefghij',
            'name': 'ProdAuth',
            'status': 'CREATING',
            'policyEngineArn': (
                'arn:aws:bedrock-agentcore:us-east-1:123:policy-engine/ProdAuth-abcdefghij'
            ),
        }
        tools = PolicyEngineTools(client_factory)
        result = await tools.policy_engine_create(ctx=mock_ctx, name='ProdAuth')
        assert isinstance(result, PolicyEngineResponse)
        assert result.status == 'success'
        assert 'ProdAuth-abcdefghij' in result.message
        assert result.policy_engine['name'] == 'ProdAuth'
        mock_boto3_client.create_policy_engine.assert_called_once_with(name='ProdAuth')

    @pytest.mark.asyncio
    async def test_with_all_params(self, mock_ctx, client_factory, mock_boto3_client):
        """Passes all optional params to the API."""
        mock_boto3_client.create_policy_engine.return_value = {
            'policyEngineId': 'eng-id',
            'status': 'CREATING',
        }
        tools = PolicyEngineTools(client_factory)
        result = await tools.policy_engine_create(
            ctx=mock_ctx,
            name='MyEngine',
            description='A production engine',
            encryption_key_arn='arn:aws:kms:us-east-1:123:key/abc',
            client_token='a' * 33,
            tags={'env': 'prod'},
        )
        assert isinstance(result, PolicyEngineResponse)
        assert result.status == 'success'
        kw = mock_boto3_client.create_policy_engine.call_args.kwargs
        assert kw['description'] == 'A production engine'
        assert kw['encryptionKeyArn'] == 'arn:aws:kms:us-east-1:123:key/abc'
        assert kw['clientToken'] == 'a' * 33
        assert kw['tags'] == {'env': 'prod'}

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.create_policy_engine.side_effect = ClientError(
            {
                'Error': {'Code': 'ValidationException', 'Message': 'bad name'},
                'ResponseMetadata': {'HTTPStatusCode': 400},
            },
            'CreatePolicyEngine',
        )
        tools = PolicyEngineTools(client_factory)
        result = await tools.policy_engine_create(ctx=mock_ctx, name='bad!')
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'
        assert 'bad name' in result.message


class TestPolicyEngineGet:
    """Tests for policy_engine_get tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns policy engine details on success."""
        mock_boto3_client.get_policy_engine.return_value = {
            'policyEngineId': 'eng-id',
            'status': 'ACTIVE',
            'name': 'ProdAuth',
        }
        tools = PolicyEngineTools(client_factory)
        result = await tools.policy_engine_get(ctx=mock_ctx, policy_engine_id='eng-id')
        assert isinstance(result, PolicyEngineResponse)
        assert result.status == 'success'
        assert result.policy_engine['status'] == 'ACTIVE'

    @pytest.mark.asyncio
    async def test_not_found(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse when engine not found."""
        mock_boto3_client.get_policy_engine.side_effect = ClientError(
            {
                'Error': {'Code': 'ResourceNotFoundException', 'Message': 'x'},
                'ResponseMetadata': {'HTTPStatusCode': 404},
            },
            'GetPolicyEngine',
        )
        tools = PolicyEngineTools(client_factory)
        result = await tools.policy_engine_get(ctx=mock_ctx, policy_engine_id='nonexist')
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'


class TestPolicyEngineUpdate:
    """Tests for policy_engine_update tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Updates policy engine description and returns response."""
        mock_boto3_client.update_policy_engine.return_value = {
            'policyEngineId': 'eng-id',
            'status': 'UPDATING',
        }
        tools = PolicyEngineTools(client_factory)
        result = await tools.policy_engine_update(
            ctx=mock_ctx,
            policy_engine_id='eng-id',
            description={'optionalValue': 'Updated desc'},
        )
        assert isinstance(result, PolicyEngineResponse)
        assert result.status == 'success'
        mock_boto3_client.update_policy_engine.assert_called_once_with(
            policyEngineId='eng-id',
            description={'optionalValue': 'Updated desc'},
        )

    @pytest.mark.asyncio
    async def test_no_params_omits_description(self, mock_ctx, client_factory, mock_boto3_client):
        """Omitting description leaves the field out of the API call."""
        mock_boto3_client.update_policy_engine.return_value = {
            'policyEngineId': 'eng-id',
            'status': 'ACTIVE',
        }
        tools = PolicyEngineTools(client_factory)
        result = await tools.policy_engine_update(ctx=mock_ctx, policy_engine_id='eng-id')
        assert isinstance(result, PolicyEngineResponse)
        kw = mock_boto3_client.update_policy_engine.call_args.kwargs
        assert 'description' not in kw
        assert kw['policyEngineId'] == 'eng-id'

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.update_policy_engine.side_effect = ClientError(
            {
                'Error': {'Code': 'ConflictException', 'Message': 'conflict'},
                'ResponseMetadata': {'HTTPStatusCode': 409},
            },
            'UpdatePolicyEngine',
        )
        tools = PolicyEngineTools(client_factory)
        result = await tools.policy_engine_update(ctx=mock_ctx, policy_engine_id='eng-id')
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'


class TestPolicyEngineDelete:
    """Tests for policy_engine_delete tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Deletes engine and returns DELETING status."""
        mock_boto3_client.delete_policy_engine.return_value = {
            'policyEngineId': 'eng-id',
            'status': 'DELETING',
        }
        tools = PolicyEngineTools(client_factory)
        result = await tools.policy_engine_delete(ctx=mock_ctx, policy_engine_id='eng-id')
        assert isinstance(result, DeletePolicyEngineResponse)
        assert result.status == 'success'
        assert result.policy_engine_id == 'eng-id'
        assert result.policy_engine_status == 'DELETING'

    @pytest.mark.asyncio
    async def test_conflict_when_has_policies(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ConflictException (engine has policies)."""
        mock_boto3_client.delete_policy_engine.side_effect = ClientError(
            {
                'Error': {
                    'Code': 'ConflictException',
                    'Message': 'engine has associated policies',
                },
                'ResponseMetadata': {'HTTPStatusCode': 409},
            },
            'DeletePolicyEngine',
        )
        tools = PolicyEngineTools(client_factory)
        result = await tools.policy_engine_delete(ctx=mock_ctx, policy_engine_id='eng-id')
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'
        assert 'associated policies' in result.message


class TestPolicyEngineList:
    """Tests for policy_engine_list tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns list of policy engines with pagination token."""
        mock_boto3_client.list_policy_engines.return_value = {
            'policyEngines': [
                {'policyEngineId': 'e1', 'status': 'ACTIVE'},
                {'policyEngineId': 'e2', 'status': 'CREATING'},
            ],
            'nextToken': 'tok123',
        }
        tools = PolicyEngineTools(client_factory)
        result = await tools.policy_engine_list(ctx=mock_ctx)
        assert isinstance(result, ListPolicyEnginesResponse)
        assert result.status == 'success'
        assert len(result.policy_engines) == 2
        assert result.next_token == 'tok123'

    @pytest.mark.asyncio
    async def test_with_pagination(self, mock_ctx, client_factory, mock_boto3_client):
        """Passes pagination params to API."""
        mock_boto3_client.list_policy_engines.return_value = {
            'policyEngines': [],
            'nextToken': None,
        }
        tools = PolicyEngineTools(client_factory)
        result = await tools.policy_engine_list(ctx=mock_ctx, max_results=10, next_token='prev')
        assert isinstance(result, ListPolicyEnginesResponse)
        assert result.status == 'success'
        mock_boto3_client.list_policy_engines.assert_called_once_with(
            maxResults=10, nextToken='prev'
        )

    @pytest.mark.asyncio
    async def test_empty(self, mock_ctx, client_factory, mock_boto3_client):
        """Handles empty policy engine list."""
        mock_boto3_client.list_policy_engines.return_value = {'policyEngines': []}
        tools = PolicyEngineTools(client_factory)
        result = await tools.policy_engine_list(ctx=mock_ctx)
        assert isinstance(result, ListPolicyEnginesResponse)
        assert result.status == 'success'
        assert len(result.policy_engines) == 0

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.list_policy_engines.side_effect = ClientError(
            {
                'Error': {'Code': 'ServiceException', 'Message': 'x'},
                'ResponseMetadata': {'HTTPStatusCode': 500},
            },
            'ListPolicyEngines',
        )
        tools = PolicyEngineTools(client_factory)
        result = await tools.policy_engine_list(ctx=mock_ctx)
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'
