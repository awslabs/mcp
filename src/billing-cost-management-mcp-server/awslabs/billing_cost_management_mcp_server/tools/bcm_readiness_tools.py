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

"""BCM readiness checker tool for the AWS Billing and Cost Management MCP server."""

from ..utilities.aws_service_base import (
    create_aws_client,
    format_response,
    handle_aws_error,
)
from .bcm_readiness_operations import (
    DEFAULT_INTENT,
    INTENT_CHECKS,
    INTENT_OPTIMIZATION,
    diagnose_readiness,
)
from botocore.exceptions import ClientError
from fastmcp import Context, FastMCP
from typing import Any, Dict, Optional


bcm_readiness_server = FastMCP(
    name='bcm-readiness-tools',
    instructions='Tool for diagnosing AWS account BCM configuration readiness',
)


@bcm_readiness_server.tool(
    name='check-bcm-readiness',
    description="""Diagnose whether an AWS account is ready for a cost-management task BEFORE running cost queries.

Call this FIRST, before cost-explorer / cost-optimization tools, to avoid silent
failures where the API returns HTTP 200 with $0/empty data when a feature is not
configured.

Parameters:
- account_id (required): the 12-digit AWS account to check.
- intent (optional, default 'basic_cost_visibility'): the user's goal. One of:
  * basic_cost_visibility - "What did I spend?" (checks IAM + Cost Explorer)
  * tag_analysis - "Show spend by team/tag" (also checks cost allocation tags)
  * optimization - "How do I reduce costs?" (also checks Cost Optimization Hub)

Returns a status of 'ready', 'blocked', or 'pending':
- ready: proceed with the cost query. Includes 'capabilities' and 'data_freshness'.
- blocked: a prerequisite is missing. 'blocker' gives issue, action, console_url,
  wait_time, is_paid (plus missing_permissions / available_tags when relevant).
  Guide the user through the fix; do NOT present $0/empty data as truth.
- pending: prerequisites met but data is still propagating. 'pending_reason' gives
  when data becomes available.

Every response includes a 'cache' block (valid_until / next_meaningful_check /
reason) - do not re-call before valid_until.

Example 1 - Default intent: {"account_id": "123456789012"}
Example 2 - Tag analysis: {"account_id": "123456789012", "intent": "tag_analysis"}""",
)
async def check_bcm_readiness(
    ctx: Context,
    account_id: str,
    intent: Optional[str] = None,
) -> Dict[str, Any]:
    """Diagnose BCM readiness for an account scoped to the given intent.

    Args:
        ctx: The MCP context object
        account_id: The 12-digit AWS account to check
        intent: The user's goal (basic_cost_visibility, tag_analysis, optimization).
            Defaults to basic_cost_visibility.

    Returns:
        Dict containing the readiness response (status, blocker/pending_reason,
        capabilities, cache)
    """
    intent = intent or DEFAULT_INTENT
    await ctx.info(f'BCM readiness check: account={account_id} intent={intent}')

    if intent not in INTENT_CHECKS:
        return format_response(
            'error',
            {
                'error_type': 'validation_error',
                'message': (
                    f"Unsupported intent '{intent}'. Supported intents: "
                    f'{", ".join(sorted(INTENT_CHECKS))}'
                ),
            },
        )

    try:
        clients: Dict[str, Any] = {
            'sts': create_aws_client('sts'),
            'iam': create_aws_client('iam'),
            'ce': create_aws_client('ce'),
        }
        if intent == INTENT_OPTIMIZATION:
            clients['coh'] = create_aws_client('cost-optimization-hub')
    except Exception as client_error:
        await ctx.error(f'Failed to create AWS client: {str(client_error)}')
        return format_response(
            'error',
            {
                'error_type': 'client_creation_error',
                'message': 'Failed to create AWS client for readiness check',
                'details': str(client_error),
            },
        )

    try:
        result = diagnose_readiness(account_id, intent, clients)
        return format_response('success', result)
    except ClientError as e:
        return await handle_aws_error(ctx, e, 'check_bcm_readiness', 'BCM Readiness')
    except Exception as e:
        return await handle_aws_error(ctx, e, 'check_bcm_readiness', 'BCM Readiness')
