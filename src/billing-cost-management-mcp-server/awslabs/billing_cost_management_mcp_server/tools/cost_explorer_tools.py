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

import json
from ..utilities.aws_service_base import (
    create_aws_client,
    format_response,
    handle_aws_error,
    parse_json,
)
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

# Arguments every operation but getSavingsPlansUtilization sends.
_COMMON = frozenset({'start_date', 'end_date', 'filter', 'billing_view_arn'})
_PAGED = frozenset({'max_items', 'next_token'})
_COST_AND_USAGE = _COMMON | _PAGED | {'granularity', 'metrics', 'group_by'}
_FORECAST = _COMMON | {'metric', 'granularity', 'prediction_interval_level'}
_DIMENSION_VALUES = _COMMON | _PAGED | {'dimension', 'dimension_key', 'context', 'search_string'}

# The arguments each operation sends to its AWS API. Any other argument a caller sets is
# rejected (except UNCHECKED_ARGUMENTS): the handler would drop it, and the result would read as if it had applied (a
# search_string that did not narrow, a metric that was not used, a context that was ignored).
OPERATION_ARGUMENTS: Dict[str, frozenset] = {
    'getCostAndUsage': _COST_AND_USAGE,
    'getCostAndUsageWithResources': _COST_AND_USAGE,
    'getDimensionValues': _DIMENSION_VALUES,
    'getCostForecast': _FORECAST,
    'getUsageForecast': _FORECAST,
    'getTagsOrValues': _COMMON | _PAGED | {'tag_key', 'search_string'},
    'getCostCategories': _COMMON | _PAGED | {'cost_category_name', 'search_string'},
    'getSavingsPlansUtilization': frozenset({'start_date', 'end_date', 'granularity', 'filter'}),
}

# Arguments that are not checked: an operation that does not list them ignores them, as its
# result has no periods or prediction interval that could be misread.
UNCHECKED_ARGUMENTS = frozenset({'granularity', 'prediction_interval_level'})

_VALUE_LISTS = 'getDimensionValues, getTagsOrValues and getCostCategories'
_PAGINATED = (
    'getCostAndUsage, getCostAndUsageWithResources, getDimensionValues, getTagsOrValues and '
    'getCostCategories'
)
_PAGINATION = (
    'its public AWS API takes no page size or page token, so the whole result comes back in one '
    f'response. max_items and next_token work only with {_PAGINATED}.'
)

# Why an operation that does not list an argument would drop it, and what to use instead.
UNUSED_ARGUMENT_REASONS: Dict[str, str] = {
    'group_by': (
        'its public AWS API has no GroupBy, so the result would not be grouped. group_by works only '
        'with getCostAndUsage and getCostAndUsageWithResources: use getCostAndUsage with '
        "group_by for cost per dimension value, getDimensionValues to list a dimension's "
        'values, or one forecast or utilization call per value with that value in filter.'
    ),
    'search_string': (
        f'it searches the value lists of {_VALUE_LISTS} only, so the result would not be '
        'narrowed. To narrow costs, put exact values in filter; to find those values, call one '
        'of those operations with search_string.'
    ),
    'tag_key': (
        'it selects the tag key whose values getTagsOrValues lists. To list them, use '
        'operation=getTagsOrValues with tag_key; to narrow costs to a tag, use a Tags leaf in '
        'filter.'
    ),
    'cost_category_name': (
        'it selects the cost category whose values getCostCategories lists. To list them, use '
        'operation=getCostCategories with cost_category_name; to narrow costs to a category, '
        'use a CostCategories leaf in filter.'
    ),
    'dimension': (
        'it names the dimension whose values getDimensionValues lists. To split costs by a '
        'dimension, use getCostAndUsage with group_by; to narrow them, use a Dimensions leaf '
        'in filter (a tag, cost category or PRODUCT_ATTRIBUTE key takes a Tags, CostCategories '
        'or ProductAttributes leaf, and the matching group_by Type); to list its values, use '
        'operation=getDimensionValues.'
    ),
    'dimension_key': (
        'it selects the PRODUCT_ATTRIBUTE key whose values getDimensionValues lists. To list '
        'them, use operation=getDimensionValues with dimension=PRODUCT_ATTRIBUTE and '
        'dimension_key; to split costs by it, use getCostAndUsage with group_by Type '
        'PRODUCT_ATTRIBUTE; to narrow them, use a ProductAttributes leaf in filter.'
    ),
    'context': (
        'it selects the getDimensionValues context (COST_AND_USAGE, RESERVATIONS or '
        'SAVINGS_PLANS). To list values in a context, use operation=getDimensionValues with '
        'dimension and context.'
    ),
    'max_items': _PAGINATION,
    'next_token': _PAGINATION,
    'metric': (
        'it is the single metric of getCostForecast and getUsageForecast. getCostAndUsage and '
        'getCostAndUsageWithResources take metrics instead (e.g. ["AmortizedCost"]).'
    ),
    'metrics': (
        'it is the metric list of getCostAndUsage and getCostAndUsageWithResources. '
        'getCostForecast and getUsageForecast take metric instead (e.g. AMORTIZED_COST for '
        'getCostForecast, USAGE_QUANTITY for getUsageForecast).'
    ),
    'billing_view_arn': (
        "its public AWS API has no billing view parameter, so it reports the calling account's own "
        'data (its primary billing view). Without billing_view_arn, say that the result is '
        'not scoped to the requested view: it can cover more accounts than the view (the '
        'whole organization when called from a management account).'
    ),
}

UNUSED_ARGUMENT_HINT = (
    'Remove every argument the message names; the message says which operation or argument '
    'does what was asked. Do **NOT** retry with those arguments.'
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
- UnblendedCost records Savings Plans upfront fees (RECORD_TYPE SavingsPlanUpfrontFee) and
  Reserved Instance upfront fees (Upfront) in the month they are charged, so a month with a
  purchase shows a one-time increase. AmortizedCost spreads upfront and recurring commitment fees
  over the commitment term
- NetUnblendedCost and NetAmortizedCost fold Private Rate Card, EDP and Bundled discounts into
  the usage line items, so those discount record types read $0 under these metrics. Under
  UnblendedCost and AmortizedCost the discounts appear as their own negative record types, and
  the totals match the net totals, so AmortizedCost minus NetAmortizedCost is not the discount
  amount
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
- Each operation takes only the arguments in its Required and Optional lists below; any other
  argument is rejected with a validation_error rather than ignored (e.g. search_string on
  getCostAndUsage, tag_key on getCostCategories, metric on getCostAndUsage). The exceptions are
  granularity and prediction_interval_level, which an operation that does not list them ignores

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

PAGINATION (max_items, next_token: getCostAndUsage, getCostAndUsageWithResources, getDimensionValues, getTagsOrValues, getCostCategories only; the other operations reject both):
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
  than one full billing cycle. That returns DataUnavailableException, and so does a forecast
  filter that matches no past costs.

FILTER EXPRESSION GRAMMAR (the `filter` argument is an object or a JSON string with double quotes; omit it for no filter, as an empty one is rejected):
The top-level object has exactly ONE of these keys:
- Leaf keys: `Dimensions`, `Tags`, `CostCategories`, `ProductAttributes`
- Logical keys: `And` and `Or` (each takes an array of at least 2 expressions), `Not` (takes
  one expression)

Leaf shape:
`{"<Dimensions|Tags|CostCategories|ProductAttributes>": {"Key": "...", "Values": [...], "MatchOptions": [...]}}`

MatchOptions accepted by getCostAndUsage and getCostAndUsageWithResources:
- Dimensions:     EQUALS, CASE_SENSITIVE
- Tags:           EQUALS, ABSENT, CASE_SENSITIVE
- CostCategories: EQUALS, ABSENT, CASE_SENSITIVE
- ProductAttributes: EQUALS, ABSENT, CASE_SENSITIVE
The default is EQUALS and CASE_SENSITIVE, so MatchOptions can usually be omitted. If you pass
MatchOptions, include EQUALS (or ABSENT): `["CASE_SENSITIVE"]` alone is rejected. ABSENT takes
no case option: `["ABSENT", "CASE_SENSITIVE"]` is rejected. Not every operation supports
MatchOptions.

The MatchOption enum also contains `CASE_INSENSITIVE`, `STARTS_WITH`, `ENDS_WITH`, `CONTAINS`,
and `GREATER_THAN_OR_EQUAL`. These apply to Cost Category rules and anomaly subscriptions, not
to these filters.

Values per leaf type:
- Dimensions: `Values` is required and must not be empty. `[""]` (one empty string) is not
  empty: in getCostAndUsage it matches costs with no value for the dimension (see
  REPORTING $0).
- Tags / CostCategories / ProductAttributes: `Values` is required, except with `ABSENT`.
  `ABSENT` matches costs where the key is not present, so there is no value to compare
  against: omit `Values` entirely (an empty `Values` list is rejected too).

Tags leaves in getCostAndUsage, getCostAndUsageWithResources, getDimensionValues,
getTagsOrValues and getCostCategories filters:
- `Key` is the tag key as getTagsOrValues lists it, with no `user:` prefix even where billing
  exports show one: `Environment`, not `user:Environment` (which matches nothing, with no
  error). The forecasts accept either form. Tags that AWS applies itself keep
  their `aws:` prefix (`aws:createdBy`). Keys and values are case-sensitive, and there is no
  case-insensitive option.
- A TAG group_by labels each group `<key>$<value>` (e.g. `Environment$Dev`), and `<key>$` for
  costs without the key or with an empty value. The label is not a filter value: filter on
  `Dev`, and use `ABSENT` for the `<key>$` group. `"Values": [""]` matches the same costs as
  `ABSENT` (unlike an empty list, it is accepted).
- getCostAndUsage only: `{"Tags": {"Key": "", "Values": []}}` (empty key, empty list) matches
  costs that carry no activated cost allocation tag (user-defined or AWS-generated), as does
  `{"Tags": {"MatchOptions": ["ABSENT"]}}` with no Key. An empty key with any value, or with
  Values omitted, is rejected, and getCostAndUsageWithResources, getDimensionValues,
  getTagsOrValues and getCostCategories reject an empty key.
- A wrong key is not an error. With `Values` it matches nothing ($0, or an empty list); with
  `ABSENT` it matches every cost, since no cost carries that key. Copy the key from
  getTagsOrValues.

ProductAttributes leaves (getCostAndUsage, getCostAndUsageWithResources and getDimensionValues
filters; the forecasts reject them):
- They filter by product attributes. Amazon Bedrock is the only supported service; its
  attribute names (the leaf's `Key`) are `provider`, `model`, `inferenceType` and `feature`.
  Cost Explorer returns this data only from 2026-09-01, in every account: a period that
  starts earlier returns DataUnavailableException, even if most of it is later.
- Keys and values are case-sensitive, with no case-insensitive or partial match. List the keys
  with getDimensionValues dimension=PRODUCT_ATTRIBUTE, and a key's values by adding dimension_key
  (its search_string does match case-insensitively and partially).
- A wrong key or value is not an error. With `Values` it matches nothing ($0). `ABSENT` (or
  `"Values": [""]`) matches the supported services' costs with no value for the key, so with a
  wrong key it matches every Bedrock cost.
- Costs of other services never match a ProductAttributes leaf, even under `Not`:
  `{"Not": <ProductAttributes leaf>}` returns only the Bedrock costs the leaf does not match.
- A PRODUCT_ATTRIBUTE group_by (`[{"Type": "PRODUCT_ATTRIBUTE", "Key": "model"}]`) covers only
  the supported services' costs, so its groups do not add up to the account total. Each group is
  labelled `<key>$<value>` (e.g. `model$Claude Sonnet 5`), and `<key>$` for costs with no value.
  Filter on the value, not the label.
- If the filter has a SERVICE leaf anywhere, it must keep the result to Bedrock services, or
  the request is rejected (ValidationException). Under `And`, one SERVICE leaf naming only
  Bedrock services is enough. Under `Or`, every branch must be scoped that way, so
  `{"Or": [<ProductAttributes leaf>, <SERVICE leaf>]}` is rejected. A SERVICE leaf under `Not`
  never counts. getDimensionValues rejects a ProductAttributes filter with no SERVICE filter:
  pair it with one in an `And`. Bedrock costs
  appear under several SERVICE names, which differ by account (e.g. `Amazon Bedrock`,
  `Amazon Bedrock Service`, and Marketplace names such as `Claude Opus 5.5 (Amazon Bedrock
  Edition)`), so one name can return $0 while the others carry the cost. List them with
  getDimensionValues dimension=SERVICE, search_string=Bedrock. Elsewhere, omit SERVICE to
  include all of them.

Correct filter examples:
- `{"Dimensions": {"Key": "SERVICE", "Values": ["Amazon Relational Database Service"]}}`
- `{"Tags": {"Key": "env", "Values": ["prod"]}}`
- `{"Tags": {"Key": "team", "MatchOptions": ["ABSENT"]}}`
- `{"ProductAttributes": {"Key": "model", "Values": ["Claude Sonnet 5"]}}`
- `{"And": [{"Dimensions": {"Key": "SERVICE", "Values": ["Amazon Elastic Compute Cloud - Compute"]}}, {"Dimensions": {"Key": "REGION", "Values": ["us-east-1"]}}]}`

Limits by operation (a filter outside them returns ValidationException):
- Every operation: at most 6,000 values in total, counted across all leaves of the filter.
- getCostAndUsage, getCostAndUsageWithResources: `And`, `Or` and `Not` nest up to 4 levels
  deep; a 5th is rejected.
- getDimensionValues (default COST_AND_USAGE context), getTagsOrValues and getCostCategories:
  `And` of leaves only (an `And` inside it is rejected); `Or` and `Not` are rejected.
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
   Optional: start_date, end_date, context, search_string, filter, max_items, next_token, billing_view_arn, dimension_key
   Defaults: If start_date is omitted, the tool uses 30 days before today; if end_date is omitted, it uses today (exclusive, so today is not included).
   Example: {"operation": "getDimensionValues", "dimension": "SERVICE", "start_date": "__PREV_MONTH_START__", "end_date": "__MONTH_START__"}
   Example (values of a product attribute key): {"operation": "getDimensionValues", "dimension": "PRODUCT_ATTRIBUTE", "dimension_key": "model", "start_date": "__PREV_MONTH_START__", "end_date": "__MONTH_START__"}
   Returns: List of values for specified dimension (see PAGINATION)
   Notes: Each context accepts its own dimensions. COST_AND_USAGE (the default) takes the DIMENSION REFERENCE keys below except SCOPE and TAG; RESOURCE_ID needs a window within the last 14 days. RESERVATIONS takes only AZ, INSTANCE_TYPE, INSTANCE_TYPE_FAMILY, LINKED_ACCOUNT, PLATFORM, REGION, SCOPE, SERVICE, TENANCY. SAVINGS_PLANS takes only INSTANCE_TYPE_FAMILY, LINKED_ACCOUNT, PAYMENT_OPTION, REGION, SAVINGS_PLAN_ARN, SAVINGS_PLANS_TYPE. TAG is not a dimension in any context: to list a cost-allocation tag key's values use operation=getTagsOrValues (with tag_key); passing dimension=TAG is rejected.

4. getCostForecast - Future cost projections
   Required: operation="getCostForecast", metric
   Optional: granularity, start_date, end_date, filter, prediction_interval_level, billing_view_arn
   Defaults: If granularity is omitted, the tool uses DAILY.
   Example 1 (default window): {"operation": "getCostForecast", "metric": "UNBLENDED_COST", "granularity": "MONTHLY"}
   Example 2 (next three months): {"operation": "getCostForecast", "metric": "UNBLENDED_COST", "granularity": "MONTHLY", "start_date": "__NEXT_MONTH_START__", "end_date": "__FOUR_MONTHS_AHEAD_START__"}
   Notes: `metric` must be ALL CAPS and one of UNBLENDED_COST, BLENDED_COST, AMORTIZED_COST, NET_UNBLENDED_COST, NET_AMORTIZED_COST (not the getCostAndUsage spelling `UnblendedCost`). `start_date` defaults to tomorrow and `end_date` to 90 days after `start_date`; a `start_date` you pass must be today or later. The horizon is up to 3 months (DAILY) or 18 months (MONTHLY). HOURLY is not supported. With MONTHLY granularity each period is a whole calendar month: Cost Explorer moves a `start_date` that isn't a 1st back to the 1st, and an `end_date` that isn't a 1st forward to the next 1st. So a MONTHLY forecast that starts this month on any day but the 1st (as the default start, tomorrow, does unless tomorrow is a 1st) returns the whole current month, and that period and `Total` include its actual costs to date. The response's `period_note` says when the period was widened. For part of a month, such as the rest of this month, use DAILY and sum the days. In `filter`, LINKED_ACCOUNT values must be 12-digit account IDs (not account names), and RESOURCE_ID is not allowed. Filter values must match exactly, including case: MatchOptions such as STARTS_WITH, CONTAINS or CASE_INSENSITIVE are accepted but not applied. A filter that matches no past costs returns the same DataUnavailableException as too little history, so check the values with getDimensionValues before reporting that no forecast is possible. Forecasts made in the first days of a month are less accurate: some services bill a large amount at once on or near the 1st, which skews the early-month average daily cost; accuracy improves as the month goes on. Volatile spend makes forecasts less accurate. Check the prediction interval, and compare the forecast with the last few months of actual cost before quoting it. If large one-time charges (Marketplace contracts, upfront fees) drive the volatility, forecast BILLING_ENTITY=AWS separately and add those charges from recent actuals.
   Returns: Cost forecast for specified time period and granularity

5. getUsageForecast - Future usage projections
   Required: operation="getUsageForecast", metric, filter
   Optional: granularity, start_date, end_date, prediction_interval_level, billing_view_arn
   Defaults: If granularity is omitted, the tool uses DAILY.
   Example 1: {"operation": "getUsageForecast", "metric": "USAGE_QUANTITY", "granularity": "MONTHLY", "start_date": "__NEXT_MONTH_START__", "end_date": "__FOUR_MONTHS_AHEAD_START__", "filter": "{\\"Dimensions\\": {\\"Key\\": \\"USAGE_TYPE_GROUP\\", \\"Values\\": [\\"EC2: Running Hours\\"]}}"}
   Example 2: {"operation": "getUsageForecast", "metric": "USAGE_QUANTITY", "granularity": "MONTHLY", "filter": "{\\"And\\": [{\\"Dimensions\\": {\\"Key\\": \\"SERVICE\\", \\"Values\\": [\\"Amazon Elastic Compute Cloud - Compute\\"]}}, {\\"Dimensions\\": {\\"Key\\": \\"USAGE_TYPE\\", \\"Values\\": [\\"BoxUsage:p4de.24xlarge\\"]}}]}"}
   Example 3 (one Region): {"operation": "getUsageForecast", "metric": "USAGE_QUANTITY", "granularity": "MONTHLY", "filter": "{\\"And\\": [{\\"Dimensions\\": {\\"Key\\": \\"USAGE_TYPE_GROUP\\", \\"Values\\": [\\"EC2: Running Hours\\"]}}, {\\"Dimensions\\": {\\"Key\\": \\"REGION\\", \\"Values\\": [\\"us-east-1\\"]}}]}"}
   Notes: Valid values for metric is: USAGE_QUANTITY, NORMALIZED_USAGE_AMOUNT. Valid values for granularity is: DAILY, MONTHLY. Filter is REQUIRED and must specify USAGE_TYPE or USAGE_TYPE_GROUP to define what usage units to forecast. Dates default and are limited as for getCostForecast, and MONTHLY periods are whole calendar months as described there. Filter values match as for getCostForecast: a filter that matches no past usage returns the same DataUnavailableException.
   Returns: Usage forecast for specified time period and granularity

6. getTagsOrValues - Available cost allocation tags or values
   Required: operation="getTagsOrValues"
   Optional: start_date, end_date, tag_key, search_string, filter, max_items, next_token, billing_view_arn
   Defaults: If start_date is omitted, the tool uses 30 days before today; if end_date is omitted, it uses today (exclusive, so today is not included).
   Example 1: {"operation": "getTagsOrValues"}
   Example 2: {"operation": "getTagsOrValues", "tag_key": "Environment"}
   Returns: List of available cost allocation tags (see PAGINATION). If tag values for a particular key are needed, pass the tag key as a parameter. The tag key list holds at most 5,000 keys in total. A filter keeps only the keys (or values) found on costs that match it, e.g. the tags used in one Region.

7. getCostCategories - Available cost categories or values inside a category
   Required: operation="getCostCategories"
   Optional: start_date, end_date, cost_category_name, search_string, filter, max_items, next_token, billing_view_arn
   Defaults: If start_date is omitted, the tool uses 30 days before today; if end_date is omitted, it uses today (exclusive, so today is not included).
   Example 1 (list category names): {"operation": "getCostCategories", "start_date": "__SIX_MONTHS_AGO_START__", "end_date": "__MONTH_START__"}
   Example 2 (list values inside a category): {"operation": "getCostCategories", "cost_category_name": "CostCenters", "start_date": "__SIX_MONTHS_AGO_START__", "end_date": "__MONTH_START__"}
   Notes: Without cost_category_name the response contains CostCategoryNames. With cost_category_name set the response contains CostCategoryValues for that category. The category name list holds at most 5,000 names in total. A filter keeps only the names (or values) found on costs that match it. See PAGINATION.

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
- PAYER_ACCOUNT: The 12-digit ID of the management (payer) account whose bill a cost is on.
  Not available in every account; if it is rejected, use LINKED_ACCOUNT
- PRODUCT_ATTRIBUTE: Product attributes of supported services (Amazon Bedrock). Not a
  `Dimensions` key: filter with a `ProductAttributes` leaf and group with Type
  PRODUCT_ATTRIBUTE (see FILTER EXPRESSION GRAMMAR). As a getDimensionValues dimension
  (COST_AND_USAGE context only) it lists the attribute names, or with dimension_key that
  attribute's values (`""` stands for costs with no value; a wrong name returns only `""`,
  not an error). dimension_key with any other dimension is rejected
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


def _tags_leaves(expression: Any) -> List[Dict[str, Any]]:
    """Return every Tags leaf in a filter expression, walking And, Or and Not."""
    if not isinstance(expression, dict):
        return []
    leaves = [expression['Tags']] if isinstance(expression.get('Tags'), dict) else []
    for key in ('And', 'Or'):
        children = expression.get(key)
        if isinstance(children, list):
            for child in children:
                leaves.extend(_tags_leaves(child))
    leaves.extend(_tags_leaves(expression.get('Not')))
    return leaves


def _tag_leaf_hints(key: str, values: List[Any], absent: bool) -> List[str]:
    """Return the hints for one Tags leaf whose key or values cannot match."""
    hints = []
    bare = key
    if key.lower().startswith('user:') and len(key) > len('user:'):
        bare = key[len('user:') :]
        hints.append(
            f"Tags key '{key}' has a user: prefix. This filter takes tag keys without it, so "
            f'this key matches no tagged cost: Values match nothing, and ABSENT matches every '
            f"cost. Use '{bare}', unless getTagsOrValues lists the key with the prefix."
        )
    if '$' in bare.strip('$'):
        label_key, label_value = bare.split('$', 1)
        fix = (
            f"Use Key '{label_key}'."
            if absent
            else f"Use Key '{label_key}' with Values ['{label_value}']."
        )
        hints.append(
            f"Tags key '{bare}' looks like a TAG group_by label (<key>$<value>), not a tag "
            f'key. {fix}'
        )
    for value in values:
        if not isinstance(value, str) or not bare:
            continue
        label_of = next((k for k in (key, bare) if value.startswith(f'{k}$')), None)
        if label_of is None:
            continue
        label_value = value[len(label_of) + 1 :]
        fix = (
            f"Filter on '{label_value}' instead."
            if label_value
            else f'Use ABSENT for the {bare}$ group (costs without the key).'
        )
        hints.append(
            f"Tags value '{value}' is a TAG group_by label, not a tag value, so it matches "
            f'nothing. {fix}'
        )
    return hints


def _tag_filter_hint(filter: Optional[Union[str, Dict[str, Any]]]) -> Optional[str]:
    """Return a hint for a Tags filter that Cost Explorer accepts but that cannot match.

    getCostAndUsage, getCostAndUsageWithResources, getDimensionValues, getTagsOrValues and
    getCostCategories add the `user:` prefix to user-defined tag keys themselves, so a
    `user:` key matches no tagged cost, and a TAG group_by label (`key$value`) is not a key
    or value. With no error, Values then match nothing and ABSENT matches every cost.
    """
    try:
        if isinstance(filter, str):
            filter = json.loads(filter)
        hints: List[str] = []
        for leaf in _tags_leaves(filter):
            key, values = leaf.get('Key'), leaf.get('Values')
            options = leaf.get('MatchOptions')
            absent = isinstance(options, list) and 'ABSENT' in options
            if isinstance(key, str):
                values = values if isinstance(values, list) else []
                for hint in _tag_leaf_hints(key, values, absent):
                    if hint not in hints:
                        hints.append(hint)
    except (ValueError, RecursionError):
        # A filter that does not parse is the API call's to reject, not the hint's.
        return None
    return ' '.join(hints) or None


def _with_hint(result: Dict[str, Any], hint: Optional[str]) -> Dict[str, Any]:
    """Add the hint to a successful response.

    Error responses keep the recovery hint the error mapping adds.
    """
    if hint and result.get('status') == 'success' and 'hint' not in result:
        result['hint'] = hint
    return result


def _is_set(name: str, value: Any) -> bool:
    """Return whether the caller set an argument.

    None and '' are not set: no handler sends them. An empty JSON group_by or metrics ('[]',
    'null') is not set either, as getCostAndUsage reads it as no grouping and the default
    metric. A value that is not JSON is set, so it gets the not-supported error.
    """
    if value is None or value == '':
        return False
    if name in ('group_by', 'metrics'):
        try:
            return bool(parse_json(value, name))
        except (ValueError, TypeError):
            return True
    return True


def _unused_arguments(operation: str, arguments: Dict[str, Any]) -> List[str]:
    """Return the arguments the caller set that the operation does not send, in signature order."""
    accepted = OPERATION_ARGUMENTS.get(operation)
    if accepted is None:
        return []
    return [
        name
        for name, value in arguments.items()
        if name not in accepted and name not in UNCHECKED_ARGUMENTS and _is_set(name, value)
    ]


def _unused_arguments_error(operation: str, unused: List[str]) -> Dict[str, Any]:
    """Return the validation_error for arguments the operation would drop."""
    message = ' '.join(
        f'{name} is not supported for {operation}: {UNUSED_ARGUMENT_REASONS[name]}'
        for name in unused
    )
    return format_response(
        'error',
        {'message': message},
        error_type='validation_error',
        operation=operation,
        service=COST_EXPLORER_SERVICE_NAME,
        hint=UNUSED_ARGUMENT_HINT,
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
    dimension_key: Optional[str] = None,
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
        dimension_key: Only for getDimensionValues with dimension PRODUCT_ATTRIBUTE. Without
            it, the call lists the product attribute names (`provider`, `model`, ...). With one
            of those names, such as `model`, it lists that attribute's values (the model names).
            Names are case-sensitive.

    Returns:
        Response from the operation handler
    """
    # Every argument but ctx and operation, captured before any local is assigned, so a new
    # parameter is checked against OPERATION_ARGUMENTS without being listed here.
    arguments = {
        name: value for name, value in locals().items() if name not in ('ctx', 'operation')
    }
    await ctx.info(f'Cost Explorer operation: {operation}')

    # Reject an argument the operation would drop, before any AWS work.
    unused = _unused_arguments(operation, arguments)
    if unused:
        return _unused_arguments_error(operation, unused)

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
        # A Tags filter that cannot match is not an error, so say so in the response.
        tag_hint = _tag_filter_hint(filter)
        await ctx.info(f'Routing to operation: {operation}')

        if operation == 'getCostAndUsage':
            return _with_hint(
                await get_cost_and_usage(
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
                ),
                tag_hint,
            )

        elif operation == 'getCostAndUsageWithResources':
            return _with_hint(
                await get_cost_and_usage_with_resources(
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
                ),
                tag_hint,
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

            return _with_hint(
                await get_dimension_values(
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
                    dimension_key=dimension_key,
                ),
                tag_hint,
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
            return _with_hint(
                await get_tags(
                    ctx,
                    ce_client,
                    start_date,
                    end_date,
                    search_string,
                    tag_key,
                    filter,
                    next_token,
                    max_items,
                    billing_view_arn,
                ),
                tag_hint,
            )

        elif operation == 'getCostCategories':
            # When `cost_category_name` is provided, the same AWS API
            # (GetCostCategories) returns the values inside that category
            # instead of the list of category names.
            return _with_hint(
                await get_cost_categories(
                    ctx,
                    ce_client,
                    start_date,
                    end_date,
                    search_string,
                    cost_category_name,
                    filter,
                    next_token,
                    max_items,
                    billing_view_arn,
                ),
                tag_hint,
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
