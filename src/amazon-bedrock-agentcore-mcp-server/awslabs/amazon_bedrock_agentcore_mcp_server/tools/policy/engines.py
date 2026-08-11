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

"""Policy Engine tools for AgentCore Policy control plane.

A Policy Engine is a top-level authorization container that holds
Cedar-based policies. Engines can be attached to Gateways to enforce
access control on tool invocations.
"""

from .error_handler import handle_policy_error
from .models import (
    DeletePolicyEngineResponse,
    ErrorResponse,
    ListPolicyEnginesResponse,
    PolicyEngineResponse,
)
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Any


class PolicyEngineTools:
    """Tools for managing AgentCore Policy Engines."""

    def __init__(self, client_factory):
        """Initialize with a callable that returns a boto3 control plane client."""
        self._get_client = client_factory

    def register(self, mcp):
        """Register policy engine tools with the MCP server."""
        mcp.tool(name='policy_engine_create')(self.policy_engine_create)
        mcp.tool(name='policy_engine_get')(self.policy_engine_get)
        mcp.tool(name='policy_engine_update')(self.policy_engine_update)
        mcp.tool(name='policy_engine_delete')(self.policy_engine_delete)
        mcp.tool(name='policy_engine_list')(self.policy_engine_list)

    async def policy_engine_create(
        self,
        ctx: Context,
        name: Annotated[
            str,
            Field(
                description=(
                    'Immutable name for the policy engine, unique within the '
                    'account. Pattern: [A-Za-z][A-Za-z0-9_]*, max 48 chars.'
                )
            ),
        ],
        description: Annotated[
            str | None,
            Field(description='Purpose and scope of the policy engine (1-4096 chars)'),
        ] = None,
        encryption_key_arn: Annotated[
            str | None,
            Field(description='KMS key ARN for encryption at rest'),
        ] = None,
        client_token: Annotated[
            str | None,
            Field(description='Idempotency token (33-256 chars)'),
        ] = None,
        tags: Annotated[
            dict[str, str] | None,
            Field(description='Tags as key-value pairs (max 50)'),
        ] = None,
    ) -> PolicyEngineResponse | ErrorResponse:
        """Create a new AgentCore Policy Engine.

        COST WARNING: Creating a policy engine provisions AWS
        infrastructure and incurs AWS charges. The engine starts in
        CREATING status and transitions to ACTIVE when ready. Use
        policy_engine_get to poll the status.

        Returns the created policy engine details including its ID and ARN.
        """
        logger.info(f'Creating policy engine: {name}')

        try:
            client = self._get_client()
            kwargs: dict[str, Any] = {'name': name}
            if description is not None:
                kwargs['description'] = description
            if encryption_key_arn is not None:
                kwargs['encryptionKeyArn'] = encryption_key_arn
            if client_token is not None:
                kwargs['clientToken'] = client_token
            if tags is not None:
                kwargs['tags'] = tags

            response = client.create_policy_engine(**kwargs)

            return PolicyEngineResponse(
                status='success',
                message=(
                    f'Policy engine "{name}" creation requested. '
                    f'ID: {response.get("policyEngineId", "unknown")}. '
                    f'Status: {response.get("status", "CREATING")}.'
                ),
                policy_engine=response,
            )
        except Exception as e:
            return handle_policy_error('CreatePolicyEngine', e)

    async def policy_engine_get(
        self,
        ctx: Context,
        policy_engine_id: Annotated[
            str,
            Field(
                description=(
                    'Policy engine ID (12-59 chars). Pattern: [A-Za-z][A-Za-z0-9_]*-[a-z0-9_]{10}'
                )
            ),
        ],
    ) -> PolicyEngineResponse | ErrorResponse:
        """Get details of an AgentCore Policy Engine.

        Returns the policy engine including status, encryption config,
        and timestamps. This is a read-only operation with no cost
        implications.
        """
        logger.info(f'Getting policy engine: {policy_engine_id}')

        try:
            client = self._get_client()
            response = client.get_policy_engine(policyEngineId=policy_engine_id)

            return PolicyEngineResponse(
                status='success',
                message=(
                    f'Policy engine {policy_engine_id} retrieved. '
                    f'Status: {response.get("status", "UNKNOWN")}.'
                ),
                policy_engine=response,
            )
        except Exception as e:
            return handle_policy_error('GetPolicyEngine', e)

    async def policy_engine_update(
        self,
        ctx: Context,
        policy_engine_id: Annotated[
            str,
            Field(description='Policy engine ID to update'),
        ],
        description: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    'UpdatedDescription object with "optionalValue" key. '
                    'Set {"optionalValue": "new text"} to change the '
                    'description, or {"optionalValue": null} to clear it. '
                    'Omit the parameter entirely to leave the description '
                    'unchanged.'
                )
            ),
        ] = None,
    ) -> PolicyEngineResponse | ErrorResponse:
        """Update an AgentCore Policy Engine.

        Currently only the description can be updated. The engine's name
        and encryption configuration are immutable after creation.
        """
        logger.info(f'Updating policy engine: {policy_engine_id}')

        try:
            client = self._get_client()
            kwargs: dict[str, Any] = {'policyEngineId': policy_engine_id}
            if description is not None:
                kwargs['description'] = description

            response = client.update_policy_engine(**kwargs)

            return PolicyEngineResponse(
                status='success',
                message=(
                    f'Policy engine {policy_engine_id} update requested. '
                    f'Status: {response.get("status", "UPDATING")}.'
                ),
                policy_engine=response,
            )
        except Exception as e:
            return handle_policy_error('UpdatePolicyEngine', e)

    async def policy_engine_delete(
        self,
        ctx: Context,
        policy_engine_id: Annotated[
            str,
            Field(description='Policy engine ID to delete'),
        ],
    ) -> DeletePolicyEngineResponse | ErrorResponse:
        """Delete an AgentCore Policy Engine.

        WARNING: This permanently deletes the policy engine. The engine
        must not have any associated policies before deletion — delete
        all policies first with policy_delete, then delete the engine.
        This action cannot be undone.
        """
        logger.info(f'Deleting policy engine: {policy_engine_id}')

        try:
            client = self._get_client()
            response = client.delete_policy_engine(policyEngineId=policy_engine_id)

            return DeletePolicyEngineResponse(
                status='success',
                message=f'Policy engine {policy_engine_id} deletion requested.',
                policy_engine_id=response.get('policyEngineId', policy_engine_id),
                policy_engine_status=response.get('status', 'DELETING'),
            )
        except Exception as e:
            return handle_policy_error('DeletePolicyEngine', e)

    async def policy_engine_list(
        self,
        ctx: Context,
        max_results: Annotated[
            int | None,
            Field(description='Max results per page (1-100, default 10)'),
        ] = None,
        next_token: Annotated[
            str | None,
            Field(description='Pagination token from previous response'),
        ] = None,
    ) -> ListPolicyEnginesResponse | ErrorResponse:
        """List AgentCore Policy Engines in the account.

        Returns policy engine summaries with IDs, ARNs, status, and
        timestamps. This is a read-only operation with no cost
        implications.
        """
        logger.info('Listing policy engines')

        try:
            client = self._get_client()
            kwargs: dict[str, Any] = {}
            if max_results is not None:
                kwargs['maxResults'] = max_results
            if next_token is not None:
                kwargs['nextToken'] = next_token

            response = client.list_policy_engines(**kwargs)
            engines = response.get('policyEngines', [])

            return ListPolicyEnginesResponse(
                status='success',
                message=f'Found {len(engines)} policy engine(s).',
                policy_engines=engines,
                next_token=response.get('nextToken'),
            )
        except Exception as e:
            return handle_policy_error('ListPolicyEngines', e)
