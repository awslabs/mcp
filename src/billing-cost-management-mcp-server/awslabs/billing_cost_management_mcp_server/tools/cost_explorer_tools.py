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

from ..utilities.aws_service_base import create_aws_client, format_response, handle_aws_error
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
from botocore.exceptions import ClientError
from fastmcp import Context, FastMCP
from typing import Any, Dict, Optional


cost_explorer_server = FastMCP(
    name='cost-explorer-tools', instructions='Tools for working with AWS Cost Explorer API'
)


@cost_explorer_server.tool(
    name='cost-explorer',
    description="""Retrieves AWS cost and usage data using the Cost Explorer API.

IMPORTANT USAGE GUIDELINES:
- Use UnblendedCost metric by default (not BlendedCost) unless user specifies otherwise
- Exclude record_types 'Credit' and 'Refund' by default unless user requests inclusion
- Choose DAILY granularity for periods <3 months, MONTHLY for longer periods
- Start with high-level dimensions (SERVICE, LINKED_ACCOUNT) before detailed ones
- Always remember that the end_date is exclusive

USE THIS TOOL FOR:
- **Historical cost trends** and spending analysis (any time period)
- **Usage pattern analysis** over time
- **Cost breakdown** by service, account, region, or any dimension
- **Forecasting** future costs and usage
- **Resource-level cost analysis** (last 14 days)
- **Multi-dimensional cost analysis** with complex grouping

## OPERATIONS

1) getCostAndUsage — account-level historical cost/usage
   Required: operation="getCostAndUsage", start_date, end_date, granularity, metrics
   Optional: group_by, filter, next_token, max_pages
   Example: {"operation": "getCostAndUsage", "start_date": "2024-01-01", "end_date": "2024-02-01", "granularity": "DAILY", "metrics": [\"UnblendedCost\"], "group_by": "[{\"Type\": \"DIMENSION\", \"Key\": \"SERVICE\"}]"}

2. getCostAndUsageWithResources - Resource-level cost data (limited to last 14 days)
   Required: operation="getCostAndUsageWithResources", filter, granularity, start_date, end_date
   Optional: metrics, group_by
   Notes: RESOURCE_ID must be included in either filter OR group_by parameters. This operation is limited to past 14 days of data from current date. Hourly granularity is only available for EC2-Instances resource-level data. All other resource-level data is available at daily granularity.
   Example: {"operation": "getCostAndUsageWithResources", "start_date": "2025-08-07", "end_date": "2025-08-21", "granularity": "DAILY", "filter": "{\"Dimensions\": {\"Key\": \"SERVICE\", \"Values\": [\"Amazon Elastic Compute Cloud - Compute\"]}}", "group_by": "[{\"Type\": \"DIMENSION\", \"Key\": \"RESOURCE_ID\"}]"}
   Returns: Cost data with resource-level granularity

3. getDimensionValues - List of available values for specified dimension
   Required: operation="getDimensionValues", dimension, start_date, end_date
   Optional: context, search_string, filter, max_results
   Example: {"operation": "getDimensionValues", "dimension": "SERVICE", "start_date": "2024-01-01", "end_date": "2024-02-01"}
   Returns: List of values for specified dimension with automatic pagination

4. getCostForecast - Future cost projections
   Required: operation="getCostForecast", metric, granularity, start_date, end_date
   Optional: filter, prediction_interval_level
   Example: {"operation": "getCostForecast", "metric": "UNBLENDED_COST", "granularity": "MONTHLY", "start_date": "2025-08-22", "end_date": "2025-11-22"}
   Notes: metric value for this operation should be in all caps
   Returns: Cost forecast for specified time period and granularity

5. getUsageForecast - Future usage projections
   Required: operation="getUsageForecast", metric, granularity, start_date, end_date, filter
   Optional: prediction_interval_level
   Example 1: {"operation": "getUsageForecast", "metric": "USAGE_QUANTITY", "granularity": "MONTHLY", "start_date": "2025-08-22", "end_date": "2025-11-22", "filter": "{\"Dimensions\": {\"Key\": \"USAGE_TYPE_GROUP\", \"Values\": [\"EC2-Instance\"]}}"}
   Example 2: {"operation": "getUsageForecast", "metric": "USAGE_QUANTITY", "granularity": "MONTHLY", "start_date": "2025-08-22", "end_date": "2025-11-22", "filter": "{\"And\": [{\"Dimensions\": {\"Key\": \"SERVICE\", \"Values\": [\"Amazon Elastic Compute Cloud - Compute\"]}}, {\"Dimensions\": {\"Key\": \"USAGE_TYPE\", \"Values\": [\"BoxUsage:p4de.24xlarge\"]}}]}"}
   Example 3: {"operation": "getUsageForecast", "metric": "USAGE_QUANTITY", "granularity": "MONTHLY", "start_date": "2025-08-22", "end_date": "2025-11-22", "filter": "{\"Dimensions\": {\"Key\": \"USAGE_TYPE\", \"Values\": [\"BoxUsage:p4de.24xlarge\", \"Reservation:p4de.24xlarge\", \"UnusedBox:p4de.24xlarge\"]}}", "group_by": "[{\"Type\": \"DIMENSION\", \"Key\": \"REGION\"}]"}
   Notes: Valid values for metric is: USAGE_QUANTITY, NORMALIZED_USAGE_AMOUNT. Valid values for granularity is: DAILY, MONTHLY. Filter is REQUIRED and must specify USAGE_TYPE or USAGE_TYPE_GROUP to define what usage units to forecast.
   Returns: Usage forecast for specified time period and granularity

6. getTagsOrValues - Available cost allocation tags or values
   Required: operation="getTagsOrValues"
   Optional: start_date, end_date, search_string, next_token, max_pages
   Example 1: {"operation": "getTagsOrValues"}
   Example 2: {"operation": "getTagsOrValues", "tag_key": "Environment"}
   Returns: List of available cost allocation tags with automatic pagination. If tag values for a particular key are needed, pass the tag key as a parameter.

8. getCostCategories - Available cost categories
   Required: operation="getCostCategories", start_date, end_date
   Optional: search_string, next_token, max_pages
   Example: {"operation": "getCostCategories", "start_date": "2024-01-01", "end_date": "2024-08-01"}
   Returns: List of available cost categories with automatic pagination

9. getSavingsPlansUtilization - Savings Plans utilization data
   Required: operation="getSavingsPlansUtilization", start_date, end_date
   Optional: granularity, filter
   Example: {"operation": "getSavingsPlansUtilization", "granularity": "MONTHLY"}
   Notes: This operation supports only DAILY and MONTHLY granularity
   Returns: Savings Plans utilization for the specified time period

DIMENSION REFERENCE:
- AZ: The Availability Zone (e.g., us-east-1a)
- DATABASE_ENGINE: The Amazon RDS database (e.g., Aurora, MySQL)
- DEPLOYMENT_OPTION: RDS deployment scope (SingleAZ, MultiAZ)
- INSTANCE_TYPE: The EC2 instance type (e.g., m4.xlarge)
- INSTANCE_TYPE_FAMILY: Family of instances (e.g., Compute Optimized, Memory Optimized)
- LINKED_ACCOUNT: AWS member accounts
- OPERATING_SYSTEM: OS type (e.g., Windows, Linux)
- PLATFORM: EC2 operating system
- PURCHASE_TYPE: Reservation type (e.g., On-Demand, Reserved)
- REGION: AWS Region
- SERVICE: AWS service (e.g., Amazon DynamoDB)
- TAG: Cost allocation tag
- TENANCY: EC2 tenancy (shared, dedicated)
- USAGE_TYPE: Usage type (e.g., DataTransfer-In-Bytes)
- RECORD_TYPE: Charge types (e.g., RI fees, usage costs)""",
)
async def cost_explorer(
    ctx: Context,
    operation: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    granularity: str = 'DAILY',
    metrics: Optional[str] = None,
    group_by: Optional[str] = None,
    filter: Optional[str] = None,
    dimension: Optional[str] = None,
    search_string: Optional[str] = None,
    max_results: Optional[int] = None,
    next_token: Optional[str] = None,
    max_pages: Optional[int] = None,
    metric: Optional[str] = None,
    prediction_interval_level: int = 80,
    tag_key: Optional[str] = None,
    cost_category_name: Optional[str] = None,
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
        metrics: Metrics to include in the response
        group_by: How to group the results
        filter: Filter to apply to the results
        dimension: Dimension to get values for (getDimensionValues)
        search_string: Search string to filter dimension values
        max_results: Maximum number of results to return
        next_token: Pagination token
        max_pages: Maximum number of pages to retrieve
        metric: Metric for cost forecasts
        prediction_interval_level: Confidence level for forecasts
        tag_key: Tag key to get values for
        cost_category_name: Cost category to get values for

    Returns:
        Response from the operation handler
    """
    await ctx.info(f'Cost Explorer operation: {operation}')

    # Create Cost Explorer client
    try:
        ce_client = create_aws_client('ce')
    except Exception as client_error:
        await ctx.error(f'Failed to create AWS client: {str(client_error)}')
        return format_response(
            'error',
            {
                'error_type': 'client_creation_error',
                'message': f'Failed to create AWS client: {str(client_error)}',
                'details': repr(client_error),
            },
        )

    # Route to the appropriate operation handler
    try:
        await ctx.info(f'Routing to operation: {operation}')

        if operation == 'getCostAndUsage':
            return await get_cost_and_usage(
                ctx,
                ce_client,
                start_date,
                end_date,
                granularity,
                metrics,
                group_by,
                filter,
                next_token,
                max_pages,
            )

        elif operation == 'getCostAndUsageWithResources':
            return await get_cost_and_usage_with_resources(
                ctx, ce_client, start_date, end_date, granularity, metrics, group_by, filter
            )

        elif operation == 'getDimensionValues':
            if not dimension:
                return format_response(
                    'error', {'message': 'dimension is required for getDimensionValues operation'}
                )

            return await get_dimension_values(
                ctx,
                ce_client,
                dimension,
                start_date,
                end_date,
                search_string,
                filter,
                max_results,
                next_token,
                max_pages,
            )

        elif operation == 'getCostForecast':
            if not metric:
                return format_response(
                    'error', {'message': 'metric is required for getCostForecast operation'}
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
            )

        elif operation == 'getUsageForecast':
            if not metric:
                return format_response(
                    'error', {'message': 'metric is required for getUsageForecast operation'}
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
            )

        elif operation == 'getTagsOrValues':
            return await get_tags(
                ctx,
                ce_client,
                start_date,
                end_date,
                search_string,
                tag_key,
                next_token,
                max_pages,
            )

        elif operation == 'getCostCategories' or operation == 'getCostCategoryValues':
            return await get_cost_categories(
                ctx,
                ce_client,
                start_date,
                end_date,
                search_string,
                cost_category_name if operation == 'getCostCategoryValues' else None,
                next_token,
                max_pages,
            )

        elif operation == 'getSavingsPlansUtilization':
            return await get_savings_plans_utilization(
                ctx, ce_client, start_date, end_date, granularity, filter, next_token, max_pages
            )

        else:
            return format_response('error', {'message': f'Unknown operation: {operation}'})

    except ClientError as e:
        # Let the shared handler take care of this
        return await handle_aws_error(ctx, e, operation, 'Cost Explorer')
    except Exception as e:
        # For all other exceptions, use the shared error handler
        return await handle_aws_error(ctx, e, operation, 'Cost Explorer')
