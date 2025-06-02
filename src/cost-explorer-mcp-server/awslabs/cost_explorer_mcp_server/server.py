"""Cost Explorer MCP server implementation.

This server provides tools for analyzing AWS costs and usage data through the AWS Cost Explorer API.
"""

import boto3
import logging
from datetime import datetime, timedelta
import pandas as pd
from mcp.server.fastmcp import Context, FastMCP
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional, Union

from awslabs.cost_explorer_mcp_server.helpers import (
    get_dimension_values,
    get_tag_values,
    validate_expression,
    validate_group_by
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize AWS Cost Explorer client
ce = boto3.client('ce')


class DateRange(BaseModel):
    """Date range model for cost queries."""
    start_date: str = Field(
        ...,
        description="The start date of the billing period in YYYY-MM-DD format. Defaults to last month, if not provided."
    )
    end_date: str = Field(
        ...,
        description="The end date of the billing period in YYYY-MM-DD format."
    )


class GroupBy(BaseModel):
    """Group by model for cost queries."""
    type: str = Field(
        ...,
        description="Type of grouping. Valid values are DIMENSION, TAG, and COST_CATEGORY."
    )
    key: str = Field(
        ...,
        description="Key to group by. For DIMENSION type, valid values include AZ, INSTANCE_TYPE, LEGAL_ENTITY_NAME, INVOICING_ENTITY, LINKED_ACCOUNT, OPERATION, PLATFORM, PURCHASE_TYPE, SERVICE, TENANCY, RECORD_TYPE, and USAGE_TYPE."
    )


class FilterExpression(BaseModel):
    """Filter expression model for cost queries."""
    filter_json: str = Field(
        ...,
        description="Filter criteria as a Python dictionary to narrow down AWS costs. Supports filtering by Dimensions (SERVICE, REGION, etc.), Tags, or CostCategories. You can use logical operators (And, Or, Not) for complex filters. Examples: 1) Simple service filter: {'Dimensions': {'Key': 'SERVICE', 'Values': ['Amazon Elastic Compute Cloud - Compute', 'Amazon Simple Storage Service'], 'MatchOptions': ['EQUALS']}}. 2) Region filter: {'Dimensions': {'Key': 'REGION', 'Values': ['us-east-1'], 'MatchOptions': ['EQUALS']}}. 3) Combined filter: {'And': [{'Dimensions': {'Key': 'SERVICE', 'Values': ['Amazon Elastic Compute Cloud - Compute'], 'MatchOptions': ['EQUALS']}}, {'Dimensions': {'Key': 'REGION', 'Values': ['us-east-1'], 'MatchOptions': ['EQUALS']}}]}."
    )


class CostMetric(BaseModel):
    """Cost metric model."""
    metric: str = Field(
        "UnblendedCost",
        description="The metric to return in the query. Valid values are AmortizedCost, BlendedCost, NetAmortizedCost, NetUnblendedCost, NormalizedUsageAmount, UnblendedCost, and UsageQuantity. Note: For UsageQuantity, the service aggregates usage numbers without considering units. To get meaningful UsageQuantity metrics, filter by UsageType or UsageTypeGroups."
    )


class DimensionKey(BaseModel):
    """Dimension key model."""
    dimension_key: str = Field(
        ...,
        description="The name of the dimension to retrieve values for. Valid values are AZ, INSTANCE_TYPE, LINKED_ACCOUNT, OPERATION, PURCHASE_TYPE, SERVICE, USAGE_TYPE, PLATFORM, TENANCY, RECORD_TYPE, LEGAL_ENTITY_NAME, INVOICING_ENTITY, DEPLOYMENT_OPTION, DATABASE_ENGINE, CACHE_ENGINE, INSTANCE_TYPE_FAMILY, REGION, BILLING_ENTITY, RESERVATION_ID, SAVINGS_PLANS_TYPE, SAVINGS_PLAN_ARN, OPERATING_SYSTEM."
    )


# Create FastMCP server
mcp = FastMCP(title="Cost Explorer MCP Server")


@app.tool("get_today_date")
async def get_today_date(ctx: Context) -> Dict[str, str]:
    """Retrieve current date information.

    This tool retrieves the current date in YYYY-MM-DD format and the current month in YYYY-MM format.
    It's useful for comparing if the billing period requested by the user is not in the future.

    Returns:
        Dictionary containing today's date and current month
    """
    return {
        'today_date': datetime.now().strftime('%Y-%m-%d'),
        'current_month': datetime.now().strftime('%Y-%m')
    }


@app.tool("get_dimension_values")
async def get_dimension_values_tool(
    ctx: Context,
    date_range: DateRange,
    dimension: DimensionKey
) -> Dict[str, Any]:
    """Retrieve available dimension values for AWS Cost Explorer.

    This tool retrieves all available and valid values for a specified dimension (e.g., SERVICE, REGION)
    over a period of time. This is useful for validating filter values or exploring available options
    for cost analysis.

    Args:
        date_range: The billing period start and end dates in YYYY-MM-DD format
        dimension: The dimension key to retrieve values for (e.g., SERVICE, REGION, LINKED_ACCOUNT)

    Returns:
        Dictionary containing the dimension name and list of available values
    """
    try:
        response = get_dimension_values(
            dimension.dimension_key,
            date_range.start_date,
            date_range.end_date
        )
        return response
    except Exception as e:
        logger.error(f"Error getting dimension values: {e}")
        return {'error': f'Error getting dimension values: {str(e)}'}


@app.tool("get_tag_values")
async def get_tag_values_tool(
    ctx: Context,
    date_range: DateRange,
    tag_key: str = Field(..., description="The tag key to retrieve values for")
) -> Dict[str, Any]:
    """Retrieve available tag values for AWS Cost Explorer.

    This tool retrieves all available values for a specified tag key over a period of time.
    This is useful for validating tag filter values or exploring available tag options for cost analysis.

    Args:
        date_range: The billing period start and end dates in YYYY-MM-DD format
        tag_key: The tag key to retrieve values for

    Returns:
        Dictionary containing the tag key and list of available values
    """
    try:
        response = get_tag_values(
            tag_key,
            date_range.start_date,
            date_range.end_date
        )
        return response
    except Exception as e:
        logger.error(f"Error getting tag values: {e}")
        return {'error': f'Error getting tag values: {str(e)}'}


@app.tool("get_cost_and_usage")
async def get_cost_and_usage(
    ctx: Context,
    date_range: DateRange,
    granularity: str = Field(
        "MONTHLY",
        description="The granularity at which cost data is aggregated. Valid values are DAILY, MONTHLY, and HOURLY. If not provided, defaults to MONTHLY."
    ),
    group_by: Optional[Union[Dict[str, str], str]] = Field(
        None,
        description="Either a dictionary with Type and Key for grouping costs, or simply a string key to group by (which will default to DIMENSION type). Example dictionary: {'Type': 'DIMENSION', 'Key': 'SERVICE'}. Example string: 'SERVICE'."
    ),
    filter_expression: Optional[Dict[str, Any]] = Field(
        None,
        description="Filter criteria as a Python dictionary to narrow down AWS costs. Supports filtering by Dimensions (SERVICE, REGION, etc.), Tags, or CostCategories. You can use logical operators (And, Or, Not) for complex filters. Examples: 1) Simple service filter: {'Dimensions': {'Key': 'SERVICE', 'Values': ['Amazon Elastic Compute Cloud - Compute', 'Amazon Simple Storage Service'], 'MatchOptions': ['EQUALS']}}. 2) Region filter: {'Dimensions': {'Key': 'REGION', 'Values': ['us-east-1'], 'MatchOptions': ['EQUALS']}}. 3) Combined filter: {'And': [{'Dimensions': {'Key': 'SERVICE', 'Values': ['Amazon Elastic Compute Cloud - Compute'], 'MatchOptions': ['EQUALS']}}, {'Dimensions': {'Key': 'REGION', 'Values': ['us-east-1'], 'MatchOptions': ['EQUALS']}}]}."
    ),
    metric: str = Field(
        "UnblendedCost",
        description="The metric to return in the query. Valid values are AmortizedCost, BlendedCost, NetAmortizedCost, NetUnblendedCost, NormalizedUsageAmount, UnblendedCost, and UsageQuantity."
    )
) -> Dict[str, Any]:
    """Retrieve AWS cost and usage data.

    This tool retrieves AWS cost and usage data for AWS services during a specified billing period,
    with optional filtering and grouping. It dynamically generates cost reports tailored to specific needs
    by specifying parameters such as granularity, billing period dates, and filter criteria.

    Note: The end_date is treated as inclusive in this tool, meaning if you specify an end_date of 
    "2025-01-31", the results will include data for January 31st. This differs from the AWS Cost Explorer 
    API which treats end_date as exclusive.


    Args:
        date_range: The billing period start and end dates in YYYY-MM-DD format (end date is inclusive)
        granularity: The granularity at which cost data is aggregated (DAILY, MONTHLY, HOURLY)
        group_by: Either a dictionary with Type and Key, or simply a string key to group by
        filter_expression: Filter criteria as a Python dictionary
        metric: Cost metric to use (UnblendedCost, BlendedCost, etc.)

    Returns:
        Dictionary containing cost report data grouped according to the specified parameters
    """

    try:
        # Process inputs
        granularity = granularity.upper()
        billing_period_start = date_range.start_date
        billing_period_end = date_range.end_date

        # Adjust end date for Cost Explorer API (exclusive)
        # Add one day to make the end date inclusive for the user
        billing_period_end_adj = (datetime.strptime(
            billing_period_end, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')

        # Process filter
        filter_criteria = filter_expression

        # Validate filter expression if provided
        if filter_criteria:
            # This validates both structure and values against AWS Cost Explorer
            validation_result = validate_expression(
                filter_criteria, billing_period_start, billing_period_end_adj)
            if 'error' in validation_result:
                return validation_result

        # Process group_by
        if not group_by:
            group_by = {"Type": "DIMENSION", "Key": "SERVICE"}
        elif isinstance(group_by, str):
            group_by = {"Type": "DIMENSION", "Key": group_by}

        # Validate group_by using the existing validate_group_by function
        validation_result = validate_group_by(group_by)
        if 'error' in validation_result:
            return validation_result

        # Prepare API call parameters
        common_params = {
            'TimePeriod': {
                'Start': billing_period_start,
                'End': billing_period_end_adj
            },
            'Granularity': granularity,
            'GroupBy': [{'Type': group_by['Type'].upper(), 'Key': group_by['Key']}],
            'Metrics': [metric]
        }

        if filter_criteria:
            common_params['Filter'] = filter_criteria

        # Get cost data
        grouped_costs = {}
        next_token = None
        while True:
            if next_token:
                common_params['NextPageToken'] = next_token

            try:
                response = ce.get_cost_and_usage(**common_params)
            except Exception as e:
                logger.error(f"Error calling Cost Explorer API: {e}")
                return {'error': f'AWS Cost Explorer API error: {str(e)}'}

            for result_by_time in response['ResultsByTime']:
                date = result_by_time['TimePeriod']['Start']
                for group in result_by_time['Groups']:
                    group_key = group['Keys'][0]
                    if metric == 'UsageQuantity':
                        unit = group['Metrics'][metric]['Unit']
                        amount = float(group['Metrics'][metric]['Amount'])
                        grouped_costs.setdefault(date, {}).update(
                            {group_key: (amount, unit)})
                    else:
                        cost = float(group['Metrics'][metric]['Amount'])
                        grouped_costs.setdefault(
                            date, {}).update({group_key: cost})

            next_token = response.get('NextPageToken')
            if not next_token:
                break

        # Process results
        if metric == 'UsageQuantity':
            # Prepare DataFrame to include usage with units
            usage_df = pd.DataFrame({(k, 'Amount'): {
                                    k1: v1[0] for k1, v1 in v.items()} for k, v in grouped_costs.items()})
            units_df = pd.DataFrame(
                {(k, 'Unit'): {k1: v1[1] for k1, v1 in v.items()} for k, v in grouped_costs.items()})
            df = pd.concat([usage_df, units_df], axis=1)
        else:
            df = pd.DataFrame.from_dict(grouped_costs).round(2)
            df['Service total'] = df.sum(axis=1).round(2)
            df.loc['Total Costs'] = df.sum().round(2)
            df = df.sort_values(by='Service total', ascending=False)

        result = {'GroupedCosts': df.to_dict()}

        # Convert all keys to strings for JSON serialization
        def stringify_keys(d):
            if isinstance(d, dict):
                return {str(k): stringify_keys(v) for k, v in d.items()}
            elif isinstance(d, list):
                return [stringify_keys(i) for i in d]
            else:
                return d

        result = stringify_keys(result)
        return result

    except Exception as e:
        logger.error(f"Error generating cost report: {e}")
        return {'error': f'Error generating cost report: {str(e)}'}

def main():
    """Run the MCP server with CLI argument support."""
    app.run()

if __name__ == "__main__":
    main()
