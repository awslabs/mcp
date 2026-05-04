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

"""Workload identity tools for AgentCore Identity.

Workload identities represent agent or automated workloads in AgentCore
Identity. They enable secure authentication to the token vault and
credential providers, and can be configured with allowed OAuth2 return
URLs for 3LO (three-legged OAuth) flows.
"""

from .error_handler import handle_identity_error, strip_response_metadata
from .models import (
    DeleteWorkloadIdentityResponse,
    ErrorResponse,
    ListWorkloadIdentitiesResponse,
    WorkloadIdentityResponse,
)
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Any


class WorkloadIdentityTools:
    """Tools for managing AgentCore workload identities."""

    def __init__(self, client_factory):
        """Initialize with a callable that returns a boto3 control plane client."""
        self._get_client = client_factory

    def register(self, mcp):
        """Register workload identity tools with the MCP server."""
        mcp.tool(name='identity_create_workload_identity')(self.identity_create_workload_identity)
        mcp.tool(name='identity_get_workload_identity')(self.identity_get_workload_identity)
        mcp.tool(name='identity_update_workload_identity')(self.identity_update_workload_identity)
        mcp.tool(name='identity_delete_workload_identity')(self.identity_delete_workload_identity)
        mcp.tool(name='identity_list_workload_identities')(self.identity_list_workload_identities)

    async def identity_create_workload_identity(
        self,
        ctx: Context,
        name: Annotated[
            str,
            Field(
                description=(
                    'Unique workload identity name (3-255 chars). Pattern: [A-Za-z0-9_.-]+'
                )
            ),
        ],
        allowed_resource_oauth2_return_urls: Annotated[
            list[str] | None,
            Field(
                description=(
                    'Allowed OAuth2 return URLs for resources accessed by this '
                    'workload (1-2048 chars each). Required before using 3LO '
                    'flows with a custom callback URL.'
                )
            ),
        ] = None,
        tags: Annotated[
            dict[str, str] | None,
            Field(description='Tags as key-value pairs (max 50)'),
        ] = None,
    ) -> WorkloadIdentityResponse | ErrorResponse:
        """Create a new AgentCore workload identity.

        COST WARNING: Creates a workload identity resource in AgentCore
        Identity. Workload identities themselves are free, but the
        workload access tokens they issue are used to retrieve stored
        credentials from the token vault.

        Returns the created workload identity details including its ARN.
        """
        logger.info(f'Creating workload identity: {name}')

        try:
            client = self._get_client()
            kwargs: dict[str, Any] = {'name': name}
            if allowed_resource_oauth2_return_urls is not None:
                kwargs['allowedResourceOauth2ReturnUrls'] = allowed_resource_oauth2_return_urls
            if tags is not None:
                kwargs['tags'] = tags

            response = client.create_workload_identity(**kwargs)
            wi = strip_response_metadata(response)

            return WorkloadIdentityResponse(
                status='success',
                message=(
                    f'Workload identity "{name}" created. '
                    f'ARN: {wi.get("workloadIdentityArn", "unknown")}.'
                ),
                workload_identity=wi,
            )
        except Exception as e:
            return handle_identity_error('CreateWorkloadIdentity', e)

    async def identity_get_workload_identity(
        self,
        ctx: Context,
        name: Annotated[
            str,
            Field(description='Workload identity name (3-255 chars)'),
        ],
    ) -> WorkloadIdentityResponse | ErrorResponse:
        """Get details of an AgentCore workload identity.

        Returns the workload identity including allowed OAuth2 return
        URLs, ARN, and timestamps. This is a read-only operation with
        no cost implications.
        """
        logger.info(f'Getting workload identity: {name}')

        try:
            client = self._get_client()
            response = client.get_workload_identity(name=name)
            wi = strip_response_metadata(response)

            return WorkloadIdentityResponse(
                status='success',
                message=f'Workload identity "{name}" retrieved.',
                workload_identity=wi,
            )
        except Exception as e:
            return handle_identity_error('GetWorkloadIdentity', e)

    async def identity_update_workload_identity(
        self,
        ctx: Context,
        name: Annotated[
            str,
            Field(description='Workload identity name to update (3-255 chars)'),
        ],
        allowed_resource_oauth2_return_urls: Annotated[
            list[str] | None,
            Field(
                description=(
                    'New list of allowed OAuth2 return URLs (replaces existing '
                    'list). Each URL 1-2048 chars.'
                )
            ),
        ] = None,
    ) -> WorkloadIdentityResponse | ErrorResponse:
        """Update an AgentCore workload identity.

        Replaces the allowed OAuth2 return URLs list. This is a config
        change only — the workload identity ARN and name are immutable.
        """
        logger.info(f'Updating workload identity: {name}')

        try:
            client = self._get_client()
            kwargs: dict[str, Any] = {'name': name}
            if allowed_resource_oauth2_return_urls is not None:
                kwargs['allowedResourceOauth2ReturnUrls'] = allowed_resource_oauth2_return_urls

            response = client.update_workload_identity(**kwargs)
            wi = strip_response_metadata(response)

            return WorkloadIdentityResponse(
                status='success',
                message=f'Workload identity "{name}" updated.',
                workload_identity=wi,
            )
        except Exception as e:
            return handle_identity_error('UpdateWorkloadIdentity', e)

    async def identity_delete_workload_identity(
        self,
        ctx: Context,
        name: Annotated[
            str,
            Field(description='Workload identity name to delete (3-255 chars)'),
        ],
    ) -> DeleteWorkloadIdentityResponse | ErrorResponse:
        """Permanently delete an AgentCore workload identity.

        WARNING: This permanently deletes the workload identity. Any
        agents or code relying on this identity will no longer be able
        to authenticate. This action cannot be undone.
        """
        logger.info(f'Deleting workload identity: {name}')

        try:
            client = self._get_client()
            client.delete_workload_identity(name=name)

            return DeleteWorkloadIdentityResponse(
                status='success',
                message=f'Workload identity "{name}" deleted.',
                name=name,
            )
        except Exception as e:
            return handle_identity_error('DeleteWorkloadIdentity', e)

    async def identity_list_workload_identities(
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
    ) -> ListWorkloadIdentitiesResponse | ErrorResponse:
        """List AgentCore workload identities in the account.

        Returns workload identity summaries with names and ARNs. This
        is a read-only operation with no cost implications.
        """
        logger.info('Listing workload identities')

        try:
            client = self._get_client()
            kwargs: dict[str, Any] = {}
            if max_results is not None:
                kwargs['maxResults'] = max_results
            if next_token is not None:
                kwargs['nextToken'] = next_token

            response = client.list_workload_identities(**kwargs)
            items = response.get('workloadIdentities', [])

            return ListWorkloadIdentitiesResponse(
                status='success',
                message=f'Found {len(items)} workload identity(ies).',
                workload_identities=items,
                next_token=response.get('nextToken'),
            )
        except Exception as e:
            return handle_identity_error('ListWorkloadIdentities', e)
