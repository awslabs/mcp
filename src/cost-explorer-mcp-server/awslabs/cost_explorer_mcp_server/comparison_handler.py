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

"""Cost Explorer MCP server implementation.

Comparison tools for Cost Explorer MCP Server.
"""

import os
import sys
from awslabs.cost_explorer_mcp_server.helpers import (
    create_detailed_group_key,
    extract_group_key_from_complex_selector,
    extract_usage_context_from_selector,
    get_cost_explorer_client,
    validate_comparison_date_range,
    validate_expression,
    validate_group_by,
)
from awslabs.cost_explorer_mcp_server.models import DateRange
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Any, Dict, Optional, Union


# Configure Loguru logging
logger.remove()
logger.add(sys.stderr, level=os.getenv('FASTMCP_LOG_LEVEL', 'WARNING'))


async def get_cost_and_usage_comparisons(
    ctx: Context,
    baseline_date_range: DateRange,
    comparison_date_range: DateRange,
    metric_for_comparison: str = Field(
        'UnblendedCost',
        description='The cost and usage metric to compare. Valid values are AmortizedCost, BlendedCost, NetAmortizedCost, NetUnblendedCost, NormalizedUsageAmount, UnblendedCost, and UsageQuantity.',
    ),
    group_by: Optional[Union[Dict[str, str], str]] = Field(
        'SERVICE',
        description="Either a dictionary with Type and Key for grouping comparisons, or simply a string key to group by (which will default to DIMENSION type). Example dictionary: {'Type': 'DIMENSION', 'Key': 'SERVICE'}. Example string: 'SERVICE'.",
    ),
    filter_expression: Optional[Dict[str, Any]] = Field(
        None,
        description='Filter criteria as a Python dictionary to narrow down AWS cost comparisons. Supports filtering by Dimensions (SERVICE, REGION, etc.), Tags, or CostCategories. You can use logical operators (And, Or, Not) for complex filters. Same format as get_cost_and_usage filter_expression.',
    ),
) -> Dict[str, Any]:
    """Compare AWS costs and usage between two time periods.

    This tool compares cost and usage data between a baseline period and a comparison period,
    providing percentage changes and absolute differences. Both periods must be exactly one month
    and start/end on the first day of a month. The tool also provides detailed cost drivers
    when available, showing what specific factors contributed to cost changes.

    Important requirements:
    - Both periods must be exactly one month duration
    - Dates must start and end on the first day of a month (e.g., 2025-01-01 to 2025-02-01)
    - Maximum lookback of 13 months (38 months if multi-year data enabled)
    - Start dates must be equal to or no later than current date

    Example: Compare January 2025 vs December 2024 EC2 costs
        await get_cost_and_usage_comparisons(
            ctx=context,
            baseline_date_range={
                "start_date": "2024-12-01",  # December 2024
                "end_date": "2025-01-01"
            },
            comparison_date_range={
                "start_date": "2025-01-01",  # January 2025
                "end_date": "2025-02-01"
            },
            metric_for_comparison="UnblendedCost",
            group_by={"Type": "DIMENSION", "Key": "SERVICE"},
            filter_expression={
                "Dimensions": {
                    "Key": "SERVICE",
                    "Values": ["Amazon Elastic Compute Cloud - Compute"],
                    "MatchOptions": ["EQUALS"]
                }
            }
        )

    Args:
        ctx: MCP context
        baseline_date_range: The reference period for comparison (exactly one month)
        comparison_date_range: The comparison period (exactly one month)
        metric_for_comparison: Cost metric to compare (UnblendedCost, BlendedCost, etc.)
        group_by: Either a dictionary with Type and Key, or simply a string key to group by
        filter_expression: Filter criteria as a Python dictionary

    Returns:
        Dictionary containing comparison data with percentage changes, absolute differences,
        and detailed cost drivers when available
    """
    # Initialize variables at function scope
    baseline_start = baseline_date_range.start_date
    baseline_end = baseline_date_range.end_date
    comparison_start = comparison_date_range.start_date
    comparison_end = comparison_date_range.end_date

    try:
        # Validate both date ranges meet comparison API requirements
        is_valid_baseline, error_baseline = validate_comparison_date_range(
            baseline_start, baseline_end
        )
        if not is_valid_baseline:
            return {'error': f'Baseline period error: {error_baseline}'}

        is_valid_comparison, error_comparison = validate_comparison_date_range(
            comparison_start, comparison_end
        )
        if not is_valid_comparison:
            return {'error': f'Comparison period error: {error_comparison}'}

        # Define valid comparison metrics
        valid_comparison_metrics = [
            'AmortizedCost',
            'BlendedCost',
            'NetAmortizedCost',
            'NetUnblendedCost',
            'NormalizedUsageAmount',
            'UnblendedCost',
            'UsageQuantity',
        ]

        if metric_for_comparison not in valid_comparison_metrics:
            return {
                'error': f'Invalid metric_for_comparison: {metric_for_comparison}. Valid values are {", ".join(valid_comparison_metrics)}.'
            }

        # Process filter - reuse existing validation
        filter_criteria = filter_expression

        # Validate filter expression if provided
        if filter_criteria:
            validation_result = validate_expression(filter_criteria, baseline_start, baseline_end)
            if 'error' in validation_result:
                return validation_result

        # Process group_by - reuse existing logic
        if group_by is None:
            group_by = {'Type': 'DIMENSION', 'Key': 'SERVICE'}
        elif isinstance(group_by, str):
            group_by = {'Type': 'DIMENSION', 'Key': group_by}

        # Validate group_by using existing function
        validation_result = validate_group_by(group_by)
        if 'error' in validation_result:
            return validation_result

        # Prepare API call parameters
        comparison_params = {
            'BaselineTimePeriod': {
                'Start': baseline_start,
                'End': baseline_end,
            },
            'ComparisonTimePeriod': {
                'Start': comparison_start,
                'End': comparison_end,
            },
            'MetricForComparison': metric_for_comparison,
            'GroupBy': [{'Type': group_by['Type'].upper(), 'Key': group_by['Key']}],
        }

        # Add filter if provided
        if filter_criteria:
            comparison_params['Filter'] = filter_criteria

        # Get comparison data
        grouped_comparisons = {}
        next_token = None
        ce = get_cost_explorer_client()

        while True:
            if next_token:
                comparison_params['NextPageToken'] = next_token

            try:
                response = ce.get_cost_and_usage_comparisons(**comparison_params)
            except Exception as e:
                logger.error(f'Error calling Cost Explorer comparison API: {e}')
                return {'error': f'AWS Cost Explorer comparison API error: {str(e)}'}

            # Process comparison results
            for comparison_result in response.get('CostAndUsageComparisons', []):
                # Extract group key from CostAndUsageSelector
                selector = comparison_result.get('CostAndUsageSelector', {})
                group_key = 'Unknown'

                # Extract the actual dimension value (e.g., service name)
                if 'Dimensions' in selector:
                    dimension_info = selector['Dimensions']
                    if 'Values' in dimension_info and dimension_info['Values']:
                        group_key = dimension_info['Values'][0]  # Use the first value as group key
                elif 'Tags' in selector:
                    tag_info = selector['Tags']
                    if 'Values' in tag_info and tag_info['Values']:
                        group_key = f'{tag_info.get("Key", "Tag")}:{tag_info["Values"][0]}'
                elif 'CostCategories' in selector:
                    cc_info = selector['CostCategories']
                    if 'Values' in cc_info and cc_info['Values']:
                        group_key = f'{cc_info.get("Key", "Category")}:{cc_info["Values"][0]}'

                # Process metrics for this group
                metrics = comparison_result.get('Metrics', {})

                for metric_name, metric_data in metrics.items():
                    if metric_name == metric_for_comparison:
                        baseline_amount = float(metric_data.get('BaselineTimePeriodAmount', 0))
                        comparison_amount = float(metric_data.get('ComparisonTimePeriodAmount', 0))
                        difference = float(metric_data.get('Difference', 0))
                        unit = metric_data.get('Unit', 'USD')

                        # Calculate percentage change
                        if baseline_amount != 0:
                            percentage_change = (difference / baseline_amount) * 100
                        else:
                            percentage_change = 100.0 if comparison_amount > 0 else 0.0

                        grouped_comparisons[group_key] = {
                            'baseline_value': round(baseline_amount, 2),
                            'comparison_value': round(comparison_amount, 2),
                            'absolute_change': round(difference, 2),
                            'percentage_change': round(percentage_change, 2),
                            'unit': unit,
                        }

            next_token = response.get('NextPageToken')
            if not next_token:
                break

        # Process total cost and usage
        total_data = {}
        total_cost_and_usage = response.get('TotalCostAndUsage', {})

        for metric_name, metric_data in total_cost_and_usage.items():
            if metric_name == metric_for_comparison:
                baseline_total = float(metric_data.get('BaselineTimePeriodAmount', 0))
                comparison_total = float(metric_data.get('ComparisonTimePeriodAmount', 0))
                difference_total = float(metric_data.get('Difference', 0))
                unit = metric_data.get('Unit', 'USD')

                # Calculate total percentage change
                if baseline_total != 0:
                    total_percentage_change = (difference_total / baseline_total) * 100
                else:
                    total_percentage_change = 100.0 if comparison_total > 0 else 0.0

                total_data = {
                    'baseline_value': round(baseline_total, 2),
                    'comparison_value': round(comparison_total, 2),
                    'absolute_change': round(difference_total, 2),
                    'percentage_change': round(total_percentage_change, 2),
                    'unit': unit,
                }
                break  # We found our metric

        # If no total data was found, calculate from grouped data
        if not total_data and grouped_comparisons:
            total_baseline = sum(comp['baseline_value'] for comp in grouped_comparisons.values())
            total_comparison = sum(
                comp['comparison_value'] for comp in grouped_comparisons.values()
            )
            total_difference = sum(
                comp['absolute_change'] for comp in grouped_comparisons.values()
            )

            if total_baseline != 0:
                total_percentage_change = (total_difference / total_baseline) * 100
            else:
                total_percentage_change = 100.0 if total_comparison > 0 else 0.0

            total_data = {
                'baseline_value': round(total_baseline, 2),
                'comparison_value': round(total_comparison, 2),
                'absolute_change': round(total_difference, 2),
                'percentage_change': round(total_percentage_change, 2),
                'unit': list(grouped_comparisons.values())[0].get('unit', 'USD')
                if grouped_comparisons
                else 'USD',
            }

        # Build response
        result = {
            'baseline_period': f'{baseline_start} to {baseline_end}',
            'comparison_period': f'{comparison_start} to {comparison_end}',
            'metric': metric_for_comparison,
            'grouped_by': group_by['Key'],
            'comparisons': grouped_comparisons,
            'total_comparison': total_data,
            'metadata': {
                'grouping_type': group_by['Type'],
                'total_groups': len(grouped_comparisons),
            },
        }

        return result

    except Exception as e:
        logger.error(
            f'Error generating cost comparison between {baseline_start}-{baseline_end} and {comparison_start}-{comparison_end}: {e}'
        )
        return {'error': f'Error generating cost comparison: {str(e)}'}


async def get_cost_comparison_drivers(
    ctx: Context,
    baseline_date_range: DateRange,
    comparison_date_range: DateRange,
    metric_for_comparison: str = Field(
        'UnblendedCost',
        description='The cost and usage metric to analyze drivers for. Valid values are AmortizedCost, BlendedCost, NetAmortizedCost, NetUnblendedCost, NormalizedUsageAmount, UnblendedCost, and UsageQuantity.',
    ),
    group_by: Optional[Union[Dict[str, str], str]] = Field(
        'SERVICE',
        description="Either a dictionary with Type and Key for grouping driver analysis, or simply a string key to group by (which will default to DIMENSION type). Example dictionary: {'Type': 'DIMENSION', 'Key': 'SERVICE'}. Example string: 'SERVICE'.",
    ),
    filter_expression: Optional[Dict[str, Any]] = Field(
        None,
        description='Filter criteria as a Python dictionary to narrow down AWS cost driver analysis. Supports filtering by Dimensions (SERVICE, REGION, etc.), Tags, or CostCategories. You can use logical operators (And, Or, Not) for complex filters. Same format as get_cost_and_usage filter_expression.',
    ),
) -> Dict[str, Any]:
    """Analyze what drove cost changes between two time periods.

    This tool provides detailed analysis of the TOP 10 most significant cost drivers
    that caused changes between periods. AWS returns only the most impactful drivers
    to focus on the changes that matter most for cost optimization.

    The tool provides rich insights including:
    - Top 10 most significant cost drivers across all services (or filtered subset)
    - Specific usage types that drove changes (e.g., "BoxUsage:c5.large", "NatGateway-Hours")
    - Multiple driver types: usage changes, savings plan impacts, enterprise discounts, support fees
    - Both cost and usage quantity changes with units (hours, GB-months, etc.)
    - Context about what infrastructure components changed
    - Detailed breakdown of usage patterns vs pricing changes

    Can be used with or without filters:
    - Without filters: Shows top 10 cost drivers across ALL services
    - With filters: Shows top 10 cost drivers within the filtered scope
    - Multiple services: Can filter to multiple services and get top 10 within that scope

    Both periods must be exactly one month and start/end on the first day of a month.

    Important requirements:
    - Both periods must be exactly one month duration
    - Dates must start and end on the first day of a month (e.g., 2025-01-01 to 2025-02-01)
    - Maximum lookback of 13 months (38 months if multi-year data enabled)
    - Start dates must be equal to or no later than current date
    - Results limited to top 10 most significant drivers (no pagination)

    Example: Analyze top 10 cost drivers across all services
        await get_cost_comparison_drivers(
            ctx=context,
            baseline_date_range={
                "start_date": "2024-12-01",  # December 2024
                "end_date": "2025-01-01"
            },
            comparison_date_range={
                "start_date": "2025-01-01",  # January 2025
                "end_date": "2025-02-01"
            },
            metric_for_comparison="UnblendedCost",
            group_by={"Type": "DIMENSION", "Key": "SERVICE"}
            # No filter = top 10 drivers across all services
        )

    Example: Analyze top 10 cost drivers for specific services
        await get_cost_comparison_drivers(
            ctx=context,
            baseline_date_range={
                "start_date": "2024-12-01",
                "end_date": "2025-01-01"
            },
            comparison_date_range={
                "start_date": "2025-01-01",
                "end_date": "2025-02-01"
            },
            metric_for_comparison="UnblendedCost",
            group_by={"Type": "DIMENSION", "Key": "SERVICE"},
            filter_expression={
                "Dimensions": {
                    "Key": "SERVICE",
                    "Values": ["Amazon Elastic Compute Cloud - Compute", "Amazon Simple Storage Service"],
                    "MatchOptions": ["EQUALS"]
                }
            }
        )

    Args:
        ctx: MCP context
        baseline_date_range: The reference period for comparison (exactly one month)
        comparison_date_range: The comparison period (exactly one month)
        metric_for_comparison: Cost metric to analyze drivers for (UnblendedCost, BlendedCost, etc.)
        group_by: Either a dictionary with Type and Key, or simply a string key to group by
        filter_expression: Filter criteria as a Python dictionary

    Returns:
        with specific usage types, usage quantity changes, driver types (savings plans, discounts, usage changes, support fees), and contextual information
    """
    # Initialize variables at function scope
    baseline_start = baseline_date_range.start_date
    baseline_end = baseline_date_range.end_date
    comparison_start = comparison_date_range.start_date
    comparison_end = comparison_date_range.end_date

    try:
        # Validate both date ranges meet comparison API requirements
        is_valid_baseline, error_baseline = validate_comparison_date_range(
            baseline_start, baseline_end
        )
        if not is_valid_baseline:
            return {'error': f'Baseline period error: {error_baseline}'}

        is_valid_comparison, error_comparison = validate_comparison_date_range(
            comparison_start, comparison_end
        )
        if not is_valid_comparison:
            return {'error': f'Comparison period error: {error_comparison}'}

        # Define valid comparison metrics
        valid_comparison_metrics = [
            'AmortizedCost',
            'BlendedCost',
            'NetAmortizedCost',
            'NetUnblendedCost',
            'NormalizedUsageAmount',
            'UnblendedCost',
            'UsageQuantity',
        ]

        if metric_for_comparison not in valid_comparison_metrics:
            return {
                'error': f'Invalid metric_for_comparison: {metric_for_comparison}. Valid values are {", ".join(valid_comparison_metrics)}.'
            }

        # Process filter - reuse existing validation
        filter_criteria = filter_expression

        # Validate filter expression if provided
        if filter_criteria:
            validation_result = validate_expression(filter_criteria, baseline_start, baseline_end)
            if 'error' in validation_result:
                return validation_result

        # Process group_by - reuse existing logic
        if group_by is None:
            group_by = {'Type': 'DIMENSION', 'Key': 'SERVICE'}
        elif isinstance(group_by, str):
            group_by = {'Type': 'DIMENSION', 'Key': group_by}

        # Validate group_by using existing function
        validation_result = validate_group_by(group_by)
        if 'error' in validation_result:
            return validation_result

        # Prepare API call parameters
        driver_params = {
            'BaselineTimePeriod': {
                'Start': baseline_start,
                'End': baseline_end,
            },
            'ComparisonTimePeriod': {
                'Start': comparison_start,
                'End': comparison_end,
            },
            'MetricForComparison': metric_for_comparison,
            'GroupBy': [{'Type': group_by['Type'].upper(), 'Key': group_by['Key']}],
        }

        # Add filter if provided
        if filter_criteria:
            driver_params['Filter'] = filter_criteria

        # Get cost driver data
        grouped_drivers = {}
        next_token = None
        ce = get_cost_explorer_client()

        while True:
            if next_token:
                driver_params['NextPageToken'] = next_token

            try:
                response = ce.get_cost_comparison_drivers(**driver_params)
            except Exception as e:
                logger.error(f'Error calling Cost Explorer comparison drivers API: {e}')
                return {'error': f'AWS Cost Explorer comparison drivers API error: {str(e)}'}

            # Process cost comparison drivers
            for driver_result in response.get('CostComparisonDrivers', []):
                # Extract group key from CostSelector using improved logic
                selector = driver_result.get('CostSelector', {})
                group_key = extract_group_key_from_complex_selector(selector, group_by)

                # Extract comprehensive context (service, usage type, region, etc.)
                usage_context = extract_usage_context_from_selector(selector)

                # Create detailed group key with context
                detailed_key = create_detailed_group_key(group_key, usage_context, group_by)

                # Process metrics for this group
                metrics = driver_result.get('Metrics', {})

                for metric_name, metric_data in metrics.items():
                    if metric_name == metric_for_comparison:
                        baseline_amount = float(metric_data.get('BaselineTimePeriodAmount', 0))
                        comparison_amount = float(metric_data.get('ComparisonTimePeriodAmount', 0))
                        difference = float(metric_data.get('Difference', 0))
                        unit = metric_data.get('Unit', 'USD')

                        # Calculate percentage change
                        if baseline_amount != 0:
                            percentage_change = (difference / baseline_amount) * 100
                        else:
                            percentage_change = 100.0 if comparison_amount > 0 else 0.0

                        driver_data = {
                            'baseline_value': round(baseline_amount, 2),
                            'comparison_value': round(comparison_amount, 2),
                            'absolute_change': round(difference, 2),
                            'percentage_change': round(percentage_change, 2),
                            'unit': unit,
                            'context': usage_context,  # Full context information
                            'primary_group_key': group_key,  # The actual group key value
                            'cost_drivers': [],
                        }

                        # Process detailed cost drivers
                        cost_drivers = driver_result.get('CostDrivers', [])
                        for driver in cost_drivers:
                            driver_metrics = driver.get('Metrics', {})

                            # Process the main comparison metric
                            if metric_for_comparison in driver_metrics:
                                driver_metric_data = driver_metrics[metric_for_comparison]
                                driver_baseline = float(
                                    driver_metric_data.get('BaselineTimePeriodAmount', 0)
                                )
                                driver_comparison = float(
                                    driver_metric_data.get('ComparisonTimePeriodAmount', 0)
                                )
                                driver_difference = float(driver_metric_data.get('Difference', 0))

                                # Calculate driver percentage change
                                if driver_baseline != 0:
                                    driver_percentage = (driver_difference / driver_baseline) * 100
                                else:
                                    driver_percentage = 100.0 if driver_comparison > 0 else 0.0

                                driver_info = {
                                    'type': driver.get('Type', 'Unknown'),
                                    'name': driver.get('Name', 'Unknown'),
                                    'baseline_value': round(driver_baseline, 2),
                                    'comparison_value': round(driver_comparison, 2),
                                    'absolute_change': round(driver_difference, 2),
                                    'percentage_change': round(driver_percentage, 2),
                                    'unit': driver_metric_data.get('Unit', 'USD'),
                                    'additional_metrics': {},
                                }

                                # Process additional metrics (like UsageQuantity)
                                for additional_metric, additional_data in driver_metrics.items():
                                    if additional_metric != metric_for_comparison:
                                        add_baseline = float(
                                            additional_data.get('BaselineTimePeriodAmount', 0)
                                        )
                                        add_comparison = float(
                                            additional_data.get('ComparisonTimePeriodAmount', 0)
                                        )
                                        add_difference = float(
                                            additional_data.get('Difference', 0)
                                        )
                                        add_unit = additional_data.get('Unit', '')

                                        # Calculate percentage for additional metric
                                        if add_baseline != 0:
                                            add_percentage = (add_difference / add_baseline) * 100
                                        else:
                                            add_percentage = 100.0 if add_comparison > 0 else 0.0

                                        driver_info['additional_metrics'][additional_metric] = {
                                            'baseline_value': round(add_baseline, 2),
                                            'comparison_value': round(add_comparison, 2),
                                            'absolute_change': round(add_difference, 2),
                                            'percentage_change': round(add_percentage, 2),
                                            'unit': add_unit,
                                        }

                                driver_data['cost_drivers'].append(driver_info)

                        # Sort cost drivers by absolute impact (descending)
                        driver_data['cost_drivers'].sort(
                            key=lambda x: abs(x['absolute_change']), reverse=True
                        )

                        grouped_drivers[detailed_key] = driver_data

            next_token = response.get('NextPageToken')
            if not next_token:
                break

        # Calculate totals from grouped data
        total_baseline = sum(driver['baseline_value'] for driver in grouped_drivers.values())
        total_comparison = sum(driver['comparison_value'] for driver in grouped_drivers.values())
        total_difference = sum(driver['absolute_change'] for driver in grouped_drivers.values())

        if total_baseline != 0:
            total_percentage_change = (total_difference / total_baseline) * 100
        else:
            total_percentage_change = 100.0 if total_comparison > 0 else 0.0

        # Build response
        result = {
            'baseline_period': f'{baseline_start} to {baseline_end}',
            'comparison_period': f'{comparison_start} to {comparison_end}',
            'metric': metric_for_comparison,
            'grouped_by': group_by['Key'],
            'driver_analysis': grouped_drivers,
            'total_analysis': {
                'baseline_value': round(total_baseline, 2),
                'comparison_value': round(total_comparison, 2),
                'absolute_change': round(total_difference, 2),
                'percentage_change': round(total_percentage_change, 2),
                'unit': list(grouped_drivers.values())[0].get('unit', 'USD')
                if grouped_drivers
                else 'USD',
            },
            'metadata': {
                'grouping_type': group_by['Type'],
                'total_groups': len(grouped_drivers),
                'total_drivers': sum(
                    len(driver.get('cost_drivers', [])) for driver in grouped_drivers.values()
                ),
                'has_usage_context': any(
                    driver.get('context') for driver in grouped_drivers.values()
                ),
                'has_additional_metrics': any(
                    any(
                        cost_driver.get('additional_metrics')
                        for cost_driver in driver.get('cost_drivers', [])
                    )
                    for driver in grouped_drivers.values()
                ),
            },
        }

        return result

    except Exception as e:
        logger.error(
            f'Error generating cost driver analysis between {baseline_start}-{baseline_end} and {comparison_start}-{comparison_end}: {e}'
        )
        return {'error': f'Error generating cost driver analysis: {str(e)}'}
