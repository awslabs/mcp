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

"""Unit tests for Identity API key credential provider tools."""

import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.identity.api_key_providers import (
    ApiKeyProviderTools,
)
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.identity.models import (
    ApiKeyProviderResponse,
    DeleteApiKeyProviderResponse,
    ErrorResponse,
    ListApiKeyProvidersResponse,
)
from botocore.exceptions import ClientError


class TestIdentityCreateApiKeyProvider:
    """Tests for identity_create_api_key_provider tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Creates API key provider and returns ARN."""
        mock_boto3_client.create_api_key_credential_provider.return_value = {
            'name': 'openai',
            'credentialProviderArn': 'arn:aws:acps:us-east-1:123:credential-provider/openai',
            'apiKeySecretArn': {'secretArn': 'arn:aws:secretsmanager:us-east-1:123:secret:a-abc'},
        }
        tools = ApiKeyProviderTools(client_factory)
        result = await tools.identity_create_api_key_provider(
            ctx=mock_ctx,
            name='openai',
            api_key='sk-test-redacted',  # pragma: allowlist secret
        )
        assert isinstance(result, ApiKeyProviderResponse)
        assert result.status == 'success'
        assert 'openai' in result.message
        assert result.provider['name'] == 'openai'
        mock_boto3_client.create_api_key_credential_provider.assert_called_once_with(
            name='openai', apiKey='sk-test-redacted'
        )

    @pytest.mark.asyncio
    async def test_with_tags(self, mock_ctx, client_factory, mock_boto3_client):
        """Passes tags through to the API."""
        mock_boto3_client.create_api_key_credential_provider.return_value = {
            'name': 'openai',
            'credentialProviderArn': 'arn:aws:acps:...:openai',
        }
        tools = ApiKeyProviderTools(client_factory)
        result = await tools.identity_create_api_key_provider(
            ctx=mock_ctx,
            name='openai',
            api_key='sk-test',  # pragma: allowlist secret
            tags={'env': 'prod'},
        )
        assert isinstance(result, ApiKeyProviderResponse)
        kw = mock_boto3_client.create_api_key_credential_provider.call_args.kwargs
        assert kw['tags'] == {'env': 'prod'}

    @pytest.mark.asyncio
    async def test_conflict(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ConflictException (duplicate name)."""
        mock_boto3_client.create_api_key_credential_provider.side_effect = ClientError(
            {
                'Error': {'Code': 'ConflictException', 'Message': 'already exists'},
                'ResponseMetadata': {'HTTPStatusCode': 409},
            },
            'CreateApiKeyCredentialProvider',
        )
        tools = ApiKeyProviderTools(client_factory)
        result = await tools.identity_create_api_key_provider(
            ctx=mock_ctx,
            name='openai',
            api_key='sk-test',  # pragma: allowlist secret
        )
        assert isinstance(result, ErrorResponse)
        assert result.error_type == 'ConflictException'


class TestIdentityGetApiKeyProvider:
    """Tests for identity_get_api_key_provider tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns provider metadata (no API key value)."""
        mock_boto3_client.get_api_key_credential_provider.return_value = {
            'name': 'openai',
            'credentialProviderArn': 'arn:aws:acps:...:openai',
            'apiKeySecretArn': {
                'secretArn': 'arn:aws:secretsmanager:...:a-abc'
            },  # pragma: allowlist secret
            'createdTime': 1700000000,
            'lastUpdatedTime': 1700000001,
        }
        tools = ApiKeyProviderTools(client_factory)
        result = await tools.identity_get_api_key_provider(ctx=mock_ctx, name='openai')
        assert isinstance(result, ApiKeyProviderResponse)
        assert result.status == 'success'
        assert result.provider['name'] == 'openai'
        # Confirm no raw API key in response (not part of the Get response shape)
        assert 'apiKey' not in result.provider

    @pytest.mark.asyncio
    async def test_not_found(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse when provider not found."""
        mock_boto3_client.get_api_key_credential_provider.side_effect = ClientError(
            {
                'Error': {'Code': 'ResourceNotFoundException', 'Message': 'missing'},
                'ResponseMetadata': {'HTTPStatusCode': 404},
            },
            'GetApiKeyCredentialProvider',
        )
        tools = ApiKeyProviderTools(client_factory)
        result = await tools.identity_get_api_key_provider(ctx=mock_ctx, name='missing')
        assert isinstance(result, ErrorResponse)
        assert result.error_type == 'ResourceNotFoundException'


class TestIdentityUpdateApiKeyProvider:
    """Tests for identity_update_api_key_provider tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Rotates the API key on an existing provider."""
        mock_boto3_client.update_api_key_credential_provider.return_value = {
            'name': 'openai',
            'credentialProviderArn': 'arn:aws:acps:...:openai',
            'apiKeySecretArn': {'secretArn': 'arn:aws:secretsmanager:...:a-abc'},
        }
        tools = ApiKeyProviderTools(client_factory)
        result = await tools.identity_update_api_key_provider(
            ctx=mock_ctx,
            name='openai',
            api_key='sk-new-key',  # pragma: allowlist secret
        )
        assert isinstance(result, ApiKeyProviderResponse)
        assert result.status == 'success'
        mock_boto3_client.update_api_key_credential_provider.assert_called_once_with(
            name='openai', apiKey='sk-new-key'
        )

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.update_api_key_credential_provider.side_effect = ClientError(
            {
                'Error': {'Code': 'ResourceNotFoundException', 'Message': 'missing'},
                'ResponseMetadata': {'HTTPStatusCode': 404},
            },
            'UpdateApiKeyCredentialProvider',
        )
        tools = ApiKeyProviderTools(client_factory)
        result = await tools.identity_update_api_key_provider(
            ctx=mock_ctx,
            name='missing',
            api_key='sk-new',  # pragma: allowlist secret
        )
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'


class TestIdentityDeleteApiKeyProvider:
    """Tests for identity_delete_api_key_provider tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Deletes an API key credential provider."""
        mock_boto3_client.delete_api_key_credential_provider.return_value = {}
        tools = ApiKeyProviderTools(client_factory)
        result = await tools.identity_delete_api_key_provider(ctx=mock_ctx, name='openai')
        assert isinstance(result, DeleteApiKeyProviderResponse)
        assert result.status == 'success'
        assert result.name == 'openai'
        mock_boto3_client.delete_api_key_credential_provider.assert_called_once_with(name='openai')

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.delete_api_key_credential_provider.side_effect = ClientError(
            {
                'Error': {'Code': 'ResourceNotFoundException', 'Message': 'gone'},
                'ResponseMetadata': {'HTTPStatusCode': 404},
            },
            'DeleteApiKeyCredentialProvider',
        )
        tools = ApiKeyProviderTools(client_factory)
        result = await tools.identity_delete_api_key_provider(ctx=mock_ctx, name='missing')
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'


class TestIdentityListApiKeyProviders:
    """Tests for identity_list_api_key_providers tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns list of providers with pagination token."""
        mock_boto3_client.list_api_key_credential_providers.return_value = {
            'credentialProviders': [
                {
                    'name': 'openai',
                    'credentialProviderArn': 'arn:aws:acps:...:openai',
                    'createdTime': 1700000000,
                    'lastUpdatedTime': 1700000001,
                },
                {
                    'name': 'stripe',
                    'credentialProviderArn': 'arn:aws:acps:...:stripe',
                    'createdTime': 1700000010,
                    'lastUpdatedTime': 1700000011,
                },
            ],
            'nextToken': 'tok-next',
        }
        tools = ApiKeyProviderTools(client_factory)
        result = await tools.identity_list_api_key_providers(ctx=mock_ctx)
        assert isinstance(result, ListApiKeyProvidersResponse)
        assert result.status == 'success'
        assert len(result.providers) == 2
        assert result.next_token == 'tok-next'

    @pytest.mark.asyncio
    async def test_with_pagination(self, mock_ctx, client_factory, mock_boto3_client):
        """Passes pagination params."""
        mock_boto3_client.list_api_key_credential_providers.return_value = {
            'credentialProviders': [],
        }
        tools = ApiKeyProviderTools(client_factory)
        result = await tools.identity_list_api_key_providers(
            ctx=mock_ctx, max_results=20, next_token='prev'
        )
        assert isinstance(result, ListApiKeyProvidersResponse)
        mock_boto3_client.list_api_key_credential_providers.assert_called_once_with(
            maxResults=20, nextToken='prev'
        )

    @pytest.mark.asyncio
    async def test_empty(self, mock_ctx, client_factory, mock_boto3_client):
        """Handles empty result list."""
        mock_boto3_client.list_api_key_credential_providers.return_value = {
            'credentialProviders': []
        }
        tools = ApiKeyProviderTools(client_factory)
        result = await tools.identity_list_api_key_providers(ctx=mock_ctx)
        assert isinstance(result, ListApiKeyProvidersResponse)
        assert len(result.providers) == 0

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.list_api_key_credential_providers.side_effect = ClientError(
            {
                'Error': {'Code': 'AccessDeniedException', 'Message': 'denied'},
                'ResponseMetadata': {'HTTPStatusCode': 403},
            },
            'ListApiKeyCredentialProviders',
        )
        tools = ApiKeyProviderTools(client_factory)
        result = await tools.identity_list_api_key_providers(ctx=mock_ctx)
        assert isinstance(result, ErrorResponse)
        assert result.error_type == 'AccessDeniedException'
