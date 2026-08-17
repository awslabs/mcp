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
    create_aws_client,
    format_response,
    handle_aws_error,
    paginate_aws_response,
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
through three operations:

1. get_savings_plans_purchase_recommendation: The recommended commitment for a given plan type,
   term, and payment option, with estimated savings, coverage, and utilization.
2. get_savings_plan_purchase_recommendation_details: The hourly data-points behind a single
   recommendation, keyed by the RecommendationDetailId returned above.
3. list_savings_plans_purchase_recommendation_generation: Generation history with status and
   timestamps.

USE THIS TOOL FOR:
- **What to buy** — the recommended commitment for a given plan type, term, and payment option
- **Whether that commitment would go unused** — the hourly EstimatedNewCommitmentUtilization behind
  the recommendation, rather than a figure derived from the raw spend series
- **How stale the recommendation is** — when it was last generated

DO NOT USE THIS TOOL FOR:
- What the customer already owns, which is sp-explorer
- Coverage or utilization of existing plans, which is sp-performance
- Modeling a commitment the customer specifies rather than a recommended one

This tool is read-only. Refreshing a recommendation is a mutation and is not exposed here.

IMPORTANT: get_savings_plans_purchase_recommendation requires savings_plans_type, term_in_years,
payment_option, and lookback_period_in_days. None of them has a default — each changes the
recommended commitment, so the caller must choose. Recommendations are precomputed and may be
stale; the response carries the generation timestamp.""",
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
    next_page_token: Optional[str] = None,
    page_size: Optional[int] = None,
    max_pages: Optional[int] = None,
) -> Dict[str, Any]:
    """Tool that retrieves AWS Savings Plans purchase recommendations.

    Args:
        ctx: The MCP context object
        operation: The operation to perform: 'get_savings_plans_purchase_recommendation', 'get_savings_plan_purchase_recommendation_details', or 'list_savings_plans_purchase_recommendation_generation'
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
        next_page_token: Pagination token.
        page_size: Maximum number of results to return per page.
        max_pages: The maximum number of pages to fetch when listing generations. Omitting it
            fetches every page.

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
                next_page_token,
                page_size,
            )
        elif operation == 'get_savings_plan_purchase_recommendation_details':
            return await get_savings_plan_purchase_recommendation_details(
                ctx, ce_client, recommendation_detail_id
            )
        elif operation == 'list_savings_plans_purchase_recommendation_generation':
            return await list_savings_plans_purchase_recommendation_generation(
                ctx,
                ce_client,
                generation_status,
                recommendation_ids,
                next_page_token,
                page_size,
                max_pages,
            )
        else:
            return format_response(
                'error',
                {},
                f'Unsupported operation: {operation}. Use '
                "'get_savings_plans_purchase_recommendation', "
                "'get_savings_plan_purchase_recommendation_details', or "
                "'list_savings_plans_purchase_recommendation_generation'.",
            )

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'sp_recommendation', 'Cost Explorer')


async def get_savings_plans_purchase_recommendation(
    ctx: Context,
    ce_client: Any,
    savings_plans_type: Optional[str],
    term_in_years: Optional[str],
    payment_option: Optional[str],
    lookback_period_in_days: Optional[str],
    account_scope: Optional[str],
    filter_expr: Optional[Dict[str, Any]],
    next_page_token: Optional[str],
    page_size: Optional[int],
) -> Dict[str, Any]:
    """Retrieves the Savings Plans recommendations for your account.

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
        next_page_token: The token to retrieve the next set of results. AWS provides the token when
            the response from a previous call has more results than the maximum page size.
        page_size: The number of recommendations that you want returned in a single response
            object.

    Returns:
        Dict containing the recommendation
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
        if next_page_token:
            request_params['NextPageToken'] = next_page_token
        if page_size:
            request_params['PageSize'] = int(page_size)

        response = ce_client.get_savings_plans_purchase_recommendation(**request_params)

        return format_response('success', response)

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


async def list_savings_plans_purchase_recommendation_generation(
    ctx: Context,
    ce_client: Any,
    generation_status: Optional[str],
    recommendation_ids: Optional[List[str]],
    next_page_token: Optional[str],
    page_size: Optional[int],
    max_pages: Optional[int],
) -> Dict[str, Any]:
    """Retrieves a list of your historical recommendation generations within the past 30 days.

    Args:
        ctx: The MCP context
        ce_client: Cost Explorer client
        generation_status: The status of the recommendation generation.
        recommendation_ids: The IDs for each specific recommendation.
        next_page_token: The token to retrieve the next set of results.
        page_size: The number of recommendations that you want returned in a single response
            object.
        max_pages: The maximum number of pages to fetch. None fetches every page.

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
        if next_page_token:
            request_params['NextPageToken'] = next_page_token
        if page_size:
            request_params['PageSize'] = int(page_size)

        all_generations, pagination_metadata = await paginate_aws_response(
            ctx=ctx,
            operation_name='ListSavingsPlansPurchaseRecommendationGeneration',
            api_function=ce_client.list_savings_plans_purchase_recommendation_generation,
            request_params=request_params,
            result_key='GenerationSummaryList',
            token_param='NextPageToken',
            token_key='NextPageToken',
            max_pages=max_pages,
        )

        return format_response(
            'success',
            {'GenerationSummaryList': all_generations, 'pagination': pagination_metadata},
        )

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(
            ctx, e, 'list_savings_plans_purchase_recommendation_generation', 'Cost Explorer'
        )
