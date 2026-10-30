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
    PageSpec,
    create_aws_client,
    format_response,
    handle_aws_error,
    paginate_aws_items,
    with_pagination,
)
from ..utilities.constants import PAGINATION_LIMIT_TEXT
from fastmcp import Context, FastMCP
from typing import Any, Callable, Dict, List, Optional, Tuple


cost_allocation_tags_server = FastMCP(
    name='cost-allocation-tags-tools',
    instructions='Tools for managing AWS Cost Allocation Tags',
)

LIST_COST_ALLOCATION_TAGS = PageSpec(
    result_key='CostAllocationTags',
    token_param='NextToken',
    token_key_in_response='NextToken',
    page_max=1000,
    page_size_param='MaxResults',
)

LIST_COST_ALLOCATION_TAG_BACKFILL_HISTORY = PageSpec(
    result_key='BackfillRequests',
    token_param='NextToken',
    token_key_in_response='NextToken',
    page_max=1000,
    page_size_param='MaxResults',
)


async def _list_by_tag_keys(
    ctx: Context,
    api_call: Callable[..., Any],
    params: Dict[str, Any],
    max_items: Optional[int],
) -> Tuple[List[Any], Dict[str, Any]]:
    """Fetch a tag_keys lookup in one request and apply max_items locally.

    With TagKeys, the service's NextToken is an offset into the key list that advances by
    the number of tags returned, not keys read, so later pages repeat some tags and skip
    others. Each key matches at most one tag and the API takes at most 100 keys, so one
    page of 1000 holds every match; the lookup never follows or returns a token.
    """
    if max_items is not None and max_items < 1:
        raise ValueError('max_items must be at least 1. Omit it to fetch every page.')
    tags, _, pagination = await paginate_aws_items(
        ctx,
        'ListCostAllocationTags',
        api_call,
        params,
        LIST_COST_ALLOCATION_TAGS,
        max_pages=1,
    )
    kept = tags[:max_items] if max_items is not None else tags
    if pagination['next_token'] is not None:
        warning = (
            f'Partial data: returned {len(kept)} tags, and the service returned a continuation '
            'token for a tag_keys lookup, which cannot be continued correctly. Split tag_keys '
            'across smaller calls, or state in the answer that the result is partial.'
        )
    elif len(kept) < len(tags):
        warning = (
            f'Partial data: returned {len(kept)} of the {len(tags)} tags that match tag_keys. '
            'A tag_keys lookup has no next_token: call again with a larger max_items, or '
            'without it, to get every match, or state in the answer that the result is '
            'partial.'
        )
    else:
        return tags, pagination
    return kept, {
        'complete_dataset': False,
        'has_more': False,
        'next_token': None,
        'items_returned': len(kept),
        'warning': warning,
    }


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

Pagination:
- max_items: total number of tags returned. If it is omitted, the tool fetches every page for """
    + PAGINATION_LIMIT_TEXT
    + """, then returns a partial result. Pass it,
  or narrow the filters, when the account can have many tags.
- If the result has complete_dataset: false, it is partial: call again with a larger
  max_items, continue with next_token, or say the result is partial.
- With tag_keys, one call returns every matching tag and there is no next_token: max_items
  only caps how many are returned. Do not pass next_token with tag_keys.

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
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List cost allocation tags.

    Args:
        ctx: The MCP context object
        status: Filter by tag status (Active, Inactive)
        tag_keys: JSON array of tag key strings to filter by (max 100)
        tag_type: Filter by tag type (AWSGenerated, UserDefined)
        max_items: Total tags to return. None fetches every page.
        next_token: Pagination token from previous response. Not used with tag_keys.

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
                    error_type='validation_error',
                    operation='ListCostAllocationTags',
                    service='Cost Explorer',
                )
        if tag_type:
            params['Type'] = tag_type

        if 'TagKeys' in params:
            if next_token is not None:
                return format_response(
                    'error',
                    {
                        'message': 'next_token cannot be used with tag_keys: a tag_keys lookup '
                        'returns every matching tag in one call. Omit next_token.',
                    },
                    error_type='validation_error',
                    operation='ListCostAllocationTags',
                    service='Cost Explorer',
                )
            tags, pagination = await _list_by_tag_keys(
                ctx, ce_client.list_cost_allocation_tags, params, max_items
            )
        else:
            tags, _, pagination = await paginate_aws_items(
                ctx,
                'ListCostAllocationTags',
                ce_client.list_cost_allocation_tags,
                params,
                LIST_COST_ALLOCATION_TAGS,
                max_items=max_items,
                next_token=next_token,
            )
        return format_response(
            'success', with_pagination({'CostAllocationTags': tags}, pagination)
        )

    except Exception as e:
        return await handle_aws_error(ctx, e, 'ListCostAllocationTags', 'Cost Explorer')


@cost_allocation_tags_server.tool(
    name='list-cost-allocation-tag-backfill-history',
    description="""Retrieves the history of cost allocation tag backfill requests using the
ListCostAllocationTagBackfillHistory API.

Backfill retroactively applies the current tag activation status to historical billing data.
Without backfill, tag activation only affects future billing periods.

Backfill requests progress through these states:
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

Pagination:
- max_items: total number of backfill requests returned. If it is omitted, the tool fetches every page for """
    + PAGINATION_LIMIT_TEXT
    + """, then returns a partial result.
- If the result has complete_dataset: false, it is partial: call again with a larger
  max_items, continue with next_token, or say the result is partial.

Example 1 - Get the latest backfill request: {"max_items": 1}
Example 2 - Get the full backfill history: {}""",
)
async def list_cost_allocation_tag_backfill_history(
    ctx: Context,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List cost allocation tag backfill history.

    Args:
        ctx: The MCP context object
        max_items: Total backfill requests to return. None fetches every page.
        next_token: Pagination token from previous response

    Returns:
        Dict containing the list of backfill requests
    """
    await ctx.info('Calling ListCostAllocationTagBackfillHistory API')

    try:
        ce_client = create_aws_client('ce')
        requests, _, pagination = await paginate_aws_items(
            ctx,
            'ListCostAllocationTagBackfillHistory',
            ce_client.list_cost_allocation_tag_backfill_history,
            {},
            LIST_COST_ALLOCATION_TAG_BACKFILL_HISTORY,
            max_items=max_items,
            next_token=next_token,
        )
        return format_response(
            'success', with_pagination({'BackfillRequests': requests}, pagination)
        )

    except Exception as e:
        return await handle_aws_error(
            ctx, e, 'ListCostAllocationTagBackfillHistory', 'Cost Explorer'
        )
