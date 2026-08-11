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

"""OAuth2 credential provider tools for AgentCore Identity.

OAuth2 credential providers hold client credentials (client_id, client_secret,
provider configuration) for popular services (Google, GitHub, Slack,
Salesforce, Atlassian, Microsoft, LinkedIn) and custom OAuth2 providers.
They support both M2M (client credentials) and 3LO (user federation) flows.
Actual token retrieval happens at runtime via the bedrock-agentcore SDK's
@requires_access_token decorator — not exposed as an MCP tool.
"""

from .error_handler import handle_identity_error, strip_response_metadata
from .models import (
    DeleteOauth2ProviderResponse,
    ErrorResponse,
    ListOauth2ProvidersResponse,
    Oauth2ProviderResponse,
)
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Any


# Supported OAuth2 credential provider vendors.
OAUTH2_VENDORS = (
    'GoogleOauth2',
    'GithubOauth2',
    'SlackOauth2',
    'SalesforceOauth2',
    'MicrosoftOauth2',
    'CustomOauth2',
    'AtlassianOauth2',
    'LinkedinOauth2',
    'XOauth2',
    'OktaOauth2',
    'OneLoginOauth2',
    'PingOneOauth2',
    'FacebookOauth2',
    'YandexOauth2',
    'RedditOauth2',
    'ZoomOauth2',
    'TwitchOauth2',
    'SpotifyOauth2',
    'DropboxOauth2',
    'NotionOauth2',
    'HubspotOauth2',
    'CyberArkOauth2',
    'FusionAuthOauth2',
    'Auth0Oauth2',
    'CognitoOauth2',
)


class Oauth2ProviderTools:
    """Tools for managing OAuth2 credential providers."""

    def __init__(self, client_factory):
        """Initialize with a callable that returns a boto3 control plane client."""
        self._get_client = client_factory

    def register(self, mcp):
        """Register OAuth2 credential provider tools with the MCP server."""
        mcp.tool(name='identity_create_oauth2_provider')(self.identity_create_oauth2_provider)
        mcp.tool(name='identity_get_oauth2_provider')(self.identity_get_oauth2_provider)
        mcp.tool(name='identity_update_oauth2_provider')(self.identity_update_oauth2_provider)
        mcp.tool(name='identity_delete_oauth2_provider')(self.identity_delete_oauth2_provider)
        mcp.tool(name='identity_list_oauth2_providers')(self.identity_list_oauth2_providers)

    async def identity_create_oauth2_provider(
        self,
        ctx: Context,
        name: Annotated[
            str,
            Field(description=('Unique provider name (1-128 chars). Pattern: [a-zA-Z0-9\\-_]+')),
        ],
        credential_provider_vendor: Annotated[
            str,
            Field(
                description=(
                    'OAuth2 vendor. One of: GoogleOauth2, GithubOauth2, '
                    'SlackOauth2, SalesforceOauth2, MicrosoftOauth2, '
                    'CustomOauth2, AtlassianOauth2, LinkedinOauth2, XOauth2, '
                    'OktaOauth2, OneLoginOauth2, PingOneOauth2, FacebookOauth2, '
                    'YandexOauth2, RedditOauth2, ZoomOauth2, TwitchOauth2, '
                    'SpotifyOauth2, DropboxOauth2, NotionOauth2, HubspotOauth2, '
                    'CyberArkOauth2, FusionAuthOauth2, Auth0Oauth2, CognitoOauth2.'
                )
            ),
        ],
        oauth2_provider_config_input: Annotated[
            dict[str, Any],
            Field(
                description=(
                    'Vendor-specific OAuth2 config as a union — specify exactly '
                    'one of: googleOauth2ProviderConfig, githubOauth2ProviderConfig, '
                    'slackOauth2ProviderConfig, salesforceOauth2ProviderConfig, '
                    'microsoftOauth2ProviderConfig, customOauth2ProviderConfig, '
                    'atlassianOauth2ProviderConfig, linkedinOauth2ProviderConfig, '
                    'includedOauth2ProviderConfig. Each contains clientId and '
                    'clientSecret (1-256 / 1-2048 chars). CustomOauth2 also '
                    'requires oauthDiscovery (either discoveryUrl or '
                    'authorizationServerMetadata).'
                )
            ),
        ],
        tags: Annotated[
            dict[str, str] | None,
            Field(description='Tags as key-value pairs (max 50)'),
        ] = None,
    ) -> Oauth2ProviderResponse | ErrorResponse:
        r"""Create an OAuth2 credential provider in AgentCore Identity.

        COST WARNING: Creates a secret in AWS Secrets Manager (holding the
        client_secret) and incurs Secrets Manager storage charges.

        SECURITY NOTE: The clientSecret inside oauth2_provider_config_input
        flows through LLM context when this tool is called by an AI
        assistant. For production secrets, strongly prefer the CLI:
            agentcore add credential --name <n> --type oauth \
              --discovery-url <url> --client-id <id> \
              --client-secret <secret> --scopes <scope1,scope2>
        The CLI accepts the secret without it entering LLM conversation
        history. Use this MCP tool for test providers, automation from
        controlled contexts, or when the client_secret is already known
        to the caller.

        The response includes a callbackUrl — the OAuth2 redirect URI you
        must register with the external provider.
        """
        logger.info(
            f'Creating OAuth2 credential provider: {name} (vendor={credential_provider_vendor})'
        )

        try:
            client = self._get_client()
            kwargs: dict[str, Any] = {
                'name': name,
                'credentialProviderVendor': credential_provider_vendor,
                'oauth2ProviderConfigInput': oauth2_provider_config_input,
            }
            if tags is not None:
                kwargs['tags'] = tags

            response = client.create_oauth2_credential_provider(**kwargs)
            provider = strip_response_metadata(response)

            return Oauth2ProviderResponse(
                status='success',
                message=(
                    f'OAuth2 credential provider "{name}" created. '
                    f'ARN: {provider.get("credentialProviderArn", "unknown")}. '
                    f'Callback URL (register with the OAuth2 provider): '
                    f'{provider.get("callbackUrl", "n/a")}.'
                ),
                provider=provider,
            )
        except Exception as e:
            return handle_identity_error('CreateOauth2CredentialProvider', e)

    async def identity_get_oauth2_provider(
        self,
        ctx: Context,
        name: Annotated[
            str,
            Field(description='Provider name (1-128 chars)'),
        ],
    ) -> Oauth2ProviderResponse | ErrorResponse:
        """Get metadata for an OAuth2 credential provider.

        Returns the provider ARN, vendor, callback URL, Secrets Manager
        secret ARN, OAuth2 discovery output, and timestamps. Does NOT
        return the client_secret value — that is stored in Secrets
        Manager and only used server-side during token exchanges.

        This is a read-only operation with no cost implications.
        """
        logger.info(f'Getting OAuth2 credential provider: {name}')

        try:
            client = self._get_client()
            response = client.get_oauth2_credential_provider(name=name)
            provider = strip_response_metadata(response)

            return Oauth2ProviderResponse(
                status='success',
                message=f'OAuth2 credential provider "{name}" retrieved.',
                provider=provider,
            )
        except Exception as e:
            return handle_identity_error('GetOauth2CredentialProvider', e)

    async def identity_update_oauth2_provider(
        self,
        ctx: Context,
        name: Annotated[
            str,
            Field(description='Provider name to update (1-128 chars)'),
        ],
        credential_provider_vendor: Annotated[
            str,
            Field(description='OAuth2 vendor (must match the existing vendor).'),
        ],
        oauth2_provider_config_input: Annotated[
            dict[str, Any],
            Field(
                description=(
                    'Updated vendor-specific OAuth2 config as a union. Same '
                    'shape as on create — contains clientId, clientSecret, '
                    'and (for CustomOauth2) oauthDiscovery.'
                )
            ),
        ],
    ) -> Oauth2ProviderResponse | ErrorResponse:
        """Update an OAuth2 credential provider's configuration.

        COST WARNING: Rotates the secret in AWS Secrets Manager. Continues
        to incur Secrets Manager storage charges.

        SECURITY NOTE: The clientSecret inside oauth2_provider_config_input
        flows through LLM context when this tool is called by an AI
        assistant. For production secret rotation, strongly prefer the
        CLI (re-running `agentcore add credential` with the same name
        rotates the credential without the value entering LLM history).

        Returns updated provider metadata. The provider ARN and callback
        URL are stable.
        """
        logger.info(f'Updating OAuth2 credential provider: {name}')

        try:
            client = self._get_client()
            response = client.update_oauth2_credential_provider(
                name=name,
                credentialProviderVendor=credential_provider_vendor,
                oauth2ProviderConfigInput=oauth2_provider_config_input,
            )
            provider = strip_response_metadata(response)

            return Oauth2ProviderResponse(
                status='success',
                message=f'OAuth2 credential provider "{name}" updated.',
                provider=provider,
            )
        except Exception as e:
            return handle_identity_error('UpdateOauth2CredentialProvider', e)

    async def identity_delete_oauth2_provider(
        self,
        ctx: Context,
        name: Annotated[
            str,
            Field(description='Provider name to delete (1-128 chars)'),
        ],
    ) -> DeleteOauth2ProviderResponse | ErrorResponse:
        """Permanently delete an OAuth2 credential provider.

        WARNING: This permanently deletes the credential provider and its
        backing secret. Any agents or workloads retrieving tokens via
        this provider will fail. Any stored 3LO user consents tied to
        this provider are lost. This action cannot be undone.
        """
        logger.info(f'Deleting OAuth2 credential provider: {name}')

        try:
            client = self._get_client()
            client.delete_oauth2_credential_provider(name=name)

            return DeleteOauth2ProviderResponse(
                status='success',
                message=f'OAuth2 credential provider "{name}" deleted.',
                name=name,
            )
        except Exception as e:
            return handle_identity_error('DeleteOauth2CredentialProvider', e)

    async def identity_list_oauth2_providers(
        self,
        ctx: Context,
        max_results: Annotated[
            int | None,
            Field(description='Max results per page (1-20)'),
        ] = None,
        next_token: Annotated[
            str | None,
            Field(description='Pagination token from previous response'),
        ] = None,
    ) -> ListOauth2ProvidersResponse | ErrorResponse:
        """List OAuth2 credential providers in the account.

        Returns provider summaries with names, ARNs, vendors, and
        timestamps. Does NOT return client secrets. This is a read-only
        operation with no cost implications.
        """
        logger.info('Listing OAuth2 credential providers')

        try:
            client = self._get_client()
            kwargs: dict[str, Any] = {}
            if max_results is not None:
                kwargs['maxResults'] = max_results
            if next_token is not None:
                kwargs['nextToken'] = next_token

            response = client.list_oauth2_credential_providers(**kwargs)
            items = response.get('credentialProviders', [])

            return ListOauth2ProvidersResponse(
                status='success',
                message=f'Found {len(items)} OAuth2 credential provider(s).',
                providers=items,
                next_token=response.get('nextToken'),
            )
        except Exception as e:
            return handle_identity_error('ListOauth2CredentialProviders', e)
