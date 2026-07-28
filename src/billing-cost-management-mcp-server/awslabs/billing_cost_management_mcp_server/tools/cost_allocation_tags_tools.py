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

"""Cost Allocation Tags tools for the AWS Billing and Cost Management MCP server."""

import json
from ..utilities.aws_service_base import (
    create_aws_client,
    format_response,
    handle_aws_error,
    paginate_aws_response,
)
from fastmcp import Context, FastMCP
from typing import Any, Dict, Optional


cost_allocation_tags_server = FastMCP(
    name='cost-allocation-tags-tools',
    instructions='Tools for managing AWS Cost Allocation Tags',
)


@cost_allocation_tags_server.tool(
    name='list-cost-allocation-tags',
    description="""Lists cost allocation tags in the account using the ListCostAllocationTags API.

Cost allocation tags must be activated before they appear in Cost Explorer, CUR, and budgets.
There are two types: AWSGenerated (auto-created by AWS services like aws:createdBy) and
UserDefined (created by customers via resource tagging APIs).

The tool returns CostAllocationTag objects containing:
- TagKey, Type (AWSGenerated/UserDefined), Status (Active/Inactive)
- LastUpdatedDate (when activation status last changed)
- LastUsedDate (last month the tag appeared on a billed resource, for identifying stale tags)

You can filter tags by:
- status: Active or Inactive
- tag_keys: JSON array of tag key strings to look up (max 100, case-sensitive).
  Example: '["Environment", "Team", "CostCenter"]'
- tag_type: AWSGenerated or UserDefined
- max_results: Results per page (1-1000, default 100)
- max_pages: Max pages to auto-paginate through

Limits: 500 active cost allocation tag keys per payer account (adjustable via Service Quotas
up to 1,000). Max 20 tags per UpdateCostAllocationTagsStatus request.

Example 1 - List active user-defined tags: {"status": "Active", "tag_type": "UserDefined"}
Example 2 - Check specific tag keys: {"tag_keys": "[\"Environment\", \"Team\"]"}
Example 3 - List all tags with no filters: {}""",
)
async def list_cost_allocation_tags(
    ctx: Context,
    status: Optional[str] = None,
    tag_keys: Optional[str] = None,
    tag_type: Optional[str] = None,
    max_results: Optional[int] = None,
    next_token: Optional[str] = None,
    max_pages: Optional[int] = None,
) -> Dict[str, Any]:
    """List cost allocation tags.

    Args:
        ctx: The MCP context object
        status: Filter by tag status (Active, Inactive)
        tag_keys: JSON array of tag key strings to filter by (max 100)
        tag_type: Filter by tag type (AWSGenerated, UserDefined)
        max_results: Max results per page (1-1000, default 100)
        next_token: Pagination token from previous response
        max_pages: Max pages to auto-paginate through

    Returns:
        Dict containing the list of cost allocation tags
    """
    await ctx.info('Calling ListCostAllocationTags API')

    try:
        ce_client = create_aws_client('ce')
        params: Dict[str, Any] = {}

        if status:
            params['Status'] = status
        if tag_keys:
            try:
                params['TagKeys'] = json.loads(tag_keys)
            except json.JSONDecodeError as e:
                return format_response(
                    'error',
                    {
                        'message': f'Invalid JSON for tag_keys parameter: {e}',
                    },
                )
        if tag_type:
            params['Type'] = tag_type
        if max_results is not None:
            params['MaxResults'] = max_results

        if next_token:
            params['NextToken'] = next_token
        if next_token or max_pages:
            results, pagination = await paginate_aws_response(
                ctx,
                'ListCostAllocationTags',
                lambda **p: ce_client.list_cost_allocation_tags(**p),
                params,
                'CostAllocationTags',
                max_pages=max_pages,
            )
            return format_response(
                'success',
                {
                    'CostAllocationTags': results,
                    'Pagination': pagination,
                },
            )

        response = ce_client.list_cost_allocation_tags(**params)
        return format_response('success', response)

    except Exception as e:
        return await handle_aws_error(ctx, e, 'ListCostAllocationTags', 'Cost Explorer')


@cost_allocation_tags_server.tool(
    name='list-cost-allocation-tag-backfill-history',
    description="""Retrieves the history of cost allocation tag backfill requests using the
ListCostAllocationTagBackfillHistory API.

Backfill retroactively applies the current tag activation status to historical billing data.
Without backfill, tag activation only affects future billing periods.

Backfill requests progress through these states:
- SCHEDULED: Initial state when the backfill is requested
- PROCESSING: System is rewriting historical tag data and reprocessing bills
- SUCCEEDED: Backfill completed, historical data updated
- FAILED: Processing error occurred (can be retried)

Constraints: Only one backfill can run at a time. There is a 24-hour cooldown between
requests. Maximum lookback is 12 months. BackfillFrom must be the first day of a month
at 00:00:00 UTC.

The tool returns CostAllocationTagBackfillRequest objects containing:
- BackfillFrom (start date, first of month UTC)
- BackfillStatus (SUCCEEDED, PROCESSING, or FAILED)
- RequestedAt, CompletedAt (null if still processing), LastUpdatedAt

You can control pagination with:
- max_results: Results per page (1-1000)
- max_pages: Max pages to auto-paginate through

Example 1 - Get latest backfill request: {"max_results": 1}
Example 2 - Get full backfill history: {"max_pages": 10}""",
)
async def list_cost_allocation_tag_backfill_history(
    ctx: Context,
    max_results: Optional[int] = None,
    next_token: Optional[str] = None,
    max_pages: Optional[int] = None,
) -> Dict[str, Any]:
    """List cost allocation tag backfill history.

    Args:
        ctx: The MCP context object
        max_results: Max results per page (1-1000)
        next_token: Pagination token from previous response
        max_pages: Max pages to auto-paginate through

    Returns:
        Dict containing the list of backfill requests
    """
    await ctx.info('Calling ListCostAllocationTagBackfillHistory API')

    try:
        ce_client = create_aws_client('ce')
        params: Dict[str, Any] = {}

        if max_results is not None:
            params['MaxResults'] = max_results

        if next_token:
            params['NextToken'] = next_token
        if next_token or max_pages:
            results, pagination = await paginate_aws_response(
                ctx,
                'ListCostAllocationTagBackfillHistory',
                lambda **p: ce_client.list_cost_allocation_tag_backfill_history(**p),
                params,
                'BackfillRequests',
                max_pages=max_pages,
            )
            return format_response(
                'success',
                {
                    'BackfillRequests': results,
                    'Pagination': pagination,
                },
            )

        response = ce_client.list_cost_allocation_tag_backfill_history(**params)
        return format_response('success', response)

    except Exception as e:
        return await handle_aws_error(
            ctx, e, 'ListCostAllocationTagBackfillHistory', 'Cost Explorer'
        )
