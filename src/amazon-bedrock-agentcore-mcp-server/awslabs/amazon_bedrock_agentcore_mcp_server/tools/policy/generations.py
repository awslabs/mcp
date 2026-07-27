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

"""Policy Generation tools for AgentCore Policy control plane.

Policy generation uses AI to translate natural-language policy intent
into Cedar policy statements. Generated assets auto-delete after 7 days;
reference them in policy_create via the "policyGeneration" union variant
to promote them into persistent policies.
"""

from .error_handler import handle_policy_error
from .models import (
    ErrorResponse,
    ListPolicyGenerationAssetsResponse,
    ListPolicyGenerationsResponse,
    PolicyGenerationResponse,
)
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Any


class PolicyGenerationTools:
    """Tools for AI-powered Cedar policy generation."""

    def __init__(self, client_factory):
        """Initialize with a callable that returns a boto3 control plane client."""
        self._get_client = client_factory

    def register(self, mcp):
        """Register policy generation tools with the MCP server."""
        mcp.tool(name='policy_generation_start')(self.policy_generation_start)
        mcp.tool(name='policy_generation_get')(self.policy_generation_get)
        mcp.tool(name='policy_generation_list')(self.policy_generation_list)
        mcp.tool(name='policy_generation_list_assets')(self.policy_generation_list_assets)

    async def policy_generation_start(
        self,
        ctx: Context,
        policy_engine_id: Annotated[
            str,
            Field(description='Policy engine ID providing context for generation'),
        ],
        name: Annotated[
            str,
            Field(
                description=(
                    'Name for tracking this generation request. '
                    'Pattern: [A-Za-z][A-Za-z0-9_]*, max 48 chars.'
                )
            ),
        ],
        content: Annotated[
            dict[str, Any],
            Field(
                description=(
                    'Content union. Specify key "rawText" with a natural-'
                    'language description (1-2000 chars) of the desired '
                    'policy behavior. Example: '
                    '{"rawText": "Allow users in group Admins to invoke '
                    'the weather tool during business hours"}.'
                )
            ),
        ],
        resource: Annotated[
            dict[str, Any],
            Field(
                description=(
                    'Resource union identifying the target for this '
                    'policy. Specify key "arn" with the resource ARN '
                    '(20-1011 chars). Currently only Gateway ARNs are '
                    'supported. Example: '
                    '{"arn": "arn:aws:bedrock-agentcore:us-east-1:'
                    '123456789012:gateway/my-gateway-abc123"}.'
                )
            ),
        ],
        client_token: Annotated[
            str | None,
            Field(description='Idempotency token (33-256 chars)'),
        ] = None,
    ) -> PolicyGenerationResponse | ErrorResponse:
        """Start an AI-powered Cedar policy generation from natural language.

        COST WARNING: Policy generation invokes foundation models and
        consumes significant compute resources. This is typically the
        most expensive Policy operation per call. Each invocation incurs
        AWS charges.

        The generation is asynchronous — starts in GENERATING and
        transitions to GENERATED or GENERATE_FAILED. Poll with
        policy_generation_get. Generated assets auto-delete after 7
        days. To persist a generated policy, reference its asset in
        policy_create via the "policyGeneration" union variant.
        """
        logger.info(f'Starting policy generation "{name}" in engine {policy_engine_id}')

        try:
            client = self._get_client()
            kwargs: dict[str, Any] = {
                'policyEngineId': policy_engine_id,
                'name': name,
                'content': content,
                'resource': resource,
            }
            if client_token is not None:
                kwargs['clientToken'] = client_token

            response = client.start_policy_generation(**kwargs)

            return PolicyGenerationResponse(
                status='success',
                message=(
                    f'Policy generation "{name}" started. '
                    f'ID: {response.get("policyGenerationId", "unknown")}. '
                    f'Status: {response.get("status", "GENERATING")}.'
                ),
                policy_generation=response,
            )
        except Exception as e:
            return handle_policy_error('StartPolicyGeneration', e)

    async def policy_generation_get(
        self,
        ctx: Context,
        policy_engine_id: Annotated[
            str,
            Field(description='Policy engine ID'),
        ],
        policy_generation_id: Annotated[
            str,
            Field(description='Policy generation ID (12-59 chars)'),
        ],
    ) -> PolicyGenerationResponse | ErrorResponse:
        """Get details of an AgentCore Policy Generation.

        Returns the generation including status, findings, and resource
        context. Use to poll after policy_generation_start. This is a
        read-only operation with no cost implications.
        """
        logger.info(
            f'Getting policy generation {policy_generation_id} in engine {policy_engine_id}'
        )

        try:
            client = self._get_client()
            response = client.get_policy_generation(
                policyEngineId=policy_engine_id,
                policyGenerationId=policy_generation_id,
            )

            return PolicyGenerationResponse(
                status='success',
                message=(
                    f'Policy generation {policy_generation_id} retrieved. '
                    f'Status: {response.get("status", "UNKNOWN")}.'
                ),
                policy_generation=response,
            )
        except Exception as e:
            return handle_policy_error('GetPolicyGeneration', e)

    async def policy_generation_list(
        self,
        ctx: Context,
        policy_engine_id: Annotated[
            str,
            Field(description='Policy engine ID'),
        ],
        max_results: Annotated[
            int | None,
            Field(description='Max results per page (1-100)'),
        ] = None,
        next_token: Annotated[
            str | None,
            Field(description='Pagination token'),
        ] = None,
    ) -> ListPolicyGenerationsResponse | ErrorResponse:
        """List policy generations within a Policy Engine.

        Returns policy generation summaries with IDs, ARNs, status,
        resource context, and timestamps. Generated assets auto-delete
        after 7 days. This is a read-only operation with no cost
        implications.
        """
        logger.info(f'Listing policy generations in engine {policy_engine_id}')

        try:
            client = self._get_client()
            kwargs: dict[str, Any] = {'policyEngineId': policy_engine_id}
            if max_results is not None:
                kwargs['maxResults'] = max_results
            if next_token is not None:
                kwargs['nextToken'] = next_token

            response = client.list_policy_generations(**kwargs)
            generations = response.get('policyGenerations', [])

            return ListPolicyGenerationsResponse(
                status='success',
                message=f'Found {len(generations)} policy generation(s).',
                policy_generations=generations,
                next_token=response.get('nextToken'),
            )
        except Exception as e:
            return handle_policy_error('ListPolicyGenerations', e)

    async def policy_generation_list_assets(
        self,
        ctx: Context,
        policy_engine_id: Annotated[
            str,
            Field(description='Policy engine ID'),
        ],
        policy_generation_id: Annotated[
            str,
            Field(description='Policy generation ID'),
        ],
        max_results: Annotated[
            int | None,
            Field(description='Max results per page (1-100, default 10)'),
        ] = None,
        next_token: Annotated[
            str | None,
            Field(description='Pagination token'),
        ] = None,
    ) -> ListPolicyGenerationAssetsResponse | ErrorResponse:
        """List Cedar policies and findings produced by policy generation.

        Returns generated policy assets — each with its Cedar definition
        (if translatable), the original natural-language fragment, and
        validation findings (VALID, INVALID, NOT_TRANSLATABLE, ALLOW_ALL,
        ALLOW_NONE, DENY_ALL, DENY_NONE). Use assets with VALID findings
        in policy_create via the "policyGeneration" definition variant.
        This is a read-only operation with no cost implications.
        """
        logger.info(
            f'Listing assets for policy generation {policy_generation_id} '
            f'in engine {policy_engine_id}'
        )

        try:
            client = self._get_client()
            kwargs: dict[str, Any] = {
                'policyEngineId': policy_engine_id,
                'policyGenerationId': policy_generation_id,
            }
            if max_results is not None:
                kwargs['maxResults'] = max_results
            if next_token is not None:
                kwargs['nextToken'] = next_token

            response = client.list_policy_generation_assets(**kwargs)
            assets = response.get('policyGenerationAssets', [])

            return ListPolicyGenerationAssetsResponse(
                status='success',
                message=f'Found {len(assets)} policy generation asset(s).',
                policy_generation_assets=assets,
                next_token=response.get('nextToken'),
            )
        except Exception as e:
            return handle_policy_error('ListPolicyGenerationAssets', e)
