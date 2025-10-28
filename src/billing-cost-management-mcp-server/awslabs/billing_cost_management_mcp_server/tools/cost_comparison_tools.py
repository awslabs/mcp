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

from ..utilities.aws_service_base import (
    create_aws_client,
    format_response,
    handle_aws_error,
    parse_json,
)
from fastmcp import Context, FastMCP
from typing import Any, Dict, Optional


cost_comparison_server = FastMCP(
    name='cost-comparison-tools', instructions='Tools for working with AWS Cost Comparison API'
)


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

STRICT LIMITATIONS:
- ONLY compares exactly one month to another month
- Both periods must start on 1st day of month, end on 1st day of next month
- Cannot compare weeks, quarters, or custom periods
- DO NOT USE for general cost analysis or flexible time periods

This tool supports two main operations:
1. getCostAndUsageComparisons: Compare costs between two time periods with flexible grouping and filtering
2. getCostComparisonDrivers: Identify key factors driving cost changes between two time periods

Both operations require:
- BaselineTimePeriod: Earlier time period for comparison (must be exactly one month)
- ComparisonTimePeriod: Later time period for comparison (must be exactly one month)
- MetricForComparison: The cost metric to compare (e.g., BlendedCost, UnblendedCost)

Supported metrics for comparison include:
- AmortizedCost: Costs with upfront and recurring reservation fees spread across the period
- BlendedCost: Average cost of all usage throughout the billing period
- NetAmortizedCost: Amortized cost after discounts
- NetUnblendedCost: Unblended cost after discounts
- NormalizedUsageAmount: Normalized usage amount
- UnblendedCost: Actual costs incurred during the specified period
- UsageQuantity: Usage amounts in their respective units

You can group results by dimensions such as:
- SERVICE: AWS service (e.g., Amazon EC2, Amazon S3)
- LINKED_ACCOUNT: Member accounts in an organization
- REGION: AWS Region
- USAGE_TYPE: Type of usage (e.g., BoxUsage:t2.micro)
- INSTANCE_TYPE: EC2 instance type (e.g., t2.micro, m5.large)
- PLATFORM: Operating system (e.g., Windows, Linux)
- TENANCY: Instance tenancy (e.g., shared, dedicated)
- RECORD_TYPE: Record type (e.g., Usage, Credit, Tax)
- LEGAL_ENTITY_NAME: AWS seller of record

Note:
- Time periods must start and end on the first day of a month, with a duration of exactly one month
- The getCostComparisonDrivers operation automatically includes SERVICE and USAGE_TYPE dimensions
- Data is available for the last 13 months, or up to 38 months if multi-year data is enabled""",
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
    max_results: Optional[int] = None,
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
        metric_for_comparison: The cost metric to compare (e.g., BlendedCost, UnblendedCost, AmortizedCost)
        group_by: Optional grouping of results as a JSON string (e.g., '[{"Type": "DIMENSION", "Key": "SERVICE"}]')
        filter: Optional filter to apply to the results as a JSON string
        max_results: Maximum number of results to return (default: 10, max: 2000 for comparisons, max: 10 for drivers)
        billing_view_arn: Optional ARN of a specific billing view

    Returns:
        Dict containing the cost comparison information
    """
    try:
        await ctx.info(f'Cost comparison operation: {operation}')

        # Initialize Cost Explorer client using shared utility
        ce_client = create_aws_client('ce', region_name='us-east-1')

        if operation == 'getCostAndUsageComparisons':
            return await get_cost_and_usage_comparisons(
                ctx,
                ce_client,
                baseline_start_date,
                baseline_end_date,
                comparison_start_date,
                comparison_end_date,
                metric_for_comparison,
                group_by,
                filter,
                max_results,
                billing_view_arn,
            )
        elif operation == 'getCostComparisonDrivers':
            return await get_cost_comparison_drivers(
                ctx,
                ce_client,
                baseline_start_date,
                baseline_end_date,
                comparison_start_date,
                comparison_end_date,
                metric_for_comparison,
                group_by,
                filter,
                max_results,
                billing_view_arn,
            )
        else:
            return format_response(
                'error',
                {},
                f"Unsupported operation: {operation}. Use 'getCostAndUsageComparisons' or 'getCostComparisonDrivers'.",
            )

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
    max_results: Optional[int],
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
        max_results: Maximum results to return
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

        if filter_expr:
            request_params['Filter'] = parse_json(filter_expr, 'filter')

        if max_results:
            request_params['MaxResults'] = max_results
        else:
            request_params['MaxResults'] = 10

        if billing_view_arn:
            request_params['BillingViewArn'] = billing_view_arn

        # Collect all data with internal pagination
        all_comparisons = []
        total_cost_and_usage = None
        next_page_token = None
        page_count = 0

        while True:
            page_count += 1

            if next_page_token:
                request_params['NextPageToken'] = next_page_token

            await ctx.info(f'Fetching cost comparison page {page_count}')
            response = ce_client.get_cost_and_usage_comparisons(**request_params)

            page_comparisons = response.get('CostAndUsageComparisons', [])
            all_comparisons.extend(page_comparisons)

            await ctx.info(
                f'Retrieved {len(page_comparisons)} comparisons (total: {len(all_comparisons)})'
            )

            # Capture total from first response
            if total_cost_and_usage is None:
                total_cost_and_usage = response.get('TotalCostAndUsage')

            next_page_token = response.get('NextPageToken')
            if not next_page_token:
                break

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

        return format_response('success', formatted_response)

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
    max_results: Optional[int],
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
        max_results: Maximum results to return
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

        if filter_expr:
            request_params['Filter'] = parse_json(filter_expr, 'filter')

        if max_results:
            request_params['MaxResults'] = max_results
        else:
            request_params['MaxResults'] = 10

        if billing_view_arn:
            request_params['BillingViewArn'] = billing_view_arn

        # Collect all data with internal pagination
        all_drivers = []
        next_page_token = None
        page_count = 0

        while True:
            page_count += 1

            if next_page_token:
                request_params['NextPageToken'] = next_page_token

            await ctx.info(f'Fetching cost comparison drivers page {page_count}')
            response = ce_client.get_cost_comparison_drivers(**request_params)

            page_drivers = response.get('CostComparisonDrivers', [])
            all_drivers.extend(page_drivers)

            await ctx.info(f'Retrieved {len(page_drivers)} drivers (total: {len(all_drivers)})')

            next_page_token = response.get('NextPageToken')
            if not next_page_token:
                break

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

        return format_response('success', formatted_response)

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'get_cost_comparison_drivers', 'Cost Explorer')
