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

"""AWS Cost Optimization Hub tools for the AWS Billing and Cost Management MCP server.

Updated to use shared utility functions.
"""

from ..utilities.aws_service_base import (
    create_aws_client,
    format_response,
    get_date_range,
    handle_aws_error,
    parse_json,
)
from ..utilities.constants import (
    COST_OPTIMIZATION_HUB_LIST_EFFICIENCY_METRICS_VALID_ORDER_DIMENSIONS,
    COST_OPTIMIZATION_HUB_LIST_RECOMMENDATIONS_VALID_ORDER_DIMENSIONS,
    COST_OPTIMIZATION_HUB_VALID_GROUP_BY_VALUES,
    EFFICIENCY_METRICS_MAX_DAILY_SPAN_DAYS,
    EFFICIENCY_METRICS_MAX_MONTHLY_SPAN_MONTHS,
    EFFICIENCY_METRICS_VALID_GRANULARITY,
    EFFICIENCY_METRICS_VALID_GROUP_BY_VALUES,
    GRANULARITY_DAILY,
    GRANULARITY_MONTHLY,
    OPERATION_GET_RECOMMENDATION,
    OPERATION_LIST_EFFICIENCY_METRICS,
    OPERATION_LIST_RECOMMENDATION_SUMMARIES,
    OPERATION_LIST_RECOMMENDATIONS,
    ORDER_BY_VALID_ORDERS,
)
from .cost_optimization_hub_helpers import (
    get_recommendation,
    list_efficiency_metrics,
    list_recommendation_summaries,
    list_recommendations,
)
from datetime import date, datetime, timedelta
from fastmcp import Context, FastMCP
from typing import Any, Dict, Optional


def _is_valid_efficiency_date(date_str: Optional[str], granularity: str) -> bool:
    """Validate an efficiency-metrics date against the format its granularity requires.

    ``ListEfficiencyMetrics`` uses ``YYYY-MM-DD`` for Daily and ``YYYY-MM`` for
    Monthly. The date is validated against the *resolved* granularity rather than
    accepting the two formats interchangeably, so a granularity/format mismatch
    (e.g. Daily + ``2026-06``) is rejected locally with a clear message instead
    of being forwarded to the API as a malformed date.
    """
    if not date_str:
        return False
    fmt = '%Y-%m-%d' if granularity == GRANULARITY_DAILY else '%Y-%m'
    try:
        parsed = datetime.strptime(date_str, fmt)
    except ValueError:
        return False
    return parsed.strftime(fmt) == date_str


def _coerce_date_for_granularity(date_str: str, granularity: str) -> str:
    """Coerce a date to the format the requested granularity expects.

    Monthly metrics use ``YYYY-MM``; truncate a ``YYYY-MM-DD`` value (e.g. from
    ``get_date_range``) to its month. Daily metrics keep the full date.
    """
    if granularity == GRANULARITY_MONTHLY:
        return date_str[:7]
    return date_str


def _today() -> date:
    """Current date, matching get_date_range's clock so default windows never clamp.

    Isolated in one function so tests can pin 'now' when exercising the clamp.
    """
    return datetime.now().date()


def _clamp_daily(start_date: str, end_date: str) -> str:
    """Move a Daily start forward into the last-90-days window the API serves.

    COH rejects a start more than 90 days before today (the limit is start-to-now,
    not the requested span). Returns the start unchanged when it is already within
    range, or when the whole window predates the range (nothing to salvage, so let
    the service reject it); otherwise returns today minus 90 days.
    """
    start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
    earliest = _today() - timedelta(days=EFFICIENCY_METRICS_MAX_DAILY_SPAN_DAYS)
    if start_dt >= earliest or earliest >= end_dt:
        return start_date
    return earliest.strftime('%Y-%m-%d')


def _clamp_monthly(start_date: str, end_date: str) -> str:
    """Move a Monthly start forward into the last-3-months window the API serves.

    COH rejects a start more than 3 months before the current month (the limit is
    start-to-now, not the requested span). Returns the start unchanged when it is
    already within range, or when the whole window predates the range (nothing to
    salvage, so let the service reject it); otherwise returns the earliest month.
    """
    start_dt = datetime.strptime(start_date, '%Y-%m')
    end_dt = datetime.strptime(end_date, '%Y-%m')
    today = _today()
    now_months = today.year * 12 + today.month
    start_months = start_dt.year * 12 + start_dt.month
    end_months = end_dt.year * 12 + end_dt.month
    earliest_months = now_months - EFFICIENCY_METRICS_MAX_MONTHLY_SPAN_MONTHS
    if start_months >= earliest_months or earliest_months >= end_months:
        return start_date
    year = (earliest_months - 1) // 12
    month = earliest_months - year * 12
    return f'{year:04d}-{month:02d}'


def _clamp_efficiency_time_span(start_date: str, end_date: str, granularity: str) -> str:
    """Move start_date forward into the lookback the COH API will serve.

    ``ListEfficiencyMetrics`` only serves data whose ``start`` is within the most
    recent 90 days (Daily) or 3 months (Monthly) of today -- the limit is measured
    from ``start`` to *now*, not the requested span -- and rejects an older start
    with a ``ValidationException``. Rather than surface that as an error, move
    ``start_date`` forward to the start of the available window (today minus the
    cap). The return value is the effective start; when it differs from the
    requested one the window was trimmed, which is reflected in the response's
    ``time_period`` / ``operation_parameters`` so the caller can explain it to
    the user.

    Dates are assumed pre-coerced to the granularity's format (``YYYY-MM-DD`` for
    Daily, ``YYYY-MM`` for Monthly) by ``_coerce_date_for_granularity``. An
    unparseable date is passed through untouched (validation happens upstream).
    """
    try:
        if granularity == GRANULARITY_DAILY:
            return _clamp_daily(start_date, end_date)
        if granularity == GRANULARITY_MONTHLY:
            return _clamp_monthly(start_date, end_date)
    except ValueError:
        # Malformed dates are rejected upstream by _is_valid_efficiency_date;
        # if one slips through, pass it to the API unchanged.
        pass
    return start_date


def _validate_order_by(order_by: Any, valid_dimensions: list) -> Optional[Dict[str, Any]]:
    """Validate a parsed ``order_by`` structure against the supported dimensions.

    Returns a ``format_response('error', ...)`` dict when the structure is
    invalid, or ``None`` when it is acceptable. ``order`` (``Asc``/``Desc``) is
    optional; when present it must be a valid order value.
    """
    if not isinstance(order_by, dict):
        return format_response(
            'error',
            {'provided_order_by': order_by},
            'order_by must be a JSON object like {"dimension": ..., "order": "Asc"|"Desc"}.',
        )
    dimension = order_by.get('dimension')
    order = order_by.get('order')
    if dimension not in valid_dimensions:
        return format_response(
            'error',
            {'provided_dimension': dimension, 'valid_dimensions': valid_dimensions},
            f'Invalid order_by dimension: {dimension}. Must be one of: {", ".join(valid_dimensions)}.',
        )
    if order is not None and order not in ORDER_BY_VALID_ORDERS:
        return format_response(
            'error',
            {'provided_order': order, 'valid_orders': ORDER_BY_VALID_ORDERS},
            f'Invalid order_by order: {order}. Must be one of: {", ".join(ORDER_BY_VALID_ORDERS)}.',
        )
    return None


cost_optimization_hub_server = FastMCP(
    name='cost-optimization-hub-tools',
    instructions='Tools for working with AWS Cost Optimization Hub API',
)


@cost_optimization_hub_server.tool(
    name='cost-optimization',
    description="""Retrieves cost optimization recommendations from AWS Cost Optimization Hub.

IMPORTANT USAGE GUIDELINES:
- Focus on recommendations with the highest estimated savings first
- Include all relevant details when presenting specific recommendations

USE THIS TOOL FOR:
- **Idle/unused resource detection** (EC2, RDS, EBS, Lambda, etc.)
- **Cost savings recommendations** (rightsizing, stopping, deleting resources)
- **Reserved Instance and Savings Plans purchase recommendations**
- **Cross-service cost optimization analysis**
- **Monthly cost reduction opportunities**

DO NOT USE FOR: Performance optimization (use compute-optimizer)

Supported Operations:
1. list_recommendation_summaries: High-level overview of savings opportunities grouped by a dimension
2. list_recommendations: Detailed list of specific recommendations
3. get_recommendation: Get detailed information about a specific recommendation
4. list_efficiency_metrics: Cost efficiency score, estimated savings, and spend as
   a time series (optionally grouped by AccountId or Region). Use for questions
   about the cost-efficiency score, its trend over time, month-over-month change,
   cross-region/cross-account comparison, and top/worst performers.

IMPORTANT: 'list_recommendation_summaries' operation REQUIRES a 'group_by' parameter.
Valid 'group_by' values: AccountId, Region, ActionType, ResourceType, RestartNeeded, RollbackPossible, ImplementationEffort

CRITICAL PARAMETER REQUIREMENTS:
- 'filters' parameter must be passed as JSON string format
- 'max_results' must be integer (not string)
- 'get_recommendation' requires only 'recommendation_id' (mapped to the API's recommendationId)
- Service only available in us-east-1 region

list_efficiency_metrics parameters:
- 'granularity': 'Daily' or 'Monthly' (defaults to 'Monthly' when omitted)
- 'start_date' / 'end_date': window bounds as 'YYYY-MM-DD' (daily) or 'YYYY-MM'
  (monthly); end is exclusive. Both default to a ~90-day lookback when omitted.
  The API only serves data whose start is within the most recent 90 days (Daily)
  or 3 months (Monthly) of today; an older start_date is automatically moved
  forward to that window, so the returned time_period/start_date may be later
  than requested.
- 'group_by' (optional): 'AccountId' or 'Region' only. Omit to aggregate across all.
- 'order_by' (optional): JSON string {"dimension": "Score"|"Savings"|"Spend",
  "order": "Asc"|"Desc"} for top/worst-performer and directional-sort questions.
- Does NOT accept 'filters'.

Sorting: 'order_by' (JSON string {"dimension": ..., "order": "Asc"|"Desc"}) is also
accepted by 'list_recommendations'. Valid dimensions: EstimatedMonthlySavings,
EstimatedMonthlyCost, RestartNeeded, ImplementationEffort, AccountId, RollbackPossible,
Region, ResourceType, ActionType, ResourceArn, ResourceId, EstimatedSavingsPercentage.
('list_recommendation_summaries' does not support order_by.)

Available Filter Parameters (pass as JSON string):
- resourceTypes: ['Ec2Instance', 'LambdaFunction', 'EbsVolume', 'EcsService', 'Ec2AutoScalingGroup', 'Ec2InstanceSavingsPlans', 'ComputeSavingsPlans', 'SageMakerSavingsPlans', 'Ec2ReservedInstances', 'RdsReservedInstances', 'OpenSearchReservedInstances', 'RedshiftReservedInstances', 'ElastiCacheReservedInstances', 'RdsDbInstanceStorage', 'RdsDbInstance', 'DynamoDbReservedCapacity', 'MemoryDbReservedInstances']
- actionTypes: ['Rightsize', 'Stop', 'Upgrade', 'PurchaseSavingsPlans', 'PurchaseReservedInstances', 'MigrateToGraviton', 'Delete', 'ScaleIn']
- implementationEfforts: ['VeryLow', 'Low', 'Medium', 'High', 'VeryHigh']
- regions: AWS region codes (e.g., ["us-east-1", "us-west-2"])
- accountIds: List of AWS account IDs
- restartNeeded: boolean
- rollbackPossible: boolean

Cost Optimization Hub provides recommendations across multiple AWS services, including:
- EC2 instances (right-sizing, Graviton migration)
- EBS volumes (unused volumes, IOPS optimization)
- RDS instances (right-sizing, engine optimization)
- Lambda functions (memory size optimization)
- SP/RI
- And more

Each recommendation includes:
- The resource ARN and ID
- The estimated monthly savings
- The current state of the resource
- The recommended state of the resource
""",
)
async def cost_optimization_hub(
    ctx: Context,
    operation: str,
    recommendation_id: Optional[str] = None,
    max_results: Optional[int] = None,
    filters: Optional[str] = None,
    group_by: Optional[str] = None,
    include_all_recommendations: Optional[bool] = None,
    next_token: Optional[str] = None,
    max_pages: Optional[int] = None,
    granularity: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    order_by: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieves recommendations and efficiency metrics from AWS Cost Optimization Hub.

    Args:
        ctx: The MCP context
        operation: The operation to perform ('list_recommendations', 'get_recommendation', 'list_recommendation_summaries', or 'list_efficiency_metrics')
        recommendation_id: Recommendation ID for get_recommendation operation (mapped to the API's recommendationId)
        max_results: Per-page result count (boto3 ``maxResults``). NOT a total
            cap. Combine with ``max_pages`` to bound total fetched results.
        filters: Optional filter expression as JSON string (not supported by list_efficiency_metrics)
        group_by: Optional grouping parameter. For list_recommendation_summaries any
            of the recommendation dimensions; for list_efficiency_metrics only
            AccountId or Region.
        include_all_recommendations: Whether to include all recommendations
        next_token: Pagination token to resume from a previous response.
            Applies to list_recommendations, list_recommendation_summaries, and
            list_efficiency_metrics.
        max_pages: Maximum number of pages to fetch when paginating
            list_recommendations, list_recommendation_summaries, or
            list_efficiency_metrics. Use with ``next_token`` to walk results
            incrementally.
        granularity: Time granularity for list_efficiency_metrics ('Daily' or
            'Monthly'). Defaults to 'Monthly' when omitted.
        start_date: Inclusive window start for list_efficiency_metrics
            ('YYYY-MM-DD' or 'YYYY-MM'). Defaults to a ~90-day lookback when omitted.
        end_date: Exclusive window end for list_efficiency_metrics ('YYYY-MM-DD'
            or 'YYYY-MM'). Defaults to today when omitted.
        order_by: Optional ordering as JSON string ``{"dimension": ..., "order":
            "Asc"|"Desc"}``. For list_efficiency_metrics the dimension is one of
            Score/Savings/Spend; also accepted by list_recommendations.

    Returns:
        Dict containing the Cost Optimization Hub recommendations

    Note:
        list_recommendations and list_recommendation_summaries follow the Cost
        Explorer pagination pattern: pass ``next_token`` and/or ``max_pages``
        to walk pages explicitly. Omit both to get a single boto3 page (the
        response's ``next_token``/``Pagination`` field can then drive the next
        call).
    """
    try:
        # Log the request
        await ctx.info(f'Cost Optimization Hub operation: {operation}')

        # Initialize Cost Optimization Hub client using shared utility
        coh_client = create_aws_client('cost-optimization-hub', region_name='us-east-1')
        await ctx.info('Created Cost Optimization Hub client in region us-east-1')

        # Validate operation-specific requirements
        if operation == OPERATION_LIST_RECOMMENDATION_SUMMARIES:
            if not group_by:
                return format_response(
                    'error',
                    {'valid_group_by_values': COST_OPTIMIZATION_HUB_VALID_GROUP_BY_VALUES},
                    f'group_by parameter is required for list_recommendation_summaries operation. Must be one of: {", ".join(COST_OPTIMIZATION_HUB_VALID_GROUP_BY_VALUES)}',
                )

            # Validate the group_by value is one of the allowed values
            if group_by not in COST_OPTIMIZATION_HUB_VALID_GROUP_BY_VALUES:
                return format_response(
                    'error',
                    {
                        'provided_group_by': group_by,
                        'valid_group_by_values': COST_OPTIMIZATION_HUB_VALID_GROUP_BY_VALUES,
                    },
                    f'Invalid group_by value: {group_by}. Must be one of: {", ".join(COST_OPTIMIZATION_HUB_VALID_GROUP_BY_VALUES)}',
                )

        elif operation == OPERATION_GET_RECOMMENDATION:
            if not recommendation_id:
                return format_response(
                    'error',
                    {},
                    'recommendation_id is required for get_recommendation operation',
                )

        # Execute the appropriate operation
        if operation == OPERATION_LIST_RECOMMENDATION_SUMMARIES:
            try:
                # Parse filters if provided
                parsed_filters = parse_json(filters, 'filters') if filters else None

                effective_group_by = str(group_by) if group_by else 'RESOURCE_TYPE'
                await ctx.info(f'Using group_by: {effective_group_by}')

                result = await list_recommendation_summaries(
                    ctx,
                    coh_client,
                    group_by=effective_group_by,
                    max_results=int(max_results) if max_results else None,
                    filters=parsed_filters,
                    next_token=next_token,
                    max_pages=max_pages,
                )

                # Add the operation parameters to the response for diagnostics
                if result.get('status') == 'success' and isinstance(result.get('data'), dict):
                    result['data']['operation_parameters'] = {
                        'group_by': effective_group_by,
                        'max_results': max_results,
                        'filters': filters,
                        'next_token': next_token,
                        'max_pages': max_pages,
                    }

                return result

            except Exception as recommendation_error:
                await ctx.error(
                    f'Error in list_recommendation_summaries: {str(recommendation_error)}'
                )

                # Create a detailed error response
                return format_response(
                    'error',
                    {
                        'error_type': 'service_error',
                        'service': 'Cost Optimization Hub',
                        'operation': 'list_recommendation_summaries',
                        'message': str(recommendation_error),
                        'group_by': group_by or 'RESOURCE_TYPE',
                    },
                    'Error fetching recommendation summaries from Cost Optimization Hub.',
                )

        elif operation == OPERATION_LIST_RECOMMENDATIONS:
            try:
                # Parse filters if provided
                parsed_filters = parse_json(filters, 'filters') if filters else None
                parsed_order_by = parse_json(order_by, 'order_by') if order_by else None
                if parsed_order_by is not None:
                    order_by_error = _validate_order_by(
                        parsed_order_by,
                        COST_OPTIMIZATION_HUB_LIST_RECOMMENDATIONS_VALID_ORDER_DIMENSIONS,
                    )
                    if order_by_error:
                        return order_by_error

                result = await list_recommendations(
                    ctx,
                    coh_client,
                    max_results,
                    parsed_filters,
                    include_all_recommendations,
                    next_token=next_token,
                    max_pages=max_pages,
                    order_by=parsed_order_by,
                )

                # Add the operation parameters to the response for diagnostics
                if result.get('status') == 'success' and isinstance(result.get('data'), dict):
                    result['data']['operation_parameters'] = {
                        'max_results': max_results,
                        'filters': filters,
                        'include_all_recommendations': include_all_recommendations,
                        'next_token': next_token,
                        'max_pages': max_pages,
                        'order_by': order_by,
                    }

                return result

            except Exception as recommendation_error:
                await ctx.error(f'Error in list_recommendations: {str(recommendation_error)}')

                # Create a detailed error response
                return format_response(
                    'error',
                    {
                        'error_type': 'service_error',
                        'service': 'Cost Optimization Hub',
                        'operation': 'list_recommendations',
                        'message': str(recommendation_error),
                    },
                    'Error fetching recommendations from Cost Optimization Hub.',
                )

        elif operation == OPERATION_GET_RECOMMENDATION:
            # recommendation_id is already validated above
            return await get_recommendation(ctx, coh_client, str(recommendation_id))

        elif operation == OPERATION_LIST_EFFICIENCY_METRICS:
            try:
                effective_granularity = granularity or GRANULARITY_MONTHLY
                if effective_granularity not in EFFICIENCY_METRICS_VALID_GRANULARITY:
                    return format_response(
                        'error',
                        {
                            'provided_granularity': granularity,
                            'valid_granularity_values': EFFICIENCY_METRICS_VALID_GRANULARITY,
                        },
                        f'Invalid granularity: {granularity}. Must be one of: {", ".join(EFFICIENCY_METRICS_VALID_GRANULARITY)}.',
                    )

                # Efficiency metrics only group by AccountId/Region (no per-service score).
                if group_by and group_by not in EFFICIENCY_METRICS_VALID_GROUP_BY_VALUES:
                    return format_response(
                        'error',
                        {
                            'provided_group_by': group_by,
                            'valid_group_by_values': EFFICIENCY_METRICS_VALID_GROUP_BY_VALUES,
                        },
                        f'Invalid group_by for list_efficiency_metrics: {group_by}. Must be one of: {", ".join(EFFICIENCY_METRICS_VALID_GROUP_BY_VALUES)}.',
                    )

                # Time window: default a ~90-day lookback when dates are omitted
                # (mirrors the Cost Explorer date-defaulting pattern).
                default_start, default_end = get_date_range(
                    start_date, end_date, default_days_ago=90
                )
                effective_start = start_date or default_start
                effective_end = end_date or default_end

                # Coerce to the format the granularity expects (Monthly ->
                # YYYY-MM, truncating any day component), THEN validate each date
                # against that resolved-granularity format. Validating after
                # coercion — instead of accepting YYYY-MM and YYYY-MM-DD
                # interchangeably — rejects a granularity/format mismatch (e.g.
                # Daily + '2026-06') locally with a clear message rather than
                # forwarding a malformed date to the API.
                effective_start = _coerce_date_for_granularity(
                    effective_start, effective_granularity
                )
                effective_end = _coerce_date_for_granularity(effective_end, effective_granularity)

                expected_format = (
                    'YYYY-MM-DD' if effective_granularity == GRANULARITY_DAILY else 'YYYY-MM'
                )
                for label, value in (
                    ('start_date', effective_start),
                    ('end_date', effective_end),
                ):
                    if not _is_valid_efficiency_date(value, effective_granularity):
                        return format_response(
                            'error',
                            {label: value, 'granularity': effective_granularity},
                            f'Invalid {label}: {value}. For {effective_granularity} '
                            f'granularity use {expected_format}.',
                        )

                # Move an over-old start forward into the window the API serves
                # (start within the last 90 days Daily / 3 months Monthly)
                # instead of letting COH reject the call with a ValidationException.
                # The effective (moved-forward) start is surfaced via
                # operation_parameters below so the caller can explain any
                # trimming to the user.
                effective_start = _clamp_efficiency_time_span(
                    effective_start, effective_end, effective_granularity
                )

                # Parse and validate order_by (JSON string -> dict), mirroring filters.
                parsed_order_by = parse_json(order_by, 'order_by') if order_by else None
                if parsed_order_by is not None:
                    order_by_error = _validate_order_by(
                        parsed_order_by,
                        COST_OPTIMIZATION_HUB_LIST_EFFICIENCY_METRICS_VALID_ORDER_DIMENSIONS,
                    )
                    if order_by_error:
                        return order_by_error

                await ctx.info(
                    f'Fetching efficiency metrics: granularity={effective_granularity}, '
                    f'window={effective_start}..{effective_end}, group_by={group_by}'
                )

                result = await list_efficiency_metrics(
                    ctx,
                    coh_client,
                    granularity=effective_granularity,
                    start_date=effective_start,
                    end_date=effective_end,
                    group_by=group_by,
                    order_by=parsed_order_by,
                    max_results=int(max_results) if max_results else None,
                    next_token=next_token,
                    max_pages=max_pages,
                )

                # Add the operation parameters to the response for diagnostics
                if result.get('status') == 'success' and isinstance(result.get('data'), dict):
                    result['data']['operation_parameters'] = {
                        'granularity': effective_granularity,
                        'start_date': effective_start,
                        'end_date': effective_end,
                        'group_by': group_by,
                        'order_by': order_by,
                        'max_results': max_results,
                        'next_token': next_token,
                        'max_pages': max_pages,
                    }

                return result

            except Exception as efficiency_error:
                await ctx.error(f'Error in list_efficiency_metrics: {str(efficiency_error)}')
                return format_response(
                    'error',
                    {
                        'error_type': 'service_error',
                        'service': 'Cost Optimization Hub',
                        'operation': 'list_efficiency_metrics',
                        'message': str(efficiency_error),
                    },
                    'Error fetching efficiency metrics from Cost Optimization Hub.',
                )

        else:
            # Return error for unsupported operations
            return format_response(
                'error',
                {
                    'supported_operations': [
                        OPERATION_LIST_RECOMMENDATION_SUMMARIES,
                        OPERATION_LIST_RECOMMENDATIONS,
                        OPERATION_GET_RECOMMENDATION,
                        OPERATION_LIST_EFFICIENCY_METRICS,
                    ]
                },
                f"Unsupported operation: {operation}. Use '{OPERATION_LIST_RECOMMENDATION_SUMMARIES}', '{OPERATION_LIST_RECOMMENDATIONS}', '{OPERATION_GET_RECOMMENDATION}', or '{OPERATION_LIST_EFFICIENCY_METRICS}'.",
            )

    except Exception as e:
        await ctx.error(f'Error in Cost Optimization Hub operation {operation}: {str(e)}')
        return await handle_aws_error(ctx, e, operation, 'Cost Optimization Hub')
