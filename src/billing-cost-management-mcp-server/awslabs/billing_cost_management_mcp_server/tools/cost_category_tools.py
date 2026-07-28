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
from ..utilities.aws_service_base import (
    create_aws_client,
    format_response,
    handle_aws_error,
    paginate_aws_response,
)
from fastmcp import Context, FastMCP
from typing import Any, Dict, Optional


cost_category_server = FastMCP(
    name='cost-category-tools',
    instructions='Tools for managing AWS Cost Categories',
)


@cost_category_server.tool(
    name='describe-cost-category-definition',
    description="""Returns the full definition of a cost category using the DescribeCostCategoryDefinition API.

Cost categories group AWS costs using rule-based expressions that match line items by
dimensions (SERVICE, LINKED_ACCOUNT, USAGE_TYPE), resource tags, or other cost category
values. Each matched line item is assigned a category value such as "Production" or
"Development". Rules can be REGULAR (explicit match) or INHERITED_VALUE (dynamic value
from a tag key or account name). A DefaultValue catches costs that do not match any rule.

The tool returns a CostCategory object containing:
- Name (1-50 chars, unique per account, case-sensitive), CostCategoryArn
- RuleVersion (always "CostCategoryExpression.v1")
- Rules array with Value, Rule expression (Dimensions/Tags/CostCategories with And/Or/Not), and Type
- DefaultValue, SplitChargeRules (PROPORTIONAL, FIXED, or EVEN allocation methods)
- EffectiveStart/EffectiveEnd (null if still active)
- ProcessingStatus: APPLIED (rules reflected in data) or PROCESSING (backfill in progress)

Linked accounts can describe cost categories from their management account.

Required parameters:
- cost_category_arn: ARN of the cost category (arn:aws:ce::<account_id>:costcategory/<uuid>).
  Use list-cost-category-definitions to discover ARNs.

Optional parameters:
- effective_on: ISO 8601 datetime (e.g., 2024-01-01T00:00:00Z) to retrieve the version
  active at that time. Defaults to the current version.

Example 1 - Get current definition:
  {"cost_category_arn": "arn:aws:ce::123456789012:costcategory/abcd-1234"}
Example 2 - Get historical version:
  {"cost_category_arn": "arn:aws:ce::123456789012:costcategory/abcd-1234", "effective_on": "2024-06-01T00:00:00Z"}""",
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
        effective_on: Optional ISO 8601 datetime to retrieve a historical version

    Returns:
        Dict containing the cost category definition
    """
    await ctx.info(f'Calling DescribeCostCategoryDefinition for {cost_category_arn}')

    try:
        ce_client = create_aws_client('ce')
        params: Dict[str, Any] = {'CostCategoryArn': cost_category_arn}

        if effective_on:
            params['EffectiveOn'] = effective_on

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

You can filter and paginate with:
- effective_on: ISO 8601 datetime to return only categories active at that time.
  Defaults to current date.
- supported_resource_types: JSON array to filter by resource type support.
  Valid values: "billing:rispgroupsharing", "billing:billingview"
  Example: '["billing:billingview"]'
  Returns only categories supporting all specified types.
- max_results: Results per page (1-100, default 20)
- max_pages: Max pages to auto-paginate through

Limits: 50 cost categories per management account, 500 rules per category (API),
100 rules per category (console), 10 split charge rules per category.

Example 1 - List all current categories: {}
Example 2 - List categories active on a date: {"effective_on": "2024-06-01T00:00:00Z"}
Example 3 - Filter by billing view support: {"supported_resource_types": "[\"billing:billingview\"]"}""",
)
async def list_cost_category_definitions(
    ctx: Context,
    effective_on: Optional[str] = None,
    supported_resource_types: Optional[str] = None,
    max_results: Optional[int] = None,
    next_token: Optional[str] = None,
    max_pages: Optional[int] = None,
) -> Dict[str, Any]:
    """List cost category definitions.

    Args:
        ctx: The MCP context object
        effective_on: Optional ISO 8601 datetime to filter by active date
        supported_resource_types: Optional JSON array of resource type strings
        max_results: Max results per page (1-100, default 20)
        next_token: Pagination token from previous response
        max_pages: Max pages to auto-paginate through

    Returns:
        Dict containing the list of cost category references
    """
    await ctx.info('Calling ListCostCategoryDefinitions API')

    try:
        ce_client = create_aws_client('ce')
        params: Dict[str, Any] = {}

        if effective_on:
            params['EffectiveOn'] = effective_on
        if supported_resource_types:
            try:
                params['SupportedResourceTypes'] = json.loads(supported_resource_types)
            except json.JSONDecodeError as e:
                return format_response(
                    'error',
                    {
                        'message': f'Invalid JSON for supported_resource_types parameter: {e}',
                    },
                )
        if max_results is not None:
            params['MaxResults'] = max_results

        if next_token:
            params['NextToken'] = next_token
        if next_token or max_pages:
            results, pagination = await paginate_aws_response(
                ctx,
                'ListCostCategoryDefinitions',
                lambda **p: ce_client.list_cost_category_definitions(**p),
                params,
                'CostCategoryReferences',
                max_pages=max_pages,
            )
            return format_response(
                'success',
                {
                    'CostCategoryReferences': results,
                    'Pagination': pagination,
                },
            )

        response = ce_client.list_cost_category_definitions(**params)
        return format_response('success', response)

    except Exception as e:
        return await handle_aws_error(ctx, e, 'ListCostCategoryDefinitions', 'Cost Explorer')
