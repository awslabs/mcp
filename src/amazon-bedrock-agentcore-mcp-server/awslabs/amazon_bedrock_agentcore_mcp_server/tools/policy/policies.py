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

"""Policy CRUD tools for AgentCore Policy control plane.

A Policy is a Cedar-based authorization rule stored within a Policy
Engine. Policies are validated against the Cedar schema generated from
associated Gateway tools' input schemas. Create/Update/Delete are
asynchronous operations — poll with policy_get to observe status.
"""

from .error_handler import handle_policy_error
from .models import (
    DeletePolicyResponse,
    ErrorResponse,
    ListPoliciesResponse,
    PolicyResponse,
)
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Any


class PolicyTools:
    """Tools for managing Cedar Policies within an AgentCore Policy Engine."""

    def __init__(self, client_factory):
        """Initialize with a callable that returns a boto3 control plane client."""
        self._get_client = client_factory

    def register(self, mcp):
        """Register policy tools with the MCP server."""
        mcp.tool(name='policy_create')(self.policy_create)
        mcp.tool(name='policy_get')(self.policy_get)
        mcp.tool(name='policy_update')(self.policy_update)
        mcp.tool(name='policy_delete')(self.policy_delete)
        mcp.tool(name='policy_list')(self.policy_list)

    async def policy_create(
        self,
        ctx: Context,
        policy_engine_id: Annotated[
            str,
            Field(description='Parent policy engine ID (12-59 chars)'),
        ],
        name: Annotated[
            str,
            Field(
                description=(
                    'Immutable, unique policy name. Pattern: [A-Za-z][A-Za-z0-9_]*, max 48 chars.'
                )
            ),
        ],
        definition: Annotated[
            dict[str, Any],
            Field(
                description=(
                    'PolicyDefinition union. Specify exactly one key: '
                    '"cedar" with {"statement": "<cedar policy text>"} '
                    'for a raw Cedar statement (35-10000 chars), OR '
                    '"policyGeneration" with '
                    '{"policyGenerationId": "<id>", '
                    '"policyGenerationAssetId": "<id>"} to reference a '
                    'generated asset from a previous policy generation.'
                )
            ),
        ],
        description: Annotated[
            str | None,
            Field(description='Human-readable description (1-4096 chars)'),
        ] = None,
        validation_mode: Annotated[
            str | None,
            Field(
                description=(
                    'How policy validation findings are handled. '
                    '"FAIL_ON_ANY_FINDINGS" (default) rejects policies '
                    'with validation findings. "IGNORE_ALL_FINDINGS" '
                    'creates the policy regardless of findings.'
                )
            ),
        ] = None,
        client_token: Annotated[
            str | None,
            Field(description='Idempotency token (33-256 chars)'),
        ] = None,
    ) -> PolicyResponse | ErrorResponse:
        """Create a Cedar policy within an AgentCore Policy Engine.

        COST WARNING: Creating a policy invokes the validation pipeline
        and provisions a billable policy resource. This incurs AWS
        charges.

        Policies are validated against the Cedar schema derived from
        the parent policy engine's associated Gateway tools. Create is
        asynchronous — the policy starts in CREATING and transitions to
        ACTIVE or CREATE_FAILED. Poll with policy_get.
        """
        logger.info(f'Creating policy "{name}" in engine {policy_engine_id}')

        try:
            client = self._get_client()
            kwargs: dict[str, Any] = {
                'policyEngineId': policy_engine_id,
                'name': name,
                'definition': definition,
            }
            if description is not None:
                kwargs['description'] = description
            if validation_mode is not None:
                kwargs['validationMode'] = validation_mode
            if client_token is not None:
                kwargs['clientToken'] = client_token

            response = client.create_policy(**kwargs)

            return PolicyResponse(
                status='success',
                message=(
                    f'Policy "{name}" creation requested. '
                    f'ID: {response.get("policyId", "unknown")}. '
                    f'Status: {response.get("status", "CREATING")}.'
                ),
                policy=response,
            )
        except Exception as e:
            return handle_policy_error('CreatePolicy', e)

    async def policy_get(
        self,
        ctx: Context,
        policy_engine_id: Annotated[
            str,
            Field(description='Parent policy engine ID'),
        ],
        policy_id: Annotated[
            str,
            Field(description='Policy ID (12-59 chars)'),
        ],
    ) -> PolicyResponse | ErrorResponse:
        """Get details of a Cedar policy.

        Returns the full policy including its Cedar definition, status,
        and timestamps. This is a read-only operation with no cost
        implications. Use to poll status after create/update/delete.
        """
        logger.info(f'Getting policy {policy_id} from engine {policy_engine_id}')

        try:
            client = self._get_client()
            response = client.get_policy(
                policyEngineId=policy_engine_id,
                policyId=policy_id,
            )

            return PolicyResponse(
                status='success',
                message=(
                    f'Policy {policy_id} retrieved. Status: {response.get("status", "UNKNOWN")}.'
                ),
                policy=response,
            )
        except Exception as e:
            return handle_policy_error('GetPolicy', e)

    async def policy_update(
        self,
        ctx: Context,
        policy_engine_id: Annotated[
            str,
            Field(description='Parent policy engine ID'),
        ],
        policy_id: Annotated[
            str,
            Field(description='Policy ID to update'),
        ],
        definition: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    'New PolicyDefinition replacing the existing one. '
                    'Union with one key: "cedar" ({"statement": "..."}) '
                    'or "policyGeneration" ({"policyGenerationId": ..., '
                    '"policyGenerationAssetId": ...}).'
                )
            ),
        ] = None,
        description: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    'UpdatedDescription object with "optionalValue" key. '
                    'Set {"optionalValue": "new text"} to update, '
                    '{"optionalValue": null} to clear. Omit to leave '
                    'unchanged.'
                )
            ),
        ] = None,
        validation_mode: Annotated[
            str | None,
            Field(
                description=(
                    'Validation mode for this update: '
                    '"FAIL_ON_ANY_FINDINGS" or "IGNORE_ALL_FINDINGS".'
                )
            ),
        ] = None,
    ) -> PolicyResponse | ErrorResponse:
        """Update a Cedar policy.

        COST WARNING: Updating a policy re-invokes the validation
        pipeline and consumes compute resources. This incurs AWS
        charges.

        Update is asynchronous — status transitions through UPDATING.
        Poll with policy_get.
        """
        logger.info(f'Updating policy {policy_id} in engine {policy_engine_id}')

        try:
            client = self._get_client()
            kwargs: dict[str, Any] = {
                'policyEngineId': policy_engine_id,
                'policyId': policy_id,
            }
            if definition is not None:
                kwargs['definition'] = definition
            if description is not None:
                kwargs['description'] = description
            if validation_mode is not None:
                kwargs['validationMode'] = validation_mode

            response = client.update_policy(**kwargs)

            return PolicyResponse(
                status='success',
                message=(
                    f'Policy {policy_id} update requested. '
                    f'Status: {response.get("status", "UPDATING")}.'
                ),
                policy=response,
            )
        except Exception as e:
            return handle_policy_error('UpdatePolicy', e)

    async def policy_delete(
        self,
        ctx: Context,
        policy_engine_id: Annotated[
            str,
            Field(description='Parent policy engine ID'),
        ],
        policy_id: Annotated[
            str,
            Field(description='Policy ID to delete'),
        ],
    ) -> DeletePolicyResponse | ErrorResponse:
        """Delete a Cedar policy.

        WARNING: This permanently deletes the policy. Delete is
        asynchronous — status transitions through DELETING. This
        action cannot be undone.
        """
        logger.info(f'Deleting policy {policy_id} from engine {policy_engine_id}')

        try:
            client = self._get_client()
            response = client.delete_policy(
                policyEngineId=policy_engine_id,
                policyId=policy_id,
            )

            return DeletePolicyResponse(
                status='success',
                message=f'Policy {policy_id} deletion requested.',
                policy_id=response.get('policyId', policy_id),
                policy_status=response.get('status', 'DELETING'),
            )
        except Exception as e:
            return handle_policy_error('DeletePolicy', e)

    async def policy_list(
        self,
        ctx: Context,
        policy_engine_id: Annotated[
            str,
            Field(description='Parent policy engine ID'),
        ],
        target_resource_scope: Annotated[
            str | None,
            Field(
                description=(
                    'Filter policies by target resource scope '
                    '(20-1011 chars). Typically a Gateway ARN.'
                )
            ),
        ] = None,
        max_results: Annotated[
            int | None,
            Field(description='Max results per page (1-100, default 10)'),
        ] = None,
        next_token: Annotated[
            str | None,
            Field(description='Pagination token'),
        ] = None,
    ) -> ListPoliciesResponse | ErrorResponse:
        """List Cedar policies within a Policy Engine.

        Returns policy summaries with IDs, ARNs, definitions, status,
        and timestamps. Optionally filter by target resource scope
        (e.g. a Gateway ARN). This is a read-only operation with no
        cost implications.
        """
        logger.info(f'Listing policies in engine {policy_engine_id}')

        try:
            client = self._get_client()
            kwargs: dict[str, Any] = {'policyEngineId': policy_engine_id}
            if target_resource_scope is not None:
                kwargs['targetResourceScope'] = target_resource_scope
            if max_results is not None:
                kwargs['maxResults'] = max_results
            if next_token is not None:
                kwargs['nextToken'] = next_token

            response = client.list_policies(**kwargs)
            policies = response.get('policies', [])

            return ListPoliciesResponse(
                status='success',
                message=f'Found {len(policies)} policy(ies).',
                policies=policies,
                next_token=response.get('nextToken'),
            )
        except Exception as e:
            return handle_policy_error('ListPolicies', e)
