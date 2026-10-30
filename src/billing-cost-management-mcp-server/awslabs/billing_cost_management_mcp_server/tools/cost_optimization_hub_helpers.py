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

from ..utilities.aws_service_base import (
    PageSpec,
    first_page_fields,
    format_response,
    handle_aws_error,
    paginate_aws_items,
    with_pagination,
)
from ..utilities.constants import (
    COST_OPTIMIZATION_HUB_SERVICE_NAME,
    EFFICIENCY_PARETO_MAX_PAGES,
    EFFICIENCY_PARETO_PAGE_SIZE,
    EFFICIENCY_PARETO_SPEND_FRACTION,
    EFFICIENCY_RANKING_MODE_PERFORMANCE,
    OPERATION_GET_PREFERENCES,
    OPERATION_GET_RECOMMENDATION,
    OPERATION_LIST_EFFICIENCY_METRICS,
    OPERATION_LIST_ENROLLMENT_STATUSES,
    OPERATION_LIST_RECOMMENDATION_SUMMARIES,
    OPERATION_LIST_RECOMMENDATIONS,
)
from ..utilities.logging_utils import get_context_logger
from ..utilities.sql_utils import convert_response_if_needed
from ..utilities.time_utils import format_timestamp_to_utc_iso
from botocore.exceptions import ClientError
from fastmcp import Context
from typing import Any, Dict, Optional


# maxResults is at most 1000 on every paginated COH list operation, and nextToken is not
# bound to it, so each page asks for what is left of max_items.
COH_LIST_RECOMMENDATIONS = PageSpec(
    result_key='items',
    token_param='nextToken',
    token_key_in_response='nextToken',
    page_max=1000,
    page_size_param='maxResults',
    # The service reports a bad caller next_token as ValidationException.
    caller_token_error_codes=frozenset({'ValidationException'}),
)
COH_LIST_RECOMMENDATION_SUMMARIES = PageSpec(
    result_key='items',
    token_param='nextToken',
    token_key_in_response='nextToken',
    page_max=1000,
    page_size_param='maxResults',
    # The service reports a bad caller next_token as ValidationException.
    caller_token_error_codes=frozenset({'ValidationException'}),
)
COH_LIST_EFFICIENCY_METRICS = PageSpec(
    result_key='efficiencyMetricsByGroup',
    token_param='nextToken',
    token_key_in_response='nextToken',
    page_max=1000,
    page_size_param='maxResults',
    # The service reports a bad caller next_token as ValidationException.
    caller_token_error_codes=frozenset({'ValidationException'}),
)
# Performance ranking's internal fetch: EFFICIENCY_PARETO_PAGE_SIZE groups per page, highest
# spend first, up to EFFICIENCY_PARETO_MAX_PAGES pages (a cap of pages x page size groups).
COH_LIST_EFFICIENCY_METRICS_PERFORMANCE = PageSpec(
    result_key='efficiencyMetricsByGroup',
    token_param='nextToken',
    token_key_in_response='nextToken',
    page_max=EFFICIENCY_PARETO_PAGE_SIZE,
    page_size_param='maxResults',
    fixed_page_size=True,
)
EFFICIENCY_PARETO_MAX_GROUPS = EFFICIENCY_PARETO_MAX_PAGES * EFFICIENCY_PARETO_PAGE_SIZE


def format_timestamp(timestamp: Any) -> Optional[str]:
    """Format a timestamp to a UTC ISO 8601 string.

    Args:
        timestamp: Timestamp from Cost Optimization Hub API: a datetime (boto3),
            epoch seconds, or epoch milliseconds.

    Returns:
        Formatted timestamp string, or None if missing or unconvertible.
    """
    return format_timestamp_to_utc_iso(timestamp)


async def list_recommendations(
    ctx: Context,
    coh_client: Any,
    max_items: Optional[int] = None,
    filters: Optional[Dict[str, Any]] = None,
    include_all_recommendations: Optional[bool] = None,
    next_token: Optional[str] = None,
    order_by: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """List recommendations from Cost Optimization Hub.

    Fetches every page, or stops before exceeding ``max_items``, and returns the combined
    recommendations with a ``pagination`` block. ``orderBy`` is sent on every page, so
    ``order_by`` + ``max_items=N`` is the top N.

    Args:
        ctx: MCP context
        coh_client: Cost Optimization Hub client
        max_items: Most recommendations to return. None fetches every page.
        filters: Optional filters dictionary
        include_all_recommendations: Whether to include all recommendations
        next_token: Pagination token to resume from a previous response
        order_by: Optional ordering dict ``{'dimension': ..., 'order': 'Asc'|'Desc'}``
            passed through as the COH ``orderBy`` structure

    Returns:
        Dict containing recommendations and pagination metadata
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

        all_recommendations, _, pagination = await paginate_aws_items(
            ctx,
            'listRecommendations',
            coh_client.list_recommendations,
            request_params,
            COH_LIST_RECOMMENDATIONS,
            max_items=max_items,
            next_token=next_token,
        )
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

        # The pagination block survives SQL offload so the model can see partial data and resume.
        response_payload = with_pagination(
            {'recommendations': formatted_recommendations}, pagination
        )

        offload_or_inline = await convert_response_if_needed(
            ctx,
            response_payload,
            'cost_optimization_hub_list_recommendations',
            order_by=order_by,
        )

        return format_response('success', offload_or_inline)

    except Exception as e:
        return await handle_aws_error(
            ctx, e, OPERATION_LIST_RECOMMENDATIONS, COST_OPTIMIZATION_HUB_SERVICE_NAME
        )


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
        # The response IS the recommendation data. A missing recommendation raises
        # ResourceNotFoundException (handled below); boto3 never returns an empty response.
        recommendation = coh_client.get_recommendation(**request_params)

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
            'last_refresh_timestamp': format_timestamp(recommendation.get('lastRefreshTimestamp')),
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

    except Exception as e:
        # A missing recommendation is reported as a warning naming the ID rather than as an error.
        if (
            isinstance(e, ClientError)
            and e.response.get('Error', {}).get('Code') == 'ResourceNotFoundException'
        ):
            await ctx_logger.warning(f'Resource not found: {recommendation_id}')
            return format_response(
                'warning',
                {
                    'error_code': 'ResourceNotFoundException',
                    'recommendation_id': recommendation_id,
                },
                f'Recommendation {recommendation_id} not found in Cost Optimization Hub. The '
                'ID may be invalid (it must be a Cost Optimization Hub recommendation ID, not a '
                'resource ID or ARN), or the recommendation may no longer exist: recommendations '
                'are refreshed daily and removed once they no longer apply. Call '
                'list_recommendations to check the current recommendations for the resource.',
            )
        return await handle_aws_error(
            ctx, e, OPERATION_GET_RECOMMENDATION, COST_OPTIMIZATION_HUB_SERVICE_NAME
        )


async def list_recommendation_summaries(
    ctx: Context,
    coh_client: Any,
    group_by: str,
    max_items: Optional[int] = None,
    filters: Optional[Dict[str, Any]] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List recommendation summaries from Cost Optimization Hub.

    Fetches every page, or stops before exceeding ``max_items``, and returns the combined
    summaries with a ``pagination`` block so callers can see partial data and continue.

    Args:
        ctx: MCP context
        coh_client: Cost Optimization Hub client
        group_by: Grouping parameter (e.g. ``RESOURCE_TYPE``)
        max_items: Most summaries to return. None fetches every page.
        filters: Optional filters dictionary
        next_token: Pagination token to resume from a previous response

    Returns:
        Dict containing recommendation summaries and pagination metadata.
    """
    ctx_logger = get_context_logger(ctx, __name__)

    try:
        # Build the boto3 request payload. Field names match the COH API.
        request_params: Dict[str, Any] = {'groupBy': str(group_by)}
        if filters:
            request_params['filter'] = dict(filters)

        all_summaries, pages, pagination = await paginate_aws_items(
            ctx,
            'listRecommendationSummaries',
            coh_client.list_recommendation_summaries,
            request_params,
            COH_LIST_RECOMMENDATION_SUMMARIES,
            max_items=max_items,
            next_token=next_token,
        )
        # ``groupBy``, ``currencyCode``, ``estimatedTotalDedupedSavings`` and ``metrics`` are
        # aggregates over the whole filtered result set, so they come from the first page.
        first_response = first_page_fields(
            pages, ['groupBy', 'currencyCode', 'estimatedTotalDedupedSavings', 'metrics']
        )
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
            'estimated_total_deduped_savings': first_response.get('estimatedTotalDedupedSavings'),
        }
        # Each recommendation falls in exactly one group, so the group counts add up to the
        # overall count, but only over every group: a partial result or a continuation would
        # undercount, so the field is left out there.
        counts = [summary['recommendation_count'] for summary in formatted_summaries]
        if (
            next_token is None
            and pagination['complete_dataset']
            and all(isinstance(count, int) for count in counts)
        ):
            formatted_response['total_recommendation_count'] = sum(counts)
        formatted_response['summaries'] = formatted_summaries
        if 'metrics' in first_response:
            formatted_response['metrics'] = {
                'savings_percentage': first_response['metrics'].get('savingsPercentage')
            }

        return format_response('success', with_pagination(formatted_response, pagination))

    except Exception as e:
        return await handle_aws_error(
            ctx, e, OPERATION_LIST_RECOMMENDATION_SUMMARIES, COST_OPTIMIZATION_HUB_SERVICE_NAME
        )


async def list_enrollment_statuses(
    ctx: Context,
    coh_client: Any,
    account_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Get the Cost Optimization Hub enrollment status of an account.

    Args:
        ctx: MCP context
        coh_client: Cost Optimization Hub client
        account_id: Optional account ID. Omit for the calling account.

    Returns:
        Dict containing the enrollment status of the account.
    """
    ctx_logger = get_context_logger(ctx, __name__)

    try:
        request_params: Dict[str, Any] = {}
        if account_id:
            request_params['accountId'] = str(account_id)

        await ctx_logger.info('Fetching Cost Optimization Hub enrollment status')
        response = coh_client.list_enrollment_statuses(**request_params)

        enrollment_statuses = [
            {
                'account_id': item.get('accountId'),
                'status': item.get('status'),
                'last_updated_timestamp': format_timestamp(item.get('lastUpdatedTimestamp')),
                'created_timestamp': format_timestamp(item.get('createdTimestamp')),
            }
            for item in response.get('items', [])
        ]
        if not enrollment_statuses:
            # A never-enrolled account has no enrollment record, so the API returns no
            # items rather than an Inactive one. Report it as Inactive so callers get an
            # explicit status instead of an empty list.
            enrollment_statuses = [{'status': 'Inactive'}]

        return format_response('success', {'enrollment_statuses': enrollment_statuses})

    except Exception as e:
        return await handle_aws_error(
            ctx, e, OPERATION_LIST_ENROLLMENT_STATUSES, COST_OPTIMIZATION_HUB_SERVICE_NAME
        )


async def get_preferences(ctx: Context, coh_client: Any) -> Dict[str, Any]:
    """Get the Cost Optimization Hub preferences of the calling account.

    Args:
        ctx: MCP context
        coh_client: Cost Optimization Hub client

    Returns:
        Dict containing the savings estimation mode, member account discount
        visibility, and preferred commitment.
    """
    ctx_logger = get_context_logger(ctx, __name__)

    try:
        await ctx_logger.info('Fetching Cost Optimization Hub preferences')
        response = coh_client.get_preferences()

        preferred_commitment = response.get('preferredCommitment') or {}
        return format_response(
            'success',
            {
                'savings_estimation_mode': response.get('savingsEstimationMode'),
                'member_account_discount_visibility': response.get(
                    'memberAccountDiscountVisibility'
                ),
                'preferred_commitment': {
                    'term': preferred_commitment.get('term'),
                    'payment_option': preferred_commitment.get('paymentOption'),
                },
            },
        )

    except Exception as e:
        return await handle_aws_error(
            ctx, e, OPERATION_GET_PREFERENCES, COST_OPTIMIZATION_HUB_SERVICE_NAME
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


def _performance_pagination(
    cap_hit: bool, groups_fetched: Optional[int], groups_returned: int
) -> Dict[str, Any]:
    """Build the pagination block for a performance ranking.

    A ranking is not continuable: groups past the fetch would be ranked on their own, so
    there is never a ``next_token``, and neither a larger ``max_items`` nor a continuation
    widens the fetch. The block is partial only when the fetch stopped before the full set;
    trimming the ranked list to ``max_items`` is a requested top N, not partial data.
    """
    pagination: Dict[str, Any] = {
        'complete_dataset': not cap_hit,
        'has_more': False,
        'next_token': None,
        'items_returned': groups_returned,
    }
    if cap_hit:
        reason = (
            'fetch cap reached'
            if (groups_fetched or 0) >= EFFICIENCY_PARETO_MAX_GROUPS
            else 'fetch stopped early'
        )
        pagination['warning'] = (
            f'Ranking covers only the top {groups_fetched} spenders ({reason}); groups '
            'beyond them were not analyzed. Group by a coarser dimension (Region) for a '
            'complete ranking, or state that it covers only the top spenders.'
        )
    return pagination


async def list_efficiency_metrics(
    ctx: Context,
    coh_client: Any,
    granularity: str,
    start_date: str,
    end_date: str,
    group_by: Optional[str] = None,
    order_by: Optional[Dict[str, Any]] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
    ranking_mode: Optional[str] = None,
) -> Dict[str, Any]:
    """List cost efficiency metrics from Cost Optimization Hub.

    Returns time-series efficiency data (efficiency score, estimated savings, and
    spend), optionally grouped by account ID or Region. Each point is a one-day
    snapshot (estimated savings of the recommendations open that day, against the
    trailing 30 days of spend); a Monthly point is the snapshot for the last day
    of the month that has data, with the trailing 30 days of spend at month-end.

    Fetches every page, or stops before exceeding ``max_items``, and returns the combined
    groups with a ``pagination`` block. ``orderBy`` is sent on every page. In ``performance``
    ranking mode the fetch is fixed (highest spend first, ``EFFICIENCY_PARETO_PAGE_SIZE`` per
    page, up to ``EFFICIENCY_PARETO_MAX_PAGES`` pages) and ``max_items`` only trims the
    ranked list returned; the ranking has no ``next_token`` and is partial only when the
    fetch stopped before the full set (see ``_performance_pagination``).

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
        max_items: Most groups to return. None fetches every page. In ``performance``
            ranking mode, the most ranked groups to return.
        next_token: Pagination token to resume from a previous response
        ranking_mode: Applies to list_efficiency_metrics only (the other COH
            operations do not accept it). When ``'performance'`` and ``group_by``
            is set, reduce the groups to the Pareto-material set (highest-spend
            groups making up ~80% of total spend, ranked by score) so tiny/idle
            groups do not surface as top performers. Forces a highest-spend-first
            paginated fetch up to the page cap; if the cap is hit the spend cutoff
            is skipped and ranking_focus flags a partial top-spenders view. Omit
            for the raw series.

    Returns:
        Dict containing efficiency metrics grouped over time and the pagination block. In ``performance`` ranking mode a ``ranking_focus``
        block describes the material vs. set-aside groups.
    """
    ctx_logger = get_context_logger(ctx, __name__)

    try:
        # Validate here: performance mode replaces max_items with its own fetch size, so the
        # paginator's check would never see the caller's value.
        if max_items is not None and max_items < 1:
            raise ValueError('max_items must be at least 1. Omit it to fetch every page.')

        request_params: Dict[str, Any] = {
            'granularity': str(granularity),
            'timePeriod': {'start': str(start_date), 'end': str(end_date)},
        }
        if group_by:
            request_params['groupBy'] = str(group_by)
        if order_by:
            request_params['orderBy'] = dict(order_by)

        # Performance ranking fetches highest-spend groups first, up to a fixed cap, so the
        # spend-material ones arrive before the cap is reached.
        performance_mode = ranking_mode == EFFICIENCY_RANKING_MODE_PERFORMANCE and bool(group_by)
        performance_direction = 'Desc'
        spec = COH_LIST_EFFICIENCY_METRICS
        fetch_max_items = max_items
        if performance_mode:
            # order_by does not drive the fetch here; it only sets the ranking
            # direction (Asc = worst first, Desc/omitted = best first).
            if isinstance(order_by, dict) and order_by.get('order') == 'Asc':
                performance_direction = 'Asc'
            request_params['orderBy'] = {'dimension': 'Spend', 'order': 'Desc'}
            # max_items is a display "top N" here, not a fetch size, so it can't shrink the
            # fetch and cap spend coverage early.
            spec = COH_LIST_EFFICIENCY_METRICS_PERFORMANCE
            fetch_max_items = EFFICIENCY_PARETO_MAX_GROUPS

        await ctx_logger.info(
            f'Fetching efficiency metrics ({granularity}) from Cost Optimization Hub'
        )
        all_groups, _, pagination = await paginate_aws_items(
            ctx,
            'listEfficiencyMetrics',
            coh_client.list_efficiency_metrics,
            request_params,
            spec,
            max_items=fetch_max_items,
            next_token=next_token,
        )

        # Flatten boto3 groups into snake_case dicts.
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
            # Cap-hit = the fetch stopped before the last page (org has more groups than
            # the cap reached); the fetched set is then the top spenders only.
            perf_capped = not pagination.get('complete_dataset', True)
            formatted_groups, ranking_focus = _apply_pareto_materiality(
                formatted_groups,
                EFFICIENCY_PARETO_SPEND_FRACTION,
                direction=performance_direction,
                cap_hit=perf_capped,
                groups_fetched=pagination.get('items_returned'),
            )
            if max_items is not None:
                # Trim only the ranked list; ranking_focus still describes the full ranking.
                formatted_groups = formatted_groups[:max_items]
            ranking_focus['groups_returned'] = len(formatted_groups)
            if len(formatted_groups) < ranking_focus['material_groups']:
                ranking_focus['note'] = (
                    f'Returned the top {len(formatted_groups)} of '
                    f'{ranking_focus["material_groups"]} ranked groups (max_items).'
                )
            pagination = _performance_pagination(
                perf_capped, pagination.get('items_returned'), len(formatted_groups)
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

        formatted_response = with_pagination(formatted_response, pagination)

        # ranking_focus is a sibling of `groups`, so it would be dropped on offload
        # (only `groups` becomes the SQL table); carry it through as metadata.
        offload_metadata: Dict[str, Any] = {}
        if ranking_focus is not None:
            offload_metadata['ranking_focus'] = ranking_focus

        offload_or_inline = await convert_response_if_needed(
            ctx,
            formatted_response,
            'cost_optimization_hub_list_efficiency_metrics',
            # Performance mode already ranked by score client-side; ignore order_by
            # here too so the (rare) offload sample matches the returned ordering.
            order_by=None if performance_mode else order_by,
            **offload_metadata,
        )

        return format_response('success', offload_or_inline)

    except Exception as e:
        return await handle_aws_error(
            ctx, e, OPERATION_LIST_EFFICIENCY_METRICS, COST_OPTIMIZATION_HUB_SERVICE_NAME
        )
