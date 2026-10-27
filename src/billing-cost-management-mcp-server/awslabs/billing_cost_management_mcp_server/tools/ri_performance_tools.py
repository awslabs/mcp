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

"""AWS Reservation Coverage and Utilization tools for the AWS Billing and Cost Management MCP server.

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
    parse_json,
    whole_query_in_one_page,
    with_pagination,
)
from fastmcp import Context, FastMCP
from typing import Any, Dict, List, Optional


ri_performance_server = FastMCP(
    name='ri-performance-tools',
    instructions='Tools for working with AWS Reserved Instance Performance (Coverage and Utilization) API',
)


@ri_performance_server.tool(
    name='ri-performance',
    description="""Retrieves AWS Reserved Instance (RI) coverage and utilization data using the Cost Explorer API.

This tool provides insights into your Reserved Instance (RI) and Savings Plans usage patterns through two main operations:

1. get_reservation_coverage: Shows how much of your eligible usage is covered by RIs
   - Helps identify opportunities to purchase additional RIs
   - Supports grouping by dimensions like REGION, INSTANCE_TYPE, etc.
   - Can filter by specific services, regions, or instance types

2. get_reservation_utilization: Shows how effectively you're using your purchased RIs
   - Reveals underutilized or idle reserved capacity
   - Can be grouped by SUBSCRIPTION_ID to see utilization per RI
   - Helps identify RIs that could be modified or sold in the marketplace

GROUPING get_reservation_coverage (group_by):
GetReservationCoverage groups ONLY by these attributes. Keys marked "only" apply just to
that service (from the SERVICE filter, EC2 when omitted); others return a ValidationException:
- AZ: Availability Zone (e.g. us-east-1a)
- CACHE_ENGINE: ElastiCache engine (e.g. Redis, Memcached). ElastiCache and MemoryDB only
- DATABASE_ENGINE: RDS database engine (e.g. PostgreSQL, MySQL, Aurora MySQL). RDS only
- DEPLOYMENT_OPTION: deployment mode (e.g. Single-AZ, Multi-AZ). RDS only
- INSTANCE_TYPE: instance type (e.g. m4.xlarge, cache.r6g.large)
- INSTANCE_TYPE_FAMILY: instance family (e.g. m5, t3). EC2 only
- LINKED_ACCOUNT: member account id in the organization
- PLATFORM: operating system / platform. EC2 only
- REGION: AWS Region (e.g. us-east-1)
- TENANCY: instance tenancy. Exact, case-sensitive values: Shared, Dedicated, Host. EC2 only
SERVICE, INVOICING_ENTITY and OPERATING_SYSTEM are NOT valid group_by attributes here —
grouping coverage by them returns a ValidationException. SERVICE is a FILTER dimension instead: pass it in
`filter` (one SERVICE value per call; if you omit a SERVICE filter, Cost Explorer
defaults to EC2), and call once per service to compare across services.
Reservation coverage applies only to reservable services. The valid SERVICE
filter values are "Amazon Elastic Compute Cloud - Compute" (the default when
omitted), "Amazon Relational Database Service", "Amazon ElastiCache",
"Amazon MemoryDB", "Amazon Redshift", "Amazon OpenSearch Service", and
"Amazon Elasticsearch Service". Use the full Cost Explorer service display name, not
"EC2"/"RDS".

GROUPING get_reservation_utilization (group_by):
GetReservationUtilization groups ONLY by SUBSCRIPTION_ID. No other attribute is
valid. The SubscriptionId it returns (and that you filter on) is a NUMERIC id
(e.g. "359809062"), not an ARN, instance id, or UUID — filtering SubscriptionId
with an ARN/UUID returns a ValidationException ("must contain only digits").

FILTERING (both operations): the Cost Explorer Expression supports only AND among
dimensions and nests one level deep; multiple values for one dimension are OR'd.
The SERVICE filter defaults to Amazon Elastic Compute Cloud - Compute when omitted.

SCOPING LARGE QUERIES: a grouped or DAILY query over a wide window or many
subscriptions can exceed the tool result size cap and return a ToolResultOversized
error. Scope such queries with `filter` (e.g. one SERVICE or one SUBSCRIPTION_ID),
a shorter window, or MONTHLY granularity before widening.

IMPORTANT: `granularity` and `group_by` are mutually exclusive. If `group_by` is
provided, `granularity` is ignored (the Cost Explorer API does not allow both for
GetReservationCoverage or GetReservationUtilization). Provide one or the other,
not both.

PAGINATION (applies only when group_by is set; an item is one group of the queried period):
- Without group_by, both operations return every time period in one response, so max_items,
  max_pages and next_token do not apply (get_reservation_utilization ignores them).
- get_reservation_coverage: max_items is the total number of groups returned. Omit it to fetch
  every page (no limit). Pass it, or narrow the filter, for queries that can be large.
  Top-N: sort_by + max_items=N.
- get_reservation_utilization takes max_pages (pages of 500 groups) instead of max_items, because
  its next_token only works with the same page size. Continue with next_token; omit max_pages to
  fetch every page.
- If the response has complete_dataset: false, call again with a larger max_items or max_pages,
  continue with next_token, or state in the answer that the result is partial.
- With group_by, the API's period `total` sums only the groups on its own page, so `total` is
  returned only when the whole query came back in one page. It is omitted from a multi-page,
  partial, or next_token continuation result; for the overall figure over the same window, call
  again without group_by, whose `total` covers every period.""",
)
async def ri_performance(
    ctx: Context,
    operation: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    granularity: str = 'DAILY',
    metrics: Optional[str] = None,
    group_by: Optional[str] = None,
    filter: Optional[str] = None,
    sort_by: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
    max_pages: Optional[int] = None,
) -> Dict[str, Any]:
    """Retrieves AWS RI coverage and utilization data using the Cost Explorer API.

    Args:
        ctx: The MCP context object
        operation: The operation to perform: 'get_reservation_coverage' or 'get_reservation_utilization'
        start_date: Start date in YYYY-MM-DD format (inclusive). Defaults to 30 days ago if not provided.
        end_date: End date in YYYY-MM-DD format (exclusive). Defaults to today if not provided.
        granularity: Time granularity of the data (DAILY or MONTHLY). Defaults to DAILY. Ignored when group_by is provided (granularity and group_by are mutually exclusive).
        metrics: List of metrics to retrieve for coverage as a JSON string (e.g., '["HoursCoverage", "CostCoverage"]'). Defaults to all metrics.
        group_by: Optional grouping as a JSON string. For coverage: AZ, CACHE_ENGINE, DATABASE_ENGINE, DEPLOYMENT_OPTION, INSTANCE_TYPE, INSTANCE_TYPE_FAMILY, LINKED_ACCOUNT, PLATFORM, REGION, or TENANCY, depending on the service (see the tool description) (SERVICE is NOT valid — filter on it instead). For utilization: SUBSCRIPTION_ID only.
        filter: Optional filter as a JSON string (e.g., by service, region, or instance type). SERVICE defaults to EC2 when omitted; valid coverage SERVICE values are "Amazon Elastic Compute Cloud - Compute", "Amazon Relational Database Service", "Amazon ElastiCache", "Amazon MemoryDB", "Amazon Redshift", "Amazon OpenSearch Service", and "Amazon Elasticsearch Service" (use the full display name, not "EC2"/"RDS"). SubscriptionId values are numeric, not ARNs/UUIDs. A wide grouped/DAILY query may exceed the result size cap (ToolResultOversized) — scope it with a filter, a shorter window, or MONTHLY granularity.
        sort_by: Optional sorting configuration as a JSON string with key and direction (ASCENDING or DESCENDING).
        max_items: Total number of groups to return across all pages. Omit it to fetch every
            page. Applies only to get_reservation_coverage with group_by set.
        next_token: The pagination.next_token from a previous response; continue with otherwise
            identical parameters. Applies only when group_by is set.
        max_pages: Number of pages of 500 groups to return. Omit it to fetch every page.
            Applies only to get_reservation_utilization with group_by set.

    Returns:
        Dict containing the reservation coverage/utilization information
    """
    try:
        await ctx.info(f'Reservation Coverage/Utilization operation: {operation}')

        # Initialize Cost Explorer client using shared utility
        ce_client = create_aws_client('ce', region_name='us-east-1')

        if operation == 'get_reservation_coverage':
            return await get_reservation_coverage(
                ctx,
                ce_client,
                start_date,
                end_date,
                granularity,
                metrics,
                group_by,
                filter,
                sort_by,
                max_items,
                next_token,
                max_pages,
            )
        elif operation == 'get_reservation_utilization':
            return await get_reservation_utilization(
                ctx,
                ce_client,
                start_date,
                end_date,
                granularity,
                group_by,
                filter,
                sort_by,
                max_items,
                next_token,
                max_pages,
            )
        else:
            return format_response(
                'error',
                {},
                f"Unsupported operation: {operation}. Use 'get_reservation_coverage' or 'get_reservation_utilization'.",
            )

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'ri_performance', 'Cost Explorer')


def _count_groups(entries: List[Dict[str, Any]]) -> int:
    """Count the groups across a page's time-period entries."""
    return sum(len(entry.get('Groups') or []) for entry in entries)


def _merge_periods(entries: List[Dict[str, Any]], keep_totals: bool) -> List[Dict[str, Any]]:
    """Merge consecutive entries for the same time period into one.

    A grouped query returns one time-period entry per page, each holding that page's groups, so
    the groups of every page are gathered under a single entry. The entry's Total sums only the
    groups on its own page, so it is kept only when ``keep_totals`` says the page is the whole
    query.
    """
    merged: List[Dict[str, Any]] = []
    for entry in entries:
        if merged and merged[-1].get('TimePeriod') == entry.get('TimePeriod'):
            merged[-1]['Groups'] = (merged[-1].get('Groups') or []) + (entry.get('Groups') or [])
        else:
            merged.append(dict(entry))
            if not keep_totals:
                merged[-1].pop('Total', None)
    return merged


# With GroupBy the API pages over the groups of a single time-period entry.
CE_GET_RESERVATION_COVERAGE_GROUPED = PageSpec(
    result_key='CoveragesByTime',
    token_param='NextPageToken',
    token_key_in_response='NextPageToken',
    page_max=10000,
    page_size_param='MaxResults',
    count_items=_count_groups,
)

# Without GroupBy every time period comes back in one response with no token.
CE_GET_RESERVATION_COVERAGE = PageSpec(
    result_key='CoveragesByTime',
    token_param='NextPageToken',
    token_key_in_response='NextPageToken',
    page_max=10000,
)


async def get_reservation_coverage(
    ctx: Context,
    ce_client: Any,
    start_date: Optional[str],
    end_date: Optional[str],
    granularity: str,
    metrics: Optional[str],
    group_by: Optional[str],
    filter_expr: Optional[str],
    sort_by: Optional[str],
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
    max_pages: Optional[int] = None,
) -> Dict[str, Any]:
    """Retrieves reservation coverage data using the AWS Cost Explorer API.

    Args:
        ctx: The MCP context
        ce_client: Cost Explorer client
        start_date: Start date for the query
        end_date: End date for the query
        granularity: Time granularity (DAILY/MONTHLY)
        metrics: Metrics to retrieve as JSON string
        group_by: Grouping dimensions as JSON string
        filter_expr: Filter expression as JSON string
        sort_by: Sort configuration as JSON string
        max_items: Total number of groups to return. None fetches every page.
        next_token: The token from a previous response.
        max_pages: Not supported; set only to report a validation error.

    Returns:
        Dict containing coverage data
    """
    try:
        if max_pages is not None:
            raise ValueError(
                'max_pages applies only to get_reservation_utilization; use max_items.'
            )

        # Get date range using shared utility
        start, end = get_date_range(start_date, end_date)

        # Log the time period
        await ctx.info(
            f'Analyzing reservation coverage from {start} to {end} with {granularity} granularity'
        )

        # Prepare the request parameters
        request_params: Dict[str, Any] = {
            'TimePeriod': {'Start': start, 'End': end},
        }

        # Add optional parameters if provided
        if metrics:
            request_params['Metrics'] = parse_json(metrics, 'metrics')

        # GetReservationCoverage treats Granularity and GroupBy as mutually
        # exclusive: "Granularity is not supported when specifying groupBy".
        # Construct exactly one of them so a grouped request cannot include
        # Granularity, which the API rejects with a ValidationException.
        if group_by:
            request_params['GroupBy'] = parse_json(group_by, 'group_by')
        else:
            request_params['Granularity'] = granularity

        if filter_expr:
            request_params['Filter'] = parse_json(filter_expr, 'filter')

        if sort_by:
            request_params['SortBy'] = parse_json(sort_by, 'sort_by')

        if group_by:
            spec = CE_GET_RESERVATION_COVERAGE_GROUPED
        else:
            # The ungrouped API returns every period in one response, so max_items and
            # next_token do not apply (same as get_reservation_utilization).
            spec = CE_GET_RESERVATION_COVERAGE
            max_items = None
            next_token = None
        coverage_entries, pages, pagination = await paginate_aws_items(
            ctx,
            'GetReservationCoverage',
            ce_client.get_reservation_coverage,
            request_params,
            spec,
            max_items=max_items,
            next_token=next_token,
        )
        # The API's Totals sum only the groups on their own page, so they cover the query only
        # when the query is that one page.
        whole_query = whole_query_in_one_page(pages, next_token, pagination)
        all_coverages = _merge_periods(coverage_entries, keep_totals=whole_query)
        total_coverage = first_page_fields(pages, ['Total']).get('Total') if whole_query else None

        # Format the response for better readability
        formatted_response: Dict[str, Any] = {
            'coverages_by_time': [],
        }

        # Format total coverage if present
        if total_coverage:
            formatted_response['total'] = format_coverage_metrics(total_coverage)

        # Format all collected coverages
        for coverage in all_coverages:
            time_period = coverage.get('TimePeriod', {})
            groups = coverage.get('Groups', [])
            total = coverage.get('Total', {})

            formatted_coverage: Dict[str, Any] = {
                'time_period': {'start': time_period.get('Start'), 'end': time_period.get('End')},
                'groups': [],
            }

            # Format total for this time period
            if total:
                formatted_coverage['total'] = format_coverage_metrics(total)

            # Format groups if present
            if groups:
                for group in groups:
                    formatted_group = {
                        'attributes': group.get('Attributes', {}),
                        'coverage': format_coverage_metrics(group.get('Coverage', {})),
                    }
                    formatted_coverage['groups'].append(formatted_group)

            formatted_response['coverages_by_time'].append(formatted_coverage)

        return format_response('success', with_pagination(formatted_response, pagination))

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'get_reservation_coverage', 'Cost Explorer')


# With GroupBy the API pages over the groups of a single time-period entry. The continuation
# token is bound to MaxResults, so every page, continuation included, must send the same value,
# and the tool takes max_pages instead of max_items. The API allows MaxResults up to 7000; 500 is
# the page size chosen here, sent on every page because the token requires the same size.
CE_GET_RESERVATION_UTILIZATION_GROUPED = PageSpec(
    result_key='UtilizationsByTime',
    token_param='NextPageToken',
    token_key_in_response='NextPageToken',
    page_max=500,
    page_size_param='MaxResults',
    fixed_page_size=True,
    count_items=_count_groups,
)

# Without GroupBy every time period comes back in one response, and any token is rejected.
CE_GET_RESERVATION_UTILIZATION = PageSpec(
    result_key='UtilizationsByTime',
    token_param='NextPageToken',
    token_key_in_response='NextPageToken',
    page_max=10000,
)


async def get_reservation_utilization(
    ctx: Context,
    ce_client: Any,
    start_date: Optional[str],
    end_date: Optional[str],
    granularity: str,
    group_by: Optional[str],
    filter_expr: Optional[str],
    sort_by: Optional[str],
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
    max_pages: Optional[int] = None,
) -> Dict[str, Any]:
    """Retrieves reservation utilization data using the AWS Cost Explorer API.

    Args:
        ctx: The MCP context
        ce_client: Cost Explorer client
        start_date: Start date for the query
        end_date: End date for the query
        granularity: Time granularity (DAILY/MONTHLY)
        group_by: Grouping dimensions as JSON string
        filter_expr: Filter expression as JSON string
        sort_by: Sort configuration as JSON string
        max_items: Not supported with group_by, where pages have a fixed size of 500 groups;
            set only to report a validation error. Ignored without group_by.
        next_token: The token from a previous response. Ignored without group_by.
        max_pages: Number of pages of 500 groups to return. None fetches every page. Ignored
            without group_by.

    Returns:
        Dict containing utilization data
    """
    try:
        # Get date range using shared utility
        start, end = get_date_range(start_date, end_date)

        # Log the time period
        await ctx.info(
            f'Analyzing reservation utilization from {start} to {end} with {granularity} granularity'
        )

        # Prepare the request parameters
        request_params: Dict[str, Any] = {
            'TimePeriod': {'Start': start, 'End': end},
        }

        # Add optional parameters if provided
        if group_by:
            request_params['GroupBy'] = parse_json(group_by, 'group_by')

        # GetReservationUtilization treats Granularity and GroupBy as mutually
        # exclusive: "If GroupBy is set, Granularity can't be set". Only send
        # Granularity when the request is not grouped, otherwise the API returns
        # a ValidationException.
        if not group_by:
            request_params['Granularity'] = granularity

        if filter_expr:
            request_params['Filter'] = parse_json(filter_expr, 'filter')

        if sort_by:
            request_params['SortBy'] = parse_json(sort_by, 'sort_by')

        if group_by:
            if max_items is not None:
                raise ValueError(
                    'get_reservation_utilization pages in fixed pages of 500 groups: use '
                    'max_pages instead of max_items.'
                )
            spec = CE_GET_RESERVATION_UTILIZATION_GROUPED
        else:
            # The ungrouped API returns everything in one response and rejects any token, so
            # max_pages and next_token do not apply.
            spec = CE_GET_RESERVATION_UTILIZATION
            max_pages = None
            next_token = None

        utilization_entries, pages, pagination = await paginate_aws_items(
            ctx,
            'GetReservationUtilization',
            ce_client.get_reservation_utilization,
            request_params,
            spec,
            next_token=next_token,
            max_pages=max_pages,
        )
        # The API's Totals sum only the groups on their own page, so they cover the query only
        # when the query is that one page.
        whole_query = whole_query_in_one_page(pages, next_token, pagination)
        all_utilizations = _merge_periods(utilization_entries, keep_totals=whole_query)
        total_utilization = (
            first_page_fields(pages, ['Total']).get('Total') if whole_query else None
        )

        # Format the response for better readability
        formatted_response: Dict[str, Any] = {
            'utilizations_by_time': [],
        }

        # Format total utilization if present
        if total_utilization:
            formatted_response['total'] = format_utilization_metrics(total_utilization)

        # Format all collected utilizations
        for utilization in all_utilizations:
            time_period = utilization.get('TimePeriod', {})
            groups = utilization.get('Groups', [])
            total = utilization.get('Total', {})

            formatted_utilization: Dict[str, Any] = {
                'time_period': {'start': time_period.get('Start'), 'end': time_period.get('End')},
                'groups': [],
            }

            # Format total for this time period
            if total:
                formatted_utilization['total'] = format_utilization_metrics(total)

            # Format groups if present
            if groups:
                for group in groups:
                    formatted_group = {
                        'attributes': group.get('Attributes', {}),
                        'utilization': format_utilization_metrics(group.get('Utilization', {})),
                    }
                    formatted_utilization['groups'].append(formatted_group)

            formatted_response['utilizations_by_time'].append(formatted_utilization)

        return format_response('success', with_pagination(formatted_response, pagination))

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'get_reservation_utilization', 'Cost Explorer')


def format_coverage_metrics(coverage_data: Dict) -> Dict:
    """Formats the coverage metrics data for better readability.

    Args:
        coverage_data: Raw coverage data from Cost Explorer API

    Returns:
        Dict containing formatted coverage metrics
    """
    formatted_coverage = {}

    # Format overall coverage metrics
    if 'CoverageHours' in coverage_data:
        ch = coverage_data['CoverageHours']
        formatted_coverage['coverage_hours'] = {
            'on_demand_hours': ch.get('OnDemandHours'),
            'reserved_hours': ch.get('ReservedHours'),
            'total_running_hours': ch.get('TotalRunningHours'),
            'coverage_hours_percentage': ch.get('CoverageHoursPercentage'),
        }

    # Format coverage by service
    if 'CoverageNormalizedUnits' in coverage_data:
        cnu = coverage_data['CoverageNormalizedUnits']
        formatted_coverage['coverage_normalized_units'] = {
            'on_demand_normalized_units': cnu.get('OnDemandNormalizedUnits'),
            'reserved_normalized_units': cnu.get('ReservedNormalizedUnits'),
            'total_running_normalized_units': cnu.get('TotalRunningNormalizedUnits'),
            'coverage_normalized_units_percentage': cnu.get('CoverageNormalizedUnitsPercentage'),
        }

    # Format cost coverage. CoverageCost holds only OnDemandCost (the on-demand cost of
    # usage reservations did not cover); Cost Explorer reports no reserved cost or cost
    # coverage percentage, so use coverage_hours_percentage for coverage.
    if 'CoverageCost' in coverage_data:
        cc = coverage_data['CoverageCost']
        formatted_coverage['coverage_cost'] = {
            'on_demand_cost': cc.get('OnDemandCost'),
        }

    return formatted_coverage


def format_utilization_metrics(utilization_data: Dict) -> Dict:
    """Formats the utilization metrics data for better readability.

    Args:
        utilization_data: Raw utilization data from Cost Explorer API

    Returns:
        Dict containing formatted utilization metrics
    """
    formatted_utilization = {}

    # Add utilization metrics
    if 'UtilizationPercentage' in utilization_data:
        formatted_utilization['utilization_percentage'] = utilization_data['UtilizationPercentage']

    if 'PurchasedHours' in utilization_data:
        formatted_utilization['purchased_hours'] = utilization_data['PurchasedHours']

    if 'TotalActualHours' in utilization_data:
        formatted_utilization['total_actual_hours'] = utilization_data['TotalActualHours']

    if 'UnusedHours' in utilization_data:
        formatted_utilization['unused_hours'] = utilization_data['UnusedHours']

    # Add normalized unit metrics if present
    if 'PurchasedUnits' in utilization_data:
        formatted_utilization['purchased_units'] = utilization_data['PurchasedUnits']

    if 'TotalActualUnits' in utilization_data:
        formatted_utilization['total_actual_units'] = utilization_data['TotalActualUnits']

    if 'UnusedUnits' in utilization_data:
        formatted_utilization['unused_units'] = utilization_data['UnusedUnits']

    if 'UtilizationPercentageInUnits' in utilization_data:
        formatted_utilization['utilization_percentage_in_units'] = utilization_data[
            'UtilizationPercentageInUnits'
        ]

    if 'OnDemandCostOfRIHoursUsed' in utilization_data:
        formatted_utilization['on_demand_cost_of_ri_hours_used'] = utilization_data[
            'OnDemandCostOfRIHoursUsed'
        ]

    if 'NetRISavings' in utilization_data:
        formatted_utilization['net_ri_savings'] = utilization_data['NetRISavings']

    if 'TotalPotentialRISavings' in utilization_data:
        formatted_utilization['total_potential_ri_savings'] = utilization_data[
            'TotalPotentialRISavings'
        ]

    if 'AmortizedUpfrontFee' in utilization_data:
        formatted_utilization['amortized_upfront_fee'] = utilization_data['AmortizedUpfrontFee']

    if 'AmortizedRecurringFee' in utilization_data:
        formatted_utilization['amortized_recurring_fee'] = utilization_data[
            'AmortizedRecurringFee'
        ]

    if 'TotalAmortizedFee' in utilization_data:
        formatted_utilization['total_amortized_fee'] = utilization_data['TotalAmortizedFee']

    if 'RICostForUnusedHours' in utilization_data:
        formatted_utilization['ri_cost_for_unused_hours'] = utilization_data[
            'RICostForUnusedHours'
        ]

    if 'RealizedSavings' in utilization_data:
        formatted_utilization['realized_savings'] = utilization_data['RealizedSavings']

    if 'UnrealizedSavings' in utilization_data:
        formatted_utilization['unrealized_savings'] = utilization_data['UnrealizedSavings']

    return formatted_utilization
