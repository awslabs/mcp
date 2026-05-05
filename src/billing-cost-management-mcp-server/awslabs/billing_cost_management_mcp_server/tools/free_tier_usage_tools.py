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
    create_aws_client,
    format_response,
    handle_aws_error,
    parse_json,
)
from fastmcp import Context, FastMCP
from typing import Any, Dict, List, Optional


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
   - Supports filtering by service, region, or usage type
   - Possible Dimensions values are: 'SERVICE'|'OPERATION'|'USAGE_TYPE'|'REGION'|'FREE_TIER_TYPE'|'DESCRIPTION'|'USAGE_PERCENTAGE'
   - Possible MatchOptions are: 'EQUALS'|'STARTS_WITH'|'ENDS_WITH'|'CONTAINS'|'GREATER_THAN_OR_EQUAL'
   """,
)
async def free_tier_usage(
    ctx: Context,
    operation: str = 'get_free_tier_usage',
    filter: Optional[str] = None,
    max_results: Optional[int] = None,
) -> Dict[str, Any]:
    """Retrieves AWS Free Tier usage information using the Free Tier Usage API.

    Args:
        ctx: The MCP context object
        operation: The operation to perform: 'get_free_tier_usage'
        filter: Optional filter to apply to the results as a JSON string.
        max_results: Maximum number of results to return per page (1-1000). Defaults to 100.

    Returns:
        Dict containing the free tier usage information
    """
    try:
        await ctx.info(f'Free Tier Usage operation: {operation}')

        # Initialize Free Tier client using shared utility
        freetier_client = create_aws_client('freetier', region_name='us-east-1')

        if operation == 'get_free_tier_usage':
            return await get_free_tier_usage_data(ctx, freetier_client, filter, max_results)
        else:
            return format_response(
                'error', {}, f"Unsupported operation: {operation}. Use 'get_free_tier_usage'."
            )

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'free_tier_usage', 'Free Tier Usage')


async def get_free_tier_usage_data(
    ctx: Context, freetier_client: Any, filter_expr: Optional[str], max_results: Optional[int]
) -> Dict[str, Any]:
    """Retrieves Free Tier usage data.

    Args:
        ctx: The MCP context
        freetier_client: Free Tier API client
        filter_expr: Optional filter as JSON string
        max_results: Maximum results to return

    Returns:
        Dict containing Free Tier usage data
    """
    try:
        # Ensure max_results is within valid range (1-1000)
        if max_results is not None:
            if max_results < 1:
                max_results = 1
            elif max_results > 1000:
                max_results = 1000
        else:
            max_results = 100

        # Create request parameters
        request_params = {}

        # Add optional parameters if provided
        if filter_expr:
            request_params['filter'] = parse_json(filter_expr, 'filter')

        if max_results:
            request_params['maxResults'] = max_results

        # Use pagination to collect all usage data
        all_usages = []
        next_token = None
        page_count = 0

        while True:
            page_count += 1

            if next_token:
                request_params['nextToken'] = next_token

            await ctx.info(f'Fetching free tier usage page {page_count}')
            response = freetier_client.get_free_tier_usage(**request_params)

            page_usages = response.get('freeTierUsages', [])
            all_usages.extend(page_usages)

            await ctx.info(
                f'Retrieved {len(page_usages)} free tier usage items (total: {len(all_usages)})'
            )

            next_token = response.get('nextToken')
            if not next_token:
                break

        # Create categorized summaries
        summary = create_free_tier_usage_summary(all_usages)

        # Return formatted response using shared utility
        return format_response('success', {'freeTierUsages': all_usages, 'summary': summary})

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'get_free_tier_usage_data', 'Free Tier Usage')


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

    for item in usages:
        # Extract essential fields
        service = item.get('service', 'Unknown Service')
        usage_type = item.get('usageType', 'Unknown Type')
        actual = item.get('actualUsageAmount')
        limit = item.get('limit')
        unit = item.get('unit', '')

        # Create formatted usage item
        usage_item = {
            'service': service,
            'usage_type': usage_type,
            'actual': actual,
            'limit': limit,
            'unit': unit,
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
        else:
            # Can't calculate percentage - missing data
            unknown_items.append(usage_item)

    # Sort items by percentage (highest first) or service name
    at_limit_items.sort(key=lambda x: (-(x.get('percentage') or 0), x.get('service', '')))
    near_limit_items.sort(key=lambda x: (-(x.get('percentage') or 0), x.get('service', '')))
    safe_items.sort(key=lambda x: (-(x.get('percentage') or 0), x.get('service', '')))
    unknown_items.sort(key=lambda x: x.get('service', ''))

    # Create the summary
    return {
        'at_limit_count': len(at_limit_items),
        'near_limit_count': len(near_limit_items),
        'safe_count': len(safe_items),
        'unknown_count': len(unknown_items),
        'at_limit_items': at_limit_items,
        'near_limit_items': near_limit_items,
        'total_services': len({item.get('service', '') for item in usages}),
    }
