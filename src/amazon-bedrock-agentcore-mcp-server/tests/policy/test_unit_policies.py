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

"""Unit tests for Policy CRUD tools."""

import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.policy.models import (
    DeletePolicyResponse,
    ErrorResponse,
    ListPoliciesResponse,
    PolicyResponse,
)
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.policy.policies import (
    PolicyTools,
)
from botocore.exceptions import ClientError


CEDAR_DEFINITION = {'cedar': {'statement': 'permit(principal, action, resource);'}}


class TestPolicyCreate:
    """Tests for policy_create tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Creates policy and returns ID and status."""
        mock_boto3_client.create_policy.return_value = {
            'policyId': 'pol-abcdefghij',
            'name': 'AdminAccess',
            'status': 'CREATING',
        }
        tools = PolicyTools(client_factory)
        result = await tools.policy_create(
            ctx=mock_ctx,
            policy_engine_id='eng-id',
            name='AdminAccess',
            definition=CEDAR_DEFINITION,
        )
        assert isinstance(result, PolicyResponse)
        assert result.status == 'success'
        assert 'pol-abcdefghij' in result.message
        kw = mock_boto3_client.create_policy.call_args.kwargs
        assert kw['policyEngineId'] == 'eng-id'
        assert kw['name'] == 'AdminAccess'
        assert kw['definition'] == CEDAR_DEFINITION

    @pytest.mark.asyncio
    async def test_with_all_params(self, mock_ctx, client_factory, mock_boto3_client):
        """Passes all optional params to the API."""
        mock_boto3_client.create_policy.return_value = {
            'policyId': 'pol-id',
            'status': 'CREATING',
        }
        tools = PolicyTools(client_factory)
        result = await tools.policy_create(
            ctx=mock_ctx,
            policy_engine_id='eng-id',
            name='P1',
            definition=CEDAR_DEFINITION,
            description='A test policy',
            validation_mode='IGNORE_ALL_FINDINGS',
            client_token='a' * 33,
        )
        assert isinstance(result, PolicyResponse)
        kw = mock_boto3_client.create_policy.call_args.kwargs
        assert kw['description'] == 'A test policy'
        assert kw['validationMode'] == 'IGNORE_ALL_FINDINGS'
        assert kw['clientToken'] == 'a' * 33

    @pytest.mark.asyncio
    async def test_with_generation_reference(self, mock_ctx, client_factory, mock_boto3_client):
        """Supports the policyGeneration union variant for definition."""
        mock_boto3_client.create_policy.return_value = {
            'policyId': 'pol-id',
            'status': 'CREATING',
        }
        gen_def = {
            'policyGeneration': {
                'policyGenerationId': 'gen-abcdefghij',
                'policyGenerationAssetId': 'asset-abcdefghij',
            }
        }
        tools = PolicyTools(client_factory)
        result = await tools.policy_create(
            ctx=mock_ctx,
            policy_engine_id='eng-id',
            name='FromGen',
            definition=gen_def,
        )
        assert isinstance(result, PolicyResponse)
        kw = mock_boto3_client.create_policy.call_args.kwargs
        assert kw['definition'] == gen_def

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.create_policy.side_effect = ClientError(
            {
                'Error': {
                    'Code': 'ValidationException',
                    'Message': 'cedar syntax error',
                },
                'ResponseMetadata': {'HTTPStatusCode': 400},
            },
            'CreatePolicy',
        )
        tools = PolicyTools(client_factory)
        result = await tools.policy_create(
            ctx=mock_ctx,
            policy_engine_id='eng-id',
            name='Bad',
            definition={'cedar': {'statement': 'invalid'}},
        )
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'
        assert 'cedar syntax error' in result.message


class TestPolicyGet:
    """Tests for policy_get tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns policy details on success."""
        mock_boto3_client.get_policy.return_value = {
            'policyId': 'pol-id',
            'status': 'ACTIVE',
            'name': 'P1',
            'definition': CEDAR_DEFINITION,
        }
        tools = PolicyTools(client_factory)
        result = await tools.policy_get(
            ctx=mock_ctx, policy_engine_id='eng-id', policy_id='pol-id'
        )
        assert isinstance(result, PolicyResponse)
        assert result.status == 'success'
        assert result.policy['status'] == 'ACTIVE'

    @pytest.mark.asyncio
    async def test_not_found(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse when policy not found."""
        mock_boto3_client.get_policy.side_effect = ClientError(
            {
                'Error': {'Code': 'ResourceNotFoundException', 'Message': 'x'},
                'ResponseMetadata': {'HTTPStatusCode': 404},
            },
            'GetPolicy',
        )
        tools = PolicyTools(client_factory)
        result = await tools.policy_get(
            ctx=mock_ctx, policy_engine_id='eng-id', policy_id='nonexist'
        )
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'


class TestPolicyUpdate:
    """Tests for policy_update tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Updates policy and returns response."""
        mock_boto3_client.update_policy.return_value = {
            'policyId': 'pol-id',
            'status': 'UPDATING',
        }
        tools = PolicyTools(client_factory)
        result = await tools.policy_update(
            ctx=mock_ctx,
            policy_engine_id='eng-id',
            policy_id='pol-id',
            definition=CEDAR_DEFINITION,
        )
        assert isinstance(result, PolicyResponse)
        assert result.status == 'success'
        kw = mock_boto3_client.update_policy.call_args.kwargs
        assert kw['policyEngineId'] == 'eng-id'
        assert kw['policyId'] == 'pol-id'
        assert kw['definition'] == CEDAR_DEFINITION

    @pytest.mark.asyncio
    async def test_with_all_params(self, mock_ctx, client_factory, mock_boto3_client):
        """Passes all optional params to the API."""
        mock_boto3_client.update_policy.return_value = {
            'policyId': 'pol-id',
            'status': 'UPDATING',
        }
        tools = PolicyTools(client_factory)
        result = await tools.policy_update(
            ctx=mock_ctx,
            policy_engine_id='eng-id',
            policy_id='pol-id',
            definition=CEDAR_DEFINITION,
            description={'optionalValue': 'new desc'},
            validation_mode='IGNORE_ALL_FINDINGS',
        )
        assert isinstance(result, PolicyResponse)
        kw = mock_boto3_client.update_policy.call_args.kwargs
        assert kw['description'] == {'optionalValue': 'new desc'}
        assert kw['validationMode'] == 'IGNORE_ALL_FINDINGS'

    @pytest.mark.asyncio
    async def test_no_params_updates_with_just_ids(
        self, mock_ctx, client_factory, mock_boto3_client
    ):
        """Omitting all optional fields sends only the IDs."""
        mock_boto3_client.update_policy.return_value = {
            'policyId': 'pol-id',
            'status': 'ACTIVE',
        }
        tools = PolicyTools(client_factory)
        result = await tools.policy_update(
            ctx=mock_ctx, policy_engine_id='eng-id', policy_id='pol-id'
        )
        assert isinstance(result, PolicyResponse)
        kw = mock_boto3_client.update_policy.call_args.kwargs
        assert 'definition' not in kw
        assert 'description' not in kw
        assert 'validationMode' not in kw

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.update_policy.side_effect = ClientError(
            {
                'Error': {'Code': 'ConflictException', 'Message': 'conflict'},
                'ResponseMetadata': {'HTTPStatusCode': 409},
            },
            'UpdatePolicy',
        )
        tools = PolicyTools(client_factory)
        result = await tools.policy_update(
            ctx=mock_ctx, policy_engine_id='eng-id', policy_id='pol-id'
        )
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'


class TestPolicyDelete:
    """Tests for policy_delete tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Deletes policy and returns DELETING status."""
        mock_boto3_client.delete_policy.return_value = {
            'policyId': 'pol-id',
            'status': 'DELETING',
        }
        tools = PolicyTools(client_factory)
        result = await tools.policy_delete(
            ctx=mock_ctx, policy_engine_id='eng-id', policy_id='pol-id'
        )
        assert isinstance(result, DeletePolicyResponse)
        assert result.status == 'success'
        assert result.policy_id == 'pol-id'
        assert result.policy_status == 'DELETING'

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.delete_policy.side_effect = ClientError(
            {
                'Error': {'Code': 'ResourceNotFoundException', 'Message': 'x'},
                'ResponseMetadata': {'HTTPStatusCode': 404},
            },
            'DeletePolicy',
        )
        tools = PolicyTools(client_factory)
        result = await tools.policy_delete(
            ctx=mock_ctx, policy_engine_id='eng-id', policy_id='bad'
        )
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'


class TestPolicyList:
    """Tests for policy_list tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns list of policies with pagination token."""
        mock_boto3_client.list_policies.return_value = {
            'policies': [
                {'policyId': 'p1', 'status': 'ACTIVE'},
                {'policyId': 'p2', 'status': 'ACTIVE'},
            ],
            'nextToken': 'tok123',
        }
        tools = PolicyTools(client_factory)
        result = await tools.policy_list(ctx=mock_ctx, policy_engine_id='eng-id')
        assert isinstance(result, ListPoliciesResponse)
        assert result.status == 'success'
        assert len(result.policies) == 2
        assert result.next_token == 'tok123'

    @pytest.mark.asyncio
    async def test_with_scope_filter(self, mock_ctx, client_factory, mock_boto3_client):
        """Passes target_resource_scope to API."""
        mock_boto3_client.list_policies.return_value = {'policies': []}
        tools = PolicyTools(client_factory)
        gateway_arn = 'arn:aws:bedrock-agentcore:us-east-1:123:gateway/gw-abcdefghij'
        result = await tools.policy_list(
            ctx=mock_ctx,
            policy_engine_id='eng-id',
            target_resource_scope=gateway_arn,
            max_results=25,
            next_token='prev',
        )
        assert isinstance(result, ListPoliciesResponse)
        kw = mock_boto3_client.list_policies.call_args.kwargs
        assert kw['policyEngineId'] == 'eng-id'
        assert kw['targetResourceScope'] == gateway_arn
        assert kw['maxResults'] == 25
        assert kw['nextToken'] == 'prev'

    @pytest.mark.asyncio
    async def test_empty(self, mock_ctx, client_factory, mock_boto3_client):
        """Handles empty policy list."""
        mock_boto3_client.list_policies.return_value = {'policies': []}
        tools = PolicyTools(client_factory)
        result = await tools.policy_list(ctx=mock_ctx, policy_engine_id='eng-id')
        assert isinstance(result, ListPoliciesResponse)
        assert result.status == 'success'
        assert len(result.policies) == 0

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.list_policies.side_effect = ClientError(
            {
                'Error': {'Code': 'ResourceNotFoundException', 'Message': 'x'},
                'ResponseMetadata': {'HTTPStatusCode': 404},
            },
            'ListPolicies',
        )
        tools = PolicyTools(client_factory)
        result = await tools.policy_list(ctx=mock_ctx, policy_engine_id='nope')
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'
