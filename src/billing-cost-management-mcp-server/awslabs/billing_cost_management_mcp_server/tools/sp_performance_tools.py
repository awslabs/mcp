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
from typing import Any, Dict, Optional, Union


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
3. get_savings_plans_utilization_details: Shows detailed per-Savings Plan utilization""",
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
        granularity: Time granularity of the data (DAILY or MONTHLY). Defaults to DAILY.
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
            'Granularity': granularity,
            'Metrics': metrics_list,
        }

        # Add optional parameters if provided
        if group_by:
            request_params['GroupBy'] = parse_json(group_by, 'group_by')

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
        request_params = {
            'TimePeriod': {'Start': start, 'End': end},
            'Granularity': granularity,
        }

        # Add optional parameters if provided
        if filter_expr:
            request_params['Filter'] = parse_json(filter_expr, 'filter')

        # Use the paginate_aws_response utility for consistent pagination
        all_utilizations, pagination_metadata = await paginate_aws_response(
            ctx=ctx,
            operation_name='GetSavingsPlansUtilization',
            api_function=ce_client.get_savings_plans_utilization,
            request_params=request_params,
            result_key='SavingsPlansUtilizations',
            token_param='NextToken',
            token_key='NextToken',
            max_pages=None,
        )

        # Check if we have any utilization data
        if not all_utilizations:
            await ctx_logger.warning(
                'No Savings Plans utilization data found for the specified period'
            )
            return format_response(
                'success',
                {
                    'savings_plans_utilizations': [],
                    'pagination': pagination_metadata,
                    'time_period': {'start': start, 'end': end},
                    'granularity': granularity,
                    'message': 'No Savings Plans utilization data found for the specified period. This could be because you do not have any active Savings Plans, or because the specified date range is outside your Savings Plans period.',
                },
            )

        # Format utilization data for better readability with proper default values
        formatted_utilizations = []
        for utilization in all_utilizations:
            # Helper function to parse monetary values with defaults
            def parse_monetary_value(key: str) -> Dict[str, Union[float, str]]:
                value = utilization.get(key, {})
                if not value or not isinstance(value, dict):
                    return {'amount': 0.0, 'currency': 'USD', 'formatted': '0.0 USD'}

                amount = value.get('Amount', 0.0)
                # Handle numeric strings or None values
                try:
                    amount = float(amount) if amount is not None else 0.0
                except (ValueError, TypeError):
                    amount = 0.0

                currency = value.get('Unit', 'USD')
                return {
                    'amount': amount,
                    'currency': currency,
                    'formatted': f'{amount} {currency}',
                }

            # Get time period with defaults
            time_period = utilization.get('TimePeriod', {})
            if not time_period:
                time_period = {'Start': start, 'End': end}

            # Get utilization percentage with default
            utilization_pct = utilization.get('UtilizationPercentage')
            if utilization_pct is None:
                utilization_pct = 0.0
            else:
                try:
                    utilization_pct = float(utilization_pct)
                except (ValueError, TypeError):
                    utilization_pct = 0.0

            # Build formatted utilization with proper defaults
            formatted_utilization = {
                'time_period': time_period,
                'total_commitment': parse_monetary_value('TotalCommitment'),
                'used_commitment': parse_monetary_value('UsedCommitment'),
                'unused_commitment': parse_monetary_value('UnusedCommitment'),
                'utilization_percentage': utilization_pct,
                'savings_plans_count': utilization.get('SavingsPlansCount', 0),
            }
            formatted_utilizations.append(formatted_utilization)

        # Format the response data
        formatted_response = {
            'savings_plans_utilizations': formatted_utilizations,
            'pagination': pagination_metadata,
            'time_period': {'start': start, 'end': end},
            'granularity': granularity,
        }

        # Add total utilization if available
        try:
            # We need to make one call to get the Total
            initial_response = ce_client.get_savings_plans_utilization(**request_params)
            if 'Total' in initial_response:
                total = initial_response['Total']

                # Parse total values with defaults
                def parse_total_monetary_value(key: str) -> Dict[str, Union[float, str]]:
                    value = total.get(key, {})
                    if not value or not isinstance(value, dict):
                        return {'amount': 0.0, 'currency': 'USD', 'formatted': '0.0 USD'}

                    amount = value.get('Amount', 0.0)
                    # Handle numeric strings or None values
                    try:
                        amount = float(amount) if amount is not None else 0.0
                    except (ValueError, TypeError):
                        amount = 0.0

                    currency = value.get('Unit', 'USD')
                    return {
                        'amount': amount,
                        'currency': currency,
                        'formatted': f'{amount} {currency}',
                    }

                # Get utilization percentage with default
                total_utilization_pct = total.get('UtilizationPercentage')
                if total_utilization_pct is None:
                    total_utilization_pct = 0.0
                else:
                    try:
                        total_utilization_pct = float(total_utilization_pct)
                    except (ValueError, TypeError):
                        total_utilization_pct = 0.0

                formatted_response['total'] = {
                    'total_commitment': parse_total_monetary_value('TotalCommitment'),
                    'used_commitment': parse_total_monetary_value('UsedCommitment'),
                    'unused_commitment': parse_total_monetary_value('UnusedCommitment'),
                    'utilization_percentage': total_utilization_pct,
                }

        except Exception as e:
            # Log but don't fail if we can't get total
            await ctx_logger.warning(f'Could not retrieve total utilization data: {str(e)}')
            # Provide default total based on summing values if possible
            if formatted_utilizations:
                total_util_pct = sum(
                    item['utilization_percentage'] for item in formatted_utilizations
                ) / len(formatted_utilizations)
                formatted_response['total'] = {
                    'utilization_percentage': total_util_pct,
                    'note': 'Estimated from individual utilization data',
                }

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

        # Format utilization details for better readability
        formatted_details = []
        for detail in all_details:
            # Helper function to parse monetary values with defaults
            def parse_monetary_value(key: str) -> Dict[str, Union[float, str]]:
                value = detail.get(key, {})
                if not value or not isinstance(value, dict):
                    return {'amount': 0.0, 'currency': 'USD', 'formatted': '0.0 USD'}

                amount = value.get('Amount', 0.0)
                # Handle numeric strings or None values
                try:
                    amount = float(amount) if amount is not None else 0.0
                except (ValueError, TypeError):
                    amount = 0.0

                currency = value.get('Unit', 'USD')
                return {
                    'amount': amount,
                    'currency': currency,
                    'formatted': f'{amount} {currency}',
                }

            # Get utilization percentage with default
            utilization_pct = detail.get('UtilizationPercentage')
            if utilization_pct is None:
                utilization_pct = 0.0
            else:
                try:
                    utilization_pct = float(utilization_pct)
                except (ValueError, TypeError):
                    utilization_pct = 0.0

            # Build formatted detail with proper defaults
            formatted_detail = {
                'savings_plan_arn': detail.get('SavingsPlanArn', ''),
                'attributes': detail.get('Attributes', {}),
                'utilization': {
                    'total_commitment': parse_monetary_value('TotalCommitment'),
                    'used_commitment': parse_monetary_value('UsedCommitment'),
                    'unused_commitment': parse_monetary_value('UnusedCommitment'),
                    'utilization_percentage': utilization_pct,
                },
                'savings': {
                    'net_savings': parse_monetary_value('NetSavings'),
                    'on_demand_cost_equivalent': parse_monetary_value('OnDemandCostEquivalent'),
                    'amortized_upfront_fee': parse_monetary_value('AmortizedUpfrontFee'),
                    'recurring_commitment': parse_monetary_value('RecurringCommitment'),
                },
            }

            # Extract relevant information from attributes if available
            if 'Attributes' in detail and detail['Attributes']:
                attributes = detail['Attributes']

                # Format and extract useful attribute information
                region = attributes.get('region')
                instance_family = attributes.get('instanceFamily')
                savings_plan_type = attributes.get('savingsPlanType')

                # Add formatted attribute info
                if region or instance_family or savings_plan_type:
                    formatted_detail['summary'] = {
                        'region': region,
                        'instance_family': instance_family,
                        'savings_plan_type': savings_plan_type,
                    }

            formatted_details.append(formatted_detail)

        # Format the response data
        formatted_response = {
            'savings_plans_utilization_details': formatted_details,
            'pagination': pagination_metadata,
            'time_period': {'start': start, 'end': end},
            'total_count': len(formatted_details),
        }

        # Add summary stats
        if formatted_details:
            try:
                total_utilization = sum(
                    detail['utilization']['utilization_percentage'] for detail in formatted_details
                ) / len(formatted_details)
                formatted_response['average_utilization_percentage'] = round(total_utilization, 2)

                total_plans = len(formatted_details)
                formatted_response['total_savings_plans'] = total_plans

                # Calculate fully utilized plans (>95%)
                fully_utilized = sum(
                    1
                    for detail in formatted_details
                    if detail['utilization']['utilization_percentage'] >= 95.0
                )
                formatted_response['fully_utilized_plans'] = fully_utilized

                # Calculate underutilized plans (<80%)
                under_utilized = sum(
                    1
                    for detail in formatted_details
                    if detail['utilization']['utilization_percentage'] < 80.0
                )
                formatted_response['under_utilized_plans'] = under_utilized

            except Exception as e:
                await ctx_logger.warning(f'Could not compute summary statistics: {str(e)}')

        return format_response('success', formatted_response)

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(
            ctx, e, 'get_savings_plans_utilization_details', 'Cost Explorer'
        )
