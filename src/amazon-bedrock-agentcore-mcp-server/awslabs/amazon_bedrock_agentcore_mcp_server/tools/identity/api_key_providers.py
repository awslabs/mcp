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

"""API key credential provider tools for AgentCore Identity.

API key credential providers store an API key in the AgentCore token
vault, encrypted at rest, and make it retrievable to workloads with
the appropriate workload identity at runtime (via the bedrock-agentcore
SDK's @requires_api_key decorator — not exposed as an MCP tool).
"""

from .error_handler import handle_identity_error, strip_response_metadata
from .models import (
    ApiKeyProviderResponse,
    DeleteApiKeyProviderResponse,
    ErrorResponse,
    ListApiKeyProvidersResponse,
)
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Any


class ApiKeyProviderTools:
    """Tools for managing API key credential providers."""

    def __init__(self, client_factory):
        """Initialize with a callable that returns a boto3 control plane client."""
        self._get_client = client_factory

    def register(self, mcp):
        """Register API key credential provider tools with the MCP server."""
        mcp.tool(name='identity_create_api_key_provider')(self.identity_create_api_key_provider)
        mcp.tool(name='identity_get_api_key_provider')(self.identity_get_api_key_provider)
        mcp.tool(name='identity_update_api_key_provider')(self.identity_update_api_key_provider)
        mcp.tool(name='identity_delete_api_key_provider')(self.identity_delete_api_key_provider)
        mcp.tool(name='identity_list_api_key_providers')(self.identity_list_api_key_providers)

    async def identity_create_api_key_provider(
        self,
        ctx: Context,
        name: Annotated[
            str,
            Field(
                description=(
                    'Unique credential provider name (1-128 chars). Pattern: [a-zA-Z0-9\\-_]+'
                )
            ),
        ],
        api_key: Annotated[
            str,
            Field(
                description=(
                    'API key value to store (1-65536 chars). Encrypted at rest '
                    'in AWS Secrets Manager via the token vault.'
                )
            ),
        ],
        tags: Annotated[
            dict[str, str] | None,
            Field(description='Tags as key-value pairs (max 50)'),
        ] = None,
    ) -> ApiKeyProviderResponse | ErrorResponse:
        """Create an API key credential provider in AgentCore Identity.

        COST WARNING: Creates a secret in AWS Secrets Manager (backing the
        credential provider) and incurs Secrets Manager storage charges.

        SECURITY NOTE: The api_key parameter value flows through LLM
        context when this tool is called by an AI assistant. For
        production secrets, strongly prefer the CLI:
            agentcore add credential --name <n> --api-key <key>
        The CLI accepts the key without it entering LLM conversation
        history. Use this MCP tool for test credentials, automation
        from controlled contexts, or when the key is already known to
        the caller.

        Returns the created provider's ARN and Secrets Manager secret ARN.
        """
        logger.info(f'Creating API key credential provider: {name}')

        try:
            client = self._get_client()
            kwargs: dict[str, Any] = {'name': name, 'apiKey': api_key}
            if tags is not None:
                kwargs['tags'] = tags

            response = client.create_api_key_credential_provider(**kwargs)
            provider = strip_response_metadata(response)

            return ApiKeyProviderResponse(
                status='success',
                message=(
                    f'API key credential provider "{name}" created. '
                    f'ARN: {provider.get("credentialProviderArn", "unknown")}.'
                ),
                provider=provider,
            )
        except Exception as e:
            return handle_identity_error('CreateApiKeyCredentialProvider', e)

    async def identity_get_api_key_provider(
        self,
        ctx: Context,
        name: Annotated[
            str,
            Field(description='Credential provider name (1-128 chars)'),
        ],
    ) -> ApiKeyProviderResponse | ErrorResponse:
        """Get metadata for an API key credential provider.

        Returns the provider ARN, the ARN of the backing Secrets Manager
        secret, and timestamps. Does NOT return the API key value itself
        — that is only retrievable at runtime by workloads with a valid
        workload identity token (via the SDK, not via MCP).

        This is a read-only operation with no cost implications.
        """
        logger.info(f'Getting API key credential provider: {name}')

        try:
            client = self._get_client()
            response = client.get_api_key_credential_provider(name=name)
            provider = strip_response_metadata(response)

            return ApiKeyProviderResponse(
                status='success',
                message=f'API key credential provider "{name}" retrieved.',
                provider=provider,
            )
        except Exception as e:
            return handle_identity_error('GetApiKeyCredentialProvider', e)

    async def identity_update_api_key_provider(
        self,
        ctx: Context,
        name: Annotated[
            str,
            Field(description='Credential provider name to update (1-128 chars)'),
        ],
        api_key: Annotated[
            str,
            Field(
                description=(
                    'New API key value (1-65536 chars). Replaces the existing '
                    'key stored in Secrets Manager.'
                )
            ),
        ],
    ) -> ApiKeyProviderResponse | ErrorResponse:
        """Update the API key stored in an existing credential provider.

        COST WARNING: Rotates the secret in AWS Secrets Manager. Continues
        to incur Secrets Manager storage charges.

        SECURITY NOTE: The api_key parameter value flows through LLM
        context when this tool is called by an AI assistant. For
        production key rotation, strongly prefer the CLI:
            agentcore add credential --name <n> --api-key <key>
        (re-running `add` with the same name rotates the key without
        the value entering LLM conversation history).

        Returns updated provider metadata. The provider ARN is stable.
        """
        logger.info(f'Updating API key credential provider: {name}')

        try:
            client = self._get_client()
            response = client.update_api_key_credential_provider(name=name, apiKey=api_key)
            provider = strip_response_metadata(response)

            return ApiKeyProviderResponse(
                status='success',
                message=f'API key credential provider "{name}" updated.',
                provider=provider,
            )
        except Exception as e:
            return handle_identity_error('UpdateApiKeyCredentialProvider', e)

    async def identity_delete_api_key_provider(
        self,
        ctx: Context,
        name: Annotated[
            str,
            Field(description='Credential provider name to delete (1-128 chars)'),
        ],
    ) -> DeleteApiKeyProviderResponse | ErrorResponse:
        """Permanently delete an API key credential provider.

        WARNING: This permanently deletes the credential provider and its
        backing secret. Any agents or workloads retrieving the key via
        this provider will fail. This action cannot be undone.
        """
        logger.info(f'Deleting API key credential provider: {name}')

        try:
            client = self._get_client()
            client.delete_api_key_credential_provider(name=name)

            return DeleteApiKeyProviderResponse(
                status='success',
                message=f'API key credential provider "{name}" deleted.',
                name=name,
            )
        except Exception as e:
            return handle_identity_error('DeleteApiKeyCredentialProvider', e)

    async def identity_list_api_key_providers(
        self,
        ctx: Context,
        max_results: Annotated[
            int | None,
            Field(description='Max results per page (1-100)'),
        ] = None,
        next_token: Annotated[
            str | None,
            Field(description='Pagination token from previous response'),
        ] = None,
    ) -> ListApiKeyProvidersResponse | ErrorResponse:
        """List API key credential providers in the account.

        Returns provider summaries with names, ARNs, and timestamps.
        Does NOT return API key values. This is a read-only operation
        with no cost implications.
        """
        logger.info('Listing API key credential providers')

        try:
            client = self._get_client()
            kwargs: dict[str, Any] = {}
            if max_results is not None:
                kwargs['maxResults'] = max_results
            if next_token is not None:
                kwargs['nextToken'] = next_token

            response = client.list_api_key_credential_providers(**kwargs)
            items = response.get('credentialProviders', [])

            return ListApiKeyProvidersResponse(
                status='success',
                message=f'Found {len(items)} API key credential provider(s).',
                providers=items,
                next_token=response.get('nextToken'),
            )
        except Exception as e:
            return handle_identity_error('ListApiKeyCredentialProviders', e)
