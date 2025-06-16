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

This server provides tools for analyzing AWS costs and usage data through the AWS Cost Explorer API.
"""

import json
import os
import pandas as pd
import sys
from awslabs.cost_explorer_mcp_server.helpers import (
    get_cost_explorer_client,
    get_dimension_values,
    get_tag_values,
    validate_date_format,
    validate_date_range,
    validate_expression,
    validate_group_by,
)
from datetime import datetime, timedelta
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import BaseModel, Field, field_validator
from typing import Any, Dict, Optional, Union


# Configure Loguru logging
logger.remove()
logger.add(sys.stderr, level=os.getenv('FASTMCP_LOG_LEVEL', 'WARNING'))

# Constants
COST_EXPLORER_END_DATE_OFFSET = 1


class DateRange(BaseModel):
    """Date range model for cost queries."""

    start_date: str = Field(
        ...,
        description='The start date of the billing period in YYYY-MM-DD format. Defaults to last month, if not provided.',
    )
    end_date: str = Field(
        ..., description='The end date of the billing period in YYYY-MM-DD format.'
    )

    @field_validator('start_date', 'end_date')
    @classmethod
    def validate_individual_dates(cls, v):
        """Validate that individual dates are in YYYY-MM-DD format and are valid dates."""
        is_valid, error = validate_date_format(v)
        if not is_valid:
            raise ValueError(error)
        return v

    def model_post_init(self, __context):
        """Validate the date range after both dates are set."""
        is_valid, error = validate_date_range(self.start_date, self.end_date)
        if not is_valid:
            raise ValueError(error)


class DimensionKey(BaseModel):
    """Dimension key model."""

    dimension_key: str = Field(
        ...,
        description='The name of the dimension to retrieve values for. Valid values are AZ, INSTANCE_TYPE, LINKED_ACCOUNT, OPERATION, PURCHASE_TYPE, SERVICE, USAGE_TYPE, PLATFORM, TENANCY, RECORD_TYPE, LEGAL_ENTITY_NAME, INVOICING_ENTITY, DEPLOYMENT_OPTION, DATABASE_ENGINE, CACHE_ENGINE, INSTANCE_TYPE_FAMILY, REGION, BILLING_ENTITY, RESERVATION_ID, SAVINGS_PLANS_TYPE, SAVINGS_PLAN_ARN, OPERATING_SYSTEM.',
    )


# Create FastMCP server
app = FastMCP(title='Cost Explorer MCP Server')


@app.tool('get_today_date')
async def get_today_date(ctx: Context) -> Dict[str, str]:
    """Retrieve current date information.

    This tool retrieves the current date in YYYY-MM-DD format and the current month in YYYY-MM format.
    It's useful for comparing if the billing period requested by the user is not in the future.

    Args:
        ctx: MCP context

    Returns:
        Dictionary containing today's date and current month
    """
    return {
        'today_date': datetime.now().strftime('%Y-%m-%d'),
        'current_month': datetime.now().strftime('%Y-%m'),
    }


@app.tool('get_dimension_values')
async def get_dimension_values_tool(
    ctx: Context, date_range: DateRange, dimension: DimensionKey
) -> Dict[str, Any]:
    """Retrieve available dimension values for AWS Cost Explorer.

    This tool retrieves all available and valid values for a specified dimension (e.g., SERVICE, REGION)
    over a period of time. This is useful for validating filter values or exploring available options
    for cost analysis.

    Args:
        ctx: MCP context
        date_range: The billing period start and end dates in YYYY-MM-DD format
        dimension: The dimension key to retrieve values for (e.g., SERVICE, REGION, LINKED_ACCOUNT)

    Returns:
        Dictionary containing the dimension name and list of available values
    """
    try:
        response = get_dimension_values(
            dimension.dimension_key, date_range.start_date, date_range.end_date
        )
        return response
    except Exception as e:
        logger.error(f'Error getting dimension values for {dimension.dimension_key}: {e}')
        return {'error': f'Error getting dimension values: {str(e)}'}


@app.tool('get_tag_values')
async def get_tag_values_tool(
    ctx: Context,
    date_range: DateRange,
    tag_key: str = Field(..., description='The tag key to retrieve values for'),
) -> Dict[str, Any]:
    """Retrieve available tag values for AWS Cost Explorer.

    This tool retrieves all available values for a specified tag key over a period of time.
    This is useful for validating tag filter values or exploring available tag options for cost analysis.

    Args:
        ctx: MCP context
        date_range: The billing period start and end dates in YYYY-MM-DD format
        tag_key: The tag key to retrieve values for

    Returns:
        Dictionary containing the tag key and list of available values
    """
    try:
        response = get_tag_values(tag_key, date_range.start_date, date_range.end_date)
        return response
    except Exception as e:
        logger.error(f'Error getting tag values for {tag_key}: {e}')
        return {'error': f'Error getting tag values: {str(e)}'}


@app.tool('get_cost_and_usage')
async def get_cost_and_usage(
    ctx: Context,
    date_range: DateRange,
    granularity: str = Field(
        'MONTHLY',
        description='The granularity at which cost data is aggregated. Valid values are DAILY, MONTHLY, and HOURLY. If not provided, defaults to MONTHLY.',
    ),
    group_by: Optional[Union[Dict[str, str], str]] = Field(
        None,
        description="Either a dictionary with Type and Key for grouping costs, or simply a string key to group by (which will default to DIMENSION type). Example dictionary: {'Type': 'DIMENSION', 'Key': 'SERVICE'}. Example string: 'SERVICE'.",
    ),
    filter_expression: Optional[Dict[str, Any]] = Field(
        None,
        description="Filter criteria as a Python dictionary to narrow down AWS costs. Supports filtering by Dimensions (SERVICE, REGION, etc.), Tags, or CostCategories. You can use logical operators (And, Or, Not) for complex filters. MatchOptions validation: For Dimensions, valid values are EQUALS and CASE_SENSITIVE. For Tags and CostCategories, valid values are EQUALS, ABSENT, and CASE_SENSITIVE (defaults to EQUALS and CASE_SENSITIVE). Examples: 1) Simple service filter: {'Dimensions': {'Key': 'SERVICE', 'Values': ['Amazon Elastic Compute Cloud - Compute', 'Amazon Simple Storage Service'], 'MatchOptions': ['EQUALS']}}. 2) Region filter: {'Dimensions': {'Key': 'REGION', 'Values': ['us-east-1'], 'MatchOptions': ['EQUALS']}}. 3) Combined filter: {'And': [{'Dimensions': {'Key': 'SERVICE', 'Values': ['Amazon Elastic Compute Cloud - Compute'], 'MatchOptions': ['EQUALS']}}, {'Dimensions': {'Key': 'REGION', 'Values': ['us-east-1'], 'MatchOptions': ['EQUALS']}}]}.",
    ),
    metric: str = Field(
        'UnblendedCost',
        description='The metric to return in the query. Valid values are AmortizedCost, BlendedCost, NetAmortizedCost, NetUnblendedCost, NormalizedUsageAmount, UnblendedCost, and UsageQuantity. IMPORTANT: For UsageQuantity, the service aggregates usage numbers without considering units, making results meaningless when mixing different unit types (e.g., compute hours + data transfer GB). To get meaningful UsageQuantity metrics, you MUST filter by USAGE_TYPE or group by USAGE_TYPE/USAGE_TYPE_GROUP to ensure consistent units.',
    ),
) -> Dict[str, Any]:
    """Retrieve AWS cost and usage data.

    This tool retrieves AWS cost and usage data for AWS services during a specified billing period,
    with optional filtering and grouping. It dynamically generates cost reports tailored to specific needs
    by specifying parameters such as granularity, billing period dates, and filter criteria.

    Note: The end_date is treated as inclusive in this tool, meaning if you specify an end_date of
    "2025-01-31", the results will include data for January 31st. This differs from the AWS Cost Explorer
    API which treats end_date as exclusive.

    IMPORTANT: When using UsageQuantity metric, AWS aggregates usage numbers without considering units.
    This makes results meaningless when different usage types have different units (e.g., EC2 compute hours
    vs data transfer GB). For meaningful UsageQuantity results, you MUST be very specific with filtering, including USAGE_TYPE or USAGE_TYPE_GROUP.

    Example: Get monthly costs for EC2 and S3 services in us-east-1 for May 2025
        await get_cost_and_usage(
            ctx=context,
            date_range={
                "start_date": "2025-05-01",
                "end_date": "2025-05-31"
            },
            granularity="MONTHLY",
            group_by={"Type": "DIMENSION", "Key": "SERVICE"},
            filter_expression={
                "And": [
                    {
                        "Dimensions": {
                            "Key": "SERVICE",
                            "Values": ["Amazon Elastic Compute Cloud - Compute", "Amazon Simple Storage Service"],
                            "MatchOptions": ["EQUALS"]
                        }
                    },
                    {
                        "Dimensions": {
                            "Key": "REGION",
                            "Values": ["us-east-1"],
                            "MatchOptions": ["EQUALS"]
                        }
                    }
                ]
            },
            metric="UnblendedCost"
        )

    Example: Get meaningful UsageQuantity for specific EC2 instance usage
        await get_cost_and_usage(
            ctx=context,
            {
            "date_range": {
                "end_date": "2025-05-01",
                "start_date": "2025-05-31"
            },
            "filter_expression": {
                "And": [
                {
                    "Dimensions": {
                    "Values": [
                        "Amazon Elastic Compute Cloud - Compute"
                    ],
                    "Key": "SERVICE",
                    "MatchOptions": [
                        "EQUALS"
                    ]
                    }
                },
                {
                    "Dimensions": {
                    "Values": [
                        "EC2: Running Hours"
                    ],
                    "Key": "USAGE_TYPE_GROUP",
                    "MatchOptions": [
                        "EQUALS"
                    ]
                    }
                }
                ]
            },
            "metric": "UsageQuantity",
            "group_by": "USAGE_TYPE",
            "granularity": "MONTHLY"
            }

    Args:
        ctx: MCP context
        date_range: The billing period start and end dates in YYYY-MM-DD format (end date is inclusive)
        granularity: The granularity at which cost data is aggregated (DAILY, MONTHLY, HOURLY)
        group_by: Either a dictionary with Type and Key, or simply a string key to group by
        filter_expression: Filter criteria as a Python dictionary
        metric: Cost metric to use (UnblendedCost, BlendedCost, etc.)

    Returns:
        Dictionary containing cost report data grouped according to the specified parameters
    """
    # Initialize variables at function scope to avoid unbound variable issues
    billing_period_start = date_range.start_date
    billing_period_end = date_range.end_date

    try:
        # Process inputs - simplified granularity validation
        granularity = str(granularity).upper()

        if granularity not in ['DAILY', 'MONTHLY', 'HOURLY']:
            return {
                'error': f'Invalid granularity: {granularity}. Valid values are DAILY, MONTHLY, and HOURLY.'
            }

        # Define valid metrics and their expected data structure
        valid_metrics = {
            'AmortizedCost': {'has_unit': True, 'is_cost': True},
            'BlendedCost': {'has_unit': True, 'is_cost': True},
            'NetAmortizedCost': {'has_unit': True, 'is_cost': True},
            'NetUnblendedCost': {'has_unit': True, 'is_cost': True},
            'UnblendedCost': {'has_unit': True, 'is_cost': True},
            'UsageQuantity': {'has_unit': True, 'is_cost': False},
        }

        if metric not in valid_metrics:
            return {
                'error': f'Invalid metric: {metric}. Valid values are {", ".join(valid_metrics.keys())}.'
            }

        metric_config = valid_metrics[metric]

        # Adjust end date for Cost Explorer API (exclusive)
        # Add one day to make the end date inclusive for the user
        billing_period_end_adj = (
            datetime.strptime(billing_period_end, '%Y-%m-%d')
            + timedelta(days=COST_EXPLORER_END_DATE_OFFSET)
        ).strftime('%Y-%m-%d')

        # Process filter
        filter_criteria = filter_expression

        # Validate filter expression if provided
        if filter_criteria:
            # This validates both structure and values against AWS Cost Explorer
            validation_result = validate_expression(
                filter_criteria, billing_period_start, billing_period_end_adj
            )
            if 'error' in validation_result:
                return validation_result

        # Process group_by
        if not group_by:
            group_by = {'Type': 'DIMENSION', 'Key': 'SERVICE'}
        elif isinstance(group_by, str):
            group_by = {'Type': 'DIMENSION', 'Key': group_by}

        # Validate group_by using the existing validate_group_by function
        validation_result = validate_group_by(group_by)
        if 'error' in validation_result:
            return validation_result

        # Prepare API call parameters
        common_params = {
            'TimePeriod': {
                'Start': billing_period_start,
                'End': billing_period_end_adj,
            },
            'Granularity': granularity,
            'GroupBy': [{'Type': group_by['Type'].upper(), 'Key': group_by['Key']}],
            'Metrics': [metric],
        }

        if filter_criteria:
            common_params['Filter'] = filter_criteria

        # Get cost data
        grouped_costs = {}
        next_token = None
        ce = get_cost_explorer_client()

        while True:
            if next_token:
                common_params['NextPageToken'] = next_token

            try:
                response = ce.get_cost_and_usage(**common_params)
            except Exception as e:
                logger.error(f'Error calling Cost Explorer API: {e}')
                return {'error': f'AWS Cost Explorer API error: {str(e)}'}

            for result_by_time in response['ResultsByTime']:
                date = result_by_time['TimePeriod']['Start']
                for group in result_by_time.get('Groups', []):
                    if not group.get('Keys') or len(group['Keys']) == 0:
                        logger.warning(f'Skipping group with no keys: {group}')
                        continue

                    group_key = group['Keys'][0]

                    # Validate that the metric exists in the response
                    if metric not in group.get('Metrics', {}):
                        logger.error(
                            f"Metric '{metric}' not found in response for group {group_key}"
                        )
                        return {
                            'error': f"Metric '{metric}' not found in response for group {group_key}"
                        }

                    try:
                        metric_data = group['Metrics'][metric]

                        # Validate metric data structure
                        if 'Amount' not in metric_data:
                            logger.error(
                                f'Amount not found in metric data for {group_key}: {metric_data}'
                            )
                            return {
                                'error': "Invalid response format: 'Amount' not found in metric data"
                            }

                        # Process based on metric type
                        if metric_config['is_cost']:
                            # Handle cost metrics
                            cost = float(metric_data['Amount'])
                            grouped_costs.setdefault(date, {}).update({group_key: cost})
                        else:
                            # Handle usage metrics (UsageQuantity, NormalizedUsageAmount)
                            if 'Unit' not in metric_data and metric_config['has_unit']:
                                logger.warning(
                                    f"Unit not found in {metric} data for {group_key}, using 'Unknown' as unit"
                                )
                                unit = 'Unknown'
                            else:
                                unit = metric_data.get('Unit', 'Count')
                            amount = float(metric_data['Amount'])
                            grouped_costs.setdefault(date, {}).update({group_key: (amount, unit)})
                    except (ValueError, TypeError) as e:
                        logger.error(f'Error processing metric data: {e}, group: {group_key}')
                        return {'error': f'Error processing metric data: {str(e)}'}

            next_token = response.get('NextPageToken')
            if not next_token:
                break

        # Process results
        if not grouped_costs:
            logger.info(
                f'No cost data found for the specified parameters: {billing_period_start} to {billing_period_end}'
            )
            return {
                'message': 'No cost data found for the specified parameters',
                'GroupedCosts': {},
            }

        try:
            if metric_config['is_cost']:
                # Process cost metrics
                df = pd.DataFrame.from_dict(grouped_costs).round(2)

                # Dynamic labeling based on group dimension
                group_dimension = group_by['Key'].lower().replace('_', ' ')
                df[f'{group_dimension.title()} Total'] = df.sum(axis=1).round(2)
                df.loc[f'Total {metric}'] = df.sum().round(2)
                df = df.sort_values(by=f'{group_dimension.title()} Total', ascending=False)

                result = {'GroupedCosts': df.to_dict()}
            else:
                # Process usage metrics with cleaner structure
                result_data = {}
                for date, groups in grouped_costs.items():
                    result_data[date] = {}
                    for group_key, (amount, unit) in groups.items():
                        result_data[date][group_key] = {
                            'amount': round(float(amount), 2),
                            'unit': unit,
                        }

                # Add metadata for usage metrics
                result = {
                    'metadata': {
                        'grouped_by': group_by['Key'],
                        'metric': metric,
                        'period': f'{billing_period_start} to {billing_period_end}',
                    },
                    'GroupedUsage': result_data,
                }
        except Exception as e:
            logger.error(f'Error processing cost data into DataFrame: {e}')
            return {
                'error': f'Error processing cost data: {str(e)}',
                'raw_data': grouped_costs,
            }

        # Test JSON serialization first, only stringify if needed
        try:
            json.dumps(result)
            return result
        except (TypeError, ValueError):
            # Only stringify if JSON serialization fails
            def stringify_keys(d: Any) -> Any:
                if isinstance(d, dict):
                    return {str(k): stringify_keys(v) for k, v in d.items()}
                elif isinstance(d, list):
                    return [stringify_keys(i) if i is not None else None for i in d]
                else:
                    return d

            try:
                result = stringify_keys(result)
                return result
            except Exception as e:
                logger.error(f'Error serializing result: {e}')
                return {'error': f'Error serializing result: {str(e)}'}

    except Exception as e:
        logger.error(
            f'Error generating cost report for period {billing_period_start} to {billing_period_end}: {e}'
        )

        return {'error': f'Error generating cost report: {str(e)}'}


def main():
    """Run the MCP server with CLI argument support."""
    app.run()


if __name__ == '__main__':
    main()
