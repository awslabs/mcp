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

"""Unit tests for Identity OAuth2 credential provider tools."""

import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.identity.models import (
    DeleteOauth2ProviderResponse,
    ErrorResponse,
    ListOauth2ProvidersResponse,
    Oauth2ProviderResponse,
)
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.identity.oauth2_providers import (
    Oauth2ProviderTools,
)
from botocore.exceptions import ClientError


class TestIdentityCreateOauth2Provider:
    """Tests for identity_create_oauth2_provider tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Creates OAuth2 provider with Google vendor."""
        mock_boto3_client.create_oauth2_credential_provider.return_value = {
            'name': 'google-login',
            'credentialProviderArn': 'arn:aws:acps:us-east-1:123:credential-provider/google-login',
            'callbackUrl': 'https://agentcore.aws/oauth2/callback',
            'clientSecretArn': {'secretArn': 'arn:aws:secretsmanager:us-east-1:123:secret:g-abc'},
            'oauth2ProviderConfigOutput': {
                'googleOauth2ProviderConfig': {'clientId': 'abc.apps.googleusercontent.com'}
            },
        }
        tools = Oauth2ProviderTools(client_factory)
        result = await tools.identity_create_oauth2_provider(
            ctx=mock_ctx,
            name='google-login',
            credential_provider_vendor='GoogleOauth2',
            oauth2_provider_config_input={
                'googleOauth2ProviderConfig': {
                    'clientId': 'abc.apps.googleusercontent.com',
                    'clientSecret': 'GOCSPX-redacted',  # pragma: allowlist secret
                }
            },
        )
        assert isinstance(result, Oauth2ProviderResponse)
        assert result.status == 'success'
        assert 'google-login' in result.message
        assert 'Callback URL' in result.message
        assert result.provider['callbackUrl'] == 'https://agentcore.aws/oauth2/callback'

    @pytest.mark.asyncio
    async def test_custom_vendor_with_discovery(self, mock_ctx, client_factory, mock_boto3_client):
        """Passes CustomOauth2 config with discoveryUrl to the API."""
        mock_boto3_client.create_oauth2_credential_provider.return_value = {
            'name': 'custom-idp',
            'credentialProviderArn': 'arn:aws:acps:...:custom-idp',
            'callbackUrl': 'https://agentcore.aws/cb',
        }
        tools = Oauth2ProviderTools(client_factory)
        config = {
            'customOauth2ProviderConfig': {
                'clientId': 'client-x',
                'clientSecret': 'secret-x',  # pragma: allowlist secret
                'oauthDiscovery': {
                    'discoveryUrl': 'https://idp.example.com/.well-known/openid-configuration'
                },
            }
        }
        result = await tools.identity_create_oauth2_provider(
            ctx=mock_ctx,
            name='custom-idp',
            credential_provider_vendor='CustomOauth2',
            oauth2_provider_config_input=config,
            tags={'env': 'test'},
        )
        assert isinstance(result, Oauth2ProviderResponse)
        kw = mock_boto3_client.create_oauth2_credential_provider.call_args.kwargs
        assert kw['credentialProviderVendor'] == 'CustomOauth2'
        assert kw['oauth2ProviderConfigInput'] == config
        assert kw['tags'] == {'env': 'test'}

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.create_oauth2_credential_provider.side_effect = ClientError(
            {
                'Error': {'Code': 'ValidationException', 'Message': 'bad vendor'},
                'ResponseMetadata': {'HTTPStatusCode': 400},
            },
            'CreateOauth2CredentialProvider',
        )
        tools = Oauth2ProviderTools(client_factory)
        result = await tools.identity_create_oauth2_provider(
            ctx=mock_ctx,
            name='bad',
            credential_provider_vendor='GoogleOauth2',
            oauth2_provider_config_input={},
        )
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'


class TestIdentityGetOauth2Provider:
    """Tests for identity_get_oauth2_provider tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns provider metadata (no client_secret)."""
        mock_boto3_client.get_oauth2_credential_provider.return_value = {
            'name': 'google-login',
            'credentialProviderArn': 'arn:aws:acps:...:google-login',
            'credentialProviderVendor': 'GoogleOauth2',
            'callbackUrl': 'https://agentcore.aws/cb',
            'clientSecretArn': {'secretArn': 'arn:aws:secretsmanager:...:g-abc'},
            'createdTime': 1700000000,
            'lastUpdatedTime': 1700000001,
            'oauth2ProviderConfigOutput': {'googleOauth2ProviderConfig': {'clientId': 'abc'}},
        }
        tools = Oauth2ProviderTools(client_factory)
        result = await tools.identity_get_oauth2_provider(ctx=mock_ctx, name='google-login')
        assert isinstance(result, Oauth2ProviderResponse)
        assert result.status == 'success'
        assert result.provider['credentialProviderVendor'] == 'GoogleOauth2'

    @pytest.mark.asyncio
    async def test_not_found(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse when not found."""
        mock_boto3_client.get_oauth2_credential_provider.side_effect = ClientError(
            {
                'Error': {'Code': 'ResourceNotFoundException', 'Message': 'missing'},
                'ResponseMetadata': {'HTTPStatusCode': 404},
            },
            'GetOauth2CredentialProvider',
        )
        tools = Oauth2ProviderTools(client_factory)
        result = await tools.identity_get_oauth2_provider(ctx=mock_ctx, name='missing')
        assert isinstance(result, ErrorResponse)
        assert result.error_type == 'ResourceNotFoundException'


class TestIdentityUpdateOauth2Provider:
    """Tests for identity_update_oauth2_provider tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Updates OAuth2 provider config."""
        mock_boto3_client.update_oauth2_credential_provider.return_value = {
            'name': 'google-login',
            'credentialProviderArn': 'arn:aws:acps:...:google-login',
            'credentialProviderVendor': 'GoogleOauth2',
            'callbackUrl': 'https://agentcore.aws/cb',
        }
        tools = Oauth2ProviderTools(client_factory)
        config = {
            'googleOauth2ProviderConfig': {
                'clientId': 'new-client-id',
                'clientSecret': 'new-secret',  # pragma: allowlist secret
            }
        }
        result = await tools.identity_update_oauth2_provider(
            ctx=mock_ctx,
            name='google-login',
            credential_provider_vendor='GoogleOauth2',
            oauth2_provider_config_input=config,
        )
        assert isinstance(result, Oauth2ProviderResponse)
        assert result.status == 'success'
        kw = mock_boto3_client.update_oauth2_credential_provider.call_args.kwargs
        assert kw['credentialProviderVendor'] == 'GoogleOauth2'
        assert kw['oauth2ProviderConfigInput'] == config

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.update_oauth2_credential_provider.side_effect = ClientError(
            {
                'Error': {'Code': 'ConflictException', 'Message': 'locked'},
                'ResponseMetadata': {'HTTPStatusCode': 409},
            },
            'UpdateOauth2CredentialProvider',
        )
        tools = Oauth2ProviderTools(client_factory)
        result = await tools.identity_update_oauth2_provider(
            ctx=mock_ctx,
            name='google-login',
            credential_provider_vendor='GoogleOauth2',
            oauth2_provider_config_input={},
        )
        assert isinstance(result, ErrorResponse)
        assert result.error_type == 'ConflictException'


class TestIdentityDeleteOauth2Provider:
    """Tests for identity_delete_oauth2_provider tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Deletes an OAuth2 credential provider."""
        mock_boto3_client.delete_oauth2_credential_provider.return_value = {}
        tools = Oauth2ProviderTools(client_factory)
        result = await tools.identity_delete_oauth2_provider(ctx=mock_ctx, name='google-login')
        assert isinstance(result, DeleteOauth2ProviderResponse)
        assert result.status == 'success'
        assert result.name == 'google-login'
        mock_boto3_client.delete_oauth2_credential_provider.assert_called_once_with(
            name='google-login'
        )

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.delete_oauth2_credential_provider.side_effect = ClientError(
            {
                'Error': {'Code': 'ResourceNotFoundException', 'Message': 'gone'},
                'ResponseMetadata': {'HTTPStatusCode': 404},
            },
            'DeleteOauth2CredentialProvider',
        )
        tools = Oauth2ProviderTools(client_factory)
        result = await tools.identity_delete_oauth2_provider(ctx=mock_ctx, name='missing')
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'


class TestIdentityListOauth2Providers:
    """Tests for identity_list_oauth2_providers tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns list of OAuth2 providers with pagination token."""
        mock_boto3_client.list_oauth2_credential_providers.return_value = {
            'credentialProviders': [
                {
                    'name': 'google-login',
                    'credentialProviderArn': 'arn:aws:acps:...:google-login',
                    'credentialProviderVendor': 'GoogleOauth2',
                    'createdTime': 1700000000,
                    'lastUpdatedTime': 1700000001,
                },
                {
                    'name': 'github-login',
                    'credentialProviderArn': 'arn:aws:acps:...:github-login',
                    'credentialProviderVendor': 'GithubOauth2',
                    'createdTime': 1700000010,
                    'lastUpdatedTime': 1700000011,
                },
            ],
            'nextToken': 'tok-next',
        }
        tools = Oauth2ProviderTools(client_factory)
        result = await tools.identity_list_oauth2_providers(ctx=mock_ctx)
        assert isinstance(result, ListOauth2ProvidersResponse)
        assert result.status == 'success'
        assert len(result.providers) == 2
        assert result.next_token == 'tok-next'

    @pytest.mark.asyncio
    async def test_with_pagination(self, mock_ctx, client_factory, mock_boto3_client):
        """Passes pagination params."""
        mock_boto3_client.list_oauth2_credential_providers.return_value = {
            'credentialProviders': [],
        }
        tools = Oauth2ProviderTools(client_factory)
        result = await tools.identity_list_oauth2_providers(
            ctx=mock_ctx, max_results=10, next_token='prev'
        )
        assert isinstance(result, ListOauth2ProvidersResponse)
        mock_boto3_client.list_oauth2_credential_providers.assert_called_once_with(
            maxResults=10, nextToken='prev'
        )

    @pytest.mark.asyncio
    async def test_empty(self, mock_ctx, client_factory, mock_boto3_client):
        """Handles empty result list."""
        mock_boto3_client.list_oauth2_credential_providers.return_value = {
            'credentialProviders': []
        }
        tools = Oauth2ProviderTools(client_factory)
        result = await tools.identity_list_oauth2_providers(ctx=mock_ctx)
        assert isinstance(result, ListOauth2ProvidersResponse)
        assert len(result.providers) == 0

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on ClientError."""
        mock_boto3_client.list_oauth2_credential_providers.side_effect = ClientError(
            {
                'Error': {'Code': 'AccessDeniedException', 'Message': 'denied'},
                'ResponseMetadata': {'HTTPStatusCode': 403},
            },
            'ListOauth2CredentialProviders',
        )
        tools = Oauth2ProviderTools(client_factory)
        result = await tools.identity_list_oauth2_providers(ctx=mock_ctx)
        assert isinstance(result, ErrorResponse)
        assert result.error_type == 'AccessDeniedException'
