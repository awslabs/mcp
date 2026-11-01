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

"""AWS Savings Plans Coverage and Utilization tools for the AWS Billing and Cost Management MCP server.

Updated to use shared utility functions.
"""

from ..utilities.aws_service_base import (
    PageSpec,
    create_aws_client,
    first_page_fields,
    format_response,
    get_date_range,
    handle_aws_error,
    paginate_aws_items,
    parse_filter,
    parse_json,
    whole_query_in_one_page,
    with_pagination,
)
from ..utilities.constants import PAGINATION_LIMIT_TEXT
from ..utilities.logging_utils import get_context_logger
from ..utilities.time_utils import monthly_period_note
from fastmcp import Context, FastMCP
from typing import Any, Dict, Optional


sp_performance_server = FastMCP(
    name='sp-performance-tools',
    instructions='Tools for working with AWS Savings Plans Performance (Coverage and Utilization) API',
)


@sp_performance_server.tool(
    name='sp-performance',
    description="""Tool that retrieves AWS Savings Plans coverage and utilization data using the Cost Explorer API.

This tool provides insights into your Savings Plans usage patterns through three main operations:

1. get_savings_plans_coverage: Shows how much of your eligible usage is covered by Savings Plans
2. get_savings_plans_utilization: Shows overall utilization metrics for your Savings Plans
3. get_savings_plans_utilization_details: Shows detailed per-Savings Plan utilization

COVERAGE grouping and filtering (get_savings_plans_coverage):
- group_by accepts ONLY INSTANCE_TYPE_FAMILY, REGION, or SERVICE. LINKED_ACCOUNT is
  NOT a valid group_by attribute — grouping by it returns a ValidationException.
- filter accepts LINKED_ACCOUNT, REGION, SERVICE, INSTANCE_TYPE_FAMILY. To see coverage
  per member account, FILTER by one LINKED_ACCOUNT and call once per account; do
  not try to group_by LINKED_ACCOUNT. SAVINGS_PLANS_TYPE is not a coverage dimension
  (ValidationException).
- Each group_by entry is a GroupDefinition with Type and Key, e.g.
  `[{"Type": "DIMENSION", "Key": "REGION"}]`. There is no "Value" field in a
  group_by entry — a `{Key, Value}` shape is rejected (seen as a boto
  ParamValidationError typed validation_error).

DATES AND DATA FRESHNESS (all three operations):
- If `start_date` is omitted, the tool uses 30 days before today; if `end_date` is
  omitted, it uses today (exclusive, so today is not included).
- start_date must be within the last 13 months (the Cost Explorer lookback); an
  older start_date returns a ValidationException.
- Savings Plans data for the most recent 2-3 days (counting today) is not processed
  yet: yesterday is usually still missing, so excluding only today is not enough. A
  start_date inside those days returns a DataUnavailableException, which the service
  sends without a message. A window that only reaches into those days succeeds but
  silently leaves them out, so the last DAILY entry can end before end_date (MONTHLY
  labels: see RESPONSE PERIODS). A start_date at least 3 days before today is usually
  past that delay.
- A DataUnavailableException means there is no data for THIS window and filter: the
  window is too recent, no plan was active in it, or a filter value matches nothing
  (an unknown SAVINGS_PLANS_TYPE, for example, returns this error, not a
  ValidationException). Report that no data is available for that window (not zero
  utilization or coverage) and do NOT resend the identical request. Correct an unknown
  filter value; query an earlier window only if the question allows it.

UTILIZATION filters (get_savings_plans_utilization):
- filter accepts LINKED_ACCOUNT, SAVINGS_PLAN_ARN, SAVINGS_PLANS_TYPE, REGION,
  PAYMENT_OPTION, INSTANCE_TYPE_FAMILY. Only Dimensions, And and Not are allowed; an Or,
  Tags or CostCategories expression returns a ValidationException.

UTILIZATION DETAILS filters (get_savings_plans_utilization_details):
- filter accepts LINKED_ACCOUNT, SAVINGS_PLAN_ARN, SAVINGS_PLANS_TYPE, REGION,
  PAYMENT_OPTION, INSTANCE_TYPE_FAMILY, AGREEMENT_END_DATE_TIME_AFTER and
  AGREEMENT_END_DATE_TIME_BEFORE (one YYYY-MM-DD value each, compared with each plan's
  end date).
- The filter is a Cost Explorer Expression. And requires at least TWO
  operands ("And expression must have at least 2 operands"). For a single
  condition, pass the leaf object directly — e.g.
  `{"Dimensions": {"Key": "REGION", "Values": ["us-east-1"]}}` — not wrapped in
  a one-element `And`.

FILTER VALUES (exact, case-sensitive spellings):
- PAYMENT_OPTION: "No Upfront", "Partial Upfront", "All Upfront".
- SAVINGS_PLANS_TYPE (get_savings_plans_utilization and
  get_savings_plans_utilization_details; not accepted by coverage): "ComputeSavingsPlans",
  "EC2InstanceSavingsPlans", "SageMakerSavingsPlans", "DatabaseSavingsPlans".
- Any other spelling (NO_UPFRONT, Compute, COMPUTE_SP) matches nothing and returns a
  DataUnavailableException, which the service sends without a message, not a
  ValidationException. On that error with a filter set, check these spellings before
  changing the window.

SORTING (sort_by; get_savings_plans_coverage and get_savings_plans_utilization_details):
- A JSON string `{"Key": "...", "SortOrder": "ASCENDING" or "DESCENDING"}`.
- Order of operations: the API sorts every matching item by the key first, then pages;
  max_items=N keeps the first N of that sorted order. So sort_by + max_items=N returns the
  top N items by the key across everything that matches, not N arbitrary items sorted
  afterwards (see PAGINATION for what an item is).
- Coverage keys: CoveragePercentage, SpendCoveredBySavingsPlan (singular, unlike the
  metric), OnDemandCost, TotalCost, InstanceFamily, Region, Service. Sort keys are not
  dimension names: sort by InstanceFamily, group by INSTANCE_TYPE_FAMILY. Sorting coverage
  by InstanceFamily, Region or Service needs that dimension in group_by
  (INSTANCE_TYPE_FAMILY, REGION or SERVICE); otherwise the API returns a ValidationException.
- Utilization details keys: UtilizationPercentage, TotalCommitment, UsedCommitment,
  UnusedCommitment, NetSavings, AmortizedRecurringCommitment, AmortizedUpfrontCommitment.
- get_savings_plans_utilization ignores sort_by and returns its periods in date order.

RESPONSE PERIODS (all three operations):
- `requested_time_period` echoes the start_date/end_date that were sent.
- MONTHLY utilization labels each entry's TimePeriod with its whole calendar month (the
  current month's entry ends at the first day without data instead), but the figures
  cover only the requested days. A 2026-08-17 to 2026-09-10 request returns
  a first entry labelled 2026-08-01 to 2026-09-01 holding only 2026-08-17 onward, and a
  last entry labelled 2026-09-01 to 2026-10-01 holding only the days before 2026-09-10.
  `period_note` says when this happened and the range the figures cover. Report those
  months as partial, not as whole months; `total` also covers only that range.
- MONTHLY coverage entries start at the requested start; they are not snapped.
- Utilization details returns `time_period`: the requested start, and an end the API
  may move earlier to the first day without complete data. Report that period.
- `granularity` appears on coverage only when it was sent (not with group_by).

IMPORTANT: For get_savings_plans_coverage, `granularity` and `group_by` are mutually
exclusive. If `group_by` is provided, `granularity` is ignored (the Cost Explorer
GetSavingsPlansCoverage API does not allow both). Valid `group_by` dimensions for
coverage are SERVICE, REGION, or INSTANCE_TYPE_FAMILY. If `metrics` is omitted, coverage uses
["SpendCoveredBySavingsPlans"] (the only valid value). `granularity` does not apply to
get_savings_plans_utilization_details.

PAGINATION (get_savings_plans_coverage, where an item is one period x group entry, and
get_savings_plans_utilization_details, where an item is one Savings Plan;
get_savings_plans_utilization is not paginated and takes neither parameter):
- max_items is the total number of items returned. If it is omitted, the tool fetches every page for """
    + PAGINATION_LIMIT_TEXT
    + """, then returns a partial result. Pass it,
  or narrow the date range or filter, for queries that can be large.
- If the response has complete_dataset: false, call again with a larger max_items, continue with
  next_token, or state in the answer that the result is partial.
- For utilization details, the API's Total covers only the Savings Plans on its own page, so
  `total` is returned only when the whole query came back in one page. It is omitted from a
  multi-page, partial, or next_token continuation result; for the overall figure over the same
  window, use the `total` of get_savings_plans_utilization. Coverage has no `total`; the
  GetSavingsPlansCoverage API does not return one.""",
)
async def sp_performance(
    ctx: Context,
    operation: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    granularity: str = 'DAILY',
    metrics: Optional[str] = None,
    group_by: Optional[str] = None,
    filter: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
    sort_by: Optional[str] = None,
) -> Dict[str, Any]:
    """Tool that retrieves AWS Savings Plans coverage and utilization data.

    Args:
        ctx: The MCP context object
        operation: The operation to perform: 'get_savings_plans_coverage', 'get_savings_plans_utilization', or 'get_savings_plans_utilization_details'
        start_date: Start date in YYYY-MM-DD format (inclusive). Defaults to 30 days ago if not provided. Must be within the last 13 months.
        end_date: End date in YYYY-MM-DD format (exclusive). Defaults to today if not provided. Savings Plans data for the last 2-3 days (counting today) is not processed yet: a start_date in those days returns a DataUnavailableException, and a window reaching into them leaves them out.
        granularity: Time granularity of the data (DAILY or MONTHLY). Defaults to DAILY. For coverage, ignored when group_by is provided (granularity and group_by are mutually exclusive).
        metrics: List of metrics to retrieve as a JSON string. For coverage, only 'SpendCoveredBySavingsPlans' is valid.
        group_by: Optional grouping of results as a JSON string. For coverage, supports SERVICE, REGION, or INSTANCE_TYPE_FAMILY (NOT LINKED_ACCOUNT). Each entry is {"Type": ..., "Key": ...}; there is no "Value" field.
        filter: Optional filter to apply to the results as a JSON string. Coverage filter dimensions: LINKED_ACCOUNT, REGION, SERVICE, INSTANCE_TYPE_FAMILY. And needs >=2 operands; for one condition pass the leaf object directly. Values are case-sensitive; see FILTER VALUES in the tool description.
        max_items: Total number of items to return across all pages. Omit it to fetch every
            page. Coverage and utilization details only. With sort_by, these are the first N
            items in the requested SortOrder (the top N), not N items sorted afterwards.
        next_token: The pagination.next_token from a previous response; continue with otherwise
            identical parameters. Coverage and utilization details only.
        sort_by: Optional sort as a JSON string, e.g. {"Key": "CoveragePercentage", "SortOrder": "ASCENDING"}.
            Applied before max_items, so sort_by + max_items=N returns the top N.
            Coverage and utilization details only (ignored by get_savings_plans_utilization);
            the valid keys differ per operation (see SORTING).

    Returns:
        Dict containing the savings plans coverage/utilization information
    """
    try:
        await ctx.info(f'Savings Plans Coverage/Utilization operation: {operation}')

        # Initialize Cost Explorer client using shared utility
        ce_client = create_aws_client('ce', region_name='us-east-1')

        if operation == 'get_savings_plans_coverage':
            return await get_savings_plans_coverage(
                ctx,
                ce_client,
                start_date,
                end_date,
                granularity,
                metrics,
                group_by,
                filter,
                max_items,
                next_token,
                sort_by,
            )
        elif operation == 'get_savings_plans_utilization':
            return await get_savings_plans_utilization(
                ctx, ce_client, start_date, end_date, granularity, filter
            )
        elif operation == 'get_savings_plans_utilization_details':
            return await get_savings_plans_utilization_details(
                ctx, ce_client, start_date, end_date, filter, max_items, next_token, sort_by
            )
        else:
            return format_response(
                'error',
                {},
                f"Unsupported operation: {operation}. Use 'get_savings_plans_coverage', 'get_savings_plans_utilization', or 'get_savings_plans_utilization_details'.",
            )

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'sp_performance', 'Cost Explorer')


# The service default page size is 500, not the documented 20, so MaxResults is always sent.
CE_GET_SAVINGS_PLANS_COVERAGE = PageSpec(
    result_key='SavingsPlansCoverages',
    token_param='NextToken',
    token_key_in_response='NextToken',
    page_max=10000,
    page_size_param='MaxResults',
)


async def get_savings_plans_coverage(
    ctx: Context,
    ce_client: Any,
    start_date: Optional[str],
    end_date: Optional[str],
    granularity: str,
    metrics: Optional[str],
    group_by: Optional[str],
    filter_expr: Optional[str],
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
    sort_by: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieves Savings Plans coverage data.

    Args:
        ctx: The MCP context
        ce_client: Cost Explorer client
        start_date: Start date for the query
        end_date: End date for the query
        granularity: Time granularity (DAILY/MONTHLY)
        metrics: Metrics to retrieve as JSON string
        group_by: Grouping dimensions as JSON string
        filter_expr: Filter expression as JSON string
        max_items: Total number of coverage entries to return. None fetches every page.
        next_token: The token from a previous response.
        sort_by: Sort definition as JSON string

    Returns:
        Dict containing coverage data
    """
    try:
        # Get date range using shared utility
        start, end = get_date_range(start_date, end_date)

        # Log the time period
        await ctx.info(
            f'Analyzing Savings Plans coverage from {start} to {end} with {granularity} granularity'
        )

        # For Savings Plans coverage, only "SpendCoveredBySavingsPlans" metric is valid
        metrics_list = ['SpendCoveredBySavingsPlans']
        if metrics:
            metrics_list = parse_json(metrics, 'metrics')

        # Prepare the request parameters
        request_params = {
            'TimePeriod': {'Start': start, 'End': end},
            'Metrics': metrics_list,
        }

        # Add optional parameters if provided.
        # GetSavingsPlansCoverage treats Granularity and GroupBy as mutually
        # exclusive: "Granularity can't be set if GroupBy is set". Only send
        # Granularity when the request is not grouped, otherwise the API returns
        # a ValidationException.
        if group_by:
            request_params['GroupBy'] = parse_json(group_by, 'group_by')
        else:
            request_params['Granularity'] = granularity

        if filter_expr is not None:
            request_params['Filter'] = parse_filter(filter_expr)

        if sort_by:
            request_params['SortBy'] = parse_json(sort_by, 'sort_by')

        all_coverages, _, pagination = await paginate_aws_items(
            ctx,
            'GetSavingsPlansCoverage',
            ce_client.get_savings_plans_coverage,
            request_params,
            CE_GET_SAVINGS_PLANS_COVERAGE,
            max_items=max_items,
            next_token=next_token,
        )

        # GetSavingsPlansCoverage returns no Total, so there is none to report.
        formatted_response: Dict[str, Any] = {
            'savings_plans_coverages': all_coverages,
            'requested_time_period': {'start': start, 'end': end},
        }
        if 'Granularity' in request_params:
            formatted_response['granularity'] = granularity

        return format_response('success', with_pagination(formatted_response, pagination))

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'get_savings_plans_coverage', 'Cost Explorer')


async def get_savings_plans_utilization(
    ctx: Context,
    ce_client: Any,
    start_date: Optional[str],
    end_date: Optional[str],
    granularity: str,
    filter_expr: Optional[str],
) -> Dict[str, Any]:
    """Retrieves Savings Plans utilization data.

    Args:
        ctx: The MCP context
        ce_client: Cost Explorer client
        start_date: Start date for the query
        end_date: End date for the query
        granularity: Time granularity (DAILY/MONTHLY)
        filter_expr: Filter expression as JSON string

    Returns:
        Dict containing utilization data
    """
    # Get context logger for consistent logging
    ctx_logger = get_context_logger(ctx, __name__)

    try:
        # Get date range using shared utility
        start, end = get_date_range(start_date, end_date)

        # Log the time period
        await ctx_logger.info(
            f'Analyzing Savings Plans utilization from {start} to {end} with {granularity} granularity'
        )

        # Prepare the request parameters
        request_params: Dict[str, Any] = {
            'TimePeriod': {'Start': start, 'End': end},
            'Granularity': granularity,
        }

        # Add optional parameters if provided
        if filter_expr is not None:
            request_params['Filter'] = parse_filter(filter_expr)

        response = ce_client.get_savings_plans_utilization(**request_params)

        utilizations_by_time = response.get('SavingsPlansUtilizationsByTime', [])
        total = response.get('Total')

        formatted_response: Dict[str, Any] = {
            'savings_plans_utilizations': utilizations_by_time,
            # The API has no top-level period. A MONTHLY entry's TimePeriod is labelled with its
            # whole calendar month even when the requested start or end falls inside that month.
            'requested_time_period': {'start': start, 'end': end},
            'granularity': granularity,
            **monthly_period_note(
                start,
                end,
                [entry.get('TimePeriod') for entry in utilizations_by_time],
                granularity,
            ),
        }

        if total is not None:
            formatted_response['total'] = total

        if not utilizations_by_time and total is None:
            await ctx_logger.warning(
                'No Savings Plans utilization data found for the specified period'
            )
            formatted_response['message'] = (
                'No Savings Plans utilization data found for the specified period. This could be '
                'because you do not have any active Savings Plans, or because the specified date '
                'range is outside your Savings Plans period.'
            )

        return format_response('success', formatted_response)

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'get_savings_plans_utilization', 'Cost Explorer')


CE_GET_SAVINGS_PLANS_UTILIZATION_DETAILS = PageSpec(
    result_key='SavingsPlansUtilizationDetails',
    token_param='NextToken',
    token_key_in_response='NextToken',
    page_max=10000,
    page_size_param='MaxResults',
)


async def get_savings_plans_utilization_details(
    ctx: Context,
    ce_client: Any,
    start_date: Optional[str],
    end_date: Optional[str],
    filter_expr: Optional[str],
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
    sort_by: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieves detailed Savings Plans utilization data.

    Args:
        ctx: The MCP context
        ce_client: Cost Explorer client
        start_date: Start date for the query
        end_date: End date for the query
        filter_expr: Filter expression as JSON string
        max_items: Total number of Savings Plans to return. None fetches every page.
        next_token: The token from a previous response.
        sort_by: Sort definition as JSON string

    Returns:
        Dict containing detailed utilization data
    """
    # Get context logger for consistent logging
    ctx_logger = get_context_logger(ctx, __name__)

    try:
        # Get date range using shared utility
        start, end = get_date_range(start_date, end_date)

        # Log the time period
        await ctx_logger.info(
            f'Analyzing detailed Savings Plans utilization from {start} to {end}'
        )

        # Create request parameters
        request_params: dict = {'TimePeriod': {'Start': start, 'End': end}}

        # Add optional parameters if provided
        if filter_expr is not None:
            request_params['Filter'] = parse_filter(filter_expr)

        if sort_by:
            request_params['SortBy'] = parse_json(sort_by, 'sort_by')

        all_details, pages, pagination = await paginate_aws_items(
            ctx,
            'GetSavingsPlansUtilizationDetails',
            ce_client.get_savings_plans_utilization_details,
            request_params,
            CE_GET_SAVINGS_PLANS_UTILIZATION_DETAILS,
            max_items=max_items,
            next_token=next_token,
        )

        requested_time_period = {'start': start, 'end': end}

        # Check if we have any details data
        if not all_details:
            await ctx_logger.warning(
                'No Savings Plans utilization details found for the specified period'
            )
            return format_response(
                'success',
                with_pagination(
                    {
                        'savings_plans_utilization_details': [],
                        'requested_time_period': requested_time_period,
                        'message': 'No Savings Plans utilization details found for the specified period. This could be because you do not have any active Savings Plans, or because the specified date range is outside your Savings Plans period.',
                    },
                    pagination,
                ),
            )

        formatted_response: Dict[str, Any] = {
            'savings_plans_utilization_details': all_details,
            'requested_time_period': requested_time_period,
        }

        first_page = first_page_fields(pages, ['Total', 'TimePeriod'])
        if 'TimePeriod' in first_page:
            formatted_response['time_period'] = first_page['TimePeriod']
        # The API's Total aggregates only the plans on its own page, so it covers the query
        # only when the query is that one page.
        if 'Total' in first_page and whole_query_in_one_page(pages, next_token, pagination):
            formatted_response['total'] = first_page['Total']

        return format_response('success', with_pagination(formatted_response, pagination))

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(
            ctx, e, 'get_savings_plans_utilization_details', 'Cost Explorer'
        )
