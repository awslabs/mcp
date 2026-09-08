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

"""AWS billing preferences operations for the AWS Billing and Cost Management MCP server.

This module contains the read-only operation handler for the
``billing-preferences`` tool (AWS Billing preferences: which member accounts
share the Reserved Instance / Savings Plans discount pool or credits, whether
new accounts join automatically, whether billing alerts are on, and the
per-billing-period history of those settings).

Only the read operation is wrapped. ``UpdateBillingPreferences`` exists in the
same API model and is deliberately not exposed, because this server is read-only.
"""

from ..utilities.aws_service_base import (
    create_aws_client,
    format_response,
    handle_aws_error,
    paginate_aws_response,
    parse_json,
)
from ..utilities.sql_utils import convert_response_if_needed
from fastmcp import Context
from typing import Any, Dict, List, Optional, Union


def _create_billing_client() -> Any:
    """Create an AWS Billing client.

    Returns:
        boto3.client: AWS Billing client.
    """
    return create_aws_client('billing')


async def get_billing_preferences(
    ctx: Context,
    features: Union[str, List[str]],
    filters: Optional[str] = None,
    max_results: Optional[int] = 50,
    next_token: Optional[str] = None,
    max_pages: Optional[int] = 5,
) -> Dict[str, Any]:
    """Get the billing preferences for one feature.

    Args:
        ctx: The MCP context object.
        features: The feature to retrieve (required). The API accepts exactly one;
            a bare string is wrapped into the single-item list it expects.
        filters: Filters as a JSON string, for example
            ``[{"name": "PREFERENCE_KEY", "value": ["credit/4242"]}]``.
        max_results: Maximum number of results per page (1-50). Defaults to the
            API maximum so a member-account list arrives in as few calls as possible.
        next_token: Pagination token from a previous response to resume from.
        max_pages: Maximum number of pages to auto-paginate through. Bounded by
            default so a very large organization cannot fill the agent's context
            unprompted; the ``pagination`` block reports the truncation. Pass None
            to fetch every page.

    Returns:
        Dict containing ``billing_preferences`` and a ``pagination`` metadata
        block, or a standardized error response.
    """
    try:
        request_params: Dict[str, Any] = {
            'features': [features] if isinstance(features, str) else list(features)
        }
        if filters:
            request_params['filters'] = parse_json(filters, 'filters')
        if max_results is not None:
            request_params['maxResults'] = max_results
        if next_token:
            request_params['nextToken'] = next_token

        client = _create_billing_client()

        preferences, pagination = await paginate_aws_response(
            ctx,
            'GetBillingPreferences',
            client.get_billing_preferences,
            request_params,
            'billingPreferences',
            token_param='nextToken',
            token_key='nextToken',
            max_pages=max_pages,
        )

        await ctx.info(f'Successfully retrieved {len(preferences)} billing preferences')

        # An organization-wide feature can return a row per member account, so
        # the shared size threshold decides whether to offload to session SQL.
        converted = await convert_response_if_needed(
            ctx,
            {'billing_preferences': preferences, 'pagination': pagination},
            'billing_preferences_get_billing_preferences',
            pagination_token_key='nextToken',
            pagination=pagination,
        )
        return format_response('success', converted)

    except Exception as e:
        return await handle_aws_error(ctx, e, 'GetBillingPreferences', 'Billing')
