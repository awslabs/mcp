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

"""Resource policy tools for AgentCore Gateway.

Resource-based policies control which principals can invoke a gateway.
Also applies to AgentCore Runtime. For Gateway, these policies work in
addition to the inbound authorization configured on the gateway itself.
"""

from .error_handler import handle_gateway_error
from .models import (
    DeleteResourcePolicyResponse,
    ErrorResponse,
    ResourcePolicyResponse,
)
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated


class ResourcePolicyTools:
    """Tools for managing resource-based policies on AgentCore Gateways."""

    def __init__(self, client_factory):
        """Initialize with a callable that returns a boto3 control plane client."""
        self._get_client = client_factory

    def register(self, mcp):
        """Register resource policy tools with the MCP server."""
        mcp.tool(name='gateway_resource_policy_put')(self.gateway_resource_policy_put)
        mcp.tool(name='gateway_resource_policy_get')(self.gateway_resource_policy_get)
        mcp.tool(name='gateway_resource_policy_delete')(self.gateway_resource_policy_delete)

    async def gateway_resource_policy_put(
        self,
        ctx: Context,
        resource_arn: Annotated[
            str,
            Field(
                description=(
                    'ARN of the gateway (or runtime) resource the policy '
                    'applies to. 20-1011 chars.'
                )
            ),
        ],
        policy: Annotated[
            str,
            Field(
                description=(
                    'IAM resource policy document as a JSON string '
                    '(1-20480 chars). Must specify Principal, Action, '
                    'Resource, and Effect per standard IAM policy syntax.'
                )
            ),
        ],
    ) -> ResourcePolicyResponse | ErrorResponse:
        """Create or update a resource-based policy on a gateway.

        COST WARNING: The policy itself is free, but misconfigured policies
        can expose a gateway to unintended principals — review carefully
        before applying.

        Creates or replaces the resource policy attached to the specified
        gateway. Use this to grant cross-account access or to restrict
        access beyond what inbound authorization provides.
        """
        logger.info(f'Putting resource policy on {resource_arn}')

        try:
            client = self._get_client()
            response = client.put_resource_policy(
                resourceArn=resource_arn,
                policy=policy,
            )

            return ResourcePolicyResponse(
                status='success',
                message=f'Resource policy set on {resource_arn}.',
                policy=response.get('policy', ''),
            )
        except Exception as e:
            return handle_gateway_error('PutResourcePolicy', e)

    async def gateway_resource_policy_get(
        self,
        ctx: Context,
        resource_arn: Annotated[
            str,
            Field(description='ARN of the gateway resource (20-1011 chars)'),
        ],
    ) -> ResourcePolicyResponse | ErrorResponse:
        """Get the resource-based policy attached to a gateway.

        Returns the raw JSON policy document. This is a read-only operation
        with no cost implications.
        """
        logger.info(f'Getting resource policy on {resource_arn}')

        try:
            client = self._get_client()
            response = client.get_resource_policy(resourceArn=resource_arn)

            return ResourcePolicyResponse(
                status='success',
                message=f'Resource policy retrieved for {resource_arn}.',
                policy=response.get('policy', ''),
            )
        except Exception as e:
            return handle_gateway_error('GetResourcePolicy', e)

    async def gateway_resource_policy_delete(
        self,
        ctx: Context,
        resource_arn: Annotated[
            str,
            Field(description='ARN of the gateway resource (20-1011 chars)'),
        ],
    ) -> DeleteResourcePolicyResponse | ErrorResponse:
        """Delete the resource-based policy attached to a gateway.

        WARNING: This removes all permissions granted by the resource
        policy. Principals that relied on the policy for access will no
        longer be able to invoke the gateway. This action cannot be undone.
        """
        logger.info(f'Deleting resource policy on {resource_arn}')

        try:
            client = self._get_client()
            client.delete_resource_policy(resourceArn=resource_arn)

            return DeleteResourcePolicyResponse(
                status='success',
                message=f'Resource policy deleted from {resource_arn}.',
                resource_arn=resource_arn,
            )
        except Exception as e:
            return handle_gateway_error('DeleteResourcePolicy', e)
