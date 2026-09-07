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

"""AWS Savings Plans inventory and offering tools for the AWS Billing and Cost Management MCP server."""

from ..utilities.aws_service_base import (
    create_aws_client,
    format_response,
    handle_aws_error,
    paginate_aws_response,
)
from ..utilities.logging_utils import get_context_logger
from fastmcp import Context, FastMCP
from typing import Any, Dict, List, Optional


sp_explorer_server = FastMCP(
    name='sp-explorer-tools',
    instructions='Tools for working with the AWS Savings Plans inventory and offering APIs',
)


@sp_explorer_server.tool(
    name='sp-explorer',
    description="""Tool that describes Savings Plans inventory and purchasable offerings.

This tool provides visibility into what an account already owns and what it can buy through four
operations:

1. describe_savings_plans: The plans the account owns, with state, term, payment option, and
   expiry. Pass states to scope the result.
2. describe_savings_plan_rates: The rates on one Savings Plan the customer already owns.
3. describe_savings_plans_offerings: The offerings available to purchase.
4. describe_savings_plans_offering_rates: The rates for offerings available to purchase.

USE THIS TOOL FOR:
- **What plans an account owns** — including plans in the queued, returned, and payment-failed
  states, which Cost Explorer does not report on
- **When a plan expires or can still be returned** — the end and returnableUntil fields
- **The rates locked in on an existing plan**
- **What is available to purchase and at what rate** — to compare the rate one plan type, term, and
  payment option gets against another for the same usage

DO NOT USE THIS TOOL FOR:
- Coverage or utilization of existing plans, which is sp-performance
- Recommended savings plans to purchase, which is sp-recommendation

Tags come back on each plan in describe_savings_plans, so there is no separate tag operation.

IMPORTANT: the vocabulary here differs from Cost Explorer's, so values carried over from a Cost
Explorer response or recommendation will be rejected. See the individual parameter descriptions.""",
)
async def sp_explorer(
    ctx: Context,
    operation: str,
    savings_plan_arns: Optional[List[str]] = None,
    savings_plan_ids: Optional[List[str]] = None,
    states: Optional[List[str]] = None,
    savings_plan_id: Optional[str] = None,
    offering_ids: Optional[List[str]] = None,
    payment_options: Optional[List[str]] = None,
    plan_types: Optional[List[str]] = None,
    product_type: Optional[str] = None,
    products: Optional[List[str]] = None,
    durations: Optional[List[int]] = None,
    currencies: Optional[List[str]] = None,
    descriptions: Optional[List[str]] = None,
    service_codes: Optional[List[str]] = None,
    usage_types: Optional[List[str]] = None,
    operations: Optional[List[str]] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
    next_token: Optional[str] = None,
    max_results: Optional[int] = None,
    max_pages: Optional[int] = None,
) -> Dict[str, Any]:
    """Tool that describes Savings Plans inventory and purchasable offerings.

    Args:
        ctx: The MCP context object
        operation: The operation to perform: 'describe_savings_plans', 'describe_savings_plan_rates', 'describe_savings_plans_offerings', or 'describe_savings_plans_offering_rates'
        savings_plan_arns: The Savings Plan ARNs to describe as a list.
        savings_plan_ids: The Savings Plan IDs to describe as a list.
        states: The current states of the Savings Plans as a list. One or more of
            payment-pending, payment-failed, active, retired, queued, queued-deleted,
            pending-return, and returned. Omitting it returns every state, which for a mature
            account means mostly retired plans.
        savings_plan_id: The ID of the Savings Plan to describe rates for. Required for
            describe_savings_plan_rates.
        offering_ids: The IDs of the offerings as a list. Used by both offering
            operations.
        payment_options: The payment options as a list. One or more of 'No Upfront',
            'Partial Upfront', and 'All Upfront' — note the spaces. Used by both offering
            operations.
        plan_types: The plan types as a list. One or more of Compute, EC2Instance,
            SageMaker, and Database. Used by both offering operations.
        product_type: The product type — EC2, Fargate, Lambda, SageMaker, RDS, DSQL, DynamoDB,
            ElastiCache, DocDB, Neptune, Timestream, Keyspaces, DMS, or OpenSearch. Used by
            describe_savings_plans_offerings.
        products: The products as a list, from the same set as product_type. Used by
            describe_savings_plans_offering_rates.
        durations: The durations, in seconds as a list. A one-year term is 31536000
            and a three-year term is 94608000.
        currencies: The currencies as a list. One or more of CNY, USD, and EUR.
        descriptions: The descriptions as a list.
        service_codes: The service codes as a list. For
            describe_savings_plans_offering_rates these are AmazonEC2, AmazonECS, AmazonEKS,
            AWSLambda, AmazonSageMaker, AmazonRDS, AuroraDSQL, AmazonDynamoDB, AmazonElastiCache,
            AmazonDocDB, AmazonNeptune, AmazonTimestream, AmazonMCS, AWSDatabaseMigrationSvc, and
            AmazonES.
        usage_types: The usage types as a list.
        operations: The operations as a list.
        filters: The filters as a list of {"name": ..., "values": [...]} objects. The
            accepted names differ per operation: describe_savings_plans takes region,
            ec2-instance-family, commitment, upfront, term, savings-plan-type, payment-option,
            start, end, and instance-family; describe_savings_plan_rates takes region, instanceType,
            productDescription, tenancy, productType, serviceCode, usageType, and operation;
            describe_savings_plans_offerings takes region and instanceFamily; and
            describe_savings_plans_offering_rates takes region, instanceFamily, instanceType,
            productDescription, tenancy, and productId.
        next_token: The token for the next page of results. Paging is handled for you, so this is
            only needed to resume from a token a previous call returned.
        max_results: The maximum number of results to return with a single call.
        max_pages: The maximum number of pages to fetch. Omitting it fetches every page.

    Returns:
        Dict containing the Savings Plans inventory, rates, or offerings
    """
    try:
        await ctx.info(f'Savings Plans explorer operation: {operation}')

        # Initialize Savings Plans client using shared utility
        sp_client = create_aws_client('savingsplans', region_name='us-east-1')

        if operation == 'describe_savings_plans':
            return await describe_savings_plans(
                ctx,
                sp_client,
                savings_plan_arns,
                savings_plan_ids,
                states,
                filters,
                next_token,
                max_results,
                max_pages,
            )
        elif operation == 'describe_savings_plan_rates':
            return await describe_savings_plan_rates(
                ctx, sp_client, savings_plan_id, filters, next_token, max_results, max_pages
            )
        elif operation == 'describe_savings_plans_offerings':
            return await describe_savings_plans_offerings(
                ctx,
                sp_client,
                offering_ids,
                payment_options,
                product_type,
                plan_types,
                durations,
                currencies,
                descriptions,
                service_codes,
                usage_types,
                operations,
                filters,
                next_token,
                max_results,
                max_pages,
            )
        elif operation == 'describe_savings_plans_offering_rates':
            return await describe_savings_plans_offering_rates(
                ctx,
                sp_client,
                offering_ids,
                payment_options,
                plan_types,
                products,
                service_codes,
                usage_types,
                operations,
                filters,
                next_token,
                max_results,
                max_pages,
            )
        else:
            return format_response(
                'error',
                {},
                f'Unsupported operation: {operation}. Use '
                "'describe_savings_plans', 'describe_savings_plan_rates', "
                "'describe_savings_plans_offerings', or "
                "'describe_savings_plans_offering_rates'.",
            )

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'sp_explorer', 'Savings Plans')


async def describe_savings_plans(
    ctx: Context,
    sp_client: Any,
    savings_plan_arns: Optional[List[str]],
    savings_plan_ids: Optional[List[str]],
    states: Optional[List[str]],
    filters: Optional[List[Dict[str, Any]]],
    next_token: Optional[str],
    max_results: Optional[int],
    max_pages: Optional[int],
) -> Dict[str, Any]:
    """Describes the specified Savings Plans.

    Args:
        ctx: The MCP context
        sp_client: Savings Plans client
        savings_plan_arns: The Savings Plan ARNs as a list.
        savings_plan_ids: The Savings Plan IDs as a list.
        states: The current states of the Savings Plans as a list.
        filters: The filters as a list.
        next_token: The token for the next page of results.
        max_results: The maximum number of results to return with a single call.
        max_pages: The maximum number of pages to fetch. None fetches every page.

    Returns:
        Dict containing the Savings Plans
    """
    # Get context logger for consistent logging
    ctx_logger = get_context_logger(ctx, __name__)

    try:
        await ctx_logger.info(f'Describing Savings Plans with states {states}')

        # Create request parameters
        request_params: dict = {}

        # Add optional parameters if provided
        if savings_plan_arns:
            request_params['savingsPlanArns'] = savings_plan_arns
        if savings_plan_ids:
            request_params['savingsPlanIds'] = savings_plan_ids
        if states:
            request_params['states'] = states
        if filters:
            request_params['filters'] = filters
        if next_token:
            request_params['nextToken'] = next_token
        if max_results:
            request_params['maxResults'] = max_results

        all_plans, pagination_metadata = await paginate_aws_response(
            ctx=ctx,
            operation_name='DescribeSavingsPlans',
            api_function=sp_client.describe_savings_plans,
            request_params=request_params,
            result_key='savingsPlans',
            token_param='nextToken',
            token_key='nextToken',
            max_pages=max_pages,
        )

        return format_response(
            'success',
            {'savingsPlans': all_plans, 'pagination': pagination_metadata},
        )

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'describe_savings_plans', 'Savings Plans')


async def describe_savings_plan_rates(
    ctx: Context,
    sp_client: Any,
    savings_plan_id: Optional[str],
    filters: Optional[List[Dict[str, Any]]],
    next_token: Optional[str],
    max_results: Optional[int],
    max_pages: Optional[int],
) -> Dict[str, Any]:
    """Describes the rates for a specific, existing Savings Plan.

    Args:
        ctx: The MCP context
        sp_client: Savings Plans client
        savings_plan_id: The ID of the Savings Plan.
        filters: The filters as a list.
        next_token: The token for the next page of results.
        max_results: The maximum number of results to return with a single call.
        max_pages: The maximum number of pages to fetch. None fetches every page.

    Returns:
        Dict containing the Savings Plan rates
    """
    # Get context logger for consistent logging
    ctx_logger = get_context_logger(ctx, __name__)

    try:
        await ctx_logger.info(f'Describing rates for Savings Plan {savings_plan_id}')

        # Create request parameters
        request_params: dict = {'savingsPlanId': savings_plan_id}

        # Add optional parameters if provided
        if filters:
            request_params['filters'] = filters
        if next_token:
            request_params['nextToken'] = next_token
        if max_results:
            request_params['maxResults'] = max_results

        all_rates, pagination_metadata = await paginate_aws_response(
            ctx=ctx,
            operation_name='DescribeSavingsPlanRates',
            api_function=sp_client.describe_savings_plan_rates,
            request_params=request_params,
            result_key='searchResults',
            token_param='nextToken',
            token_key='nextToken',
            max_pages=max_pages,
        )

        # savingsPlanId is echoed at the top level of each page. Carry it through
        # so the merged result still says which plan these rates belong to.
        return format_response(
            'success',
            {
                'savingsPlanId': savings_plan_id,
                'searchResults': all_rates,
                'pagination': pagination_metadata,
            },
        )

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'describe_savings_plan_rates', 'Savings Plans')


async def describe_savings_plans_offerings(
    ctx: Context,
    sp_client: Any,
    offering_ids: Optional[List[str]],
    payment_options: Optional[List[str]],
    product_type: Optional[str],
    plan_types: Optional[List[str]],
    durations: Optional[List[int]],
    currencies: Optional[List[str]],
    descriptions: Optional[List[str]],
    service_codes: Optional[List[str]],
    usage_types: Optional[List[str]],
    operations: Optional[List[str]],
    filters: Optional[List[Dict[str, Any]]],
    next_token: Optional[str],
    max_results: Optional[int],
    max_pages: Optional[int],
) -> Dict[str, Any]:
    """Describes the offerings for the specified Savings Plans.

    Args:
        ctx: The MCP context
        sp_client: Savings Plans client
        offering_ids: The IDs of the offerings as a list.
        payment_options: The payment options as a list.
        product_type: The product type.
        plan_types: The plan types as a list.
        durations: The durations, in seconds as a list.
        currencies: The currencies as a list.
        descriptions: The descriptions as a list.
        service_codes: The service codes as a list.
        usage_types: The usage types as a list.
        operations: The operations as a list.
        filters: The filters as a list.
        next_token: The token for the next page of results.
        max_results: The maximum number of results to return with a single call.
        max_pages: The maximum number of pages to fetch. None fetches every page.

    Returns:
        Dict containing the Savings Plans offerings
    """
    # Get context logger for consistent logging
    ctx_logger = get_context_logger(ctx, __name__)

    try:
        await ctx_logger.info('Describing Savings Plans offerings')

        # Create request parameters
        request_params: dict = {}

        # Add optional parameters if provided
        if offering_ids:
            request_params['offeringIds'] = offering_ids
        if payment_options:
            request_params['paymentOptions'] = payment_options
        if product_type:
            request_params['productType'] = product_type
        if plan_types:
            request_params['planTypes'] = plan_types
        if durations:
            request_params['durations'] = durations
        if currencies:
            request_params['currencies'] = currencies
        if descriptions:
            request_params['descriptions'] = descriptions
        if service_codes:
            request_params['serviceCodes'] = service_codes
        if usage_types:
            request_params['usageTypes'] = usage_types
        if operations:
            request_params['operations'] = operations
        if filters:
            request_params['filters'] = filters
        if next_token:
            request_params['nextToken'] = next_token
        if max_results:
            request_params['maxResults'] = max_results

        # The offering catalog runs to thousands of entries for an unfiltered
        # query. Page through it here: the token key is lowercase `nextToken` on
        # this service and `NextToken` or `NextPageToken` on Cost Explorer, and a
        # caller that threads the wrong one silently re-reads the first page.
        all_offerings, pagination_metadata = await paginate_aws_response(
            ctx=ctx,
            operation_name='DescribeSavingsPlansOfferings',
            api_function=sp_client.describe_savings_plans_offerings,
            request_params=request_params,
            result_key='searchResults',
            token_param='nextToken',
            token_key='nextToken',
            max_pages=max_pages,
        )

        return format_response(
            'success',
            {'searchResults': all_offerings, 'pagination': pagination_metadata},
        )

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'describe_savings_plans_offerings', 'Savings Plans')


async def describe_savings_plans_offering_rates(
    ctx: Context,
    sp_client: Any,
    offering_ids: Optional[List[str]],
    payment_options: Optional[List[str]],
    plan_types: Optional[List[str]],
    products: Optional[List[str]],
    service_codes: Optional[List[str]],
    usage_types: Optional[List[str]],
    operations: Optional[List[str]],
    filters: Optional[List[Dict[str, Any]]],
    next_token: Optional[str],
    max_results: Optional[int],
    max_pages: Optional[int],
) -> Dict[str, Any]:
    """Describes the offering rates for Savings Plans you might want to purchase.

    Args:
        ctx: The MCP context
        sp_client: Savings Plans client
        offering_ids: The IDs of the offerings as a list.
        payment_options: The payment options as a list.
        plan_types: The plan types as a list.
        products: The products as a list.
        service_codes: The service codes as a list.
        usage_types: The usage types as a list.
        operations: The operations as a list.
        filters: The filters as a list.
        next_token: The token for the next page of results.
        max_results: The maximum number of results to return with a single call.
        max_pages: The maximum number of pages to fetch. None fetches every page.

    Returns:
        Dict containing the Savings Plans offering rates
    """
    # Get context logger for consistent logging
    ctx_logger = get_context_logger(ctx, __name__)

    try:
        await ctx_logger.info('Describing Savings Plans offering rates')

        # Create request parameters
        request_params: dict = {}

        # Add optional parameters if provided
        # This API prefixes three fields that describe_savings_plans_offerings leaves bare. The
        # tool exposes one parameter name for each concept and maps it here, so a caller does not
        # have to know which spelling a given operation wants.
        if offering_ids:
            request_params['savingsPlanOfferingIds'] = offering_ids
        if payment_options:
            request_params['savingsPlanPaymentOptions'] = payment_options
        if plan_types:
            request_params['savingsPlanTypes'] = plan_types
        if products:
            request_params['products'] = products
        if service_codes:
            request_params['serviceCodes'] = service_codes
        if usage_types:
            request_params['usageTypes'] = usage_types
        if operations:
            request_params['operations'] = operations
        if filters:
            request_params['filters'] = filters
        if next_token:
            request_params['nextToken'] = next_token
        if max_results:
            request_params['maxResults'] = max_results

        all_rates, pagination_metadata = await paginate_aws_response(
            ctx=ctx,
            operation_name='DescribeSavingsPlansOfferingRates',
            api_function=sp_client.describe_savings_plans_offering_rates,
            request_params=request_params,
            result_key='searchResults',
            token_param='nextToken',
            token_key='nextToken',
            max_pages=max_pages,
        )

        return format_response(
            'success',
            {'searchResults': all_rates, 'pagination': pagination_metadata},
        )

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(
            ctx, e, 'describe_savings_plans_offering_rates', 'Savings Plans'
        )
