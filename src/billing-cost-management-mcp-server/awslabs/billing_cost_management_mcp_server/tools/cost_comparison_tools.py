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

"""AWS Cost Comparison tools for the AWS Billing and Cost Management MCP server.

Updated to use shared utility functions.
"""

import calendar
import re
from ..utilities.aws_service_base import (
    PageSpec,
    create_aws_client,
    first_page_fields,
    format_response,
    handle_aws_error,
    paginate_aws_items,
    parse_filter,
    parse_json,
    with_pagination,
)
from ..utilities.constants import PAGINATION_LIMIT_TEXT
from datetime import date, datetime, timezone
from fastmcp import Context, FastMCP
from typing import Any, Dict, Optional, Tuple


cost_comparison_server = FastMCP(
    name='cost-comparison-tools', instructions='Tools for working with AWS Cost Comparison API'
)

GET_COST_AND_USAGE_COMPARISONS = PageSpec(
    result_key='CostAndUsageComparisons',
    token_param='NextPageToken',
    token_key_in_response='NextPageToken',
    page_max=2000,
    page_size_param='MaxResults',
)

GET_COST_COMPARISON_DRIVERS = PageSpec(
    result_key='CostComparisonDrivers',
    token_param='NextPageToken',
    token_key_in_response='NextPageToken',
    page_max=10,
    page_size_param='MaxResults',
)

# The request rules the Cost Explorer comparison APIs enforce, checked here so that a
# request CE would reject fails without an AWS call and names the rule it broke.
_DATE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}Z)?$')
MAX_HISTORY_MONTHS = 38
DEFAULT_HISTORY_MONTHS = 13
COMPARISON_METRICS = (
    'AmortizedCost',
    'BlendedCost',
    'NetAmortizedCost',
    'NetUnblendedCost',
    'NormalizedUsageAmount',
    'UnblendedCost',
    'UsageQuantity',
)
DRIVER_METRICS = tuple(m for m in COMPARISON_METRICS if 'Cost' in m)
_OPERATION_METRICS = {
    'getCostAndUsageComparisons': COMPARISON_METRICS,
    'getCostComparisonDrivers': DRIVER_METRICS,
}
_WHOLE_MONTHS = (
    'cost-comparison needs whole calendar months: each period starts on the 1st of a month '
    'and ends on the 1st of the next month (for example 2026-08-01 to 2026-09-01). For other '
    'windows, use cost-explorer getCostAndUsage once per window.'
)
_MULTI_YEAR_HINT = (
    'A period starts more than 13 months ago. Cost Explorer keeps 13 months of cost history '
    'unless multi-year data at monthly granularity is enabled in Cost Management preferences '
    '(up to 38 months). Do not retry the same request: choose months within the last 13 '
    'months, or tell the user to enable multi-year data.'
)


def _utc_today() -> date:
    """Today's date in UTC, the clock Cost Explorer checks periods against."""
    return datetime.now(timezone.utc).date()


def _months_before(day: date, months: int) -> date:
    """``day`` minus ``months`` months, clamped to the month's last day (Java minusMonths)."""
    index = day.year * 12 + day.month - 1 - months
    year, month = divmod(index, 12)
    month += 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def _upper_snake(metric: str) -> str:
    """UnblendedCost -> UNBLENDED_COST, the alternative spelling CE also accepts."""
    return re.sub(r'(?<!^)(?=[A-Z])', '_', metric).upper()


def _parse_month(name: str, start: str, end: str) -> Tuple[date, date]:
    """Parse one period and require it to be exactly one calendar month."""
    for value in (start, end):
        if not isinstance(value, str) or not _DATE_PATTERN.match(value):
            raise ValueError(
                f'{name} period date {value!r} is not in YYYY-MM-DD format. {_WHOLE_MONTHS}'
            )
    try:
        first, last = date.fromisoformat(start[:10]), date.fromisoformat(end[:10])
    except ValueError:
        raise ValueError(
            f'{name} period {start} to {end} contains an invalid date. {_WHOLE_MONTHS}'
        ) from None
    next_month = _months_before(first, -1)
    if first.day != 1 or last != next_month:
        raise ValueError(f'{name} period {start} to {end} is not one whole month. {_WHOLE_MONTHS}')
    return first, last


def validate_comparison_request(
    operation: str,
    baseline_start_date: str,
    baseline_end_date: str,
    comparison_start_date: str,
    comparison_end_date: str,
    metric_for_comparison: str,
    today: Optional[date] = None,
) -> None:
    """Raise ValueError naming the rule if Cost Explorer would reject the request.

    Only rules the CE comparison backend enforces are checked, so nothing CE accepts is
    rejected: the baseline may be later than the comparison period, and a period 14 to
    38 months back is left to CE, since only CE knows whether multi-year data is enabled.

    Args:
        operation: getCostAndUsageComparisons or getCostComparisonDrivers
        baseline_start_date: Baseline period start
        baseline_end_date: Baseline period end (exclusive)
        comparison_start_date: Comparison period start
        comparison_end_date: Comparison period end (exclusive)
        metric_for_comparison: The metric to compare
        today: The current UTC date; defaults to the real one

    Raises:
        ValueError: The request breaks a rule; the message names it.
    """
    today = today or _utc_today()
    periods = {
        'baseline': _parse_month('baseline', baseline_start_date, baseline_end_date),
        'comparison': _parse_month('comparison', comparison_start_date, comparison_end_date),
    }
    if periods['baseline'] == periods['comparison']:
        raise ValueError(
            'baseline and comparison periods are the same month. Compare two different months.'
        )
    oldest = _months_before(today, MAX_HISTORY_MONTHS)
    for name, (first, last) in periods.items():
        if last > today:
            raise ValueError(
                f'{name} period {first} to {last} includes the current or a future month. '
                'cost-comparison compares completed months only; the latest you can use is '
                f'{_months_before(today.replace(day=1), 1)} to {today.replace(day=1)}. For '
                'month-to-date costs, use cost-explorer getCostAndUsage.'
            )
        if first < oldest:
            raise ValueError(
                f'{name} period {first} to {last} starts more than {MAX_HISTORY_MONTHS} months '
                f'ago (before {oldest}). Cost Explorer keeps at most {MAX_HISTORY_MONTHS} months '
                f'of history ({DEFAULT_HISTORY_MONTHS} unless multi-year data is enabled), so no '
                'setting makes this month available.'
            )
    allowed = _OPERATION_METRICS.get(operation, COMPARISON_METRICS)
    if metric_for_comparison not in allowed and metric_for_comparison not in {
        _upper_snake(m) for m in allowed
    }:
        raise ValueError(
            f'metric_for_comparison {metric_for_comparison!r} is not supported by {operation}. '
            f'Use one of (exact case): {", ".join(allowed)}.'
        )


# MatchOptions the comparison APIs honor. With any other option they still match each
# value exactly, so a value in another case or a prefix matches nothing: a silent $0
# (or everything under Not).
_FILTER_MATCH_OPTIONS = {
    'Dimensions': ('EQUALS', 'CASE_SENSITIVE'),
    'Tags': ('EQUALS', 'CASE_SENSITIVE', 'ABSENT'),
    'CostCategories': ('EQUALS', 'CASE_SENSITIVE', 'ABSENT'),
}
# A filter nested this deep fails in Cost Explorer: getCostComparisonDrivers returns
# InternalFailure at 97 levels and both operations reject 98 ("Value is too deeply
# nested"). Checked here also so the walk below cannot exhaust Python's recursion limit.
MAX_FILTER_DEPTH = 97


def validate_comparison_filter(expression: Any, depth: int = 0) -> None:
    """Raise ValueError for a filter the comparison APIs mishandle.

    Checks every nested And, Or and Not. Shapes botocore validates (wrong types,
    unknown keys) are left to botocore.

    Args:
        expression: The parsed filter Expression
        depth: Nesting depth of ``expression`` in the whole filter

    Raises:
        ValueError: The filter uses an ignored MatchOption, ABSENT with Values, a
            RESOURCE_ID key, or is nested too deeply.
    """
    if not isinstance(expression, dict):
        return
    if depth >= MAX_FILTER_DEPTH:
        raise ValueError(
            f'filter is nested {MAX_FILTER_DEPTH} or more And/Or/Not levels deep. Flatten '
            'it, for example by listing several Values in one Dimensions filter.'
        )
    for operator in ('And', 'Or'):
        children = expression.get(operator)
        for child in children if isinstance(children, list) else []:
            validate_comparison_filter(child, depth + 1)
    validate_comparison_filter(expression.get('Not'), depth + 1)
    for kind, allowed in _FILTER_MATCH_OPTIONS.items():
        values = expression.get(kind)
        if not isinstance(values, dict):
            continue
        if kind == 'Dimensions' and values.get('Key') == 'RESOURCE_ID':
            raise ValueError(
                'RESOURCE_ID is not supported in a cost-comparison filter. For per-resource '
                'costs, use cost-explorer getCostAndUsageWithResources (last 14 days only).'
            )
        options = values.get('MatchOptions')
        options = options if isinstance(options, list) else []
        unsupported = [str(o) for o in dict.fromkeys(options) if o not in allowed]
        if unsupported:
            raise ValueError(
                f'filter {kind} MatchOptions {", ".join(unsupported)} are not supported by '
                f'cost-comparison. Allowed here: {", ".join(allowed)}. With any other option '
                "Cost Explorer's comparison APIs still match each value exactly, so a value in "
                'another case or a partial value silently returns $0 or no drivers (or '
                'everything under Not). Drop the other options and pass exact values from '
                'cost-explorer getDimensionValues (or getTagsOrValues, getCostCategories).'
            )
        if 'ABSENT' in options and values.get('Values'):
            raise ValueError(
                f'filter {kind} with ABSENT ignores its Values: the comparison APIs return only '
                f'costs without the key {values.get("Key")!r}. Drop Values to match those '
                'costs, or use a separate filter (combined with Or) to match specific values.'
            )


def _starts_before_default_history(today: date, *starts: str) -> bool:
    """True if any period start is older than the default 13-month history."""
    cutoff = _months_before(today, DEFAULT_HISTORY_MONTHS)
    return any(date.fromisoformat(start[:10]) < cutoff for start in starts)


@cost_comparison_server.tool(
    name='cost-comparison',
    description="""Retrieves AWS cost comparisons between two one-month periods.

Do not use this tool except for comparing the costs of one month to the costs of another month. This tool should not be used for week-over-week or quarter-over-quarter (e.g., comparing Q2 vs. Q1) analysis.

USE THIS TOOL ONLY FOR:
- **Month-to-month cost variance analysis** (e.g., January vs February)
- **Root cause analysis** of cost changes between specific months
- **Detailed cost driver identification** (what exactly caused the cost change)
- **Service-level impact analysis** for month-over-month changes
- **Executive reporting** on monthly cost variances

STRICT LIMITATIONS (requests that break them fail with validation_error and no AWS call):
- ONLY compares exactly one month to another month
- Both periods must start on 1st day of month, end on 1st day of next month
- The two periods must be different months (either one may be the earlier)
- Only completed months: the current month and future months are rejected
- Cannot compare weeks, quarters, or custom periods: use cost-explorer getCostAndUsage
- DO NOT USE for general cost analysis or flexible time periods

This tool supports two main operations:
1. getCostAndUsageComparisons: Compare costs between two time periods with flexible grouping and filtering
2. getCostComparisonDrivers: Identify key factors driving cost changes between two time periods

Both operations require:
- BaselineTimePeriod: The reference period, usually the earlier one (must be exactly one month)
- ComparisonTimePeriod: The period compared against the baseline, usually the later one (must be exactly one month)
- MetricForComparison: The cost metric to compare (e.g., BlendedCost, UnblendedCost)

Supported metrics (exact case):
- AmortizedCost: Costs with upfront and recurring reservation fees spread across the period
- BlendedCost: Average cost of all usage throughout the billing period
- NetAmortizedCost: Amortized cost after discounts
- NetUnblendedCost: Unblended cost after discounts
- NormalizedUsageAmount: Normalized usage amount. getCostAndUsageComparisons only
- UnblendedCost: Actual costs incurred during the specified period
- UsageQuantity: Usage amounts in their respective units. getCostAndUsageComparisons only
getCostComparisonDrivers accepts only the five cost metrics.

You can group results by dimensions such as:
- SERVICE: AWS service (e.g., Amazon EC2, Amazon S3)
- LINKED_ACCOUNT: Member accounts in an organization
- REGION: AWS Region
- USAGE_TYPE: Type of usage (e.g., BoxUsage:t2.micro)
- INSTANCE_TYPE: EC2 instance type (e.g., t2.micro, m5.large)
- PLATFORM: Operating system (e.g., Linux/UNIX, Windows (Amazon VPC))
- TENANCY: Instance tenancy. Exact, case-sensitive values: Shared, Dedicated, Host
- RECORD_TYPE: Record type (e.g., Usage, Credit, Tax)
- LEGAL_ENTITY_NAME: AWS seller of record

Costs with no value for a grouped dimension come back under a placeholder such as NoRegion or
NoTenancy, including in each comparison's cost_and_usage_selector. The placeholder is not a
value: a filter on it matches nothing. To filter on those costs, pass the empty string:
`{"Dimensions": {"Key": "REGION", "Values": [""]}}`.

Note:
- Time periods must start and end on the first day of a month, with a duration of exactly one month
- The getCostComparisonDrivers operation automatically includes SERVICE and USAGE_TYPE dimensions
- Data is available for the last 13 months, or up to 38 months if multi-year data is enabled.
  A period starting more than 38 months ago is rejected locally. For 14-38 months back,
  Cost Explorer decides; if it reports the data unavailable, the error carries a hint
  about multi-year data

Filter (optional): a Cost Explorer Expression using And, Or, Not, Dimensions, Tags or
CostCategories. Keys and values match exactly, including case: get them from cost-explorer
getDimensionValues (or getTagsOrValues, getCostCategories). Rejected with validation_error and no
AWS call:
- MatchOptions other than EQUALS and CASE_SENSITIVE (the default), plus ABSENT for Tags and
  CostCategories. The comparison APIs ignore the others (CASE_INSENSITIVE, STARTS_WITH,
  ENDS_WITH, CONTAINS, ...) and still match exactly, so a value in another case or a partial
  value would silently return $0 or no drivers (or everything under Not)
- ABSENT together with Values: the comparison APIs drop the Values
- A RESOURCE_ID filter
- Nesting of 97 or more And/Or/Not levels, which fails in Cost Explorer
In group_by, Cost Explorer itself rejects RESOURCE_ID and USAGE_TYPE_GROUP.

Pagination (both operations):
- max_items: total number of comparisons or drivers returned. If it is omitted, the tool fetches every page for """
    + PAGINATION_LIMIT_TEXT
    + """, then returns a partial result. Pass it, or narrow group_by/filter, for comparisons that can be large (for
  example grouped by USAGE_TYPE or LINKED_ACCOUNT).
- If the result has complete_dataset: false, it is partial: call again with a larger
  max_items, continue with next_token, or say the result is partial.
- total_cost_and_usage comes from the first page only and isn't repeated on continuation
  calls.""",
)
async def cost_comparison(
    ctx: Context,
    operation: str,
    baseline_start_date: str,
    baseline_end_date: str,
    comparison_start_date: str,
    comparison_end_date: str,
    metric_for_comparison: str,
    group_by: Optional[str] = None,
    filter: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
    billing_view_arn: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieves AWS cost comparison data using the Cost Explorer API.

    Args:
        ctx: The MCP context object
        operation: The operation to perform: 'getCostAndUsageComparisons' or 'getCostComparisonDrivers'
        baseline_start_date: Baseline period start date in YYYY-MM-DD format (must be first day of month)
        baseline_end_date: Baseline period end date in YYYY-MM-DD format (must be first day of next month)
        comparison_start_date: Comparison period start date in YYYY-MM-DD format (must be first day of month)
        comparison_end_date: Comparison period end date in YYYY-MM-DD format (must be first day of next month)
        metric_for_comparison: The metric to compare, exact case. getCostAndUsageComparisons: AmortizedCost, BlendedCost, NetAmortizedCost, NetUnblendedCost, NormalizedUsageAmount, UnblendedCost, UsageQuantity. getCostComparisonDrivers: the five *Cost metrics only
        group_by: Optional grouping of results as a JSON string (e.g., '[{"Type": "DIMENSION", "Key": "SERVICE"}]')
        filter: Optional Cost Explorer Expression as a JSON string. Keys and values match exactly, including case; MatchOptions only EQUALS/CASE_SENSITIVE (plus ABSENT, without Values, for Tags and CostCategories); no RESOURCE_ID
        max_items: Total comparisons or drivers to return. None fetches every page.
        next_token: Pagination token from a previous response
        billing_view_arn: Optional ARN of a specific billing view

    Returns:
        Dict containing the cost comparison information
    """
    try:
        await ctx.info(f'Cost comparison operation: {operation}')

        if operation not in _OPERATION_METRICS:
            return format_response(
                'error',
                {},
                f"Unsupported operation: {operation}. Use 'getCostAndUsageComparisons' or 'getCostComparisonDrivers'.",
                error_type='validation_error',
            )

        today = _utc_today()
        validate_comparison_request(
            operation,
            baseline_start_date,
            baseline_end_date,
            comparison_start_date,
            comparison_end_date,
            metric_for_comparison,
            today,
        )
        validate_comparison_filter(parse_json(filter, 'filter'))

        # Initialize Cost Explorer client using shared utility
        ce_client = create_aws_client('ce', region_name='us-east-1')

        if operation == 'getCostAndUsageComparisons':
            result = await get_cost_and_usage_comparisons(
                ctx,
                ce_client,
                baseline_start_date,
                baseline_end_date,
                comparison_start_date,
                comparison_end_date,
                metric_for_comparison,
                group_by,
                filter,
                max_items,
                next_token,
                billing_view_arn,
            )
        else:
            result = await get_cost_comparison_drivers(
                ctx,
                ce_client,
                baseline_start_date,
                baseline_end_date,
                comparison_start_date,
                comparison_end_date,
                metric_for_comparison,
                group_by,
                filter,
                max_items,
                next_token,
                billing_view_arn,
            )

        # CE has no data for a period older than its history window; when that may be
        # the 13-month default, say how to extend it.
        unavailable = result.get('error_type') == 'DataUnavailableException'
        if unavailable and _starts_before_default_history(
            today, baseline_start_date, comparison_start_date
        ):
            result['hint'] = _MULTI_YEAR_HINT
        return result

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'cost_comparison', 'Cost Explorer')


async def get_cost_and_usage_comparisons(
    ctx: Context,
    ce_client: Any,
    baseline_start_date: str,
    baseline_end_date: str,
    comparison_start_date: str,
    comparison_end_date: str,
    metric_for_comparison: str,
    group_by: Optional[str],
    filter_expr: Optional[str],
    max_items: Optional[int],
    next_token: Optional[str],
    billing_view_arn: Optional[str],
) -> Dict[str, Any]:
    """Retrieves cost and usage comparison data using the AWS Cost Explorer API.

    Args:
        ctx: The MCP context
        ce_client: Cost Explorer client
        baseline_start_date: Start date for baseline period
        baseline_end_date: End date for baseline period
        comparison_start_date: Start date for comparison period
        comparison_end_date: End date for comparison period
        metric_for_comparison: Metric to compare
        group_by: Optional grouping as JSON string
        filter_expr: Optional filter as JSON string
        max_items: Total items to return. None fetches every page.
        next_token: Pagination token from a previous response
        billing_view_arn: Optional billing view ARN

    Returns:
        Dict containing comparison data
    """
    try:
        # Prepare the request parameters
        request_params = {
            'BaselineTimePeriod': {'Start': baseline_start_date, 'End': baseline_end_date},
            'ComparisonTimePeriod': {'Start': comparison_start_date, 'End': comparison_end_date},
            'MetricForComparison': metric_for_comparison,
        }

        # Add optional parameters if provided
        if group_by:
            request_params['GroupBy'] = parse_json(group_by, 'group_by')

        if filter_expr is not None:
            request_params['Filter'] = parse_filter(filter_expr)

        if billing_view_arn:
            request_params['BillingViewArn'] = billing_view_arn

        all_comparisons, pages, pagination = await paginate_aws_items(
            ctx,
            'GetCostAndUsageComparisons',
            ce_client.get_cost_and_usage_comparisons,
            request_params,
            GET_COST_AND_USAGE_COMPARISONS,
            max_items=max_items,
            next_token=next_token,
        )
        # The total covers the whole query, so only the first page carries it.
        total_cost_and_usage = first_page_fields(pages, ['TotalCostAndUsage']).get(
            'TotalCostAndUsage'
        )

        # Format the response for better readability
        formatted_response: Dict[str, Any] = {'cost_and_usage_comparisons': []}

        # Add total cost and usage if present
        if total_cost_and_usage:
            formatted_response['total_cost_and_usage'] = {}
            for metric_name, metric_data in total_cost_and_usage.items():
                formatted_response['total_cost_and_usage'][metric_name] = {
                    'baseline_time_period_amount': metric_data.get('BaselineTimePeriodAmount'),
                    'comparison_time_period_amount': metric_data.get('ComparisonTimePeriodAmount'),
                    'difference': metric_data.get('Difference'),
                    'unit': metric_data.get('Unit'),
                }

        # Format all collected comparisons
        for comparison in all_comparisons:
            formatted_comparison = {
                'cost_and_usage_selector': comparison.get('CostAndUsageSelector', {}),
                'metrics': {},
            }

            # Format metrics
            for metric_name, metric_data in comparison.get('Metrics', {}).items():
                formatted_comparison['metrics'][metric_name] = {
                    'baseline_time_period_amount': metric_data.get('BaselineTimePeriodAmount'),
                    'comparison_time_period_amount': metric_data.get('ComparisonTimePeriodAmount'),
                    'difference': metric_data.get('Difference'),
                    'unit': metric_data.get('Unit'),
                }

            formatted_response['cost_and_usage_comparisons'].append(formatted_comparison)

        return format_response('success', with_pagination(formatted_response, pagination))

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'get_cost_and_usage_comparisons', 'Cost Explorer')


async def get_cost_comparison_drivers(
    ctx: Context,
    ce_client: Any,
    baseline_start_date: str,
    baseline_end_date: str,
    comparison_start_date: str,
    comparison_end_date: str,
    metric_for_comparison: str,
    group_by: Optional[str],
    filter_expr: Optional[str],
    max_items: Optional[int],
    next_token: Optional[str],
    billing_view_arn: Optional[str],
) -> Dict[str, Any]:
    """Retrieves cost comparison drivers using the AWS Cost Explorer API.

    Args:
        ctx: The MCP context
        ce_client: Cost Explorer client
        baseline_start_date: Start date for baseline period
        baseline_end_date: End date for baseline period
        comparison_start_date: Start date for comparison period
        comparison_end_date: End date for comparison period
        metric_for_comparison: Metric to compare
        group_by: Optional grouping as JSON string
        filter_expr: Optional filter as JSON string
        max_items: Total items to return. None fetches every page.
        next_token: Pagination token from a previous response
        billing_view_arn: Optional billing view ARN

    Returns:
        Dict containing driver data
    """
    try:
        # Prepare the request parameters
        request_params = {
            'BaselineTimePeriod': {'Start': baseline_start_date, 'End': baseline_end_date},
            'ComparisonTimePeriod': {'Start': comparison_start_date, 'End': comparison_end_date},
            'MetricForComparison': metric_for_comparison,
        }

        # Add optional parameters if provided
        if group_by:
            request_params['GroupBy'] = parse_json(group_by, 'group_by')

        if filter_expr is not None:
            request_params['Filter'] = parse_filter(filter_expr)

        if billing_view_arn:
            request_params['BillingViewArn'] = billing_view_arn

        all_drivers, _, pagination = await paginate_aws_items(
            ctx,
            'GetCostComparisonDrivers',
            ce_client.get_cost_comparison_drivers,
            request_params,
            GET_COST_COMPARISON_DRIVERS,
            max_items=max_items,
            next_token=next_token,
        )

        # Format the response for better readability
        formatted_response: Dict[str, Any] = {'cost_comparison_drivers': []}

        # Format all collected drivers
        for driver in all_drivers:
            formatted_driver = {
                'cost_selector': driver.get('CostSelector', {}),
                'metrics': {},
                'cost_drivers': [],
            }

            # Format metrics
            for metric_name, metric_data in driver.get('Metrics', {}).items():
                formatted_driver['metrics'][metric_name] = {
                    'baseline_time_period_amount': metric_data.get('BaselineTimePeriodAmount'),
                    'comparison_time_period_amount': metric_data.get('ComparisonTimePeriodAmount'),
                    'difference': metric_data.get('Difference'),
                    'unit': metric_data.get('Unit'),
                }

            # Format cost drivers
            for cost_driver in driver.get('CostDrivers', []):
                formatted_cost_driver = {
                    'name': cost_driver.get('Name'),
                    'type': cost_driver.get('Type'),
                    'metrics': {},
                }

                # Format cost driver metrics
                for metric_name, metric_data in cost_driver.get('Metrics', {}).items():
                    formatted_cost_driver['metrics'][metric_name] = {
                        'baseline_time_period_amount': metric_data.get('BaselineTimePeriodAmount'),
                        'comparison_time_period_amount': metric_data.get(
                            'ComparisonTimePeriodAmount'
                        ),
                        'difference': metric_data.get('Difference'),
                        'unit': metric_data.get('Unit'),
                    }

                formatted_driver['cost_drivers'].append(formatted_cost_driver)

            formatted_response['cost_comparison_drivers'].append(formatted_driver)

        return format_response('success', with_pagination(formatted_response, pagination))

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'get_cost_comparison_drivers', 'Cost Explorer')
