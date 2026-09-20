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

"""Helper functions for AWS Cost Optimization Hub operations.

These functions handle the specific operations for the Cost Optimization Hub tool.
"""

from ..utilities.aws_service_base import format_response, paginate_aws_response
from ..utilities.constants import (
    EFFICIENCY_PARETO_MAX_PAGES,
    EFFICIENCY_PARETO_PAGE_SIZE,
    EFFICIENCY_PARETO_SPEND_FRACTION,
    EFFICIENCY_RANKING_MODE_PERFORMANCE,
)
from ..utilities.logging_utils import get_context_logger
from ..utilities.sql_utils import convert_response_if_needed
from botocore.exceptions import ClientError
from datetime import datetime
from fastmcp import Context
from typing import Any, Dict, Optional


def format_timestamp(timestamp: Any) -> Optional[str]:
    """Format a timestamp to ISO format string.

    Args:
        timestamp: Timestamp from Cost Optimization Hub API

    Returns:
        Formatted timestamp string
    """
    if not timestamp:
        return None

    try:
        # Check if it's already a datetime object
        if isinstance(timestamp, datetime):
            return timestamp.isoformat()
        else:
            # Assume it's a Unix timestamp in milliseconds
            from datetime import timezone

            return (
                datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
                .astimezone()
                .replace(tzinfo=None)
                .isoformat()
            )
    except Exception as e:
        return str(f'Error: {e}, Timestamp: {timestamp}')


async def list_recommendations(
    ctx: Context,
    coh_client: Any,
    max_results: Optional[int] = None,
    filters: Optional[Dict[str, Any]] = None,
    include_all_recommendations: Optional[bool] = None,
    next_token: Optional[str] = None,
    max_pages: Optional[int] = None,
    order_by: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """List recommendations from Cost Optimization Hub.

    - When neither ``next_token`` nor ``max_pages`` is provided, a single boto3
      call is made and the raw response (including ``nextToken``, if any) is
      returned. Callers wanting more pages re-invoke with the returned token.
    - When either is provided, ``paginate_aws_response`` walks pages up to
      ``max_pages`` and returns a combined ``items`` list with a ``Pagination``
      envelope so the SQL-offload helper can carry pagination metadata through.

    Args:
        ctx: MCP context
        coh_client: Cost Optimization Hub client
        max_results: Per-page result count (boto3 ``maxResults``). NOT a total
            cap. To bound total fetched results, combine with ``max_pages``.
        filters: Optional filters dictionary
        include_all_recommendations: Whether to include all recommendations
        next_token: Pagination token to resume from a previous response
        max_pages: Maximum number of pages to fetch when paginating
        order_by: Optional ordering dict ``{'dimension': ..., 'order': 'Asc'|'Desc'}``
            passed through as the COH ``orderBy`` structure

    Returns:
        Dict containing recommendations and (when paginated) pagination metadata
    """
    ctx_logger = get_context_logger(ctx, __name__)

    try:
        # Build the boto3 request payload. Field names match the COH API
        # (``filter``, ``maxResults``, ``nextToken``, ``includeAllRecommendations``,
        # ``orderBy``).
        request_params: Dict[str, Any] = {
            'includeAllRecommendations': bool(include_all_recommendations or False)
        }
        if filters:
            request_params['filter'] = dict(filters)
        if order_by:
            request_params['orderBy'] = dict(order_by)
        if max_results:
            request_params['maxResults'] = int(max_results)
        if next_token:
            request_params['nextToken'] = next_token

        # Pagination dispatch — same shape as cost_explorer_operations.
        if next_token or max_pages:
            items, pagination_metadata = await paginate_aws_response(
                ctx,
                'listRecommendations',
                lambda **params: coh_client.list_recommendations(**params),
                request_params,
                'items',
                'nextToken',
                'nextToken',
                max_pages,
            )
            raw_response: Dict[str, Any] = {
                'items': items,
                'Pagination': pagination_metadata,
            }
        else:
            await ctx_logger.info('Fetching recommendations from Cost Optimization Hub')
            raw_response = coh_client.list_recommendations(**request_params)

        # Flatten boto3 items into snake_case dicts. Done after pagination so
        # both code paths reuse the same formatting.
        all_recommendations = raw_response.get('items', [])
        await ctx_logger.info(f'Processing {len(all_recommendations)} total recommendations')

        formatted_recommendations = []
        for item in all_recommendations:
            recommendation = {
                'recommendation_id': item.get('recommendationId'),
                'account_id': item.get('accountId'),
                'region': item.get('region'),
                'resource_id': item.get('resourceId'),
                'resource_arn': item.get('resourceArn'),
                'action_type': item.get('actionType'),
                'current_resource_type': item.get('currentResourceType'),
                'recommended_resource_type': item.get('recommendedResourceType'),
                'current_resource_summary': item.get('currentResourceSummary'),
                'recommended_resource_summary': item.get('recommendedResourceSummary'),
                'estimated_monthly_savings': item.get('estimatedMonthlySavings'),
                'estimated_savings_percentage': item.get('estimatedSavingsPercentage'),
                'estimated_monthly_cost': item.get('estimatedMonthlyCost'),
                'currency_code': item.get('currencyCode'),
                'implementation_effort': item.get('implementationEffort'),
                'last_refresh_timestamp': format_timestamp(item.get('lastRefreshTimestamp')),
                'lookback_period_in_days': item.get('recommendationLookbackPeriodInDays'),
                'restart_needed': item.get('restartNeeded'),
                'rollback_possible': item.get('rollbackPossible'),
            }
            formatted_recommendations.append(recommendation)

        # Preserve the pagination envelope through SQL offload so the model
        # can resume. ``_derive_pagination_envelope`` recognizes both the
        # multi-page ``Pagination`` dict and a single-page ``nextToken`` key.
        response_payload: Dict[str, Any] = {'recommendations': formatted_recommendations}
        if 'Pagination' in raw_response:
            response_payload['Pagination'] = raw_response['Pagination']
        elif 'nextToken' in raw_response:
            response_payload['nextToken'] = raw_response['nextToken']

        offload_or_inline = await convert_response_if_needed(
            ctx,
            response_payload,
            'cost_optimization_hub_list_recommendations',
            pagination_token_key='nextToken',
            order_by=order_by,
        )

        return format_response('success', offload_or_inline)

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', 'An unknown error occurred')
        await ctx_logger.error(f'AWS ClientError in list_recommendations: {error_code}')
        return format_response(
            'error',
            {'error_code': error_code},
            error_message,
        )

    except Exception as e:
        # Let the parent try-catch handle other exceptions
        await ctx_logger.error(f'Unexpected error in list_recommendations: {str(e)}')
        raise


async def get_recommendation(
    ctx: Context, coh_client: Any, recommendation_id: str
) -> Dict[str, Any]:
    """Get detailed information about a specific recommendation.

    Args:
        ctx: MCP context
        coh_client: Cost Optimization Hub client
        recommendation_id: Recommendation ID to retrieve

    Returns:
        Dict containing detailed recommendation information
    """
    # Get context logger for consistent logging
    ctx_logger = get_context_logger(ctx, __name__)

    try:
        # Prepare the request parameters
        request_params = {'recommendationId': recommendation_id}

        # Make the API call
        await ctx_logger.info(f'Fetching recommendation {recommendation_id}')
        response = coh_client.get_recommendation(**request_params)

        # The response IS the recommendation data
        recommendation = response

        if not recommendation:
            await ctx_logger.warning(
                f'No recommendation found for recommendation {recommendation_id}'
            )
            return format_response(
                'warning',
                {
                    'recommendation_id': recommendation_id,
                    'message': 'No recommendation found for the specified recommendation.',
                },
                'No recommendation found. The recommendation may not have optimization opportunities, or the recommendation ID may be incorrect.',
            )

        # Build response using actual API fields
        formatted_response = {
            'recommendation_id': recommendation.get('recommendationId'),
            'account_id': recommendation.get('accountId'),
            'resource_id': recommendation.get('resourceId'),
            'resource_arn': recommendation.get('resourceArn'),
            'current_resource_type': recommendation.get('currentResourceType'),
            'recommended_resource_type': recommendation.get('recommendedResourceType'),
            'region': recommendation.get('region'),
            'action_type': recommendation.get('actionType'),
            'estimated_monthly_savings': recommendation.get('estimatedMonthlySavings'),
            'estimated_savings_percentage': recommendation.get('estimatedSavingsPercentage'),
            'estimated_monthly_cost': recommendation.get('estimatedMonthlyCost'),
            'currency_code': recommendation.get('currencyCode'),
            'implementation_effort': recommendation.get('implementationEffort'),
            'source': recommendation.get('source'),
            'last_refresh_timestamp': str(recommendation.get('lastRefreshTimestamp')),
            'lookback_period_in_days': recommendation.get('recommendationLookbackPeriodInDays'),
            'cost_calculation_lookback_period_in_days': recommendation.get(
                'costCalculationLookbackPeriodInDays'
            ),
            'restart_needed': recommendation.get('restartNeeded'),
            'rollback_possible': recommendation.get('rollbackPossible'),
        }

        # Add complex nested fields if they exist
        if 'currentResourceDetails' in recommendation:
            formatted_response['current_resource_details'] = recommendation.get(
                'currentResourceDetails'
            )

        if 'recommendedResourceDetails' in recommendation:
            formatted_response['recommended_resource_details'] = recommendation.get(
                'recommendedResourceDetails'
            )

        if 'tags' in recommendation:
            formatted_response['tags'] = recommendation.get('tags')

        # Return formatted response
        return format_response('success', formatted_response)

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', 'An unknown error occurred')

        if error_code == 'ValidationException':
            await ctx_logger.warning(f'Validation error in get_recommendation: {error_message}')
            return format_response(
                'error',
                {'error_code': error_code, 'error_message': error_message},
                f'Cost Optimization Hub validation error: {error_message}',
            )
        elif error_code == 'AccessDeniedException':
            await ctx_logger.error(
                f'Access denied for Cost Optimization Hub get_recommendation: {error_message}'
            )
            return format_response(
                'error',
                {'error_code': error_code},
                'Access denied for Cost Optimization Hub. Ensure you have the necessary permissions: cost-optimization-hub:GetRecommendation.',
            )
        elif error_code == 'ResourceNotFoundException':
            await ctx_logger.warning(f'Resource not found: {error_message}')
            return format_response(
                'warning',
                {
                    'error_code': error_code,
                    'recommendation_id': recommendation_id,
                },
                f'Recommendation {recommendation_id} not found in Cost Optimization Hub.',
            )
        else:
            # Re-raise for other errors
            raise

    except Exception as e:
        await ctx_logger.error(f'Unexpected error in get_recommendation: {str(e)}')
        raise


async def list_recommendation_summaries(
    ctx: Context,
    coh_client: Any,
    group_by: str,
    max_results: Optional[int] = None,
    filters: Optional[Dict[str, Any]] = None,
    next_token: Optional[str] = None,
    max_pages: Optional[int] = None,
) -> Dict[str, Any]:
    """List recommendation summaries from Cost Optimization Hub.

    - When neither ``next_token`` nor ``max_pages`` is provided, a single boto3
      call is made and the raw response is formatted (its ``nextToken`` field,
      if any, is exposed in the result so callers can resume).
    - When either is provided, ``paginate_aws_response`` walks pages up to
      ``max_pages`` and the combined summaries are returned with a
      ``Pagination`` envelope so callers can continue paging.

    Args:
        ctx: MCP context
        coh_client: Cost Optimization Hub client
        group_by: Grouping parameter (e.g. ``RESOURCE_TYPE``)
        max_results: Per-page result count (boto3 ``maxResults``). NOT a total
            cap. Combine with ``max_pages`` to bound total fetched results.
        filters: Optional filters dictionary
        next_token: Pagination token to resume from a previous response
        max_pages: Maximum number of pages to fetch when paginating

    Returns:
        Dict containing recommendation summaries and (when paginated)
        pagination metadata.
    """
    ctx_logger = get_context_logger(ctx, __name__)

    try:
        # Build the boto3 request payload. Field names match the COH API.
        request_params: Dict[str, Any] = {'groupBy': str(group_by)}
        if filters:
            request_params['filter'] = dict(filters)
        if max_results:
            request_params['maxResults'] = int(max_results)
        if next_token:
            request_params['nextToken'] = next_token

        # The top-level metadata fields (``groupBy``, ``currencyCode``,
        # ``estimatedTotalDedupedSavings``, ``metrics``) are global aggregates
        # over the full filtered result set, not per-page values. Capture the
        # FIRST response (rather than the last) so the aggregate header
        # describes the result set the caller started paginating — and so the
        # code stays correct if the API ever made these fields page-scoped.
        first_response: Dict[str, Any] = {}

        if next_token or max_pages:

            def api_call(**params: Any) -> Dict[str, Any]:
                # Stash the first response so we can read its top-level
                # aggregate fields after paginate_aws_response returns.
                nonlocal first_response
                response = coh_client.list_recommendation_summaries(**params)
                if not first_response:
                    first_response = response
                return response

            items, pagination_metadata = await paginate_aws_response(
                ctx,
                'listRecommendationSummaries',
                api_call,
                request_params,
                'items',
                'nextToken',
                'nextToken',
                max_pages,
            )
            raw_response: Dict[str, Any] = {
                'items': items,
                'Pagination': pagination_metadata,
            }
        else:
            await ctx_logger.info(f'Fetching recommendation summaries grouped by {group_by}')
            first_response = coh_client.list_recommendation_summaries(**request_params)
            raw_response = first_response

        # Flatten boto3 items into snake_case dicts. Done after pagination so
        # both code paths reuse the same formatting.
        all_summaries = raw_response.get('items', [])
        await ctx_logger.info(f'Processing {len(all_summaries)} total recommendation summaries')

        formatted_summaries = [
            {
                'group': item.get('group'),
                'estimated_monthly_savings': item.get('estimatedMonthlySavings'),
                'recommendation_count': item.get('recommendationCount'),
            }
            for item in all_summaries
        ]

        formatted_response: Dict[str, Any] = {
            'group_by': first_response.get('groupBy', group_by),
            'currency_code': first_response.get('currencyCode', 'USD'),
            'estimated_total_savings': first_response.get('estimatedTotalDedupedSavings'),
            'summaries': formatted_summaries,
        }
        if 'metrics' in first_response:
            formatted_response['metrics'] = {
                'savings_percentage': first_response['metrics'].get('savingsPercentage')
            }

        # Preserve resumption state. Multi-page path carries the canonical
        # ``Pagination`` envelope; single-page exposes the raw ``nextToken``
        # so callers can continue paging on their own.
        if 'Pagination' in raw_response:
            formatted_response['Pagination'] = raw_response['Pagination']
        elif 'nextToken' in raw_response:
            formatted_response['nextToken'] = raw_response['nextToken']

        return format_response('success', formatted_response)

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', 'An unknown error occurred')
        await ctx_logger.error(f'AWS ClientError in list_recommendation_summaries: {error_code}')
        return format_response(
            'error',
            {'error_code': error_code},
            error_message,
        )

    except Exception as e:
        # Handle non-AWS errors
        await ctx_logger.error(f'Unexpected error in list_recommendation_summaries: {str(e)}')
        return format_response(
            'error',
            {
                'error_type': 'service_error',
                'service': 'Cost Optimization Hub',
                'operation': 'list_recommendation_summaries',
                'message': str(e),
            },
            'Error retrieving recommendation summaries. Try using list_recommendations operation instead.',
        )


def _latest_efficiency_point(metrics_by_time: list) -> Optional[Dict[str, Any]]:
    """Return a group's most recent usable metrics point, or ``None``.

    "Usable" means the point with the max ``timestamp`` that has both a score and
    a spend; ``None`` is returned when the group has no such point.

    Timestamps are ``YYYY-MM`` (Monthly) or ``YYYY-MM-DD`` (Daily); both sort
    lexicographically within a single granularity, so the last element after a
    string sort is the latest period.
    """
    points = [p for p in (metrics_by_time or []) if p.get('timestamp')]
    if not points:
        return None
    for point in sorted(points, key=lambda p: p['timestamp'], reverse=True):
        if point.get('score') is not None and point.get('spend') is not None:
            return point
    return None


def _apply_pareto_materiality(
    groups: list,
    fraction: float,
    direction: str = 'Desc',
    cap_hit: bool = False,
    groups_fetched: Optional[int] = None,
) -> tuple:
    """Rank grouped efficiency metrics by score, spend-materiality aware.

    The fetch that feeds this is highest-spend-first (orderBy Spend Desc), so the
    input is the org's biggest spenders. Ranking accounts/Regions purely by score
    can surface low-spend groups with little savings opportunity -- which score
    near-100% -- over the big spenders, so:
    1. Drop groups with no usable latest score or non-positive latest spend.
    2. **If the full set was retrieved** (``cap_hit`` False): keep the highest-spend
       groups whose cumulative spend first reaches ``fraction`` of the total (the
       Pareto "vital few") — a valid cutoff because total spend is known.
    3. **If the fetch hit the page cap** (``cap_hit`` True): total org spend is
       unknown, so DO NOT apply the cutoff — keep every scored group fetched (the
       top spenders) and disclose it as a partial, top-spenders-only view.
    4. Rank the kept groups by latest score in ``direction`` (``'Desc'`` = best
       first / top performers; ``'Asc'`` = worst first / lowest performers).

    Returns ``(ranked_groups, ranking_focus)`` where ``ranking_focus`` is metadata
    describing what was kept vs. set aside (so the caller can explain it without
    misreporting omitted/unfetched groups as "missing"). ``ranking_focus`` also
    carries ``material_spend`` (the kept groups' combined latest spend) and
    ``material_spend_fraction`` (their ACTUAL cumulative share of ``total_spend``,
    a real number to state instead of the ``pareto_spend_fraction`` cutoff) -- the
    fraction is ``None`` when capped, because ``total_spend`` then covers only the
    fetched top-spenders, not the whole org.
    """
    scored = []  # (group, latest_spend, latest_score)
    for group in groups:
        point = _latest_efficiency_point(group.get('metrics_by_time'))
        if point is None:
            continue
        score = point.get('score')
        spend = point.get('spend')
        if score is None or score < 0:
            continue
        if spend is None or spend <= 0:
            continue
        scored.append((group, float(spend), float(score)))

    total_spend = sum(spend for _, spend, _ in scored)
    scored.sort(key=lambda t: t[1], reverse=True)  # spend desc

    pareto_applied = not cap_hit
    if pareto_applied:
        # Full set in hand -> keep the vital few up to the spend fraction.
        material = []
        cumulative = 0.0
        cutoff = total_spend * fraction
        for entry in scored:
            material.append(entry)
            cumulative += entry[1]
            if cumulative >= cutoff:
                break
    else:
        # Capped -> total spend unknown, so no cutoff; rank all fetched spenders.
        material = list(scored)

    score_descending = direction != 'Asc'
    material.sort(key=lambda t: t[2], reverse=score_descending)  # score in requested direction
    ranked_groups = [group for group, _, _ in material]

    omitted = len(scored) - len(ranked_groups)
    material_spend = sum(spend for _, spend, _ in material)
    # Kept groups' true share of total_spend. Only meaningful when the cutoff was
    # applied (total_spend is the full scored-set total); when capped it covers
    # only fetched top spenders, so leave it None rather than read as ~100%.
    material_spend_fraction = (
        material_spend / total_spend if pareto_applied and total_spend > 0 else None
    )
    ranking_focus = {
        'mode': EFFICIENCY_RANKING_MODE_PERFORMANCE,
        'direction': direction,
        'pareto_applied': pareto_applied,
        'pareto_spend_fraction': fraction if pareto_applied else None,
        'total_groups_ranked': len(scored),
        'material_groups': len(ranked_groups),
        'omitted_groups': omitted,
        'total_spend': total_spend,
        'material_spend': material_spend,
        'material_spend_fraction': material_spend_fraction,
        'cap_hit': bool(cap_hit),
        'groups_fetched': groups_fetched,
    }
    return ranked_groups, ranking_focus


async def list_efficiency_metrics(
    ctx: Context,
    coh_client: Any,
    granularity: str,
    start_date: str,
    end_date: str,
    group_by: Optional[str] = None,
    order_by: Optional[Dict[str, Any]] = None,
    max_results: Optional[int] = None,
    next_token: Optional[str] = None,
    max_pages: Optional[int] = None,
    ranking_mode: Optional[str] = None,
) -> Dict[str, Any]:
    """List cost efficiency metrics from Cost Optimization Hub.

    Returns time-series efficiency data (efficiency score, estimated savings, and
    spend) aggregated over the requested time period and optionally grouped by
    account ID or Region.

    - When neither ``next_token`` nor ``max_pages`` is provided, a single boto3
      call is made and the raw response (including ``nextToken``, if any) is
      formatted so callers can resume.
    - When either is provided, ``paginate_aws_response`` walks pages up to
      ``max_pages`` and the combined groups are returned with a ``Pagination``
      envelope.

    Args:
        ctx: MCP context
        coh_client: Cost Optimization Hub client
        granularity: ``Daily`` or ``Monthly`` (COH title-case values)
        start_date: Inclusive start of the window (``YYYY-MM-DD`` or ``YYYY-MM``)
        end_date: Exclusive end of the window (``YYYY-MM-DD`` or ``YYYY-MM``)
        group_by: Optional grouping dimension (``AccountId`` or ``Region``); omit
            to aggregate across all resources
        order_by: Optional ordering dict ``{'dimension': 'Score'|'Savings'|'Spend',
            'order': 'Asc'|'Desc'}`` passed through as the COH ``orderBy`` structure
        max_results: Per-page result count (boto3 ``maxResults``). NOT a total
            cap. Combine with ``max_pages`` to bound total fetched results.
        next_token: Pagination token to resume from a previous response
        max_pages: Maximum number of pages to fetch when paginating
        ranking_mode: Applies to list_efficiency_metrics only (the other COH
            operations do not accept it). When ``'performance'`` and ``group_by``
            is set, reduce the groups to the Pareto-material set (highest-spend
            groups making up ~80% of total spend, ranked by score) so tiny/idle
            groups do not surface as top performers. Forces a highest-spend-first
            paginated fetch up to the page cap; if the cap is hit the spend cutoff
            is skipped and ranking_focus flags a partial top-spenders view. Omit
            for the raw series.

    Returns:
        Dict containing efficiency metrics grouped over time and (when paginated)
        pagination metadata. In ``performance`` ranking mode a ``ranking_focus``
        block describes the material vs. set-aside groups.
    """
    ctx_logger = get_context_logger(ctx, __name__)

    try:
        request_params: Dict[str, Any] = {
            'granularity': str(granularity),
            'timePeriod': {'start': str(start_date), 'end': str(end_date)},
        }
        if group_by:
            request_params['groupBy'] = str(group_by)
        if order_by:
            request_params['orderBy'] = dict(order_by)
        if max_results:
            request_params['maxResults'] = int(max_results)
        if next_token:
            request_params['nextToken'] = next_token

        # Performance ranking fetches highest-spend accounts first, up to the page
        # cap, so the spend-material ones arrive before the cap is reached.
        performance_mode = ranking_mode == EFFICIENCY_RANKING_MODE_PERFORMANCE and bool(group_by)
        performance_direction = 'Desc'
        if performance_mode:
            # order_by does not drive the fetch here; it only sets the ranking
            # direction (Asc = worst first, Desc/omitted = best first).
            if isinstance(order_by, dict) and order_by.get('order') == 'Asc':
                performance_direction = 'Asc'
            request_params['orderBy'] = {'dimension': 'Spend', 'order': 'Desc'}
            # A caller max_results is a display "top N", not a fetch size — drop it
            # so it can't shrink the fetch and cap spend coverage early.
            request_params.pop('maxResults', None)
        effective_max_pages = max_pages
        if performance_mode and not next_token:
            effective_max_pages = max_pages or EFFICIENCY_PARETO_MAX_PAGES
            # Bounded per-page size; page cap x page size = the top-spenders ceiling.
            request_params['maxResults'] = EFFICIENCY_PARETO_PAGE_SIZE

        # Pagination dispatch — same shape as the other list helpers, but the
        # result list lives under ``efficiencyMetricsByGroup``.
        if next_token or effective_max_pages:
            groups, pagination_metadata = await paginate_aws_response(
                ctx,
                'listEfficiencyMetrics',
                lambda **params: coh_client.list_efficiency_metrics(**params),
                request_params,
                'efficiencyMetricsByGroup',
                'nextToken',
                'nextToken',
                effective_max_pages,
            )
            raw_response: Dict[str, Any] = {
                'efficiencyMetricsByGroup': groups,
                'Pagination': pagination_metadata,
            }
        else:
            await ctx_logger.info(
                f'Fetching efficiency metrics ({granularity}) from Cost Optimization Hub'
            )
            raw_response = coh_client.list_efficiency_metrics(**request_params)

        # Flatten boto3 groups into snake_case dicts. Done after pagination so
        # both code paths reuse the same formatting.
        all_groups = raw_response.get('efficiencyMetricsByGroup', [])
        await ctx_logger.info(f'Processing {len(all_groups)} total efficiency-metric groups')

        formatted_groups = [
            {
                'group': group.get('group'),
                'message': group.get('message'),
                'metrics_by_time': [
                    {
                        'timestamp': point.get('timestamp'),
                        'score': point.get('score'),
                        'savings': point.get('savings'),
                        'spend': point.get('spend'),
                    }
                    for point in (group.get('metricsByTime') or [])
                ],
            }
            for group in all_groups
        ]

        # Rank by score, dropping idle/no-score groups (see _apply_pareto_materiality).
        ranking_focus = None
        if performance_mode:
            # Cap-hit = a nextToken still remained (org has more groups than the cap
            # reached); the fetched set is then the top spenders only.
            pagination = raw_response.get('Pagination')
            perf_capped = (
                bool(pagination.get('has_more')) if isinstance(pagination, dict) else False
            )
            fetched_count = (
                pagination.get('total_results') if isinstance(pagination, dict) else None
            )
            formatted_groups, ranking_focus = _apply_pareto_materiality(
                formatted_groups,
                EFFICIENCY_PARETO_SPEND_FRACTION,
                direction=performance_direction,
                cap_hit=perf_capped,
                groups_fetched=fetched_count,
            )
            await ctx_logger.info(
                f'Performance ranking (score {performance_direction}): kept '
                f'{ranking_focus["material_groups"]} of {ranking_focus["total_groups_ranked"]} '
                f'scored groups; pareto_applied={ranking_focus["pareto_applied"]}; '
                f'cap_hit={perf_capped}'
            )

        formatted_response: Dict[str, Any] = {
            'granularity': granularity,
            'time_period': {'start': start_date, 'end': end_date},
            'group_by': group_by,
            'groups': formatted_groups,
        }
        if ranking_focus is not None:
            formatted_response['ranking_focus'] = ranking_focus

        # Preserve resumption state. Multi-page path carries the canonical
        # ``Pagination`` envelope; single-page exposes the raw ``nextToken``.
        if 'Pagination' in raw_response:
            formatted_response['Pagination'] = raw_response['Pagination']
        elif 'nextToken' in raw_response:
            formatted_response['nextToken'] = raw_response['nextToken']

        # ranking_focus is a sibling of `groups`, so it would be dropped on offload
        # (only `groups` becomes the SQL table); carry it through as metadata.
        offload_metadata: Dict[str, Any] = {}
        if ranking_focus is not None:
            offload_metadata['ranking_focus'] = ranking_focus

        offload_or_inline = await convert_response_if_needed(
            ctx,
            formatted_response,
            'cost_optimization_hub_list_efficiency_metrics',
            pagination_token_key='nextToken',
            # Performance mode already ranked by score client-side; ignore order_by
            # here too so the (rare) offload sample matches the returned ordering.
            order_by=None if performance_mode else order_by,
            **offload_metadata,
        )

        return format_response('success', offload_or_inline)

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', 'An unknown error occurred')
        await ctx_logger.error(f'AWS ClientError in list_efficiency_metrics: {error_code}')
        return format_response(
            'error',
            {'error_code': error_code},
            error_message,
        )

    except Exception as e:
        # Let the parent try-catch handle other exceptions
        await ctx_logger.error(f'Unexpected error in list_efficiency_metrics: {str(e)}')
        raise
