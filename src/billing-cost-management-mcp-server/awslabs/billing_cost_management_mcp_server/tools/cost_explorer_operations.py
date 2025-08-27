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

"""AWS Cost Explorer operations for the AWS Billing and Cost Management MCP server.

This module contains the individual operation handlers for the Cost Explorer tool.
Updated to use shared utility functions.
"""

from ..utilities.aws_service_base import (
    format_response,
    get_date_range,
    handle_aws_error,
    paginate_aws_response,
    parse_json,
)
from ..utilities.sql_utils import convert_api_response_to_table
from datetime import datetime, timedelta
from fastmcp import Context
from typing import Any, Dict, Optional


async def get_cost_and_usage(
    ctx: Context,
    ce_client,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    granularity: str = 'DAILY',
    metrics: Optional[str] = None,
    group_by: Optional[str] = None,
    filter_expr: Optional[str] = None,
    next_token: Optional[str] = None,
    max_pages: Optional[int] = None,
) -> Dict[str, Any]:
    """Get cost and usage data with automatic pagination.

    Uses shared utilities for date handling, JSON parsing, and pagination.

    Args:
        ctx: MCP context
        ce_client: AWS Cost Explorer client
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format (exclusive)
        granularity: Time granularity (DAILY, MONTHLY, HOURLY)
        metrics: List of metrics as JSON string
        group_by: Optional grouping as JSON string
        filter_expr: Optional filters as JSON string
        next_token: Pagination token
        max_pages: Maximum number of pages to fetch

    Returns:
        Cost and usage data response
    """
    await ctx.info(f'Getting cost and usage data with granularity: {granularity}')

    try:
        # Get date range with defaults
        start, end = get_date_range(start_date, end_date)
        await ctx.info(f'Using date range: {start} to {end}')

        # Parse JSON inputs
        metrics_list = parse_json(metrics, 'metrics')
        group_by_list = parse_json(group_by, 'group_by')
        filters = parse_json(filter_expr, 'filter')

        # Set default metrics if not provided
        if not metrics_list:
            metrics_list = ['UnblendedCost']

        # Build request parameters
        request_params = {
            'TimePeriod': {'Start': start, 'End': end},
            'Granularity': granularity,
            'Metrics': metrics_list,
        }

        # Add optional parameters if provided
        if group_by_list:
            request_params['GroupBy'] = group_by_list

        if filters:
            request_params['Filter'] = filters

        # Handle pagination

        # Create function to call API
        def api_call(**params):
            return ce_client.get_cost_and_usage(**params)

        # Use shared pagination utility
        if next_token or max_pages:
            # For paginated requests, use the paginate utility
            results, pagination_metadata = await paginate_aws_response(
                ctx,
                'getCostAndUsage',
                api_call,
                request_params,
                'ResultsByTime',
                'NextPageToken',
                'NextPageToken',
                max_pages,
            )

            # Format paginated response
            response = {'ResultsByTime': results, 'Pagination': pagination_metadata}
        else:
            # For single page, make direct call
            response = ce_client.get_cost_and_usage(**request_params)

        # Convert large responses to SQL table
        table_response = await convert_api_response_to_table(
            ctx,
            response,
            'getCostAndUsage',
            granularity=granularity,
            start_date=start,
            end_date=end,
            group_by=group_by,
            metrics=metrics,
        )

        # Return the response (either the original or the SQL table info)
        return format_response(
            'success',
            table_response
            if isinstance(table_response, dict) and 'data_stored' in table_response
            else response,
        )

    except Exception as e:
        # Use shared error handling
        return await handle_aws_error(ctx, e, 'getCostAndUsage', 'Cost Explorer')


async def get_cost_and_usage_with_resources(
    ctx: Context,
    ce_client,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    granularity: str = 'DAILY',
    metrics: Optional[str] = None,
    group_by: Optional[str] = None,
    filter_expr: Optional[str] = None,
) -> Dict[str, Any]:
    """Get resource-level cost and usage data.

    Note: Limited to the last 14 days of data.

    Args:
        ctx: MCP context
        ce_client: AWS Cost Explorer client
        start_date: Start date in YYYY-MM-DD format (last 14 days max)
        end_date: End date in YYYY-MM-DD format (exclusive)
        granularity: Time granularity (DAILY, MONTHLY, HOURLY)
        metrics: List of metrics as JSON string
        group_by: Optional grouping as JSON string
        filter_expr: Optional filters as JSON string

    Returns:
        Resource-level cost and usage data response
    """
    await ctx.info('Getting resource-level cost and usage data')

    try:
        # Get date range with defaults
        if not start_date:
            # Default to 7 days ago for resource-level data (limited to 14 days)
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

        start, end = get_date_range(start_date, end_date)
        await ctx.info(f'Using date range: {start} to {end}')

        # Parse JSON inputs
        metrics_list = parse_json(metrics, 'metrics')
        group_by_list = parse_json(group_by, 'group_by')
        filters = parse_json(filter_expr, 'filter')

        # Set default metrics if not provided
        if not metrics_list:
            metrics_list = ['UnblendedCost']

        # Build request parameters
        request_params = {
            'TimePeriod': {'Start': start, 'End': end},
            'Granularity': granularity,
            'Metrics': metrics_list,
        }

        # Add optional parameters if provided
        if group_by_list:
            request_params['GroupBy'] = group_by_list

        if filters:
            request_params['Filter'] = filters

        # Make API call
        await ctx.info('Calling getCostAndUsageWithResources API')
        response = ce_client.get_cost_and_usage_with_resources(**request_params)

        return format_response('success', response)

    except Exception as e:
        return await handle_aws_error(ctx, e, 'getCostAndUsageWithResources', 'Cost Explorer')


async def get_dimension_values(
    ctx: Context,
    ce_client,
    dimension: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search_string: Optional[str] = None,
    filter_expr: Optional[str] = None,
    max_results: Optional[int] = None,
    next_token: Optional[str] = None,
    max_pages: Optional[int] = None,
) -> Dict[str, Any]:
    """Get available dimension values.

    Args:
        ctx: MCP context
        ce_client: AWS Cost Explorer client
        dimension: The dimension to get values for
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format (exclusive)
        search_string: Optional string to filter results
        filter_expr: Optional filters as JSON string
        max_results: Maximum number of results per page
        next_token: Pagination token
        max_pages: Maximum number of pages to fetch

    Returns:
        Dimension values response
    """
    await ctx.info(f'Getting dimension values for: {dimension}')

    try:
        # Get date range with defaults
        start, end = get_date_range(start_date, end_date)
        await ctx.info(f'Using date range: {start} to {end}')

        # Parse JSON filter if provided
        filters = parse_json(filter_expr, 'filter')

        # Build request parameters
        request_params = {'TimePeriod': {'Start': start, 'End': end}, 'Dimension': dimension}

        # Add optional parameters if provided
        if search_string:
            request_params['SearchString'] = search_string

        if filters:
            request_params['Filter'] = filters

        if max_results:
            request_params['MaxResults'] = max_results

        # Handle pagination
        if next_token or max_pages:
            # For paginated requests, use the paginate utility
            results, pagination_metadata = await paginate_aws_response(
                ctx,
                'getDimensionValues',
                lambda **params: ce_client.get_dimension_values(**params),
                request_params,
                'DimensionValues',
                'NextPageToken',
                'NextPageToken',
                max_pages,
            )

            # Format paginated response
            response = {'DimensionValues': results, 'Pagination': pagination_metadata}
        else:
            # For single page, make direct call
            response = ce_client.get_dimension_values(**request_params)

        return format_response('success', response)

    except Exception as e:
        # Use shared error handling
        return await handle_aws_error(ctx, e, 'getDimensionValues', 'Cost Explorer')


async def get_cost_forecast(
    ctx: Context,
    ce_client,
    metric: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    granularity: str = 'MONTHLY',
    filter_expr: Optional[str] = None,
    prediction_interval_level: int = 80,
) -> Dict[str, Any]:
    """Get cost forecast.

    Args:
        ctx: MCP context
        ce_client: AWS Cost Explorer client
        metric: Cost metric to forecast
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format (exclusive)
        granularity: Time granularity (DAILY, MONTHLY)
        filter_expr: Optional filters as JSON string
        prediction_interval_level: Confidence interval (70-99)

    Returns:
        Cost forecast response
    """
    await ctx.info(f'Getting cost forecast for metric: {metric}')

    try:
        # Set default dates if not provided (forecast should be future-looking)

        if not start_date:
            # Default to tomorrow
            start_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

        if not end_date:
            # Default to 3 months from start
            end_date = (datetime.strptime(start_date, '%Y-%m-%d') + timedelta(days=90)).strftime(
                '%Y-%m-%d'
            )

        await ctx.info(f'Using forecast date range: {start_date} to {end_date}')

        # Parse JSON filter if provided
        filters = parse_json(filter_expr, 'filter')

        # Build request parameters
        request_params = {
            'TimePeriod': {'Start': start_date, 'End': end_date},
            'Metric': metric,
            'Granularity': granularity,
            'PredictionIntervalLevel': prediction_interval_level,
        }

        # Add filters if provided
        if filters:
            request_params['Filter'] = filters

        # Make API call
        await ctx.info('Calling getCostForecast API')
        response = ce_client.get_cost_forecast(**request_params)

        return format_response('success', response)

    except Exception as e:
        # Use shared error handling
        return await handle_aws_error(ctx, e, 'getCostForecast', 'Cost Explorer')


async def get_usage_forecast(
    ctx: Context,
    ce_client,
    metric: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    granularity: str = 'MONTHLY',
    filter_expr: Optional[str] = None,
    prediction_interval_level: int = 80,
) -> Dict[str, Any]:
    """Get usage forecast.

    Args:
        ctx: MCP context
        ce_client: AWS Cost Explorer client
        metric: Usage metric to forecast
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format (exclusive)
        granularity: Time granularity (DAILY, MONTHLY)
        filter_expr: Optional filters as JSON string
        prediction_interval_level: Confidence interval (70-99)

    Returns:
        Usage forecast response
    """
    await ctx.info(f'Getting usage forecast for metric: {metric}')

    try:
        # Set default dates if not provided (forecast should be future-looking)
        if not start_date:
            # Default to tomorrow
            start_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

        if not end_date:
            # Default to 3 months from start
            end_date = (datetime.strptime(start_date, '%Y-%m-%d') + timedelta(days=90)).strftime(
                '%Y-%m-%d'
            )

        await ctx.info(f'Using forecast date range: {start_date} to {end_date}')

        # Parse JSON filter if provided
        filters = parse_json(filter_expr, 'filter')

        # Build request parameters
        request_params = {
            'TimePeriod': {'Start': start_date, 'End': end_date},
            'Metric': metric,
            'Granularity': granularity,
            'PredictionIntervalLevel': prediction_interval_level,
        }

        # Add filters if provided
        if filters:
            request_params['Filter'] = filters

        # Make API call
        await ctx.info('Calling getUsageForecast API')
        response = ce_client.get_usage_forecast(**request_params)

        return format_response('success', response)

    except Exception as e:
        # Use shared error handling
        return await handle_aws_error(ctx, e, 'getUsageForecast', 'Cost Explorer')


async def get_tags(
    ctx: Context,
    ce_client,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search_string: Optional[str] = None,
    tag_key: Optional[str] = None,
    next_token: Optional[str] = None,
    max_pages: Optional[int] = None,
) -> Dict[str, Any]:
    """Get tags used for Cost Explorer grouping.

    Args:
        ctx: MCP context
        ce_client: AWS Cost Explorer client
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format (exclusive)
        search_string: Optional string to filter results
        tag_key: Optional specific tag key to get values for
        next_token: Pagination token
        max_pages: Maximum number of pages to fetch

    Returns:
        Tags response
    """
    operation = 'getTagsOrValues'
    await ctx.info(f'Calling {operation} API')

    try:
        # Get date range with defaults
        start, end = get_date_range(start_date, end_date)
        await ctx.info(f'Using date range: {start} to {end}')

        # Build request parameters
        request_params: dict = {'TimePeriod': {'Start': start, 'End': end}}

        # Add optional parameters
        if search_string:
            request_params['SearchString'] = str(search_string)

        if tag_key:
            request_params['TagKey'] = str(tag_key)

        # Handle pagination
        if next_token or max_pages:
            api_function = ce_client.get_tags
            result_key = 'Tags' if not tag_key else 'TagValues'

            # For paginated requests, use the paginate utility
            results, pagination_metadata = await paginate_aws_response(
                ctx,
                operation,
                lambda **params: api_function(**params),
                request_params,
                result_key,
                'NextPageToken',
                'NextPageToken',
                max_pages,
            )

            # Format paginated response
            response = {result_key: results, 'Pagination': pagination_metadata}
        else:
            # For single page, make direct call
            response = ce_client.get_tags(**request_params)

        return format_response('success', response)

    except Exception as e:
        # Use shared error handling
        return await handle_aws_error(ctx, e, operation, 'Cost Explorer')


async def get_cost_categories(
    ctx: Context,
    ce_client,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search_string: Optional[str] = None,
    cost_category_name: Optional[str] = None,
    next_token: Optional[str] = None,
    max_pages: Optional[int] = None,
) -> Dict[str, Any]:
    """Get cost categories.

    Args:
        ctx: MCP context
        ce_client: AWS Cost Explorer client
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format (exclusive)
        search_string: Optional string to filter results
        cost_category_name: Optional specific cost category to get values for
        next_token: Pagination token
        max_pages: Maximum number of pages to fetch

    Returns:
        Cost categories response
    """
    operation = 'getCostCategories' if not cost_category_name else 'getCostCategoryValues'
    await ctx.info(f'Calling {operation} API')

    try:
        # Get date range with defaults
        start, end = get_date_range(start_date, end_date)
        await ctx.info(f'Using date range: {start} to {end}')

        # Build request parameters
        request_params: dict = {'TimePeriod': {'Start': start, 'End': end}}

        # Add optional parameters
        if search_string:
            request_params['SearchString'] = str(search_string)

        if cost_category_name:
            request_params['CostCategoryName'] = str(cost_category_name)

        # Handle pagination
        if next_token or max_pages:
            api_function = (
                ce_client.get_cost_categories
                if not cost_category_name
                else ce_client.get_cost_category_values
            )
            result_key = 'CostCategories' if not cost_category_name else 'CostCategoryValues'

            # For paginated requests, use the paginate utility
            results, pagination_metadata = await paginate_aws_response(
                ctx,
                operation,
                lambda **params: api_function(**params),
                request_params,
                result_key,
                'NextPageToken',
                'NextPageToken',
                max_pages,
            )

            # Format paginated response
            response = {result_key: results, 'Pagination': pagination_metadata}
        else:
            # For single page, make direct call
            if cost_category_name:
                response = ce_client.get_cost_category_values(**request_params)
            else:
                response = ce_client.get_cost_categories(**request_params)

        return format_response('success', response)

    except Exception as e:
        # Use shared error handling
        return await handle_aws_error(ctx, e, operation, 'Cost Explorer')


async def get_savings_plans_utilization(
    ctx: Context,
    ce_client,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    granularity: str = 'MONTHLY',
    filter_expr: Optional[str] = None,
    next_token: Optional[str] = None,
    max_pages: Optional[int] = None,
) -> Dict[str, Any]:
    """Get Savings Plans utilization.

    Args:
        ctx: MCP context
        ce_client: AWS Cost Explorer client
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format (exclusive)
        granularity: Time granularity (DAILY, MONTHLY)
        filter_expr: Optional filters as JSON string
        next_token: Pagination token
        max_pages: Maximum number of pages to fetch

    Returns:
        Savings Plans utilization response
    """
    await ctx.info('Getting Savings Plans utilization')

    try:
        # Get date range with defaults
        start, end = get_date_range(start_date, end_date)
        await ctx.info(f'Using date range: {start} to {end}')

        # Parse JSON filter if provided
        filters = parse_json(filter_expr, 'filter')

        # Build request parameters
        request_params = {'TimePeriod': {'Start': start, 'End': end}, 'Granularity': granularity}

        # Add optional parameters
        if filters:
            request_params['Filter'] = filters

        # Handle pagination
        if next_token or max_pages:
            # For paginated requests, use the paginate utility
            results, pagination_metadata = await paginate_aws_response(
                ctx,
                'getSavingsPlansUtilization',
                lambda **params: ce_client.get_savings_plans_utilization(**params),
                request_params,
                'SavingsPlansUtilizationsByTime',
                'NextToken',
                'NextToken',
                max_pages,
            )

            # Format paginated response
            response = {
                'SavingsPlansUtilizationsByTime': results,
                'Pagination': pagination_metadata,
            }
        else:
            # For single page, make direct call
            response = ce_client.get_savings_plans_utilization(**request_params)

        return format_response('success', response)

    except Exception as e:
        # Use shared error handling
        return await handle_aws_error(ctx, e, 'getSavingsPlansUtilization', 'Cost Explorer')
