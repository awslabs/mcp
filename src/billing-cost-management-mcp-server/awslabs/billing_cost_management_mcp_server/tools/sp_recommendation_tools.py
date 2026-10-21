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

"""AWS Savings Plans purchase recommendation tools for the AWS Billing and Cost Management MCP server."""

from ..utilities.aws_service_base import (
    PageSpec,
    create_aws_client,
    format_response,
    handle_aws_error,
    paginate_aws_items,
    with_pagination,
)
from ..utilities.logging_utils import get_context_logger
from fastmcp import Context, FastMCP
from typing import Any, Dict, List, Optional


sp_recommendation_server = FastMCP(
    name='sp-recommendation-tools',
    instructions='Tools for working with AWS Savings Plans purchase recommendations',
)


@sp_recommendation_server.tool(
    name='sp-recommendation',
    description="""Tool that retrieves AWS Savings Plans purchase recommendations using the Cost Explorer API.

This tool provides the commitment a customer should consider buying, and the evidence behind it,
through four operations:

1. get_savings_plans_purchase_recommendation: The recommended commitment for a given plan type,
   term, and payment option, with estimated savings, coverage, and utilization.
2. get_savings_plan_purchase_recommendation_details: The hourly data-points behind a single
   recommendation, keyed by the RecommendationDetailId returned above.
3. start_savings_plans_purchase_recommendation_generation: Recalculates the recommendation against
   the latest usage and the current Savings Plans inventory.
4. list_savings_plans_purchase_recommendation_generation: Generation history with status and
   timestamps.

USE THIS TOOL FOR:
- **What to buy** — the recommended commitment for a given plan type, term, and payment option
- **Whether that commitment would go unused** — the hourly EstimatedNewCommitmentUtilization behind
  the recommendation, rather than a figure derived from the raw spend series
- **How stale the recommendation is** — when it was last generated
- **A recommendation that reflects a purchase just made** — refresh it, since the stored one predates
  the purchase

DO NOT USE THIS TOOL FOR:
- What the customer already owns, which is sp-explorer
- Coverage or utilization of existing plans, which is sp-performance
- Modeling a commitment the customer specifies rather than a recommended one, which is
  sp-purchase-analyzer

ASYNCHRONOUS: start_savings_plans_purchase_recommendation_generation returns a RecommendationId and
an EstimatedCompletionTime, not a recommendation. Poll
list_savings_plans_purchase_recommendation_generation, filtered on that RecommendationId, until
GenerationStatus leaves PROCESSING, then read the refreshed recommendation with
get_savings_plans_purchase_recommendation. Completion time scales with the size of the billing
family, so read EstimatedCompletionTime rather than assuming a duration.

WRITE OPERATION: a consolidated billing family can refresh recommendations three times a day, and
only one generation runs at a time. Check the generation history before starting another — a
recommendation generated hours ago is usually fresh enough, and a refresh that fails leaves the
older recommendation in place with a timestamp that does not say so.

IMPORTANT: get_savings_plans_purchase_recommendation requires savings_plans_type, term_in_years,
payment_option, and lookback_period_in_days. None of them has a default — each changes the
recommended commitment, so the caller must choose. Recommendations are precomputed and may be
stale; the response carries the generation timestamp.

PAGINATION (get_savings_plans_purchase_recommendation, where the items are the recommendation
details, and list_savings_plans_purchase_recommendation_generation; the other operations take
neither parameter):
- max_items is the total number of items returned. Omit it to fetch every page (no limit). Pass it,
  or narrow the filter, for queries that can be large.
- If the response has complete_dataset: false, call again with a larger max_items, continue with
  next_token, or state in the answer that the result is partial.""",
)
async def sp_recommendation(
    ctx: Context,
    operation: str,
    savings_plans_type: Optional[str] = None,
    term_in_years: Optional[str] = None,
    payment_option: Optional[str] = None,
    lookback_period_in_days: Optional[str] = None,
    account_scope: Optional[str] = None,
    filter: Optional[Dict[str, Any]] = None,
    recommendation_detail_id: Optional[str] = None,
    generation_status: Optional[str] = None,
    recommendation_ids: Optional[List[str]] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Tool that retrieves AWS Savings Plans purchase recommendations.

    Args:
        ctx: The MCP context object
        operation: The operation to perform: 'get_savings_plans_purchase_recommendation', 'get_savings_plan_purchase_recommendation_details', 'start_savings_plans_purchase_recommendation_generation', or 'list_savings_plans_purchase_recommendation_generation'
        savings_plans_type: COMPUTE_SP, EC2_INSTANCE_SP, SAGEMAKER_SP, or DATABASE_SP. Required for get_savings_plans_purchase_recommendation.
        term_in_years: ONE_YEAR or THREE_YEARS. Required for get_savings_plans_purchase_recommendation.
        payment_option: NO_UPFRONT, PARTIAL_UPFRONT, or ALL_UPFRONT. Required for get_savings_plans_purchase_recommendation. The API shape also accepts three
            LIGHT/MEDIUM/HEAVY_UTILIZATION values, which are Reserved Instance utilization levels and do not apply to Savings Plans.
        lookback_period_in_days: SEVEN_DAYS, THIRTY_DAYS, or SIXTY_DAYS. Required for get_savings_plans_purchase_recommendation.
        account_scope: PAYER or LINKED.
        filter: Filter recommendations by Account ID. Includes Dimensions only,
            with Key as LINKED_ACCOUNT and Value one or more Account IDs. AND and OR operators are
            not supported. Applies to get_savings_plans_purchase_recommendation only.
        recommendation_detail_id: Required for get_savings_plan_purchase_recommendation_details. Comes from the RecommendationDetailId field of a recommendation.
        generation_status: SUCCEEDED, PROCESSING, or FAILED. Filters list_savings_plans_purchase_recommendation_generation.
        recommendation_ids: Recommendation IDs to filter to.
        max_items: Total number of items (recommendation details, or generations) to return
            across all pages. Omit it to fetch every page. Paginated operations only.
        next_token: The pagination.next_token from a previous response; continue with otherwise
            identical parameters. A token belongs to the request that produced it and to the
            recommendation it was generated against, so it stops working once the parameters
            change or the recommendation is regenerated; read from the first page again when that
            happens. Paginated operations only.

    Returns:
        Dict containing the savings plans purchase recommendation information
    """
    try:
        await ctx.info(f'Savings Plans purchase recommendation operation: {operation}')

        # Initialize Cost Explorer client using shared utility
        ce_client = create_aws_client('ce', region_name='us-east-1')

        if operation == 'get_savings_plans_purchase_recommendation':
            return await get_savings_plans_purchase_recommendation(
                ctx,
                ce_client,
                savings_plans_type,
                term_in_years,
                payment_option,
                lookback_period_in_days,
                account_scope,
                filter,
                max_items,
                next_token,
            )
        elif operation == 'get_savings_plan_purchase_recommendation_details':
            return await get_savings_plan_purchase_recommendation_details(
                ctx, ce_client, recommendation_detail_id
            )
        elif operation == 'start_savings_plans_purchase_recommendation_generation':
            return await start_savings_plans_purchase_recommendation_generation(ctx, ce_client)
        elif operation == 'list_savings_plans_purchase_recommendation_generation':
            return await list_savings_plans_purchase_recommendation_generation(
                ctx,
                ce_client,
                generation_status,
                recommendation_ids,
                max_items,
                next_token,
            )
        else:
            return format_response(
                'error',
                {},
                f'Unsupported operation: {operation}. Use '
                "'get_savings_plans_purchase_recommendation', "
                "'get_savings_plan_purchase_recommendation_details', "
                "'start_savings_plans_purchase_recommendation_generation', or "
                "'list_savings_plans_purchase_recommendation_generation'.",
            )

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'sp_recommendation', 'Cost Explorer')


# The details list sits inside SavingsPlansPurchaseRecommendation, alongside the term, payment
# option, and summary that give the details their meaning.
CE_GET_SAVINGS_PLANS_PURCHASE_RECOMMENDATION = PageSpec(
    result_key=('SavingsPlansPurchaseRecommendation', 'SavingsPlansPurchaseRecommendationDetails'),
    token_param='NextPageToken',
    token_key_in_response='NextPageToken',
    page_max=6000,
    page_size_param='PageSize',
)


async def get_savings_plans_purchase_recommendation(
    ctx: Context,
    ce_client: Any,
    savings_plans_type: Optional[str],
    term_in_years: Optional[str],
    payment_option: Optional[str],
    lookback_period_in_days: Optional[str],
    account_scope: Optional[str],
    filter_expr: Optional[Dict[str, Any]],
    max_items: Optional[int],
    next_token: Optional[str],
) -> Dict[str, Any]:
    """Retrieves the Savings Plans recommendations for your account.

    The recommendation details are paged, so this walks the pages and merges them into the first
    page's recommendation.

    Args:
        ctx: The MCP context
        ce_client: Cost Explorer client
        savings_plans_type: The Savings Plans recommendation type that's requested.
        term_in_years: The savings plan recommendation term that's used to generate these
            recommendations.
        payment_option: The payment option that's used to generate these recommendations.
        lookback_period_in_days: The lookback period that's used to generate the recommendation.
        account_scope: The account scope that you want your recommendations for. AWS calculates
            recommendations including the management account and member accounts if the value is
            set to PAYER. If the value is LINKED, recommendations are calculated for individual
            member accounts only.
        filter_expr: Filter by Account ID with the LINKED_ACCOUNT dimension.
        max_items: Total number of recommendation details to return. None fetches every page.
        next_token: The token from a previous response.

    Returns:
        Dict containing the recommendation with every page of details merged
    """
    # Get context logger for consistent logging
    ctx_logger = get_context_logger(ctx, __name__)

    try:
        await ctx_logger.info(
            f'Fetching {savings_plans_type} recommendation: {term_in_years}, '
            f'{payment_option}, {lookback_period_in_days} lookback'
        )

        # Prepare the request parameters
        request_params: dict = {
            'SavingsPlansType': savings_plans_type,
            'TermInYears': term_in_years,
            'PaymentOption': payment_option,
            'LookbackPeriodInDays': lookback_period_in_days,
        }

        # Add optional parameters if provided
        if account_scope:
            request_params['AccountScope'] = account_scope
        if filter_expr:
            request_params['Filter'] = filter_expr

        details, pages, pagination = await paginate_aws_items(
            ctx,
            'GetSavingsPlansPurchaseRecommendation',
            ce_client.get_savings_plans_purchase_recommendation,
            request_params,
            CE_GET_SAVINGS_PLANS_PURCHASE_RECOMMENDATION,
            max_items=max_items,
            next_token=next_token,
        )

        # Rebuild the response the API shapes, with the merged details in place of one page of
        # them. Every field outside the details list (Metadata, the summary, the term and payment
        # option) is taken from the first page fetched: it repeats unchanged on later pages
        # because a token pins the recommendation version it was generated against. The
        # top-level token is dropped because pagination reports it instead.
        first_page = pages[0] if pages else {}
        merged_recommendation = dict(first_page.get('SavingsPlansPurchaseRecommendation') or {})
        merged_recommendation['SavingsPlansPurchaseRecommendationDetails'] = details

        data = {k: v for k, v in first_page.items() if k != 'NextPageToken'}
        data['SavingsPlansPurchaseRecommendation'] = merged_recommendation

        return format_response('success', with_pagination(data, pagination))

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(
            ctx, e, 'get_savings_plans_purchase_recommendation', 'Cost Explorer'
        )


async def get_savings_plan_purchase_recommendation_details(
    ctx: Context,
    ce_client: Any,
    recommendation_detail_id: Optional[str],
) -> Dict[str, Any]:
    """Retrieves the details for a Savings Plan recommendation.

    These details include the hourly data-points that construct the cost, coverage, and
    utilization charts.

    Args:
        ctx: The MCP context
        ce_client: Cost Explorer client
        recommendation_detail_id: The ID that is associated with the Savings Plan recommendation.

    Returns:
        Dict containing the recommendation detail
    """
    # Get context logger for consistent logging
    ctx_logger = get_context_logger(ctx, __name__)

    try:
        await ctx_logger.info(f'Fetching recommendation detail {recommendation_detail_id}')

        response = ce_client.get_savings_plan_purchase_recommendation_details(
            RecommendationDetailId=recommendation_detail_id
        )

        return format_response('success', response)

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(
            ctx, e, 'get_savings_plan_purchase_recommendation_details', 'Cost Explorer'
        )


async def start_savings_plans_purchase_recommendation_generation(
    ctx: Context,
    ce_client: Any,
) -> Dict[str, Any]:
    """Requests a Savings Plans recommendation generation.

    This enables you to calculate a fresh set of Savings Plans recommendations that takes your
    latest usage data and current Savings Plans inventory into account. You can refresh Savings
    Plans recommendations up to three times daily for a consolidated billing family. The operation
    has no request syntax because no input parameters are needed to support it.

    Args:
        ctx: The MCP context
        ce_client: Cost Explorer client

    Returns:
        Dict containing the generation identifiers
    """
    # Get context logger for consistent logging
    ctx_logger = get_context_logger(ctx, __name__)

    try:
        await ctx_logger.info('Starting Savings Plans purchase recommendation generation')

        response = ce_client.start_savings_plans_purchase_recommendation_generation()

        return format_response('success', response)

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(
            ctx, e, 'start_savings_plans_purchase_recommendation_generation', 'Cost Explorer'
        )


CE_LIST_SAVINGS_PLANS_PURCHASE_RECOMMENDATION_GENERATION = PageSpec(
    result_key='GenerationSummaryList',
    token_param='NextPageToken',
    token_key_in_response='NextPageToken',
    page_max=6000,
    page_size_param='PageSize',
)


async def list_savings_plans_purchase_recommendation_generation(
    ctx: Context,
    ce_client: Any,
    generation_status: Optional[str],
    recommendation_ids: Optional[List[str]],
    max_items: Optional[int],
    next_token: Optional[str],
) -> Dict[str, Any]:
    """Retrieves a list of your historical recommendation generations within the past 30 days.

    Args:
        ctx: The MCP context
        ce_client: Cost Explorer client
        generation_status: The status of the recommendation generation.
        recommendation_ids: The IDs for each specific recommendation.
        max_items: Total number of generations to return. None fetches every page.
        next_token: The token from a previous response.

    Returns:
        Dict containing the generation history
    """
    # Get context logger for consistent logging
    ctx_logger = get_context_logger(ctx, __name__)

    try:
        await ctx_logger.info('Listing Savings Plans purchase recommendation generations')

        # Create request parameters
        request_params: dict = {}

        # Add optional parameters if provided
        if generation_status:
            request_params['GenerationStatus'] = generation_status
        if recommendation_ids:
            request_params['RecommendationIds'] = recommendation_ids

        all_generations, _, pagination = await paginate_aws_items(
            ctx,
            'ListSavingsPlansPurchaseRecommendationGeneration',
            ce_client.list_savings_plans_purchase_recommendation_generation,
            request_params,
            CE_LIST_SAVINGS_PLANS_PURCHASE_RECOMMENDATION_GENERATION,
            max_items=max_items,
            next_token=next_token,
        )

        return format_response(
            'success', with_pagination({'GenerationSummaryList': all_generations}, pagination)
        )

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(
            ctx, e, 'list_savings_plans_purchase_recommendation_generation', 'Cost Explorer'
        )
