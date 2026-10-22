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

"""AWS Cost Explorer tools for the AWS Billing and Cost Management MCP server.

Updated to use shared utility functions.
"""

from ..utilities.aws_service_base import create_aws_client, format_response, handle_aws_error
from .cost_explorer_operations import (
    get_cost_and_usage,
    get_cost_and_usage_with_resources,
    get_cost_categories,
    get_cost_forecast,
    get_dimension_values,
    get_savings_plans_utilization,
    get_tags,
    get_usage_forecast,
)
from datetime import date, timedelta
from fastmcp import Context, FastMCP
from typing import Any, Dict, List, Optional, Union


COST_EXPLORER_SERVICE_NAME = 'Cost Explorer'

cost_explorer_server = FastMCP(
    name='cost-explorer-tools', instructions='Tools for working with AWS Cost Explorer API'
)


def _add_months(day: date, months: int) -> date:
    """Return the first day of the month `months` after the month of `day`."""
    year, month = divmod(day.month - 1 + months, 12)
    return date(day.year + year, month + 1, 1)


def _with_example_dates(description: str) -> str:
    """Fill the example dates relative to today, so every example is valid as written.

    Literal dates go stale: Cost Explorer rejects a forecast that starts before today, a
    resource-level query older than 14 days, and history older than 13 months.
    """
    today = date.today()
    month_start = today.replace(day=1)
    dates = {
        '__TODAY__': today,
        '__WEEK_AGO__': today - timedelta(days=7),
        '__MONTH_START__': month_start,
        '__PREV_MONTH_START__': _add_months(month_start, -1),
        '__SIX_MONTHS_AGO_START__': _add_months(month_start, -6),
        '__NEXT_MONTH_START__': _add_months(month_start, 1),
        '__FOUR_MONTHS_AHEAD_START__': _add_months(month_start, 4),
    }
    for token, value in dates.items():
        description = description.replace(token, value.isoformat())
    return description


COST_EXPLORER_DESCRIPTION = _with_example_dates("""Retrieves AWS cost and usage data using the Cost Explorer API.

IMPORTANT USAGE GUIDELINES:
- Use UnblendedCost metric by default (not BlendedCost) unless user specifies otherwise
- Exclude record_types 'Credit' and 'Refund' by default unless user requests inclusion
- Use MONTHLY granularity for totals or rankings over whole months; use DAILY only when a daily
  trend is asked for or the window is shorter than a month
- Start with high-level dimensions (SERVICE, LINKED_ACCOUNT) before detailed ones
- Always remember that the end_date is exclusive
- Never filter on a dimension value you are guessing; group_by that dimension instead and read
  the exact values back with their costs

REPORTING $0:
An empty result is indistinguishable from a genuine zero, so a wrong filter value or a wrong
filter KEY returns no rows, reads as $0, and the miss is silent: "Amazon RDS" returns nothing
because the value is "Amazon Relational Database Service", and AWS Marketplace spend returns
nothing when filtered on LEGAL_ENTITY_NAME because the key for it is BILLING_ENTITY.
1. If you FILTERED, the filter was probably wrong. Confirm the value exists by calling
   getDimensionValues (purpose-built for this, lighter than a full breakdown), and confirm the
   KEY carries the concept you asked about (see DIMENSION REFERENCE). It returns only values
   with usage in the period, so absence is not proof the value is invalid. If you also need the
   spend, re-run grouped by that dimension to get the value and its cost in one call.
2. If you GROUPED and the line genuinely shows $0, report "$0.00", not "no data found".

PAGINATION (max_items, next_token: getCostAndUsage, getCostAndUsageWithResources, getDimensionValues, getTagsOrValues, getCostCategories only; the other operations take neither):
- max_items is the total number of items returned (getCostAndUsage: one item per group per period, or per period without group_by). Omit it to fetch every page (no limit). Pass it, or narrow the time range, filter or group_by, for queries that can be large (e.g. daily data grouped by RESOURCE_ID, USAGE_TYPE or LINKED_ACCOUNT).
- These operations don't support ordering, so max_items returns the first items the service sends, not the top N. For a top-N, fetch the full result (or a narrower one) and rank it.
- If the result has complete_dataset: false, it is partial: totals and counts undercount. Call again with a larger max_items, continue with next_token (same parameters otherwise; pass explicit start_date and end_date, since defaults are computed from today and a changed date range invalidates the token), or state that the result is partial. Never report a page size or the number of returned items as a total count.
- Fields from the first page only (GroupDefinitions, TotalSize) aren't repeated on continuation calls.

USE THIS TOOL FOR:
- **Historical cost trends** and spending analysis (any time period)
- **Usage pattern analysis** over time
- **Cost breakdown** by service, account, region, or any dimension
- **Forecasting** future costs and usage
- **Resource-level cost analysis** (last 14 days)
- **Multi-dimensional cost analysis** with complex grouping

WINDOW LIMITS:
- getCostAndUsage: the current month and the previous 13 months at DAILY and MONTHLY
  granularity. Older months are available at MONTHLY granularity only if multi-year data is
  enabled in Cost Explorer settings. HOURLY data covers only the previous 14 days and must also
  be enabled there.
- getCostAndUsageWithResources: the range must be within the last 14 days (start_date no
  earlier than 14 days ago).
- getSavingsPlansUtilization: start_date must be within the last 13 months, and end_date must
  be after start_date and before the current date.
- getCostForecast, getUsageForecast: start_date must be today or later. The maximum horizon is
  3 months at DAILY granularity and 18 months at MONTHLY. Cost Explorer does not produce a
  forecast when the account has too little history, which is common for accounts with less
  than one full billing cycle.

FILTER EXPRESSION GRAMMAR (the `filter` argument is an object or a JSON string):
The top-level object has exactly ONE of these keys:
- Leaf keys: `Dimensions`, `Tags`, `CostCategories`
- Logical keys: `And` and `Or` (each takes an array of expressions), `Not` (takes one
  expression)

Leaf shape:
`{"<Dimensions|Tags|CostCategories>": {"Key": "...", "Values": [...], "MatchOptions": [...]}}`

MatchOptions accepted by getCostAndUsage and getCostAndUsageWithResources:
- Dimensions:     EQUALS, CASE_SENSITIVE
- Tags:           EQUALS, ABSENT, CASE_SENSITIVE
- CostCategories: EQUALS, ABSENT, CASE_SENSITIVE
The default is EQUALS and CASE_SENSITIVE, so MatchOptions can usually be omitted. Not every
operation supports MatchOptions.

The MatchOption enum also contains `CASE_INSENSITIVE`, `STARTS_WITH`, `ENDS_WITH`, `CONTAINS`,
and `GREATER_THAN_OR_EQUAL`. These apply to Cost Category rules and anomaly subscriptions, not
to these filters.

Values per leaf type:
- Dimensions: `Values` is required and must not be empty.
- Tags / CostCategories: `Values` is required, except with `ABSENT`. `ABSENT` matches costs
  where the tag or cost category key is not present, so there is no value to compare against:
  omit `Values` entirely (an empty `Values` list is rejected too).

Correct filter examples:
- `{"Dimensions": {"Key": "SERVICE", "Values": ["Amazon Relational Database Service"]}}`
- `{"Tags": {"Key": "env", "Values": ["prod"]}}`
- `{"Tags": {"Key": "team", "MatchOptions": ["ABSENT"]}}`
- `{"And": [{"Dimensions": {"Key": "SERVICE", "Values": ["Amazon Elastic Compute Cloud - Compute"]}}, {"Dimensions": {"Key": "REGION", "Values": ["us-east-1"]}}]}`

## OPERATIONS

1) getCostAndUsage — account-level historical cost/usage
   Required: operation="getCostAndUsage", start_date, end_date, granularity, metrics
   Optional: group_by, filter, max_items, next_token, billing_view_arn
   Example: {"operation": "getCostAndUsage", "start_date": "__PREV_MONTH_START__", "end_date": "__MONTH_START__", "granularity": "MONTHLY", "metrics": "[\\"UnblendedCost\\"]", "group_by": "[{\\"Type\\": \\"DIMENSION\\", \\"Key\\": \\"SERVICE\\"}]"}

2. getCostAndUsageWithResources - Resource-level cost data (limited to last 14 days)
   Required: operation="getCostAndUsageWithResources", filter, granularity, start_date, end_date
   Optional: metrics, group_by, max_items, next_token, billing_view_arn
   Notes: RESOURCE_ID must be included in either filter OR group_by parameters. The range must be within the last 14 days (start_date no earlier than 14 days ago). Hourly granularity is only available for EC2-Instances resource-level data. All other resource-level data is available at daily granularity.
   Example: {"operation": "getCostAndUsageWithResources", "start_date": "__WEEK_AGO__", "end_date": "__TODAY__", "granularity": "DAILY", "filter": "{\\"Dimensions\\": {\\"Key\\": \\"SERVICE\\", \\"Values\\": [\\"Amazon Elastic Compute Cloud - Compute\\"]}}", "group_by": "[{\\"Type\\": \\"DIMENSION\\", \\"Key\\": \\"RESOURCE_ID\\"}]"}
   Returns: Cost data with resource-level granularity

3. getDimensionValues - List of available values for specified dimension
   Required: operation="getDimensionValues", dimension, start_date, end_date
   Optional: context, search_string, filter, max_items, next_token, billing_view_arn
   Example: {"operation": "getDimensionValues", "dimension": "SERVICE", "start_date": "__PREV_MONTH_START__", "end_date": "__MONTH_START__"}
   Returns: List of values for specified dimension (see PAGINATION)
   Notes: Each context accepts its own dimensions. COST_AND_USAGE (the default) takes the DIMENSION REFERENCE keys below; RESOURCE_ID needs a window within the last 14 days. RESERVATIONS takes only AZ, INSTANCE_TYPE, INSTANCE_TYPE_FAMILY, LINKED_ACCOUNT, PLATFORM, REGION, SCOPE, SERVICE, TENANCY. SAVINGS_PLANS takes only INSTANCE_TYPE_FAMILY, LINKED_ACCOUNT, PAYMENT_OPTION, REGION, SAVINGS_PLAN_ARN, SAVINGS_PLANS_TYPE. TAG is not a dimension in any context: to list a cost-allocation tag key's values use operation=getTagsOrValues (with tag_key); passing dimension=TAG is rejected.

4. getCostForecast - Future cost projections
   Required: operation="getCostForecast", metric, granularity
   Optional: start_date, end_date, filter, prediction_interval_level, billing_view_arn
   Example 1 (default window): {"operation": "getCostForecast", "metric": "UNBLENDED_COST", "granularity": "MONTHLY"}
   Example 2 (next three months): {"operation": "getCostForecast", "metric": "UNBLENDED_COST", "granularity": "MONTHLY", "start_date": "__NEXT_MONTH_START__", "end_date": "__FOUR_MONTHS_AHEAD_START__"}
   Notes: `metric` must be ALL CAPS and one of UNBLENDED_COST, BLENDED_COST, AMORTIZED_COST, NET_UNBLENDED_COST, NET_AMORTIZED_COST (not the getCostAndUsage spelling `UnblendedCost`). `start_date` defaults to tomorrow and `end_date` to 90 days after `start_date`; a `start_date` you pass must be today or later. The horizon is up to 3 months (DAILY) or 18 months (MONTHLY). HOURLY is not supported. In `filter`, LINKED_ACCOUNT values must be 12-digit account IDs (not account names), and RESOURCE_ID is not allowed.
   Returns: Cost forecast for specified time period and granularity

5. getUsageForecast - Future usage projections
   Required: operation="getUsageForecast", metric, granularity, filter
   Optional: start_date, end_date, prediction_interval_level, billing_view_arn
   Example 1: {"operation": "getUsageForecast", "metric": "USAGE_QUANTITY", "granularity": "MONTHLY", "start_date": "__NEXT_MONTH_START__", "end_date": "__FOUR_MONTHS_AHEAD_START__", "filter": "{\\"Dimensions\\": {\\"Key\\": \\"USAGE_TYPE_GROUP\\", \\"Values\\": [\\"EC2: Running Hours\\"]}}"}
   Example 2: {"operation": "getUsageForecast", "metric": "USAGE_QUANTITY", "granularity": "MONTHLY", "filter": "{\\"And\\": [{\\"Dimensions\\": {\\"Key\\": \\"SERVICE\\", \\"Values\\": [\\"Amazon Elastic Compute Cloud - Compute\\"]}}, {\\"Dimensions\\": {\\"Key\\": \\"USAGE_TYPE\\", \\"Values\\": [\\"BoxUsage:p4de.24xlarge\\"]}}]}"}
   Example 3: {"operation": "getUsageForecast", "metric": "USAGE_QUANTITY", "granularity": "MONTHLY", "filter": "{\\"Dimensions\\": {\\"Key\\": \\"USAGE_TYPE\\", \\"Values\\": [\\"BoxUsage:p4de.24xlarge\\", \\"Reservation:p4de.24xlarge\\", \\"UnusedBox:p4de.24xlarge\\"]}}", "group_by": "[{\\"Type\\": \\"DIMENSION\\", \\"Key\\": \\"REGION\\"}]"}
   Notes: Valid values for metric is: USAGE_QUANTITY, NORMALIZED_USAGE_AMOUNT. Valid values for granularity is: DAILY, MONTHLY. Filter is REQUIRED and must specify USAGE_TYPE or USAGE_TYPE_GROUP to define what usage units to forecast. Dates default and are limited as for getCostForecast.
   Returns: Usage forecast for specified time period and granularity

6. getTagsOrValues - Available cost allocation tags or values
   Required: operation="getTagsOrValues"
   Optional: start_date, end_date, tag_key, search_string, max_items, next_token, billing_view_arn
   Example 1: {"operation": "getTagsOrValues"}
   Example 2: {"operation": "getTagsOrValues", "tag_key": "Environment"}
   Returns: List of available cost allocation tags (see PAGINATION). If tag values for a particular key are needed, pass the tag key as a parameter. The tag key list holds at most 5,000 keys in total.

7. getCostCategories - Available cost categories or values inside a category
   Required: operation="getCostCategories", start_date, end_date
   Optional: cost_category_name, search_string, max_items, next_token, billing_view_arn
   Example 1 (list category names): {"operation": "getCostCategories", "start_date": "__SIX_MONTHS_AGO_START__", "end_date": "__MONTH_START__"}
   Example 2 (list values inside a category): {"operation": "getCostCategories", "cost_category_name": "CostCenters", "start_date": "__SIX_MONTHS_AGO_START__", "end_date": "__MONTH_START__"}
   Notes: Without cost_category_name the response contains CostCategoryNames. With cost_category_name set the response contains CostCategoryValues for that category. The category name list holds at most 5,000 names in total. See PAGINATION.

8. getSavingsPlansUtilization - Savings Plans utilization data
   Required: operation="getSavingsPlansUtilization", start_date, end_date
   Optional: granularity, filter
   Example: {"operation": "getSavingsPlansUtilization", "granularity": "MONTHLY"}
   Notes: Supports only DAILY and MONTHLY granularity. start_date must be within the last 13 months, and end_date must be before the current date. Data lags ~1 day: a window ending today (an incomplete UTC day) may come back empty or as a DataUnavailableException. A DataUnavailableException here means there is no Savings Plans data for THIS window (no active plans, or the window is outside the plan period) — report none/zero and do NOT retry the identical window; change the window (e.g. set end_date to yesterday) instead.
   Returns: Savings Plans utilization for the specified time period

DIMENSION REFERENCE:
- AZ: The Availability Zone (e.g., us-east-1a)
- BILLING_ENTITY: Who bills the charge - "AWS" for AWS services, "AWS Marketplace" for
  third-party Marketplace purchases. This is the key for Marketplace spend, NOT LEGAL_ENTITY_NAME
- DATABASE_ENGINE: The Amazon RDS database (e.g., Aurora, MySQL)
- DEPLOYMENT_OPTION: RDS deployment scope (SingleAZ, MultiAZ)
- INSTANCE_TYPE: The EC2 instance type (e.g., m4.xlarge)
- INSTANCE_TYPE_FAMILY: Family of instances (e.g., Compute Optimized, Memory Optimized)
- INVOICING_ENTITY: The AWS entity that issued the invoice (e.g., Amazon Web Services, Inc.)
- LEGAL_ENTITY_NAME: The AWS seller of record (e.g., Amazon Web Services, Inc.); it does not
  separate Marketplace from AWS charges
- LINKED_ACCOUNT: AWS member accounts
- OPERATING_SYSTEM: OS type (e.g., Windows, Linux)
- OPERATION: The API operation behind a charge (e.g., RunInstances, PutObject; for Amazon Bedrock, model-invocation operations). The dimension is OPERATION — there is no API_OPERATION dimension.
- PLATFORM: EC2 operating system
- PURCHASE_TYPE: Reservation type (e.g., On-Demand, Reserved)
- REGION: AWS Region
- RESOURCE_ID: Resource identifier. Only for getCostAndUsageWithResources (last 14 days)
- SERVICE: AWS service (e.g., Amazon DynamoDB)
- TAG: Cost allocation tag — valid as a GroupBy Type (`[{"Type":"TAG","Key":"<tag_key>"}]`) and inside filter `Tags` leaves, but NOT a getDimensionValues dimension in any context; to list a tag key's values use operation=getTagsOrValues (with tag_key).
- TENANCY: EC2 tenancy. Exact, case-sensitive values: Shared, Dedicated (Dedicated Instance),
  Host (Dedicated Host)
- USAGE_TYPE: Usage type (e.g., DataTransfer-In-Bytes)
- USAGE_TYPE_GROUP: Group of related usage types (e.g., EC2: Running Hours)
- RECORD_TYPE: Charge types (e.g., RI fees, usage costs)

BILLING VIEW SUPPORT:
Most Cost Explorer operations support an optional billing_view_arn parameter that allows you to scope
your query to a specific billing view. If not provided, the query defaults to the account's primary
billing view. You can use the list-billing-views and get-billing-view tools upon request to discover
available billing views and their ARNs.

Billing view types:
- PRIMARY: Default view with all cost data for the account/org. Use for standard cost analysis.
- BILLING_GROUP: AWS managed view for Billing Conductor billing groups with pro forma cost data.
- CUSTOM: Customer-created views with filtered cost data that can be shared across accounts and
  organizations. Use for business-unit, team, or cross-org cost visibility without management
  account access.
- BILLING_TRANSFER: Available to Bill Transfer (bill receiver) account, who is responsible for
  paying the consolidated bill on behalf of the other organization.
  AWS managed view containing chargeable data, which is what the Bill Transfer (bill receiver)
  account owes to AWS for their Bill Source accounts' cloud consumption.
- BILLING_TRANSFER_SHOWBACK: Available to Bill Transfer (bill receiver) account.
  AWS managed view showing pro forma showback/chargeback data (what Bill Source account owe their partner).
  Use for showback/chargeback reporting in billing transfer scenarios.""")


@cost_explorer_server.tool(
    name='cost-explorer',
    description=COST_EXPLORER_DESCRIPTION,
)
async def cost_explorer(
    ctx: Context,
    operation: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    granularity: str = 'DAILY',
    metrics: Optional[Union[str, List[str]]] = None,
    group_by: Optional[Union[str, List[Dict[str, Any]]]] = None,
    filter: Optional[Union[str, Dict[str, Any]]] = None,
    dimension: Optional[str] = None,
    search_string: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
    metric: Optional[str] = None,
    prediction_interval_level: int = 80,
    tag_key: Optional[str] = None,
    cost_category_name: Optional[str] = None,
    billing_view_arn: Optional[str] = None,
    context: Optional[str] = None,
) -> Dict[str, Any]:
    """Main entry point for Cost Explorer operations.

    This function routes requests to the appropriate operation handler
    based on the operation parameter.

    Args:
        ctx: MCP context
        operation: The operation to perform
        start_date: Start date for cost data in YYYY-MM-DD format
        end_date: End date for cost data in YYYY-MM-DD format (exclusive)
        granularity: Granularity of the returned data (DAILY, MONTHLY, etc.)
        metrics: Metrics to include in the response, as a list or a JSON string
        group_by: How to group the results, as a list of objects or a JSON string
        filter: Filter to apply to the results, as an object or a JSON string
        dimension: Dimension to get values for (getDimensionValues)
        search_string: Search string to filter dimension values
        max_items: Most items to return, for the paginated operations only. Omit to fetch
            every page.
        next_token: Continuation token from a previous response, for the paginated
            operations only
        metric: Metric for cost forecasts
        prediction_interval_level: Confidence level for forecasts
        tag_key: Tag key to get values for
        cost_category_name: Cost category to get values for
        billing_view_arn: Optional ARN of a billing view to scope the query
        context: The context for (getDimensionValues), which can be COST_AND_USAGE (the default),
            RESERVATIONS, or SAVINGS_PLANS. SAVINGS_PLANS scopes values to the plans an account owns.

    Returns:
        Response from the operation handler
    """
    await ctx.info(f'Cost Explorer operation: {operation}')

    # Create Cost Explorer client
    try:
        ce_client = create_aws_client('ce')
    except Exception as client_error:
        await ctx.error(f'Failed to create AWS client: {str(client_error)}')
        error_message = f'Failed to create AWS client: {str(client_error)}'
        return format_response(
            'error',
            {
                'error_type': 'client_creation_error',
                'message': error_message,
                'details': repr(client_error),
            },
            error_message,
            error_type='client_creation_error',
            operation=operation,
            service=COST_EXPLORER_SERVICE_NAME,
        )

    # Route to the appropriate operation handler
    try:
        await ctx.info(f'Routing to operation: {operation}')

        if operation == 'getCostAndUsage':
            return await get_cost_and_usage(
                ctx,
                ce_client,
                start_date,
                end_date,
                granularity,
                metrics,
                group_by,
                filter,
                next_token,
                max_items,
                billing_view_arn,
            )

        elif operation == 'getCostAndUsageWithResources':
            return await get_cost_and_usage_with_resources(
                ctx,
                ce_client,
                start_date,
                end_date,
                granularity,
                metrics,
                group_by,
                filter,
                next_token,
                max_items,
                billing_view_arn,
            )

        elif operation == 'getDimensionValues':
            if not dimension:
                return format_response(
                    'error',
                    {'message': 'dimension is required for getDimensionValues operation'},
                    error_type='validation_error',
                    operation=operation,
                    service=COST_EXPLORER_SERVICE_NAME,
                )

            # TAG is not a GetDimensionValues dimension in any context: AWS rejects it with
            # ValidationException for COST_AND_USAGE, RESERVATIONS and SAVINGS_PLANS alike.
            # Catch it before the API round-trip and point to the operation that actually
            # lists tag values.
            if dimension == 'TAG':
                return format_response(
                    'error',
                    {
                        'message': (
                            'TAG is not a getDimensionValues dimension in any context. '
                            "To list a tag key's values use operation=getTagsOrValues "
                            '(optionally with tag_key).'
                        )
                    },
                    error_type='validation_error',
                    operation=operation,
                    service=COST_EXPLORER_SERVICE_NAME,
                    hint=(
                        "To list a cost-allocation tag key's values, call this tool with "
                        'operation=getTagsOrValues (pass tag_key for one key). Do **NOT** retry '
                        'getDimensionValues with dimension=TAG.'
                    ),
                )

            return await get_dimension_values(
                ctx,
                ce_client,
                dimension,
                start_date,
                end_date,
                search_string,
                filter,
                next_token,
                max_items,
                billing_view_arn,
                context,
            )

        elif operation == 'getCostForecast':
            if not metric:
                return format_response(
                    'error',
                    {'message': 'metric is required for getCostForecast operation'},
                    error_type='validation_error',
                    operation=operation,
                    service=COST_EXPLORER_SERVICE_NAME,
                )

            return await get_cost_forecast(
                ctx,
                ce_client,
                metric,
                start_date,
                end_date,
                granularity,
                filter,
                prediction_interval_level,
                billing_view_arn,
            )

        elif operation == 'getUsageForecast':
            if not metric:
                return format_response(
                    'error',
                    {'message': 'metric is required for getUsageForecast operation'},
                    error_type='validation_error',
                    operation=operation,
                    service=COST_EXPLORER_SERVICE_NAME,
                )

            return await get_usage_forecast(
                ctx,
                ce_client,
                metric,
                start_date,
                end_date,
                granularity,
                filter,
                prediction_interval_level,
                billing_view_arn,
            )

        elif operation == 'getTagsOrValues':
            return await get_tags(
                ctx,
                ce_client,
                start_date,
                end_date,
                search_string,
                tag_key,
                next_token,
                max_items,
                billing_view_arn,
            )

        elif operation == 'getCostCategories':
            # When `cost_category_name` is provided, the same AWS API
            # (GetCostCategories) returns the values inside that category
            # instead of the list of category names.
            return await get_cost_categories(
                ctx,
                ce_client,
                start_date,
                end_date,
                search_string,
                cost_category_name,
                next_token,
                max_items,
                billing_view_arn,
            )

        elif operation == 'getSavingsPlansUtilization':
            return await get_savings_plans_utilization(
                ctx, ce_client, start_date, end_date, granularity, filter
            )

        else:
            return format_response(
                'error',
                {'message': f'Unknown operation: {operation}'},
                error_type='validation_error',
                operation=operation,
                service=COST_EXPLORER_SERVICE_NAME,
            )

    except Exception as e:
        # The shared handler classifies ClientError and all other exceptions
        return await handle_aws_error(ctx, e, operation, COST_EXPLORER_SERVICE_NAME)
