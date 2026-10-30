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
from ..utilities.constants import PAGINATION_LIMIT_TEXT
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

# Operations whose AWS API has no GroupBy. The handlers never send group_by, so a caller who
# passes it would get one ungrouped result that reads as if it were split by the dimension.
OPERATIONS_WITHOUT_GROUP_BY = frozenset(
    {
        'getDimensionValues',
        'getCostForecast',
        'getUsageForecast',
        'getTagsOrValues',
        'getCostCategories',
        'getSavingsPlansUtilization',
    }
)

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


COST_EXPLORER_DESCRIPTION = _with_example_dates(
    """Retrieves AWS cost and usage data using the Cost Explorer API.

IMPORTANT USAGE GUIDELINES:
- If metrics is omitted, getCostAndUsage and getCostAndUsageWithResources use ["UnblendedCost"]
- A query with no RECORD_TYPE filter returns net cost: credits and refunds are already
  subtracted. Filtering them out returns charges before credits, which can be far higher than
  what the account paid: a commitment fee refunded in the same month
  is counted once with no offsetting refund. Group by RECORD_TYPE to see which charge types
  (usage, fees, credits, refunds, tax) make up a total
- Use MONTHLY granularity for totals or rankings over whole months; use DAILY only when a daily
  trend is asked for or the window is shorter than a month
- If granularity is omitted, every operation that takes it uses DAILY
- Start with high-level dimensions (SERVICE, LINKED_ACCOUNT) before detailed ones
- Always remember that the end_date is exclusive
- Never filter on a dimension value you are guessing; group_by that dimension instead and read
  the exact values back with their costs
- group_by works only with getCostAndUsage and getCostAndUsageWithResources; the other
  operations reject it. Forecasts return one total per period: for a forecast per Region (or
  any other value), run one forecast per value with that value in the filter

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
3. A grouped result shows costs with no value for the dimension under a placeholder key such
   as NoRegion or NoTenancy. The placeholder is not a value: a filter on it matches nothing
   and returns $0, and getDimensionValues lists the empty value as "". To filter on those
   costs, pass the empty string: `{"Dimensions": {"Key": "REGION", "Values": [""]}}`. For
   costs without a tag or cost category key, use `ABSENT` instead (see FILTER EXPRESSION
   GRAMMAR).

PAGINATION (max_items, next_token: getCostAndUsage, getCostAndUsageWithResources, getDimensionValues, getTagsOrValues, getCostCategories only; the other operations take neither):
- max_items is the total number of items returned (getCostAndUsage: one item per group per period, or per period without group_by). If it is omitted, the tool fetches every page for """
    + PAGINATION_LIMIT_TEXT
    + """, then returns a partial result. Pass it, or narrow the time range, filter or group_by, for queries that can be large (e.g. daily data grouped by RESOURCE_ID, USAGE_TYPE or LINKED_ACCOUNT).
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

FILTER EXPRESSION GRAMMAR (the `filter` argument is an object or a JSON string with double quotes; omit it for no filter, as an empty one is rejected):
The top-level object has exactly ONE of these keys:
- Leaf keys: `Dimensions`, `Tags`, `CostCategories`
- Logical keys: `And` and `Or` (each takes an array of at least 2 expressions), `Not` (takes
  one expression)

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
- Dimensions: `Values` is required and must not be empty. `[""]` (one empty string) is not
  empty: in getCostAndUsage it matches costs with no value for the dimension (see
  REPORTING $0).
- Tags / CostCategories: `Values` is required, except with `ABSENT`. `ABSENT` matches costs
  where the tag or cost category key is not present, so there is no value to compare against:
  omit `Values` entirely (an empty `Values` list is rejected too).

Correct filter examples:
- `{"Dimensions": {"Key": "SERVICE", "Values": ["Amazon Relational Database Service"]}}`
- `{"Tags": {"Key": "env", "Values": ["prod"]}}`
- `{"Tags": {"Key": "team", "MatchOptions": ["ABSENT"]}}`
- `{"And": [{"Dimensions": {"Key": "SERVICE", "Values": ["Amazon Elastic Compute Cloud - Compute"]}}, {"Dimensions": {"Key": "REGION", "Values": ["us-east-1"]}}]}`

Limits by operation (a filter outside them returns ValidationException):
- getCostAndUsage, getCostAndUsageWithResources: `And`, `Or` and `Not` nest up to 4 levels
  deep; a 5th is rejected.
- getDimensionValues (default COST_AND_USAGE context): `And` only; `Or` and `Not` are rejected.
- getSavingsPlansUtilization: `And` and `Not` only; `Or` is rejected.

## OPERATIONS

1) getCostAndUsage — account-level historical cost/usage
   Required: operation="getCostAndUsage"
   Optional: start_date, end_date, granularity, metrics, group_by, filter, max_items, next_token, billing_view_arn
   Defaults: If start_date is omitted, the tool uses 30 days before today; if end_date is omitted, it uses today (exclusive, so today is not included). If granularity is omitted, the tool uses DAILY. If metrics is omitted, the tool uses ["UnblendedCost"].
   Example: {"operation": "getCostAndUsage", "start_date": "__PREV_MONTH_START__", "end_date": "__MONTH_START__", "granularity": "MONTHLY", "metrics": "[\\"UnblendedCost\\"]", "group_by": "[{\\"Type\\": \\"DIMENSION\\", \\"Key\\": \\"SERVICE\\"}]"}

2. getCostAndUsageWithResources - Resource-level cost data (limited to last 14 days)
   Required: operation="getCostAndUsageWithResources", filter
   Optional: start_date, end_date, granularity, metrics, group_by, max_items, next_token, billing_view_arn
   Defaults: If start_date is omitted, the tool uses 7 days before today; if end_date is omitted, it uses today (exclusive). If granularity is omitted, the tool uses DAILY. If metrics is omitted, the tool uses ["UnblendedCost"].
   Notes: RESOURCE_ID must be included in either filter OR group_by parameters. The range must be within the last 14 days (start_date no earlier than 14 days ago). Hourly granularity is only available for EC2-Instances resource-level data. All other resource-level data is available at daily granularity.
   Services: works for every service the account has opted in to resource-level data (Cost Explorer settings), not only EC2. Any filter works: a SERVICE filter is not required, though the API reference says SERVICE = Amazon Elastic Compute Cloud - Compute is.
   Example: {"operation": "getCostAndUsageWithResources", "start_date": "__WEEK_AGO__", "end_date": "__TODAY__", "granularity": "DAILY", "filter": "{\\"Dimensions\\": {\\"Key\\": \\"SERVICE\\", \\"Values\\": [\\"Amazon Relational Database Service\\"]}}", "group_by": "[{\\"Type\\": \\"DIMENSION\\", \\"Key\\": \\"RESOURCE_ID\\"}]"}
   Returns: Cost data with resource-level granularity

3. getDimensionValues - List of available values for specified dimension
   Required: operation="getDimensionValues", dimension
   Optional: start_date, end_date, context, search_string, filter, max_items, next_token, billing_view_arn
   Defaults: If start_date is omitted, the tool uses 30 days before today; if end_date is omitted, it uses today (exclusive, so today is not included).
   Example: {"operation": "getDimensionValues", "dimension": "SERVICE", "start_date": "__PREV_MONTH_START__", "end_date": "__MONTH_START__"}
   Returns: List of values for specified dimension (see PAGINATION)
   Notes: Each context accepts its own dimensions. COST_AND_USAGE (the default) takes the DIMENSION REFERENCE keys below except SCOPE and TAG; RESOURCE_ID needs a window within the last 14 days. RESERVATIONS takes only AZ, INSTANCE_TYPE, INSTANCE_TYPE_FAMILY, LINKED_ACCOUNT, PLATFORM, REGION, SCOPE, SERVICE, TENANCY. SAVINGS_PLANS takes only INSTANCE_TYPE_FAMILY, LINKED_ACCOUNT, PAYMENT_OPTION, REGION, SAVINGS_PLAN_ARN, SAVINGS_PLANS_TYPE. TAG is not a dimension in any context: to list a cost-allocation tag key's values use operation=getTagsOrValues (with tag_key); passing dimension=TAG is rejected.

4. getCostForecast - Future cost projections
   Required: operation="getCostForecast", metric
   Optional: granularity, start_date, end_date, filter, prediction_interval_level, billing_view_arn
   Defaults: If granularity is omitted, the tool uses DAILY.
   Example 1 (default window): {"operation": "getCostForecast", "metric": "UNBLENDED_COST", "granularity": "MONTHLY"}
   Example 2 (next three months): {"operation": "getCostForecast", "metric": "UNBLENDED_COST", "granularity": "MONTHLY", "start_date": "__NEXT_MONTH_START__", "end_date": "__FOUR_MONTHS_AHEAD_START__"}
   Notes: `metric` must be ALL CAPS and one of UNBLENDED_COST, BLENDED_COST, AMORTIZED_COST, NET_UNBLENDED_COST, NET_AMORTIZED_COST (not the getCostAndUsage spelling `UnblendedCost`). `start_date` defaults to tomorrow and `end_date` to 90 days after `start_date`; a `start_date` you pass must be today or later. The horizon is up to 3 months (DAILY) or 18 months (MONTHLY). HOURLY is not supported. With MONTHLY granularity each period is a whole calendar month: Cost Explorer moves a `start_date` that isn't a 1st back to the 1st, and an `end_date` that isn't a 1st forward to the next 1st. So a MONTHLY forecast that starts this month on any day but the 1st (as the default start, tomorrow, does unless tomorrow is a 1st) returns the whole current month, and that period and `Total` include its actual costs to date. The response's `period_note` says when the period was widened. For part of a month, such as the rest of this month, use DAILY and sum the days. In `filter`, LINKED_ACCOUNT values must be 12-digit account IDs (not account names), and RESOURCE_ID is not allowed.
   Returns: Cost forecast for specified time period and granularity

5. getUsageForecast - Future usage projections
   Required: operation="getUsageForecast", metric, filter
   Optional: granularity, start_date, end_date, prediction_interval_level, billing_view_arn
   Defaults: If granularity is omitted, the tool uses DAILY.
   Example 1: {"operation": "getUsageForecast", "metric": "USAGE_QUANTITY", "granularity": "MONTHLY", "start_date": "__NEXT_MONTH_START__", "end_date": "__FOUR_MONTHS_AHEAD_START__", "filter": "{\\"Dimensions\\": {\\"Key\\": \\"USAGE_TYPE_GROUP\\", \\"Values\\": [\\"EC2: Running Hours\\"]}}"}
   Example 2: {"operation": "getUsageForecast", "metric": "USAGE_QUANTITY", "granularity": "MONTHLY", "filter": "{\\"And\\": [{\\"Dimensions\\": {\\"Key\\": \\"SERVICE\\", \\"Values\\": [\\"Amazon Elastic Compute Cloud - Compute\\"]}}, {\\"Dimensions\\": {\\"Key\\": \\"USAGE_TYPE\\", \\"Values\\": [\\"BoxUsage:p4de.24xlarge\\"]}}]}"}
   Example 3 (one Region): {"operation": "getUsageForecast", "metric": "USAGE_QUANTITY", "granularity": "MONTHLY", "filter": "{\\"And\\": [{\\"Dimensions\\": {\\"Key\\": \\"USAGE_TYPE_GROUP\\", \\"Values\\": [\\"EC2: Running Hours\\"]}}, {\\"Dimensions\\": {\\"Key\\": \\"REGION\\", \\"Values\\": [\\"us-east-1\\"]}}]}"}
   Notes: Valid values for metric is: USAGE_QUANTITY, NORMALIZED_USAGE_AMOUNT. Valid values for granularity is: DAILY, MONTHLY. Filter is REQUIRED and must specify USAGE_TYPE or USAGE_TYPE_GROUP to define what usage units to forecast. Dates default and are limited as for getCostForecast, and MONTHLY periods are whole calendar months as described there.
   Returns: Usage forecast for specified time period and granularity

6. getTagsOrValues - Available cost allocation tags or values
   Required: operation="getTagsOrValues"
   Optional: start_date, end_date, tag_key, search_string, max_items, next_token, billing_view_arn
   Defaults: If start_date is omitted, the tool uses 30 days before today; if end_date is omitted, it uses today (exclusive, so today is not included).
   Example 1: {"operation": "getTagsOrValues"}
   Example 2: {"operation": "getTagsOrValues", "tag_key": "Environment"}
   Returns: List of available cost allocation tags (see PAGINATION). If tag values for a particular key are needed, pass the tag key as a parameter. The tag key list holds at most 5,000 keys in total.

7. getCostCategories - Available cost categories or values inside a category
   Required: operation="getCostCategories"
   Optional: start_date, end_date, cost_category_name, search_string, max_items, next_token, billing_view_arn
   Defaults: If start_date is omitted, the tool uses 30 days before today; if end_date is omitted, it uses today (exclusive, so today is not included).
   Example 1 (list category names): {"operation": "getCostCategories", "start_date": "__SIX_MONTHS_AGO_START__", "end_date": "__MONTH_START__"}
   Example 2 (list values inside a category): {"operation": "getCostCategories", "cost_category_name": "CostCenters", "start_date": "__SIX_MONTHS_AGO_START__", "end_date": "__MONTH_START__"}
   Notes: Without cost_category_name the response contains CostCategoryNames. With cost_category_name set the response contains CostCategoryValues for that category. The category name list holds at most 5,000 names in total. See PAGINATION.

8. getSavingsPlansUtilization - Savings Plans utilization data
   Required: operation="getSavingsPlansUtilization"
   Optional: start_date, end_date, granularity, filter
   Defaults: If start_date is omitted, the tool uses 30 days before today; if end_date is omitted, it uses today (exclusive, so today is not included). If granularity is omitted, the tool uses DAILY.
   Example: {"operation": "getSavingsPlansUtilization", "granularity": "MONTHLY"}
   Notes: Supports only DAILY and MONTHLY granularity. With MONTHLY granularity each entry's TimePeriod is its whole calendar month (the current month's entry ends at the first day without data instead), but the figures (and Total) cover only the requested days: a start_date or end_date inside a month makes that month's entry partial though it is labelled with the whole month. The response's `period_note` says when this happened; report those months as partial. start_date must be within the last 13 months, and end_date is exclusive and may be today. Data for the most recent 2-3 days (counting today) is not processed yet: a start_date in those days returns a DataUnavailableException, and a window that reaches into them silently leaves them out; a start_date at least 3 days before today is usually past that delay. A DataUnavailableException here means there is no Savings Plans data for THIS window and filter (the window is too recent, no plan was active in it, or a filter value such as an unknown SAVINGS_PLANS_TYPE matches nothing) — report that no data is available for that window (not zero) and do NOT resend the identical request; correct an unknown filter value, and query an earlier window only if the question allows it.
   Returns: Savings Plans utilization for the specified time period

DIMENSION REFERENCE:
Unless an entry says otherwise, a key works as a filter key and a group_by key in
getCostAndUsage and getCostAndUsageWithResources, as a filter key in the forecasts, and as a
getDimensionValues dimension.
- AZ: The Availability Zone (e.g., us-east-1a)
- BILLING_ENTITY: Who bills the charge - "AWS" for AWS services, "AWS Marketplace" for
  third-party Marketplace purchases. This is the key for Marketplace spend, NOT LEGAL_ENTITY_NAME
- CACHE_ENGINE: The Amazon ElastiCache engine
- DATABASE_ENGINE: The database engine (e.g., Aurora MySQL, Aurora PostgreSQL, MySQL, PostgreSQL)
- DEPLOYMENT_OPTION: Deployment option (e.g., Single-AZ, Multi-AZ)
- INSTANCE_TYPE: The EC2 instance type (e.g., m4.xlarge)
- INSTANCE_TYPE_FAMILY: Instance family (e.g., m5, t3, c6g); the case can vary by service (e.g., r5
  and R5 are separate values)
- INVOICING_ENTITY: The AWS entity that issued the invoice (e.g., Amazon Web Services, Inc.)
- LEGAL_ENTITY_NAME: The AWS seller of record (e.g., Amazon Web Services, Inc.); it does not
  separate Marketplace from AWS charges
- LINKED_ACCOUNT: AWS member accounts, as 12-digit account IDs in every operation. With the
  default match, any other value, such as an account name, is rejected with ValidationException
  (a forecast with CONTAINS, STARTS_WITH or ENDS_WITH is not checked and returns
  DataUnavailableException, which reads like missing history).
  LINKED_ACCOUNT_NAME is not a filter key. To map a name to its ID, call getDimensionValues with dimension
  LINKED_ACCOUNT: each value is an ID and its attributes carry the account name (`description`)
- OPERATING_SYSTEM: OS type (e.g., Linux/UNIX, Windows (Amazon VPC))
- OPERATION: The API operation behind a charge (e.g., RunInstances, PutObject; for Amazon Bedrock, model-invocation operations). The dimension is OPERATION — there is no API_OPERATION dimension.
- PLATFORM: EC2 operating system (e.g., Linux/UNIX, Windows (Amazon VPC))
- PURCHASE_TYPE: Purchase option (e.g., On Demand Instances, Standard Reserved Instances, Savings
  Plans)
- REGION: AWS Region
- RESERVATION_ID: The Reserved Instance a cost belongs to
- RESOURCE_ID: Resource identifier, last 14 days only. A filter and group_by key in getCostAndUsageWithResources, and a getDimensionValues dimension and filter key; not usable in getCostAndUsage or the forecasts
- SAVINGS_PLAN_ARN: The ARN of the Savings Plan a cost belongs to
- SAVINGS_PLANS_TYPE: The type of Savings Plan a cost belongs to
- SCOPE: Reserved Instance scope. Only a getDimensionValues dimension in the RESERVATIONS
  context; not a filter or group_by key in the other operations (the forecast API reference
  lists it as a filter key, but the service rejects it)
- SERVICE: AWS service (e.g., Amazon DynamoDB)
- TAG: Cost allocation tag — valid as a GroupBy Type (`[{"Type":"TAG","Key":"<tag_key>"}]`) and inside filter `Tags` leaves, but NOT a getDimensionValues dimension in any context; to list a tag key's values use operation=getTagsOrValues (with tag_key).
- TENANCY: EC2 tenancy. Exact, case-sensitive values: Shared, Dedicated (Dedicated Instance),
  Host (Dedicated Host)
- USAGE_TYPE: Usage type (e.g., DataTransfer-In-Bytes)
- USAGE_TYPE_GROUP: Group of related usage types (e.g., EC2: Running Hours). Filter only: not a
  group_by key
- RECORD_TYPE: Charge type. Values are case-sensitive: Usage, DiscountedUsage (RI-covered
  usage), SavingsPlanCoveredUsage, SavingsPlanNegation, SavingsPlanRecurringFee,
  SavingsPlanUpfrontFee, Recurring (RI recurring fee), Upfront (RI upfront fee), Support, Other
  (out-of-cycle and non-RI subscription charges), Tax, Credit, Refund, and these discounts by full
  name: Bundled Discount, Distributor Discount, Enterprise Discount Program Discount, Marketplace
  Discount, Private Rate Card Discount, RI Volume Discount, Solution Provider Program Discount.
  These differ from the CUR and Cost Categories line-item types: Cost Explorer reports RIFee as
  Recurring, so a RIFee filter matches nothing, and reports most CUR Fee rows as Upfront, Other or
  Support, so a Fee filter misses them (use Upfront for RI upfront fees, Other for other
  subscription fees). Any other CUR line-item type, such as a Fee with no subscription that is not
  a support charge, passes through unchanged. Call getDimensionValues with RECORD_TYPE for the
  values present in the account.

BILLING VIEW SUPPORT:
billing_view_arn is accepted by getCostAndUsage, getCostAndUsageWithResources, getDimensionValues
(COST_AND_USAGE context only), getCostForecast, getUsageForecast, getTagsOrValues and
getCostCategories, and scopes the query to that billing view. If not provided, the query defaults
to the account's primary billing view. getSavingsPlansUtilization (the AWS API has no billing view
parameter) and getDimensionValues with context RESERVATIONS or SAVINGS_PLANS (AWS does not apply
the view there) do not accept billing_view_arn; setting it returns a validation_error. You can use
the list-billing-views and get-billing-view tools upon request to discover available billing views
and their ARNs.

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
  Use for showback/chargeback reporting in billing transfer scenarios."""
)


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
            (getCostAndUsage and getCostAndUsageWithResources only)
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
        billing_view_arn: Optional ARN of a billing view to scope the query. Rejected for
            getSavingsPlansUtilization, whose API has no billing view parameter, and for
            getDimensionValues with context RESERVATIONS or SAVINGS_PLANS, where AWS does not
            apply the view
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

        if group_by and operation in OPERATIONS_WITHOUT_GROUP_BY:
            return format_response(
                'error',
                {
                    'message': (
                        f'group_by is not supported for {operation}: its AWS API has no '
                        'GroupBy, so the result would not be grouped. group_by works only '
                        'with getCostAndUsage and getCostAndUsageWithResources.'
                    )
                },
                error_type='validation_error',
                operation=operation,
                service=COST_EXPLORER_SERVICE_NAME,
                hint=(
                    'Remove group_by. For cost per dimension value, use getCostAndUsage with '
                    'group_by; for a forecast or utilization per value (e.g. per Region), call '
                    'once per value with that value in filter. Do **NOT** retry with group_by.'
                ),
            )

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

            # In the RESERVATIONS and SAVINGS_PLANS contexts AWS accepts BillingViewArn but does
            # not apply the view: the values are the same as without it, including accounts
            # outside the view, and a well-formed ARN that names no view is not rejected. Refuse
            # it rather than return unscoped values the caller believes are scoped to their view.
            # Match the exact spelling: AWS rejects any other case of context on its own.
            if billing_view_arn and context in ('RESERVATIONS', 'SAVINGS_PLANS'):
                return format_response(
                    'error',
                    {
                        'message': (
                            'billing_view_arn is not supported for getDimensionValues with '
                            f'context={context}: AWS does not apply the billing view in this '
                            "context, so the values cover the calling account's own data (its "
                            'primary billing view), including accounts outside the view.'
                        )
                    },
                    error_type='validation_error',
                    operation=operation,
                    service=COST_EXPLORER_SERVICE_NAME,
                    hint=(
                        'Remove billing_view_arn to list the values for the calling '
                        "account's own data, and say that they are not scoped to the requested "
                        'view: they can include accounts the view does not cover. Do **NOT** '
                        'retry with the same billing_view_arn.'
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
            # GetSavingsPlansUtilization has no BillingViewArn, so the ARN cannot be sent.
            # Refuse it: dropping it would return primary-view data the caller believes is
            # scoped to their view.
            if billing_view_arn:
                return format_response(
                    'error',
                    {
                        'message': (
                            'billing_view_arn is not supported for getSavingsPlansUtilization: '
                            'the GetSavingsPlansUtilization API has no billing view parameter, '
                            "so it always reports the calling account's own data (its primary "
                            'billing view).'
                        )
                    },
                    error_type='validation_error',
                    operation=operation,
                    service=COST_EXPLORER_SERVICE_NAME,
                    hint=(
                        'Remove billing_view_arn to get Savings Plans utilization for the calling '
                        "account's own data, and say that it is not scoped to the requested view: "
                        'it can cover more accounts than the view (the whole organization when '
                        'called from a management account). Do **NOT** retry with the same '
                        'billing_view_arn.'
                    ),
                )

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
