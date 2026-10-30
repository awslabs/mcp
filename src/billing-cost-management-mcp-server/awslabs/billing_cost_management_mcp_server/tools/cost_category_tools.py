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

"""Cost Category tools for the AWS Billing and Cost Management MCP server.

Dedicated tools for Cost Category management APIs:
- DescribeCostCategoryDefinition
- ListCostCategoryDefinitions
"""

import json
import re
from ..utilities.aws_service_base import (
    PageSpec,
    create_aws_client,
    format_response,
    handle_aws_error,
    paginate_aws_items,
    validate_date_format,
    with_pagination,
)
from ..utilities.constants import PAGINATION_LIMIT_TEXT
from fastmcp import Context, FastMCP
from typing import Any, Dict, Optional


cost_category_server = FastMCP(
    name='cost-category-tools',
    instructions='Tools for managing AWS Cost Categories',
)

LIST_COST_CATEGORY_DEFINITIONS = PageSpec(
    result_key='CostCategoryReferences',
    token_param='NextToken',
    token_key_in_response='NextToken',
    page_max=100,
    page_size_param='MaxResults',
)


_DATE_ONLY = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}')


def _normalize_effective_on(effective_on: str) -> str:
    """Return a YYYY-MM-DD date as midnight UTC; the API needs a full datetime.

    Raises ValueError for a YYYY-MM-DD value that is not a calendar date. Any other
    value is returned unchanged for the API to validate.
    """
    if not _DATE_ONLY.fullmatch(effective_on):
        return effective_on
    if not validate_date_format(effective_on):
        raise ValueError(
            f'effective_on {effective_on!r} is not a calendar date. '
            'Use YYYY-MM-DD, or YYYY-MM-DDTHH:MM:SS followed by Z or +HH:MM/-HH:MM.'
        )
    return f'{effective_on}T00:00:00Z'


def _effective_on_error(error: ValueError, operation: str) -> Dict[str, Any]:
    return format_response(
        'error',
        {'message': str(error)},
        error_type='validation_error',
        operation=operation,
        service='Cost Explorer',
    )


@cost_category_server.tool(
    name='describe-cost-category-definition',
    description="""Returns the full definition of a cost category using the DescribeCostCategoryDefinition API.

Cost categories group AWS costs using rule-based expressions that match line items by
dimensions, resource tags, or other cost category values. Each matched line item is
assigned a category value such as "Production" or "Development". Rules can be REGULAR
(explicit match) or INHERITED_VALUE (dynamic value from a tag key or account name). A
DefaultValue catches costs that do not match any rule.

How rules work:
- Rules are evaluated in order; the first rule that matches a line item sets its value.
- Rule dimensions include LINKED_ACCOUNT, SERVICE_CODE, RECORD_TYPE, LINKED_ACCOUNT_NAME,
  REGION and USAGE_TYPE. SERVICE_CODE holds service codes such as "AmazonEC2", not
  service names such as "Amazon Elastic Compute Cloud - Compute".
- MatchOptions can include STARTS_WITH, ENDS_WITH and CONTAINS. On dimensions, these
  work only with LINKED_ACCOUNT_NAME and USAGE_TYPE.

The tool returns a CostCategory object containing:
- Name (1-50 chars, unique per account, case-sensitive), CostCategoryArn
- RuleVersion (always "CostCategoryExpression.v1")
- Rules array with Value, Rule expression (Dimensions/Tags/CostCategories with And/Or/Not), and Type
- DefaultValue, SplitChargeRules (PROPORTIONAL, FIXED, or EVEN allocation methods)
- EffectiveStart/EffectiveEnd (null if still active)
- ProcessingStatus: APPLIED (rules reflected in data) or PROCESSING (backfill in progress)

Only a management account or a standalone account can call this; member (linked)
accounts get an access denied error.

Required parameters:
- cost_category_arn: ARN of the cost category (arn:aws:ce::<account_id>:costcategory/<uuid>).
  Use list-cost-category-definitions to discover ARNs.

Optional parameters:
- effective_on: YYYY-MM-DDTHH:MM:SS followed by Z or +HH:MM/-HH:MM, without fractional
  seconds (e.g., 2024-01-01T00:00:00Z), or YYYY-MM-DD (read as midnight UTC), to
  retrieve the version active at that time. Defaults to the current
  version. Each version starts on the first day of a month; a date before the first
  version returns ResourceNotFoundException.

Example 1 - Get current definition:
  {"cost_category_arn": "arn:aws:ce::123456789012:costcategory/abcd-1234"}
Example 2 - Get historical version:
  {"cost_category_arn": "arn:aws:ce::123456789012:costcategory/abcd-1234", "effective_on": "2024-06-01"}""",
)
async def describe_cost_category_definition(
    ctx: Context,
    cost_category_arn: str,
    effective_on: Optional[str] = None,
) -> Dict[str, Any]:
    """Describe a cost category definition.

    Args:
        ctx: The MCP context object
        cost_category_arn: ARN of the cost category to describe
        effective_on: Optional ISO 8601 datetime or YYYY-MM-DD to retrieve a historical version

    Returns:
        Dict containing the cost category definition
    """
    await ctx.info(f'Calling DescribeCostCategoryDefinition for {cost_category_arn}')

    try:
        ce_client = create_aws_client('ce')
        params: Dict[str, Any] = {'CostCategoryArn': cost_category_arn}

        if effective_on:
            try:
                params['EffectiveOn'] = _normalize_effective_on(effective_on)
            except ValueError as e:
                return _effective_on_error(e, 'DescribeCostCategoryDefinition')

        response = ce_client.describe_cost_category_definition(**params)
        return format_response('success', response)

    except Exception as e:
        return await handle_aws_error(ctx, e, 'DescribeCostCategoryDefinition', 'Cost Explorer')


@cost_category_server.tool(
    name='list-cost-category-definitions',
    description="""Lists all cost category definitions in the account using the ListCostCategoryDefinitions API.

Returns lightweight references for each cost category, not full rule definitions. Use
describe-cost-category-definition with the returned ARN to get the complete rule set.

The tool returns CostCategoryReference objects containing:
- CostCategoryArn, Name (unique, case-sensitive), NumberOfRules
- EffectiveStart, EffectiveEnd (null if current)
- DefaultValue, Values (all category values defined in the rules)
- ProcessingStatus: APPLIED or PROCESSING
- SupportedResourceTypes

You can filter with:
- effective_on: YYYY-MM-DDTHH:MM:SS followed by Z or +HH:MM/-HH:MM, without fractional
  seconds, or YYYY-MM-DD (read as midnight UTC), to return only categories active at
  that time. Defaults to current date. Each version starts on the
  first day of a month.
- supported_resource_types: JSON array to filter by resource type support.
  Valid values: "billing:rispgroupsharing", "billing:billingview",
  "billing:creditsharing". At most 5 values.
  Example: '["billing:billingview"]'
  Returns only categories that support every listed type. A value of the form
  `service:type` (letters, digits, `-`, `/` or `_` on each side of one colon) that is
  not a known type returns no categories, not an error. Any other value, such as
  "billingview" or "billing:", fails with ValidationException.

Pagination:
- max_items: total number of cost categories returned. If it is omitted, the tool fetches every page for """
    + PAGINATION_LIMIT_TEXT
    + """, then returns a partial result.
- If the result has complete_dataset: false, it is partial: call again with a larger
  max_items, continue with next_token, or say the result is partial.

Only a management account or a standalone account can call this; member (linked)
accounts get an access denied error.

Limits: 50 cost categories per management account, 500 rules per category (API),
100 rules per category (console), 10 split charge rules per category.

Example 1 - List all current categories: {}
Example 2 - List categories active on a date: {"effective_on": "2024-06-01"}
Example 3 - Filter by billing view support: {"supported_resource_types": "[\"billing:billingview\"]"}""",
)
async def list_cost_category_definitions(
    ctx: Context,
    effective_on: Optional[str] = None,
    supported_resource_types: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List cost category definitions.

    Args:
        ctx: The MCP context object
        effective_on: Optional ISO 8601 datetime or YYYY-MM-DD to filter by active date
        supported_resource_types: Optional JSON array of resource type strings
        max_items: Total cost categories to return. None fetches every page.
        next_token: Pagination token from previous response

    Returns:
        Dict containing the list of cost category references
    """
    await ctx.info('Calling ListCostCategoryDefinitions API')

    try:
        ce_client = create_aws_client('ce')
        params: Dict[str, Any] = {}

        if effective_on:
            try:
                params['EffectiveOn'] = _normalize_effective_on(effective_on)
            except ValueError as e:
                return _effective_on_error(e, 'ListCostCategoryDefinitions')
        if supported_resource_types:
            try:
                params['SupportedResourceTypes'] = json.loads(supported_resource_types)
            except json.JSONDecodeError as e:
                return format_response(
                    'error',
                    {
                        'message': f'Invalid JSON for supported_resource_types parameter: {e}',
                    },
                    error_type='validation_error',
                    operation='ListCostCategoryDefinitions',
                    service='Cost Explorer',
                )

        references, _, pagination = await paginate_aws_items(
            ctx,
            'ListCostCategoryDefinitions',
            ce_client.list_cost_category_definitions,
            params,
            LIST_COST_CATEGORY_DEFINITIONS,
            max_items=max_items,
            next_token=next_token,
        )
        return format_response(
            'success', with_pagination({'CostCategoryReferences': references}, pagination)
        )

    except Exception as e:
        return await handle_aws_error(ctx, e, 'ListCostCategoryDefinitions', 'Cost Explorer')
