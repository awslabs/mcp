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
    create_aws_client,
    format_response,
    handle_aws_error,
    paginate_aws_response,
)
from ..utilities.logging_utils import get_context_logger
from fastmcp import Context, FastMCP
from typing import Any, Dict, List, Optional


sp_purchase_analyzer_server = FastMCP(
    name='sp-purchase-analyzer-tools',
    instructions='Tools for reading AWS Savings Plans Purchase Analyzer results',
)


@sp_purchase_analyzer_server.tool(
    name='sp-purchase-analyzer',
    description="""Tool that reads AWS Savings Plans Purchase Analyzer results using the Cost Explorer API.

This tool retrieves the projected cost, coverage, and utilization of a planned commitment purchase
from an analysis that has already been run, through two operations:

1. get_commitment_purchase_analysis: Retrieves a result by AnalysisId.
2. list_commitment_purchase_analyses: Lists the analyses for the account, so an existing result can
   be found without knowing its id.

USE THIS TOOL FOR:
- **What a planned purchase would do** — the projected coverage, utilization, and cost from a
  completed analysis
- **Whether an analysis is finished** — the AnalysisStatus field
- **What analyses have already been run** — including one still in progress

DO NOT USE THIS TOOL FOR:
- Starting an analysis. This tool is read-only, and no operation here starts one. An analysis has to
  be started in the AWS Cost Management console, under Savings Plans, Purchase Analyzer.
- A precomputed recommendation, which is sp-recommendation and needs no analysis at all
- What the customer already owns, which is sp-explorer
- Coverage or utilization of existing plans, which is sp-performance

IMPORTANT: an analysis carries the configuration it was run with. Read AnalysisType from the
response rather than assuming which scenario it modelled — MAX_SAVINGS, CUSTOM_COMMITMENT, and
TARGET_AVERAGE_COVERAGE answer different questions, and a result presented as the wrong one is
misleading.""",
)
async def sp_purchase_analyzer(
    ctx: Context,
    operation: str,
    analysis_id: Optional[str] = None,
    analysis_ids: Optional[List[str]] = None,
    analysis_status: Optional[str] = None,
    next_page_token: Optional[str] = None,
    page_size: Optional[int] = None,
    max_pages: Optional[int] = None,
) -> Dict[str, Any]:
    """Tool that reads AWS Savings Plans Purchase Analyzer results.

    Args:
        ctx: The MCP context object
        operation: The operation to perform: 'get_commitment_purchase_analysis' or 'list_commitment_purchase_analyses'
        analysis_id: The analysis ID that's associated with the commitment purchase analysis.
            Required for get_commitment_purchase_analysis.
        analysis_ids: The analysis IDs associated with the commitment purchase analyses.
            Filters list_commitment_purchase_analyses.
        analysis_status: The status of the analysis — SUCCEEDED, PROCESSING, or FAILED. Filters
            list_commitment_purchase_analyses.
        next_page_token: The token to retrieve the next set of results. Paging is handled for you, so
            this is only needed to resume from a token a previous call returned.
        page_size: The number of analyses that you want returned in a single response object.
        max_pages: The maximum number of pages to fetch. Omitting it fetches every page.

    Returns:
        Dict containing the analysis results or history
    """
    try:
        await ctx.info(f'Savings Plans Purchase Analyzer operation: {operation}')

        # Initialize Cost Explorer client using shared utility
        ce_client = create_aws_client('ce', region_name='us-east-1')

        if operation == 'get_commitment_purchase_analysis':
            return await get_commitment_purchase_analysis(ctx, ce_client, analysis_id)
        elif operation == 'list_commitment_purchase_analyses':
            return await list_commitment_purchase_analyses(
                ctx,
                ce_client,
                analysis_status,
                analysis_ids,
                next_page_token,
                page_size,
                max_pages,
            )
        else:
            return format_response(
                'error',
                {},
                f'Unsupported operation: {operation}. Use '
                "'get_commitment_purchase_analysis' or 'list_commitment_purchase_analyses'.",
            )

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'sp_purchase_analyzer', 'Cost Explorer')


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


async def list_commitment_purchase_analyses(
    ctx: Context,
    ce_client: Any,
    analysis_status: Optional[str],
    analysis_ids: Optional[List[str]],
    next_page_token: Optional[str],
    page_size: Optional[int],
    max_pages: Optional[int],
) -> Dict[str, Any]:
    """Lists the commitment purchase analyses for your account.

    Args:
        ctx: The MCP context
        ce_client: Cost Explorer client
        analysis_status: The status of the analysis.
        analysis_ids: The analysis IDs associated with the commitment purchase analyses.
        next_page_token: The token to retrieve the next set of results.
        page_size: The number of analyses that you want returned in a single response object.
        max_pages: The maximum number of pages to fetch. None fetches every page.

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
        if next_page_token:
            request_params['NextPageToken'] = next_page_token
        if page_size:
            request_params['PageSize'] = int(page_size)

        all_analyses, pagination_metadata = await paginate_aws_response(
            ctx=ctx,
            operation_name='ListCommitmentPurchaseAnalyses',
            api_function=ce_client.list_commitment_purchase_analyses,
            request_params=request_params,
            result_key='AnalysisSummaryList',
            token_param='NextPageToken',
            token_key='NextPageToken',
            max_pages=max_pages,
        )

        return format_response(
            'success',
            {'AnalysisSummaryList': all_analyses, 'pagination': pagination_metadata},
        )

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'list_commitment_purchase_analyses', 'Cost Explorer')
