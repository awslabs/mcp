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

"""AWS Savings Plans Purchase Analyzer tools for the AWS Billing and Cost Management MCP server."""

from ..utilities.aws_service_base import (
    PageSpec,
    create_aws_client,
    format_response,
    handle_aws_error,
    paginate_aws_items,
    with_pagination,
)
from ..utilities.constants import PAGINATION_LIMIT_TEXT
from ..utilities.logging_utils import get_context_logger
from fastmcp import Context, FastMCP
from typing import Any, Dict, List, Optional


sp_purchase_analyzer_server = FastMCP(
    name='sp-purchase-analyzer-tools',
    instructions='Tools for working with the AWS Savings Plans Purchase Analyzer',
)


@sp_purchase_analyzer_server.tool(
    name='sp-purchase-analyzer',
    description="""Tool that runs AWS Savings Plans Purchase Analyzer what-if analyses using the Cost Explorer API.

This tool estimates the cost, coverage, and utilization impact of a commitment purchase the caller
specifies, through three operations:

1. start_commitment_purchase_analysis: Starts an analysis. Returns an AnalysisId and an
   EstimatedCompletionTime; it does not return results.
2. get_commitment_purchase_analysis: Retrieves a result by AnalysisId.
3. list_commitment_purchase_analyses: Lists the analyses for the account.

USE THIS TOOL FOR:
- **What commitment reaches a specific coverage target** — TARGET_AVERAGE_COVERAGE
- **What a specific commitment would do** — CUSTOM_COMMITMENT
- **What the largest saving would be, modelled now** — MAX_SAVINGS
- **What an expiring plan is worth** — exclude it and compare the result
- **Retrieving an analysis that was already started** — by its AnalysisId

DO NOT USE THIS TOOL FOR:
- A precomputed recommendation, which is sp-recommendation
- What the customer already owns, which is sp-explorer
- Coverage or utilization of existing plans, which is sp-performance

ASYNCHRONOUS: start_commitment_purchase_analysis returns an AnalysisId and an
EstimatedCompletionTime, not a result. Report the AnalysisId before waiting on it — a wait that ends
early leaves the analysis running server-side, and recovering it then means listing the account's
analyses and picking one out by start time. Then poll get_commitment_purchase_analysis until
AnalysisStatus leaves PROCESSING. Completion time scales with account size, so read
EstimatedCompletionTime rather than assuming a duration.

WRITE OPERATION: an account can start 20 analyses a day, one at a time. GenerationExistsException
means one is already running, ServiceQuotaExceededException means the day's 20 are used up, and
LimitExceededException is transient. They are not interchangeable.

IMPORTANT: the API takes one nested CommitmentPurchaseAnalysisConfiguration, which this tool builds
from analysis_type, savings_plans_to_add, look_back_start, and look_back_end. All four are needed —
savings_plans_to_add for every analysis type, MAX_SAVINGS included, since the plan type, term, and
payment option live inside it. None has a default: each changes the result, and a wrong guess spends
one of the day's analyses on a scenario nobody asked for. A validation error names the nested field
it rejected rather than the parameter, so read the path in the message. An analysis also carries the
configuration it was run with, so read AnalysisType from a result rather than assuming which
scenario it modelled.

PAGINATION (list_commitment_purchase_analyses only; the other operations take neither parameter):
- max_items is the total number of analyses returned. If it is omitted, the tool fetches every page for """
    + PAGINATION_LIMIT_TEXT
    + """, then returns a partial result.
- If the response has complete_dataset: false, call again with a larger max_items, continue with
  next_token, or state in the answer that the result is partial.""",
)
async def sp_purchase_analyzer(
    ctx: Context,
    operation: str,
    analysis_type: Optional[str] = None,
    savings_plans_to_add: Optional[List[Dict[str, Any]]] = None,
    savings_plans_to_exclude: Optional[List[str]] = None,
    look_back_start: Optional[str] = None,
    look_back_end: Optional[str] = None,
    savings_plans_target_coverage: Optional[int] = None,
    account_scope: Optional[str] = None,
    account_id: Optional[str] = None,
    analysis_id: Optional[str] = None,
    analysis_ids: Optional[List[str]] = None,
    analysis_status: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Tool that runs AWS Savings Plans Purchase Analyzer what-if analyses.

    Args:
        ctx: The MCP context object
        operation: The operation to perform: 'start_commitment_purchase_analysis', 'get_commitment_purchase_analysis', or 'list_commitment_purchase_analyses'
        analysis_type: The type of analysis — MAX_SAVINGS, CUSTOM_COMMITMENT, or
            TARGET_AVERAGE_COVERAGE. Required for start_commitment_purchase_analysis.
        savings_plans_to_add: Savings Plans to include in the analysis. Each entry accepts
            SavingsPlansType (COMPUTE_SP, EC2_INSTANCE_SP, SAGEMAKER_SP, or DATABASE_SP),
            TermInYears (ONE_YEAR or THREE_YEARS), PaymentOption (NO_UPFRONT, PARTIAL_UPFRONT, or
            ALL_UPFRONT), SavingsPlansCommitment as an hourly amount, Region, InstanceFamily, and
            OfferingId. Required for start_commitment_purchase_analysis — for example
            [{"SavingsPlansType": "COMPUTE_SP", "TermInYears": "ONE_YEAR", "PaymentOption":
            "NO_UPFRONT"}].
        savings_plans_to_exclude: Savings Plan ARNs to exclude from the analysis. Use it to model the
            gap an expiring plan leaves behind.
        look_back_start: Start of the time period associated with the analysis, in YYYY-MM-DD format.
            Required for start_commitment_purchase_analysis.
        look_back_end: End of the time period associated with the analysis, in YYYY-MM-DD format.
            Required for start_commitment_purchase_analysis.
        savings_plans_target_coverage: The target Savings Plans coverage as a whole-number
            percentage from 10 to 100 — 85, not 0.85 or 85.5. It defines the target average hourly
            coverage that the recommended Savings Plans commitment should achieve over the lookback
            period. Required when analysis_type is TARGET_AVERAGE_COVERAGE.
        account_scope: The account scope that you want your analysis for — PAYER or LINKED.
        account_id: The account that the analysis is for.
        analysis_id: The analysis ID that's associated with the commitment purchase analysis.
            Required for get_commitment_purchase_analysis.
        analysis_ids: The analysis IDs associated with the commitment purchase analyses.
            Filters list_commitment_purchase_analyses.
        analysis_status: The status of the analysis — SUCCEEDED, PROCESSING, or FAILED. Filters
            list_commitment_purchase_analyses.
        max_items: Total number of analyses to return across all pages. Omit it to fetch every
            page. list_commitment_purchase_analyses only.
        next_token: The pagination.next_token from a previous response; continue with otherwise
            identical parameters. list_commitment_purchase_analyses only.

    Returns:
        Dict containing the analysis identifiers or results
    """
    try:
        await ctx.info(f'Savings Plans Purchase Analyzer operation: {operation}')

        # Initialize Cost Explorer client using shared utility
        ce_client = create_aws_client('ce', region_name='us-east-1')

        if operation == 'start_commitment_purchase_analysis':
            return await start_commitment_purchase_analysis(
                ctx,
                ce_client,
                analysis_type,
                savings_plans_to_add,
                savings_plans_to_exclude,
                look_back_start,
                look_back_end,
                savings_plans_target_coverage,
                account_scope,
                account_id,
            )
        elif operation == 'get_commitment_purchase_analysis':
            return await get_commitment_purchase_analysis(ctx, ce_client, analysis_id)
        elif operation == 'list_commitment_purchase_analyses':
            return await list_commitment_purchase_analyses(
                ctx,
                ce_client,
                analysis_status,
                analysis_ids,
                max_items,
                next_token,
            )
        else:
            return format_response(
                'error',
                {},
                f'Unsupported operation: {operation}. Use '
                "'start_commitment_purchase_analysis', 'get_commitment_purchase_analysis', or "
                "'list_commitment_purchase_analyses'.",
            )

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'sp_purchase_analyzer', 'Cost Explorer')


async def start_commitment_purchase_analysis(
    ctx: Context,
    ce_client: Any,
    analysis_type: Optional[str],
    savings_plans_to_add: Optional[List[Dict[str, Any]]],
    savings_plans_to_exclude: Optional[List[str]],
    look_back_start: Optional[str],
    look_back_end: Optional[str],
    savings_plans_target_coverage: Optional[int],
    account_scope: Optional[str],
    account_id: Optional[str],
) -> Dict[str, Any]:
    """Specifies the parameters of a planned commitment purchase and starts the analysis.

    This enables you to estimate the cost, coverage, and utilization impact of your planned
    commitment purchases.

    Args:
        ctx: The MCP context
        ce_client: Cost Explorer client
        analysis_type: The type of analysis.
        savings_plans_to_add: Savings Plans to include in the analysis.
        savings_plans_to_exclude: Savings Plan ARNs to exclude from the analysis.
        look_back_start: Start of the time period associated with the analysis.
        look_back_end: End of the time period associated with the analysis.
        savings_plans_target_coverage: The target Savings Plans coverage as a percentage.
        account_scope: The account scope that you want your analysis for.
        account_id: The account that the analysis is for.

    Returns:
        Dict containing the analysis id and timing
    """
    # Get context logger for consistent logging
    ctx_logger = get_context_logger(ctx, __name__)

    try:
        await ctx_logger.info(
            f'Starting {analysis_type} analysis over {look_back_start} to {look_back_end}'
        )

        # Build the nested configuration the API expects. AnalysisType, SavingsPlansToAdd, and
        # LookBackTimePeriod are required, but they are only set when the caller supplied them:
        # sending them as None makes botocore report a type error, while leaving them out makes it
        # name the field that is missing.
        config: dict = {}
        if analysis_type:
            config['AnalysisType'] = analysis_type
        if savings_plans_to_add:
            config['SavingsPlansToAdd'] = savings_plans_to_add
        if look_back_start and look_back_end:
            config['LookBackTimePeriod'] = {'Start': look_back_start, 'End': look_back_end}

        # Add optional parameters if provided
        if savings_plans_to_exclude:
            config['SavingsPlansToExclude'] = savings_plans_to_exclude
        if savings_plans_target_coverage is not None:
            config['SavingsPlansTargetCoverage'] = savings_plans_target_coverage
        if account_scope:
            config['AccountScope'] = account_scope
        if account_id:
            config['AccountId'] = account_id

        response = ce_client.start_commitment_purchase_analysis(
            CommitmentPurchaseAnalysisConfiguration={
                'SavingsPlansPurchaseAnalysisConfiguration': config
            }
        )

        return format_response('success', response)

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(
            ctx, e, 'start_commitment_purchase_analysis', 'Cost Explorer'
        )


async def get_commitment_purchase_analysis(
    ctx: Context,
    ce_client: Any,
    analysis_id: Optional[str],
) -> Dict[str, Any]:
    """Retrieves a commitment purchase analysis result based on the AnalysisId.

    Args:
        ctx: The MCP context
        ce_client: Cost Explorer client
        analysis_id: The analysis ID that's associated with the commitment purchase analysis.

    Returns:
        Dict containing the analysis status and, once complete, its results
    """
    # Get context logger for consistent logging
    ctx_logger = get_context_logger(ctx, __name__)

    try:
        await ctx_logger.info(f'Fetching commitment purchase analysis {analysis_id}')

        response = ce_client.get_commitment_purchase_analysis(AnalysisId=analysis_id)

        return format_response('success', response)

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'get_commitment_purchase_analysis', 'Cost Explorer')


CE_LIST_COMMITMENT_PURCHASE_ANALYSES = PageSpec(
    result_key='AnalysisSummaryList',
    token_param='NextPageToken',
    token_key_in_response='NextPageToken',
    page_max=600,
    page_size_param='PageSize',
)


async def list_commitment_purchase_analyses(
    ctx: Context,
    ce_client: Any,
    analysis_status: Optional[str],
    analysis_ids: Optional[List[str]],
    max_items: Optional[int],
    next_token: Optional[str],
) -> Dict[str, Any]:
    """Lists the commitment purchase analyses for your account.

    Args:
        ctx: The MCP context
        ce_client: Cost Explorer client
        analysis_status: The status of the analysis.
        analysis_ids: The analysis IDs associated with the commitment purchase analyses.
        max_items: Total number of analyses to return. None fetches every page.
        next_token: The token from a previous response.

    Returns:
        Dict containing the analysis history
    """
    # Get context logger for consistent logging
    ctx_logger = get_context_logger(ctx, __name__)

    try:
        await ctx_logger.info('Listing commitment purchase analyses')

        # Create request parameters
        request_params: dict = {}

        # Add optional parameters if provided
        if analysis_status:
            request_params['AnalysisStatus'] = analysis_status
        if analysis_ids:
            request_params['AnalysisIds'] = analysis_ids

        all_analyses, _, pagination = await paginate_aws_items(
            ctx,
            'ListCommitmentPurchaseAnalyses',
            ce_client.list_commitment_purchase_analyses,
            request_params,
            CE_LIST_COMMITMENT_PURCHASE_ANALYSES,
            max_items=max_items,
            next_token=next_token,
        )

        return format_response(
            'success', with_pagination({'AnalysisSummaryList': all_analyses}, pagination)
        )

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'list_commitment_purchase_analyses', 'Cost Explorer')
