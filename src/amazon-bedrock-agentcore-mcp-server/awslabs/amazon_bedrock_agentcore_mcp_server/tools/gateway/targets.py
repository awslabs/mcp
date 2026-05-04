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

"""Control plane tools for AgentCore Gateway target management.

Gateway targets define the endpoints (Lambda, API Gateway, OpenAPI,
Smithy, MCP server) that a gateway exposes as MCP tools to agents.
"""

from .error_handler import handle_gateway_error
from .models import (
    DeleteGatewayTargetResponse,
    ErrorResponse,
    GatewayTargetResponse,
    ListGatewayTargetsResponse,
    SynchronizeTargetsResponse,
)
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Any


class GatewayTargetTools:
    """Tools for managing AgentCore Gateway targets (control plane)."""

    def __init__(self, client_factory):
        """Initialize with a callable that returns a boto3 control plane client."""
        self._get_client = client_factory

    def register(self, mcp):
        """Register gateway target tools with the MCP server."""
        mcp.tool(name='gateway_target_create')(self.gateway_target_create)
        mcp.tool(name='gateway_target_get')(self.gateway_target_get)
        mcp.tool(name='gateway_target_update')(self.gateway_target_update)
        mcp.tool(name='gateway_target_delete')(self.gateway_target_delete)
        mcp.tool(name='gateway_target_list')(self.gateway_target_list)
        mcp.tool(name='gateway_target_synchronize')(self.gateway_target_synchronize)

    async def gateway_target_create(
        self,
        ctx: Context,
        gateway_identifier: Annotated[
            str,
            Field(description='Gateway ID to attach the target to'),
        ],
        name: Annotated[
            str,
            Field(
                description=(
                    'Unique target name within the gateway. Pattern: '
                    '([0-9a-zA-Z][-]?){1,100}. Tool names exposed via MCP '
                    'are prefixed with this name, e.g. '
                    '"${target_name}___${tool_name}".'
                )
            ),
        ],
        target_configuration: Annotated[
            dict[str, Any],
            Field(
                description=(
                    'Target endpoint and schema config. Union with one key '
                    'under "mcp": "lambda", "apiGateway", "openApiSchema", '
                    '"smithyModel", or "mcpServer". Examples: '
                    '{"mcp":{"lambda":{"lambdaArn":"...","toolSchema":{...}}}}; '
                    '{"mcp":{"mcpServer":{"endpoint":"https://..."}}}; '
                    '{"mcp":{"openApiSchema":{"s3":{"uri":"s3://..."}}}}; '
                    '{"mcp":{"apiGateway":{"restApiId":"...","stage":"...",'
                    '"apiGatewayToolConfiguration":{"toolFilters":[...]}}}}.'
                )
            ),
        ],
        credential_provider_configurations: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    'Outbound auth (exactly 1 item if provided). Each: '
                    '{"credentialProviderType": "GATEWAY_IAM_ROLE" | "OAUTH" '
                    '| "API_KEY", "credentialProvider": {...}}. For OAUTH/'
                    'API_KEY, credentialProvider references a provider ARN '
                    'created via AgentCore Identity (use the agentcore CLI '
                    '"add credential" command or the Identity MCP tools). '
                    'Omit for GATEWAY_IAM_ROLE with no provider config.'
                )
            ),
        ] = None,
        description: Annotated[
            str | None,
            Field(description='Target description (1-200 chars)'),
        ] = None,
        metadata_configuration: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    'Header/query parameter propagation. Shape: '
                    '{"allowedRequestHeaders": [...], '
                    '"allowedResponseHeaders": [...], '
                    '"allowedQueryParameters": [...]}. Max 10 items each. '
                    'Restricted headers (Authorization, Content-Type, etc.) '
                    'cannot be allowlisted.'
                )
            ),
        ] = None,
        client_token: Annotated[
            str | None,
            Field(description='Idempotency token (33-256 chars)'),
        ] = None,
    ) -> GatewayTargetResponse | ErrorResponse:
        """Create a new gateway target to expose tools through a gateway.

        COST WARNING: Target creation is free, but tool invocations through
        the gateway (Lambda calls, REST API calls, MCP server calls) incur
        per-request costs against the underlying services. For mcpServer
        targets, target creation triggers an implicit synchronization that
        calls the MCP server's tools/list — this may take several minutes
        for large tool sets.

        The target starts in CREATING status and transitions to READY when
        available. For mcpServer targets, status may also go through
        SYNCHRONIZING. Use gateway_target_get to check status.

        Security note: Credential material (API keys, OAuth secrets) is
        NOT accepted directly — only provider ARNs. Create the credential
        provider separately using the agentcore CLI or the AgentCore
        Identity service so secrets never flow through LLM context.
        """
        logger.info(f'Creating target in gateway {gateway_identifier}: name={name}')

        try:
            client = self._get_client()
            kwargs: dict[str, Any] = {
                'gatewayIdentifier': gateway_identifier,
                'name': name,
                'targetConfiguration': target_configuration,
            }
            if credential_provider_configurations is not None:
                kwargs['credentialProviderConfigurations'] = credential_provider_configurations
            if description is not None:
                kwargs['description'] = description
            if metadata_configuration is not None:
                kwargs['metadataConfiguration'] = metadata_configuration
            if client_token is not None:
                kwargs['clientToken'] = client_token

            response = client.create_gateway_target(**kwargs)
            target_id = response.get('targetId', 'unknown')
            status = response.get('status', 'CREATING')

            return GatewayTargetResponse(
                status='success',
                message=(
                    f'Target "{name}" created in gateway {gateway_identifier}. '
                    f'Target ID: {target_id}. Status: {status}.'
                ),
                target=response,
            )
        except Exception as e:
            return handle_gateway_error('CreateGatewayTarget', e)

    async def gateway_target_get(
        self,
        ctx: Context,
        gateway_identifier: Annotated[
            str,
            Field(description='Gateway ID'),
        ],
        target_id: Annotated[
            str,
            Field(description='Target ID. Pattern: [0-9a-zA-Z]{10}'),
        ],
    ) -> GatewayTargetResponse | ErrorResponse:
        """Get details of a gateway target.

        Returns the target including status, credential provider config,
        target configuration, metadata configuration, and sync timestamps.
        This is a read-only operation with no cost implications.
        """
        logger.info(f'Getting target {target_id} in gateway {gateway_identifier}')

        try:
            client = self._get_client()
            response = client.get_gateway_target(
                gatewayIdentifier=gateway_identifier,
                targetId=target_id,
            )

            return GatewayTargetResponse(
                status='success',
                message=(
                    f'Target {target_id} retrieved. Status: {response.get("status", "UNKNOWN")}.'
                ),
                target=response,
            )
        except Exception as e:
            return handle_gateway_error('GetGatewayTarget', e)

    async def gateway_target_update(
        self,
        ctx: Context,
        gateway_identifier: Annotated[
            str,
            Field(description='Gateway ID'),
        ],
        target_id: Annotated[
            str,
            Field(description='Target ID to update'),
        ],
        name: Annotated[
            str,
            Field(description='Updated target name'),
        ],
        target_configuration: Annotated[
            dict[str, Any],
            Field(description='Updated target configuration (same shape as create)'),
        ],
        credential_provider_configurations: Annotated[
            list[dict[str, Any]] | None,
            Field(description='Updated credential provider config (1 item)'),
        ] = None,
        description: Annotated[
            str | None,
            Field(description='Updated description (1-200 chars)'),
        ] = None,
        metadata_configuration: Annotated[
            dict[str, Any] | None,
            Field(description='Updated header/query propagation config'),
        ] = None,
    ) -> GatewayTargetResponse | ErrorResponse:
        """Update an existing gateway target.

        COST WARNING: For mcpServer targets, updating triggers implicit
        synchronization with the MCP server's tools/list endpoint, which
        can take several minutes for large tool sets.

        Updates the target configuration, credentials, metadata, or
        description. Returns the updated target details.
        """
        logger.info(f'Updating target {target_id} in gateway {gateway_identifier}')

        try:
            client = self._get_client()
            kwargs: dict[str, Any] = {
                'gatewayIdentifier': gateway_identifier,
                'targetId': target_id,
                'name': name,
                'targetConfiguration': target_configuration,
            }
            if credential_provider_configurations is not None:
                kwargs['credentialProviderConfigurations'] = credential_provider_configurations
            if description is not None:
                kwargs['description'] = description
            if metadata_configuration is not None:
                kwargs['metadataConfiguration'] = metadata_configuration

            response = client.update_gateway_target(**kwargs)

            return GatewayTargetResponse(
                status='success',
                message=f'Target {target_id} updated.',
                target=response,
            )
        except Exception as e:
            return handle_gateway_error('UpdateGatewayTarget', e)

    async def gateway_target_delete(
        self,
        ctx: Context,
        gateway_identifier: Annotated[
            str,
            Field(description='Gateway ID'),
        ],
        target_id: Annotated[
            str,
            Field(description='Target ID to delete'),
        ],
    ) -> DeleteGatewayTargetResponse | ErrorResponse:
        """Delete a gateway target.

        WARNING: This permanently removes the target from the gateway.
        Tools exposed via this target will no longer be available to
        agents. This action cannot be undone.
        """
        logger.info(f'Deleting target {target_id} from gateway {gateway_identifier}')

        try:
            client = self._get_client()
            response = client.delete_gateway_target(
                gatewayIdentifier=gateway_identifier,
                targetId=target_id,
            )

            return DeleteGatewayTargetResponse(
                status='success',
                message=f'Target {target_id} deletion requested.',
                target_id=response.get('targetId', target_id),
                target_status=response.get('status', 'DELETING'),
            )
        except Exception as e:
            return handle_gateway_error('DeleteGatewayTarget', e)

    async def gateway_target_list(
        self,
        ctx: Context,
        gateway_identifier: Annotated[
            str,
            Field(description='Gateway ID whose targets to list'),
        ],
        max_results: Annotated[
            int | None,
            Field(description='Max results per page (1-1000)'),
        ] = None,
        next_token: Annotated[
            str | None,
            Field(description='Pagination token'),
        ] = None,
    ) -> ListGatewayTargetsResponse | ErrorResponse:
        """List all targets attached to a gateway.

        Returns target summaries with IDs, names, status, and timestamps.
        This is a read-only operation with no cost implications.
        """
        logger.info(f'Listing targets for gateway {gateway_identifier}')

        try:
            client = self._get_client()
            kwargs: dict[str, Any] = {'gatewayIdentifier': gateway_identifier}
            if max_results is not None:
                kwargs['maxResults'] = max_results
            if next_token is not None:
                kwargs['nextToken'] = next_token

            response = client.list_gateway_targets(**kwargs)
            items = response.get('items', [])

            return ListGatewayTargetsResponse(
                status='success',
                message=f'Found {len(items)} target(s).',
                targets=items,
                next_token=response.get('nextToken'),
            )
        except Exception as e:
            return handle_gateway_error('ListGatewayTargets', e)

    async def gateway_target_synchronize(
        self,
        ctx: Context,
        gateway_identifier: Annotated[
            str,
            Field(description='Gateway ID'),
        ],
        target_id_list: Annotated[
            list[str],
            Field(
                description=(
                    'Target IDs to synchronize (exactly 1 item). Pattern '
                    'per item: [0-9a-zA-Z]{10}.'
                )
            ),
        ],
    ) -> SynchronizeTargetsResponse | ErrorResponse:
        """Explicitly synchronize gateway targets with their upstream tool catalog.

        COST WARNING: Synchronization calls the MCP server's tools/list
        endpoint and re-indexes the tool catalog (including rebuilding
        semantic search embeddings if enabled). This incurs compute costs
        and can take several minutes for large tool sets. The API returns
        a 202 response and processes asynchronously — monitor progress via
        gateway_target_get.

        Use this for mcpServer targets when the upstream MCP server has
        added, removed, or changed tools. CreateGatewayTarget and
        UpdateGatewayTarget already trigger implicit synchronization, so
        this is only needed when the upstream catalog changes independently.
        """
        logger.info(
            f'Synchronizing targets in gateway {gateway_identifier}: count={len(target_id_list)}'
        )

        try:
            client = self._get_client()
            response = client.synchronize_gateway_targets(
                gatewayIdentifier=gateway_identifier,
                targetIdList=target_id_list,
            )
            targets = response.get('targets', [])

            return SynchronizeTargetsResponse(
                status='success',
                message=f'Synchronization requested for {len(targets)} target(s).',
                targets=targets,
            )
        except Exception as e:
            return handle_gateway_error('SynchronizeGatewayTargets', e)
