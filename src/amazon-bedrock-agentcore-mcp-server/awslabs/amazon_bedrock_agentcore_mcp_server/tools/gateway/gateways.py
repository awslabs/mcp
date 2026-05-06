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

"""Control plane tools for AgentCore Gateway resource management.

Provides tools to create, get, update, delete, and list Gateway resources.
"""

from .error_handler import handle_gateway_error
from .models import (
    DeleteGatewayResponse,
    ErrorResponse,
    GatewayResponse,
    ListGatewaysResponse,
)
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Any


class GatewayTools:
    """Tools for managing AgentCore Gateway resources (control plane)."""

    def __init__(self, client_factory):
        """Initialize with a callable that returns a boto3 control plane client."""
        self._get_client = client_factory

    def register(self, mcp):
        """Register gateway control plane tools with the MCP server."""
        mcp.tool(name='gateway_create')(self.gateway_create)
        mcp.tool(name='gateway_get')(self.gateway_get)
        mcp.tool(name='gateway_update')(self.gateway_update)
        mcp.tool(name='gateway_delete')(self.gateway_delete)
        mcp.tool(name='gateway_list')(self.gateway_list)

    async def gateway_create(
        self,
        ctx: Context,
        name: Annotated[
            str,
            Field(description=('Unique gateway name. Pattern: ([0-9a-zA-Z][-]?){1,100}')),
        ],
        role_arn: Annotated[
            str,
            Field(
                description=(
                    'IAM service role ARN that AgentCore assumes to invoke '
                    'targets. Must trust bedrock-agentcore.amazonaws.com.'
                )
            ),
        ],
        protocol_type: Annotated[
            str,
            Field(description='Protocol type for the gateway. Currently only "MCP".'),
        ],
        authorizer_type: Annotated[
            str,
            Field(
                description=(
                    'Inbound authorization type: "CUSTOM_JWT", "AWS_IAM", '
                    'or "NONE". NONE gateways are unauthenticated and should '
                    'only be used for public production endpoints with other '
                    'security layers in place.'
                )
            ),
        ],
        authorizer_configuration: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    'Authorizer config. Required when authorizer_type is '
                    '"CUSTOM_JWT". Shape: {"customJWTAuthorizer": '
                    '{"discoveryUrl": "...", "allowedClients": [...], '
                    '"allowedAudience": [...], "allowedScopes": [...]}}.'
                )
            ),
        ] = None,
        description: Annotated[
            str | None,
            Field(description='Gateway description (1-200 chars)'),
        ] = None,
        kms_key_arn: Annotated[
            str | None,
            Field(
                description=(
                    'Customer-managed KMS key ARN for at-rest encryption. '
                    'Omit to use the AWS-managed key.'
                )
            ),
        ] = None,
        exception_level: Annotated[
            str | None,
            Field(
                description=(
                    'Error detail level. Set to "DEBUG" during development '
                    'to return detailed errors on invocation. Omit for '
                    'production to return generic errors only.'
                )
            ),
        ] = None,
        protocol_configuration: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    'Protocol-specific settings. For MCP: '
                    '{"mcp": {"searchType": "SEMANTIC", "instructions": '
                    '"...", "supportedVersions": [...]}}. searchType enables '
                    'the built-in x_amz_bedrock_agentcore_search tool and '
                    'cannot be changed after creation.'
                )
            ),
        ] = None,
        policy_engine_configuration: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    'Policy engine association. Shape: {"arn": '
                    '"<policy-engine-arn>", "mode": "LOG_ONLY" | "ENFORCE"}.'
                )
            ),
        ] = None,
        interceptor_configurations: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    'Lambda interceptors (1-2 items). Each has: '
                    '"interceptor": {"lambda": {"arn": "..."}}, '
                    '"interceptionPoints": ["REQUEST" | "RESPONSE"], '
                    'optional "inputConfiguration": {"passRequestHeaders": bool}.'
                )
            ),
        ] = None,
        client_token: Annotated[
            str | None,
            Field(description='Idempotency token (33-256 chars)'),
        ] = None,
        tags: Annotated[
            dict[str, str] | None,
            Field(description='Tags as key-value pairs (max 50)'),
        ] = None,
    ) -> GatewayResponse | ErrorResponse:
        """Create a new AgentCore Gateway resource.

        COST WARNING: Creating a gateway provisions AWS infrastructure and
        incurs AWS charges. Gateway invocations are billed separately per
        request. A workload identity is also auto-created alongside the
        gateway.

        The gateway starts in CREATING status and transitions to READY when
        ready for invocation. Use gateway_get to check status. The returned
        gatewayUrl is the endpoint for MCP invocations; tools are added via
        gateway_target_create.

        Returns the created gateway details including its ID, ARN, URL, and
        auto-created workload identity ARN.
        """
        logger.info(f'Creating gateway: name={name}')

        try:
            client = self._get_client()
            kwargs: dict[str, Any] = {
                'name': name,
                'roleArn': role_arn,
                'protocolType': protocol_type,
                'authorizerType': authorizer_type,
            }
            if authorizer_configuration is not None:
                kwargs['authorizerConfiguration'] = authorizer_configuration
            if description is not None:
                kwargs['description'] = description
            if kms_key_arn is not None:
                kwargs['kmsKeyArn'] = kms_key_arn
            if exception_level is not None:
                kwargs['exceptionLevel'] = exception_level
            if protocol_configuration is not None:
                kwargs['protocolConfiguration'] = protocol_configuration
            if policy_engine_configuration is not None:
                kwargs['policyEngineConfiguration'] = policy_engine_configuration
            if interceptor_configurations is not None:
                kwargs['interceptorConfigurations'] = interceptor_configurations
            if client_token is not None:
                kwargs['clientToken'] = client_token
            if tags is not None:
                kwargs['tags'] = tags

            response = client.create_gateway(**kwargs)
            gateway_id = response.get('gatewayId', 'unknown')
            status = response.get('status', 'CREATING')

            return GatewayResponse(
                status='success',
                message=(f'Gateway "{name}" created. ID: {gateway_id}. Status: {status}.'),
                gateway=response,
            )
        except Exception as e:
            return handle_gateway_error('CreateGateway', e)

    async def gateway_get(
        self,
        ctx: Context,
        gateway_identifier: Annotated[
            str,
            Field(description=('Gateway ID. Pattern: ([0-9a-z][-]?){1,100}-[0-9a-z]{10}')),
        ],
    ) -> GatewayResponse | ErrorResponse:
        """Get details of an AgentCore Gateway.

        Returns the gateway including status, authorizer configuration, URL,
        protocol settings, and associated workload identity. This is a
        read-only operation with no cost implications.
        """
        logger.info(f'Getting gateway: {gateway_identifier}')

        try:
            client = self._get_client()
            response = client.get_gateway(gatewayIdentifier=gateway_identifier)

            return GatewayResponse(
                status='success',
                message=(
                    f'Gateway {gateway_identifier} retrieved. '
                    f'Status: {response.get("status", "UNKNOWN")}.'
                ),
                gateway=response,
            )
        except Exception as e:
            return handle_gateway_error('GetGateway', e)

    async def gateway_update(
        self,
        ctx: Context,
        gateway_identifier: Annotated[
            str,
            Field(description='Gateway ID to update'),
        ],
        name: Annotated[
            str,
            Field(
                description=(
                    'Gateway name. Must match the original creation name. '
                    'Pattern: ([0-9a-zA-Z][-]?){1,100}'
                )
            ),
        ],
        role_arn: Annotated[
            str,
            Field(description='Updated IAM service role ARN'),
        ],
        protocol_type: Annotated[
            str,
            Field(description='Protocol type. Currently only "MCP".'),
        ],
        authorizer_type: Annotated[
            str,
            Field(description='Inbound auth: "CUSTOM_JWT", "AWS_IAM", or "NONE"'),
        ],
        authorizer_configuration: Annotated[
            dict[str, Any] | None,
            Field(description='Updated authorizer config (required for CUSTOM_JWT)'),
        ] = None,
        description: Annotated[
            str | None,
            Field(description='Updated description (1-200 chars)'),
        ] = None,
        kms_key_arn: Annotated[
            str | None,
            Field(description='Updated KMS key ARN'),
        ] = None,
        exception_level: Annotated[
            str | None,
            Field(
                description=(
                    'Error detail level. Set to "DEBUG" to enable detailed '
                    'errors; omit to disable.'
                )
            ),
        ] = None,
        protocol_configuration: Annotated[
            dict[str, Any] | None,
            Field(description='Updated protocol config'),
        ] = None,
        policy_engine_configuration: Annotated[
            dict[str, Any] | None,
            Field(description='Updated policy engine config'),
        ] = None,
        interceptor_configurations: Annotated[
            list[dict[str, Any]] | None,
            Field(description='Updated interceptor configs (1-2 items)'),
        ] = None,
    ) -> GatewayResponse | ErrorResponse:
        """Update an AgentCore Gateway.

        COST WARNING: Adding or enabling interceptors adds Lambda invocation
        costs on every gateway request. Policy engine enforcement may also
        affect latency and cost profile.

        Note: UpdateGateway requires all fields that were part of the create
        call — even ones you aren't changing — or the existing values will
        be replaced. Fetch with gateway_get first, then pass through the
        existing values for fields you don't want to change.

        Returns the updated gateway details.
        """
        logger.info(f'Updating gateway: {gateway_identifier}')

        try:
            client = self._get_client()
            kwargs: dict[str, Any] = {
                'gatewayIdentifier': gateway_identifier,
                'name': name,
                'roleArn': role_arn,
                'protocolType': protocol_type,
                'authorizerType': authorizer_type,
            }
            if authorizer_configuration is not None:
                kwargs['authorizerConfiguration'] = authorizer_configuration
            if description is not None:
                kwargs['description'] = description
            if kms_key_arn is not None:
                kwargs['kmsKeyArn'] = kms_key_arn
            if exception_level is not None:
                kwargs['exceptionLevel'] = exception_level
            if protocol_configuration is not None:
                kwargs['protocolConfiguration'] = protocol_configuration
            if policy_engine_configuration is not None:
                kwargs['policyEngineConfiguration'] = policy_engine_configuration
            if interceptor_configurations is not None:
                kwargs['interceptorConfigurations'] = interceptor_configurations

            response = client.update_gateway(**kwargs)

            return GatewayResponse(
                status='success',
                message=f'Gateway {gateway_identifier} updated.',
                gateway=response,
            )
        except Exception as e:
            return handle_gateway_error('UpdateGateway', e)

    async def gateway_delete(
        self,
        ctx: Context,
        gateway_identifier: Annotated[
            str,
            Field(description='Gateway ID to delete'),
        ],
    ) -> DeleteGatewayResponse | ErrorResponse:
        """Delete an AgentCore Gateway.

        WARNING: This permanently deletes the gateway. All associated
        targets and the auto-created workload identity are removed. Agents
        pointing to this gateway's URL will fail to invoke. This action
        cannot be undone.

        Note: You may need to delete gateway targets first if the gateway
        has any; otherwise the API will return a ConflictException.
        """
        logger.info(f'Deleting gateway: {gateway_identifier}')

        try:
            client = self._get_client()
            response = client.delete_gateway(gatewayIdentifier=gateway_identifier)

            return DeleteGatewayResponse(
                status='success',
                message=f'Gateway {gateway_identifier} deletion requested.',
                gateway_id=response.get('gatewayId', gateway_identifier),
                gateway_status=response.get('status', 'DELETING'),
            )
        except Exception as e:
            return handle_gateway_error('DeleteGateway', e)

    async def gateway_list(
        self,
        ctx: Context,
        max_results: Annotated[
            int | None,
            Field(description='Max results per page (1-1000)'),
        ] = None,
        next_token: Annotated[
            str | None,
            Field(description='Pagination token from previous response'),
        ] = None,
    ) -> ListGatewaysResponse | ErrorResponse:
        """List all AgentCore Gateways in the account.

        Returns gateway summaries with IDs, names, authorizer types, status,
        and timestamps. This is a read-only operation with no cost
        implications.
        """
        logger.info('Listing gateways')

        try:
            client = self._get_client()
            kwargs: dict[str, Any] = {}
            if max_results is not None:
                kwargs['maxResults'] = max_results
            if next_token is not None:
                kwargs['nextToken'] = next_token

            response = client.list_gateways(**kwargs)
            items = response.get('items', [])

            return ListGatewaysResponse(
                status='success',
                message=f'Found {len(items)} gateway(s).',
                gateways=items,
                next_token=response.get('nextToken'),
            )
        except Exception as e:
            return handle_gateway_error('ListGateways', e)
