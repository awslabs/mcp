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

"""Resource-based policy tools for AgentCore Identity.

Resource-based policies control which principals can invoke and manage
AgentCore resources (Agent Runtime, Endpoint, Gateway, and — by
extension — Identity-adjacent resources referenced by ARN). They use
standard IAM policy document JSON.
"""

import json
from .error_handler import handle_identity_error
from .models import (
    DeleteResourcePolicyResponse,
    ErrorResponse,
    ResourcePolicyResponse,
)
from botocore.exceptions import ClientError
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated


class ResourcePolicyTools:
    """Tools for managing resource-based policies on AgentCore resources."""

    def __init__(self, client_factory):
        """Initialize with a callable that returns a boto3 control plane client."""
        self._get_client = client_factory

    def register(self, mcp):
        """Register resource policy tools with the MCP server."""
        mcp.tool(name='identity_put_resource_policy')(self.identity_put_resource_policy)
        mcp.tool(name='identity_get_resource_policy')(self.identity_get_resource_policy)
        mcp.tool(name='identity_delete_resource_policy')(self.identity_delete_resource_policy)

    async def identity_put_resource_policy(
        self,
        ctx: Context,
        resource_arn: Annotated[
            str,
            Field(
                description=(
                    'ARN of the AgentCore resource to attach the policy to. '
                    'Supported: Agent Runtime, Agent Runtime Endpoint, Gateway.'
                )
            ),
        ],
        policy_document: Annotated[
            dict,
            Field(
                description=(
                    'IAM-style resource-based policy document as a JSON object. '
                    'Must include "Version" and "Statement" fields. Each '
                    'statement needs Effect (Allow|Deny), Principal, Action, '
                    'and Resource. Example: {"Version": "2012-10-17", '
                    '"Statement": [{"Effect": "Allow", "Principal": '
                    '{"AWS": "arn:aws:iam::123:role/x"}, "Action": '
                    '"bedrock-agentcore:InvokeAgentRuntime", "Resource": "*"}]}.'
                )
            ),
        ],
    ) -> ResourcePolicyResponse | ErrorResponse:
        """Create or replace the resource-based policy on an AgentCore resource.

        ACCESS CONTROL WARNING: This modifies who can invoke or manage
        the target resource. Overly permissive policies (e.g. broad
        Principal wildcards or cross-account access) can expose the
        resource to unintended callers. Review policy documents
        carefully before applying, and prefer least-privilege
        statements scoped to specific principals and actions.

        This is an idempotent replace — it overwrites any existing
        policy on the resource.
        """
        logger.info(f'Putting resource policy for {resource_arn}')

        try:
            client = self._get_client()
            policy_str = json.dumps(policy_document)
            response = client.put_resource_policy(resourceArn=resource_arn, policy=policy_str)
            stored_policy_str = response.get('policy')
            stored_policy = json.loads(stored_policy_str) if stored_policy_str else policy_document

            return ResourcePolicyResponse(
                status='success',
                message=f'Resource policy put on {resource_arn}.',
                resource_arn=resource_arn,
                policy=stored_policy,
            )
        except Exception as e:
            return handle_identity_error('PutResourcePolicy', e)

    async def identity_get_resource_policy(
        self,
        ctx: Context,
        resource_arn: Annotated[
            str,
            Field(description='ARN of the AgentCore resource.'),
        ],
    ) -> ResourcePolicyResponse | ErrorResponse:
        """Get the resource-based policy attached to an AgentCore resource.

        Returns the policy as a JSON object. If no policy is attached,
        returns a success response with an empty policy. This is a
        read-only operation with no cost implications.
        """
        logger.info(f'Getting resource policy for {resource_arn}')

        try:
            client = self._get_client()
            response = client.get_resource_policy(resourceArn=resource_arn)
            policy_str = response.get('policy')

            if policy_str:
                policy = json.loads(policy_str)
                return ResourcePolicyResponse(
                    status='success',
                    message=f'Resource policy retrieved for {resource_arn}.',
                    resource_arn=resource_arn,
                    policy=policy,
                )
            return ResourcePolicyResponse(
                status='success',
                message=f'No resource policy attached to {resource_arn}.',
                resource_arn=resource_arn,
                policy={},
            )
        except ClientError as e:
            # A not-found for resource policy is a common, expected state —
            # still surfaces as ErrorResponse so the caller can distinguish it.
            return handle_identity_error('GetResourcePolicy', e)
        except Exception as e:
            return handle_identity_error('GetResourcePolicy', e)

    async def identity_delete_resource_policy(
        self,
        ctx: Context,
        resource_arn: Annotated[
            str,
            Field(description='ARN of the AgentCore resource.'),
        ],
    ) -> DeleteResourcePolicyResponse | ErrorResponse:
        """Permanently delete the resource-based policy on an AgentCore resource.

        WARNING: Removes ALL access-control statements from the target
        resource. After deletion, only principals authorized by
        identity-based IAM policies (not resource-based policies) can
        invoke or manage the resource. This action cannot be undone.
        """
        logger.info(f'Deleting resource policy for {resource_arn}')

        try:
            client = self._get_client()
            client.delete_resource_policy(resourceArn=resource_arn)

            return DeleteResourcePolicyResponse(
                status='success',
                message=f'Resource policy on {resource_arn} deleted.',
                resource_arn=resource_arn,
            )
        except Exception as e:
            return handle_identity_error('DeleteResourcePolicy', e)
