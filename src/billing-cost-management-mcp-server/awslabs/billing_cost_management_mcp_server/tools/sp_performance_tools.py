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
    create_aws_client,
    format_response,
    get_date_range,
    handle_aws_error,
    paginate_aws_response,
    parse_json,
)
from ..utilities.logging_utils import get_context_logger
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

IMPORTANT: For get_savings_plans_coverage, `granularity` and `group_by` are mutually
exclusive. If `group_by` is provided, `granularity` is ignored (the Cost Explorer
GetSavingsPlansCoverage API does not allow both). Valid `group_by` dimensions for
coverage are SERVICE, REGION, or INSTANCE_FAMILY.""",
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
    max_results: Optional[int] = None,
) -> Dict[str, Any]:
    """Tool that retrieves AWS Savings Plans coverage and utilization data.

    Args:
        ctx: The MCP context object
        operation: The operation to perform: 'get_savings_plans_coverage', 'get_savings_plans_utilization', or 'get_savings_plans_utilization_details'
        start_date: Start date in YYYY-MM-DD format (inclusive). Defaults to 30 days ago if not provided.
        end_date: End date in YYYY-MM-DD format (exclusive). Defaults to today if not provided.
        granularity: Time granularity of the data (DAILY or MONTHLY). Defaults to DAILY. For coverage, ignored when group_by is provided (granularity and group_by are mutually exclusive).
        metrics: List of metrics to retrieve as a JSON string. For coverage, only 'SpendCoveredBySavingsPlans' is valid.
        group_by: Optional grouping of results as a JSON string. For coverage, supports SERVICE, REGION, or INSTANCE_FAMILY.
        filter: Optional filter to apply to the results as a JSON string.
        max_results: Maximum number of results to return per page.

    Returns:
        Dict containing the savings plans coverage/utilization information
    """
    try:
        await ctx.info(f'Savings Plans Coverage/Utilization operation: {operation}')

        # Initialize Cost Explorer client using shared utility
        ce_client = create_aws_client('ce', region_name='us-east-1')

        if operation == 'get_savings_plans_coverage':
            return await get_savings_plans_coverage(
                ctx, ce_client, start_date, end_date, granularity, metrics, group_by, filter
            )
        elif operation == 'get_savings_plans_utilization':
            return await get_savings_plans_utilization(
                ctx, ce_client, start_date, end_date, granularity, filter
            )
        elif operation == 'get_savings_plans_utilization_details':
            return await get_savings_plans_utilization_details(
                ctx, ce_client, start_date, end_date, filter, max_results
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


async def get_savings_plans_coverage(
    ctx: Context,
    ce_client: Any,
    start_date: Optional[str],
    end_date: Optional[str],
    granularity: str,
    metrics: Optional[str],
    group_by: Optional[str],
    filter_expr: Optional[str],
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

        if filter_expr:
            request_params['Filter'] = parse_json(filter_expr, 'filter')

        # Use the paginate_aws_response utility for consistent pagination
        all_coverages, pagination_metadata = await paginate_aws_response(
            ctx=ctx,
            operation_name='GetSavingsPlansCoverage',
            api_function=ce_client.get_savings_plans_coverage,
            request_params=request_params,
            result_key='SavingsPlansCoverages',
            token_param='NextToken',
            token_key='NextToken',
            max_pages=None,
        )

        # Format the response data
        formatted_response = {
            'savings_plans_coverages': all_coverages,
            'pagination': pagination_metadata,
            'time_period': {'start': start, 'end': end},
            'granularity': granularity,
        }

        # Add total coverage metrics if available
        if all_coverages:
            # We need to make one call to get the Total
            initial_response = ce_client.get_savings_plans_coverage(**request_params)
            if 'Total' in initial_response:
                formatted_response['total'] = initial_response['Total']

        return format_response('success', formatted_response)

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
        if filter_expr:
            request_params['Filter'] = parse_json(filter_expr, 'filter')

        response = ce_client.get_savings_plans_utilization(**request_params)

        utilizations_by_time = response.get('SavingsPlansUtilizationsByTime', [])
        total = response.get('Total')

        formatted_response: Dict[str, Any] = {
            'savings_plans_utilizations': utilizations_by_time,
            'time_period': {'start': start, 'end': end},
            'granularity': granularity,
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


async def get_savings_plans_utilization_details(
    ctx: Context,
    ce_client: Any,
    start_date: Optional[str],
    end_date: Optional[str],
    filter_expr: Optional[str],
    max_results: Optional[int],
) -> Dict[str, Any]:
    """Retrieves detailed Savings Plans utilization data.

    Args:
        ctx: The MCP context
        ce_client: Cost Explorer client
        start_date: Start date for the query
        end_date: End date for the query
        filter_expr: Filter expression as JSON string
        max_results: Maximum results to return

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
        if filter_expr:
            request_params['Filter'] = parse_json(filter_expr, 'filter')

        if max_results:
            request_params['MaxResults'] = int(max_results)
        else:
            request_params['MaxResults'] = 20  # Default

        # Use the paginate_aws_response utility for consistent pagination
        all_details, pagination_metadata = await paginate_aws_response(
            ctx=ctx,
            operation_name='GetSavingsPlansUtilizationDetails',
            api_function=ce_client.get_savings_plans_utilization_details,
            request_params=request_params,
            result_key='SavingsPlansUtilizationDetails',
            token_param='NextToken',
            token_key='NextToken',
            max_pages=None,
        )

        # Check if we have any details data
        if not all_details:
            await ctx_logger.warning(
                'No Savings Plans utilization details found for the specified period'
            )
            return format_response(
                'success',
                {
                    'savings_plans_utilization_details': [],
                    'pagination': pagination_metadata,
                    'time_period': {'start': start, 'end': end},
                    'total_count': 0,
                    'message': 'No Savings Plans utilization details found for the specified period. This could be because you do not have any active Savings Plans, or because the specified date range is outside your Savings Plans period.',
                },
            )

        formatted_response: Dict[str, Any] = {
            'savings_plans_utilization_details': all_details,
            'pagination': pagination_metadata,
            'time_period': {'start': start, 'end': end},
            'total_count': len(all_details),
        }

        return format_response('success', formatted_response)

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(
            ctx, e, 'get_savings_plans_utilization_details', 'Cost Explorer'
        )
