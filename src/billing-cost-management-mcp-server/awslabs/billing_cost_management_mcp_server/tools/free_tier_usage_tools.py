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

"""AWS Free Tier Usage tools for the AWS Billing and Cost Management MCP server.

Updated to use shared utility functions.
"""

from ..utilities.aws_service_base import (
    PageSpec,
    create_aws_client,
    format_response,
    handle_aws_error,
    paginate_aws_items,
    parse_filter,
    with_pagination,
)
from ..utilities.constants import PAGINATION_LIMIT_TEXT
from fastmcp import Context, FastMCP
from typing import Any, Dict, List, Optional


# GetFreeTierUsage returns up to 1,000 usage rows per page.
GET_FREE_TIER_USAGE_PAGE_SPEC = PageSpec(
    result_key='freeTierUsages',
    token_param='nextToken',
    token_key_in_response='nextToken',
    page_max=1000,
    page_size_param='maxResults',
    # The service reports a bad caller next_token as ValidationException.
    caller_token_error_codes=frozenset({'ValidationException'}),
)

# GetFreeTierUsage rejects a filter value longer than this.
MAX_FILTER_VALUE_LENGTH = 20

# Filter keys GetFreeTierUsage matches as text. Only USAGE_PERCENTAGE is numeric.
TEXT_FILTER_KEYS = frozenset(
    {'SERVICE', 'OPERATION', 'USAGE_TYPE', 'REGION', 'FREE_TIER_TYPE', 'DESCRIPTION'}
)

free_tier_usage_server = FastMCP(
    name='free-tier-usage-tools', instructions='Tools for working with AWS Free Tier Usage API'
)


@free_tier_usage_server.tool(
    name='free-tier-usage',
    description="""Retrieves AWS Free Tier usage information using the Free Tier Usage API.

This tool provides insights into your AWS Free Tier usage across services:

1. get_free_tier_usage: Shows your current Free Tier usage across AWS services
   - Helps identify where you are approaching Free Tier limits
   - Shows actual usage against Free Tier allocations
   - Returns `data.freeTierUsages`, a `data.summary` computed over the returned rows, and `data.pagination`

SUMMARY (`data.summary`):
- Each row is counted as at_limit (99.9% or more of its limit), near_limit (80% to under 99.9%), safe (under 80%) or unknown (no usable limit or usage), by actual month-to-date usage. Items are listed for at_limit and near_limit, highest first.
- forecast_exceeds_limit_items lists rows still under the limit whose month-end forecast (forecastedUsageAmount) reaches 99.9% or more of it, highest first. The forecast is month-to-date usage projected in a straight line to month end, so early in the month it can greatly overstate. Rows already at the limit are not repeated there.
- Each item is one row, with its `forecast`, `region` and `free_tier_type`, and `forecast_percentage` when the forecast is at least the actual usage (the API defaults the forecast to 0, and a forecast below actual usage is not a real one). One service can have a row per region, so read `region` before saying which limit is reached. free_tier_type tells whether the offer ends ("12 Months Free", "Free Trial") or does not ("Always Free"); an empty one says neither.

FILTER (optional JSON string):
- Shape: {"Dimensions": {"Key": "SERVICE", "Values": ["AmazonSNS"], "MatchOptions": ["EQUALS"]}}. MatchOptions is required and takes exactly one option. A row matches if it matches any of the Values.
- Combine filters with {"And": [...]} or {"Or": [...]} (at least 2 filters each) or {"Not": {...}}. Each object holds exactly one of Dimensions, And, Or, Not.
- Keys SERVICE, OPERATION, USAGE_TYPE, REGION, FREE_TIER_TYPE and DESCRIPTION take EQUALS, STARTS_WITH, ENDS_WITH or CONTAINS. Matching ignores case and spaces, so "awslambda" matches "AWS Lambda".
- Each value is at most 20 characters of letters, digits, spaces and - : . _ / , $ ( ). A long service name such as "Amazon Simple Notification Service" is rejected. Use CONTAINS with part of the name ("Notification"), or the short code the API accepts for some long names (AmazonSNS, AmazonEC2, AmazonS3, AmazonRDS, AmazonSES, AWSSQS).
- REGION is a region code such as us-east-1, or "global".
- FREE_TIER_TYPE is one of "Always Free", "12 Months Free" or "Free Trial" (empty for a row with no type).
- USAGE_PERCENTAGE is actual usage as a percent of the limit. It takes GREATER_THAN_OR_EQUAL and one number from 0 to 100 (80 means 80%). Only USAGE_PERCENTAGE takes GREATER_THAN_OR_EQUAL.

PAGINATION:
- max_items: total usage rows returned. If it is omitted, the tool fetches every page for """
    + PAGINATION_LIMIT_TEXT
    + """, then returns a partial result. Pass it, or narrow the filter, when the account has many Free Tier rows.
- A partial result has `complete_dataset: false` and a warning. The summary then covers only the returned rows, so its counts undercount. Call again with a larger max_items, continue with next_token (the `pagination.next_token` from that response, sent with the same filter), or state in the answer that the result is partial.
- A continuation call's summary covers only that call's rows.
   """,
)
async def free_tier_usage(
    ctx: Context,
    operation: str = 'get_free_tier_usage',
    filter: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieves AWS Free Tier usage information using the Free Tier Usage API.

    Args:
        ctx: The MCP context object
        operation: The operation to perform: 'get_free_tier_usage'
        filter: Optional filter as a JSON string, in the shape the description gives.
        max_items: Total usage rows to return. None fetches every page.
        next_token: Continuation token from a previous response.

    Returns:
        Dict containing the free tier usage information
    """
    try:
        await ctx.info(f'Free Tier Usage operation: {operation}')

        # Initialize Free Tier client using shared utility
        freetier_client = create_aws_client('freetier', region_name='us-east-1')

        if operation == 'get_free_tier_usage':
            return await get_free_tier_usage_data(
                ctx, freetier_client, filter, max_items=max_items, next_token=next_token
            )
        else:
            return format_response(
                'error', {}, f"Unsupported operation: {operation}. Use 'get_free_tier_usage'."
            )

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'free_tier_usage', 'Free Tier Usage')


async def get_free_tier_usage_data(
    ctx: Context,
    freetier_client: Any,
    filter_expr: Optional[str],
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieves Free Tier usage data.

    Args:
        ctx: The MCP context
        freetier_client: Free Tier API client
        filter_expr: Optional filter as JSON string
        max_items: Total usage rows to return. None fetches every page.
        next_token: Continuation token from a previous response.

    Returns:
        Dict containing Free Tier usage data, a summary over the returned rows, and a
        ``pagination`` block
    """
    try:
        # Create request parameters. The token and page size are added per page.
        request_params: Dict[str, Any] = {}
        if filter_expr is not None:
            request_params['filter'] = parse_filter(filter_expr)
            filter_error = _filter_error(request_params['filter'])
            if filter_error:
                return format_response(
                    'error',
                    {'invalid_parameter': 'filter'},
                    filter_error,
                    error_type='validation_error',
                    operation='get_free_tier_usage',
                    service='Free Tier Usage',
                )

        all_usages, _, pagination = await paginate_aws_items(
            ctx,
            'GetFreeTierUsage',
            freetier_client.get_free_tier_usage,
            request_params,
            GET_FREE_TIER_USAGE_PAGE_SPEC,
            max_items=max_items,
            next_token=next_token,
        )

        # Create categorized summaries. When the result is partial, the top-level
        # warning tells the caller the summary undercounts.
        summary = create_free_tier_usage_summary(all_usages)

        # Return formatted response using shared utility
        return format_response(
            'success',
            with_pagination({'freeTierUsages': all_usages, 'summary': summary}, pagination),
        )

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'get_free_tier_usage_data', 'Free Tier Usage')


def _filter_error(expression: Any) -> Optional[str]:
    """Return why a filter would fail or never match, else None.

    Only these two traps are checked: the API rejects a value over 20 characters, and
    accepts GREATER_THAN_OR_EQUAL on a text key but it matches no row (every row under Not). Any
    other malformed filter is left for the SDK and the API to report.

    Args:
        expression: The parsed filter expression

    Returns:
        The error message, or None when neither trap applies
    """
    if not isinstance(expression, dict):
        return None
    dimensions = expression.get('Dimensions')
    if isinstance(dimensions, dict):
        key = dimensions.get('Key')
        match_options = dimensions.get('MatchOptions')
        if key in TEXT_FILTER_KEYS and match_options == ['GREATER_THAN_OR_EQUAL']:
            return (
                f'GREATER_THAN_OR_EQUAL applies only to USAGE_PERCENTAGE. The API accepts it '
                f'on {key} but it matches no row (and under Not, every row). Use EQUALS, '
                'STARTS_WITH, ENDS_WITH or CONTAINS.'
            )
        values = dimensions.get('Values')
        for value in values if isinstance(values, list) else []:
            if isinstance(value, str) and len(value) > MAX_FILTER_VALUE_LENGTH:
                return (
                    f'Filter value "{value}" for {key} is {len(value)} characters; the API '
                    f'allows at most {MAX_FILTER_VALUE_LENGTH}. For a long service name, use '
                    'CONTAINS with part of the name, or its short code where the API has one '
                    '(for example AmazonSNS).'
                )
    children = [expression.get('Not')]
    for operator in ('And', 'Or'):
        operands = expression.get(operator)
        if isinstance(operands, list):
            children.extend(operands)
    for child in children:
        error = _filter_error(child)
        if error:
            return error
    return None


def create_free_tier_usage_summary(usages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create a summary of Free Tier usage focusing on items at or near limits.

    Args:
        usages: List of Free Tier usage items

    Returns:
        Dict containing usage summaries
    """
    # Create categories for different usage levels
    at_limit_items = []
    near_limit_items = []
    safe_items = []
    unknown_items = []
    forecast_exceeds_limit_items = []

    for item in usages:
        # Extract essential fields
        service = item.get('service', 'Unknown Service')
        usage_type = item.get('usageType', 'Unknown Type')
        actual = item.get('actualUsageAmount')
        limit = item.get('limit')
        unit = item.get('unit', '')
        forecast = item.get('forecastedUsageAmount')

        # Create formatted usage item. One service has a row per region and offer, so
        # region and free_tier_type tell those rows apart.
        usage_item = {
            'service': service,
            'usage_type': usage_type,
            'actual': actual,
            'limit': limit,
            'unit': unit,
            'forecast': forecast,
            'region': item.get('region'),
            'free_tier_type': item.get('freeTierType'),
        }

        # Categorize based on usage percentage if we have valid numbers
        if actual is not None and limit is not None and limit > 0:
            usage_pct = (actual / limit) * 100
            usage_item['percentage'] = round(usage_pct, 1)

            if usage_pct >= 99.9:  # At limit (accounting for floating point imprecision)
                at_limit_items.append(usage_item)
            elif usage_pct >= 80:  # Near limit (80%+)
                near_limit_items.append(usage_item)
            else:  # Safe (under 80%)
                safe_items.append(usage_item)

            # The API defaults the forecast to 0 when it has none. A forecast below the
            # month-to-date actual is never a real one, so it gets no percentage.
            if forecast is not None and forecast >= actual:
                forecast_pct = (forecast / limit) * 100
                usage_item['forecast_percentage'] = round(forecast_pct, 1)
                # Under the limit now, but forecast to reach it by month end
                if usage_pct < 99.9 and forecast_pct >= 99.9:
                    forecast_exceeds_limit_items.append(usage_item)
        else:
            # Can't calculate percentage - missing data
            unknown_items.append(usage_item)

    # Sort items by percentage (highest first) or service name
    at_limit_items.sort(key=lambda x: (-(x.get('percentage') or 0), x.get('service', '')))
    near_limit_items.sort(key=lambda x: (-(x.get('percentage') or 0), x.get('service', '')))
    safe_items.sort(key=lambda x: (-(x.get('percentage') or 0), x.get('service', '')))
    unknown_items.sort(key=lambda x: x.get('service', ''))
    forecast_exceeds_limit_items.sort(
        key=lambda x: (-(x.get('forecast_percentage') or 0), x.get('service', ''))
    )

    # Create the summary
    return {
        'at_limit_count': len(at_limit_items),
        'near_limit_count': len(near_limit_items),
        'safe_count': len(safe_items),
        'unknown_count': len(unknown_items),
        'at_limit_items': at_limit_items,
        'near_limit_items': near_limit_items,
        'forecast_exceeds_limit_count': len(forecast_exceeds_limit_items),
        'forecast_exceeds_limit_items': forecast_exceeds_limit_items,
        'total_services': len({item.get('service', '') for item in usages}),
    }
