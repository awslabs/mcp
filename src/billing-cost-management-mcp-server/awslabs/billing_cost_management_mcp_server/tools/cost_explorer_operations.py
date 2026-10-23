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

import math
from ..utilities.aws_service_base import (
    PageSpec,
    first_page_fields,
    format_response,
    get_date_range,
    handle_aws_error,
    paginate_aws_items,
    parse_json,
    parse_metrics,
    with_pagination,
)
from ..utilities.sql_utils import convert_response_if_needed
from dataclasses import replace
from datetime import datetime, timedelta
from fastmcp import Context
from typing import Any, Callable, Dict, List, Optional, Union


# Most rows (period x group cells) one GetCostAndUsage page holds, shared across its metrics.
CE_COST_AND_USAGE_CELLS_PER_PAGE = 5000

# Fields only the first page carries in full. Per-page lists that describe that page's
# results (DimensionValueAttributes) are concatenated instead.
_FIRST_PAGE_KEYS = ('GroupDefinitions', 'TotalSize')
_CONCATENATED_PAGE_KEYS = ('DimensionValueAttributes',)


def count_cost_and_usage_rows(results_by_time: List[Dict[str, Any]]) -> int:
    """Count GetCostAndUsage rows: one per group per period, or one per period without groups.

    Periods with no groups still count as one row, as they do toward the server's page size.
    """
    return sum(max(1, len(period.get('Groups') or [])) for period in results_by_time)


# getCostAndUsage / WithResources: the service sets the page size, which shrinks with the
# number of metrics. page_max is replaced per request (see _cost_and_usage_spec).
CE_GET_COST_AND_USAGE = PageSpec(
    result_key='ResultsByTime',
    token_param='NextPageToken',
    token_key_in_response='NextPageToken',
    page_max=CE_COST_AND_USAGE_CELLS_PER_PAGE,
    count_items=count_cost_and_usage_rows,
)

# getDimensionValues / getTags / getCostCategories without SortBy: up to 5,000 values per
# page. MaxResults is ignored or rejected without SortBy, so it is never sent.
CE_GET_DIMENSION_VALUES = PageSpec(
    result_key='DimensionValues',
    token_param='NextPageToken',
    token_key_in_response='NextPageToken',
    page_max=5000,
)
CE_GET_TAGS = replace(CE_GET_DIMENSION_VALUES, result_key='Tags')
CE_GET_COST_CATEGORY_NAMES = replace(CE_GET_DIMENSION_VALUES, result_key='CostCategoryNames')
CE_GET_COST_CATEGORY_VALUES = replace(CE_GET_DIMENSION_VALUES, result_key='CostCategoryValues')


def _cost_and_usage_spec(metrics: List[str]) -> PageSpec:
    """GetCostAndUsage's spec for one request: the page holds 5,000 cells across all metrics."""
    page_max = math.ceil(CE_COST_AND_USAGE_CELLS_PER_PAGE / max(1, len(set(metrics))))
    return replace(CE_GET_COST_AND_USAGE, page_max=page_max)


def merge_pages(pages: List[Dict[str, Any]], items: List[Any], result_key: str) -> Dict[str, Any]:
    """Merge fetched Cost Explorer pages into one boto3-shaped response, without the token.

    ``GroupDefinitions`` and ``TotalSize`` come from the first page,
    ``DimensionValueAttributes`` are concatenated and ``ReturnSize`` is recomputed.
    """
    response = first_page_fields(pages, _FIRST_PAGE_KEYS)
    for key in _CONCATENATED_PAGE_KEYS:
        if any(key in page for page in pages):
            # A value can repeat on several pages (e.g. one account's name), so keep the first.
            merged: List[Any] = []
            seen_values = set()
            for value in (v for page in pages for v in page.get(key) or []):
                marker = value.get('Value') if isinstance(value, dict) else None
                if marker is not None and marker in seen_values:
                    continue
                if marker is not None:
                    seen_values.add(marker)
                merged.append(value)
            response[key] = merged
    response[result_key] = items
    if any('ReturnSize' in page for page in pages):
        response['ReturnSize'] = len(items)
    return response


async def _fetch_pages(
    ctx: Context,
    operation: str,
    api_call: Callable[..., Dict[str, Any]],
    request_params: Dict[str, Any],
    spec: PageSpec,
    max_items: Optional[int],
    next_token: Optional[str],
) -> Dict[str, Any]:
    """Fetch pages per ``spec`` and merge them, with the ``pagination`` block attached."""
    items, pages, pagination = await paginate_aws_items(
        ctx,
        operation,
        api_call,
        request_params,
        spec,
        max_items=max_items,
        next_token=next_token,
    )
    merged = merge_pages(pages, items, str(spec.result_key))
    return with_pagination(merged, pagination)


async def get_cost_and_usage(
    ctx: Context,
    ce_client,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    granularity: str = 'DAILY',
    metrics: Optional[Union[str, List[str]]] = None,
    group_by: Optional[Union[str, List[Dict[str, Any]]]] = None,
    filter_expr: Optional[Union[str, Dict[str, Any]]] = None,
    next_token: Optional[str] = None,
    max_items: Optional[int] = None,
    billing_view_arn: Optional[str] = None,
) -> Dict[str, Any]:
    """Get cost and usage data, fetching every page unless ``max_items`` stops earlier.

    Args:
        ctx: MCP context
        ce_client: AWS Cost Explorer client
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format (exclusive)
        granularity: Time granularity (DAILY, MONTHLY, HOURLY)
        metrics: List of metrics, as a list or JSON string
        group_by: Optional grouping, as a list or JSON string
        filter_expr: Optional filters, as an object or JSON string
        next_token: Continuation token from a previous response
        max_items: Most items to return; None fetches every page
        billing_view_arn: Optional ARN of a billing view to scope the query.
            If not provided, defaults to the account's primary billing view.

    Returns:
        Cost and usage data response
    """
    await ctx.info(f'Getting cost and usage data with granularity: {granularity}')

    try:
        # Get date range with defaults
        start, end = get_date_range(start_date, end_date)
        await ctx.info(f'Using date range: {start} to {end}')

        # Parse JSON inputs
        metrics_list = parse_metrics(metrics)
        group_by_list = parse_json(group_by, 'group_by')
        filters = parse_json(filter_expr, 'filter')

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

        if billing_view_arn:
            request_params['BillingViewArn'] = billing_view_arn

        response = await _fetch_pages(
            ctx,
            'getCostAndUsage',
            ce_client.get_cost_and_usage,
            request_params,
            _cost_and_usage_spec(metrics_list),
            max_items,
            next_token,
        )

        table_response = await convert_response_if_needed(
            ctx,
            response,
            'cost_explorer_get_cost_and_usage',
            granularity=granularity,
            start_date=start,
            end_date=end,
            group_by=group_by,
            metrics=metrics_list,
        )

        return format_response('success', table_response)

    except Exception as e:
        # Use shared error handling
        return await handle_aws_error(ctx, e, 'getCostAndUsage', 'Cost Explorer')


async def get_cost_and_usage_with_resources(
    ctx: Context,
    ce_client,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    granularity: str = 'DAILY',
    metrics: Optional[Union[str, List[str]]] = None,
    group_by: Optional[Union[str, List[Dict[str, Any]]]] = None,
    filter_expr: Optional[Union[str, Dict[str, Any]]] = None,
    next_token: Optional[str] = None,
    max_items: Optional[int] = None,
    billing_view_arn: Optional[str] = None,
) -> Dict[str, Any]:
    """Get resource-level cost and usage data.

    Note: Limited to the last 14 days of data.

    Args:
        ctx: MCP context
        ce_client: AWS Cost Explorer client
        start_date: Start date in YYYY-MM-DD format (last 14 days max)
        end_date: End date in YYYY-MM-DD format (exclusive)
        granularity: Time granularity (DAILY, MONTHLY, HOURLY)
        metrics: List of metrics, as a list or JSON string
        group_by: Optional grouping, as a list or JSON string
        filter_expr: Optional filters, as an object or JSON string
        next_token: Continuation token from a previous response
        max_items: Most items to return; None fetches every page
        billing_view_arn: Optional ARN of a billing view to scope the query.
            If not provided, defaults to the account's primary billing view.

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
        metrics_list = parse_metrics(metrics)
        group_by_list = parse_json(group_by, 'group_by')
        filters = parse_json(filter_expr, 'filter')

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

        if billing_view_arn:
            request_params['BillingViewArn'] = billing_view_arn

        response = await _fetch_pages(
            ctx,
            'getCostAndUsageWithResources',
            ce_client.get_cost_and_usage_with_resources,
            request_params,
            _cost_and_usage_spec(metrics_list),
            max_items,
            next_token,
        )

        table_response = await convert_response_if_needed(
            ctx,
            response,
            'cost_explorer_get_cost_and_usage_with_resources',
            granularity=granularity,
            start_date=start,
            end_date=end,
            group_by=group_by,
            metrics=metrics_list,
        )

        return format_response('success', table_response)

    except Exception as e:
        return await handle_aws_error(ctx, e, 'getCostAndUsageWithResources', 'Cost Explorer')


async def get_dimension_values(
    ctx: Context,
    ce_client,
    dimension: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search_string: Optional[str] = None,
    filter_expr: Optional[Union[str, Dict[str, Any]]] = None,
    next_token: Optional[str] = None,
    max_items: Optional[int] = None,
    billing_view_arn: Optional[str] = None,
    context: Optional[str] = None,
) -> Dict[str, Any]:
    """Get available dimension values.

    Args:
        ctx: MCP context
        ce_client: AWS Cost Explorer client
        dimension: The dimension to get values for
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format (exclusive)
        search_string: Optional string to filter results
        filter_expr: Optional filters, as an object or JSON string
        next_token: Continuation token from a previous response
        max_items: Most items to return; None fetches every page
        billing_view_arn: Optional ARN of a billing view to scope the query.
            If not provided, defaults to the account's primary billing view.
        context: The context for the call, which can be COST_AND_USAGE, RESERVATIONS, or
            SAVINGS_PLANS. The default is COST_AND_USAGE. The context scopes which values come back.

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

        if billing_view_arn:
            request_params['BillingViewArn'] = billing_view_arn

        if context:
            request_params['Context'] = context

        response = await _fetch_pages(
            ctx,
            'getDimensionValues',
            ce_client.get_dimension_values,
            request_params,
            CE_GET_DIMENSION_VALUES,
            max_items,
            next_token,
        )

        table_response = await convert_response_if_needed(
            ctx,
            response,
            'cost_explorer_get_dimension_values',
            dimension=dimension,
            start_date=start,
            end_date=end,
            search_string=search_string,
        )

        return format_response('success', table_response)

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
    filter_expr: Optional[Union[str, Dict[str, Any]]] = None,
    prediction_interval_level: int = 80,
    billing_view_arn: Optional[str] = None,
) -> Dict[str, Any]:
    """Get cost forecast.

    Args:
        ctx: MCP context
        ce_client: AWS Cost Explorer client
        metric: Cost metric to forecast
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format (exclusive)
        granularity: Time granularity (DAILY, MONTHLY)
        filter_expr: Optional filters, as an object or JSON string
        prediction_interval_level: Confidence interval (70-99)
        billing_view_arn: Optional ARN of a billing view to scope the query.
            If not provided, defaults to the account's primary billing view.

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

        if billing_view_arn:
            request_params['BillingViewArn'] = billing_view_arn

        # Make API call
        await ctx.info('Calling getCostForecast API')
        response = ce_client.get_cost_forecast(**request_params)

        # Forecast responses can be large with DAILY granularity over months —
        # offload through the SQL gate so callers get a queryable table.
        table_response = await convert_response_if_needed(
            ctx,
            response,
            'cost_explorer_get_cost_forecast',
            metric=metric,
            granularity=granularity,
            start_date=start_date,
            end_date=end_date,
        )

        return format_response('success', table_response)

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
    filter_expr: Optional[Union[str, Dict[str, Any]]] = None,
    prediction_interval_level: int = 80,
    billing_view_arn: Optional[str] = None,
) -> Dict[str, Any]:
    """Get usage forecast.

    Args:
        ctx: MCP context
        ce_client: AWS Cost Explorer client
        metric: Usage metric to forecast
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format (exclusive)
        granularity: Time granularity (DAILY, MONTHLY)
        filter_expr: Optional filters, as an object or JSON string
        prediction_interval_level: Confidence interval (70-99)
        billing_view_arn: Optional ARN of a billing view to scope the query.
            If not provided, defaults to the account's primary billing view.

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

        if billing_view_arn:
            request_params['BillingViewArn'] = billing_view_arn

        # Make API call
        await ctx.info('Calling getUsageForecast API')
        response = ce_client.get_usage_forecast(**request_params)

        table_response = await convert_response_if_needed(
            ctx,
            response,
            'cost_explorer_get_usage_forecast',
            metric=metric,
            granularity=granularity,
            start_date=start_date,
            end_date=end_date,
        )

        return format_response('success', table_response)

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
    max_items: Optional[int] = None,
    billing_view_arn: Optional[str] = None,
) -> Dict[str, Any]:
    """Get tags used for Cost Explorer grouping.

    Args:
        ctx: MCP context
        ce_client: AWS Cost Explorer client
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format (exclusive)
        search_string: Optional string to filter results
        tag_key: Optional specific tag key to get values for
        next_token: Continuation token from a previous response
        max_items: Most items to return; None fetches every page
        billing_view_arn: Optional ARN of a billing view to scope the query.
            If not provided, defaults to the account's primary billing view.

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

        if billing_view_arn:
            request_params['BillingViewArn'] = billing_view_arn

        # GetTags returns tag values under 'Tags' too when TagKey is set.
        response = await _fetch_pages(
            ctx, operation, ce_client.get_tags, request_params, CE_GET_TAGS, max_items, next_token
        )

        table_response = await convert_response_if_needed(
            ctx,
            response,
            'cost_explorer_get_tags',
            start_date=start,
            end_date=end,
            search_string=search_string,
            tag_key=tag_key,
        )

        return format_response('success', table_response)

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
    max_items: Optional[int] = None,
    billing_view_arn: Optional[str] = None,
) -> Dict[str, Any]:
    """Get cost categories.

    Args:
        ctx: MCP context
        ce_client: AWS Cost Explorer client
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format (exclusive)
        search_string: Optional string to filter results
        cost_category_name: Optional specific cost category to get values for
        next_token: Continuation token from a previous response
        max_items: Most items to return; None fetches every page
        billing_view_arn: Optional ARN of a billing view to scope the query.
            If not provided, defaults to the account's primary billing view.

    Returns:
        Cost categories response
    """
    operation = 'getCostCategories'
    # The category name is customer content, so it is not logged.
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

        # When CostCategoryName is provided the API returns CostCategoryValues
        # (the values inside that category) instead of CostCategoryNames.
        if cost_category_name:
            request_params['CostCategoryName'] = str(cost_category_name)

        if billing_view_arn:
            request_params['BillingViewArn'] = billing_view_arn

        # Response field name depends on whether CostCategoryName was supplied.
        spec = CE_GET_COST_CATEGORY_VALUES if cost_category_name else CE_GET_COST_CATEGORY_NAMES

        response = await _fetch_pages(
            ctx,
            operation,
            ce_client.get_cost_categories,
            request_params,
            spec,
            max_items,
            next_token,
        )

        table_response = await convert_response_if_needed(
            ctx,
            response,
            'cost_explorer_get_cost_categories',
            start_date=start,
            end_date=end,
            search_string=search_string,
            cost_category_name=cost_category_name,
        )

        return format_response('success', table_response)

    except Exception as e:
        # Use shared error handling
        return await handle_aws_error(ctx, e, operation, 'Cost Explorer')


async def get_savings_plans_utilization(
    ctx: Context,
    ce_client,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    granularity: str = 'MONTHLY',
    filter_expr: Optional[Union[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Get Savings Plans utilization. The API is not paginated.

    Args:
        ctx: MCP context
        ce_client: AWS Cost Explorer client
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format (exclusive)
        granularity: Time granularity (DAILY, MONTHLY)
        filter_expr: Optional filters, as an object or JSON string

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

        response = ce_client.get_savings_plans_utilization(**request_params)

        return format_response('success', response)

    except Exception as e:
        # Use shared error handling
        return await handle_aws_error(ctx, e, 'getSavingsPlansUtilization', 'Cost Explorer')
