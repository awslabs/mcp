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
    PageSpec,
    create_aws_client,
    format_response,
    handle_aws_error,
    paginate_aws_items,
    with_pagination,
)
from ..utilities.constants import PAGINATION_LIMIT_TEXT
from ..utilities.logging_utils import get_context_logger
from ..utilities.sql_utils import convert_response_if_needed
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

1. describe_savings_plans: the plans owned by the calling account only, with state, term, payment
   option, and expiry. No member-account plans are returned, even from a management account, so an
   empty result does not mean the organization owns none. Pass states to scope the result. For an
   organization-wide inventory use sp-performance get_savings_plans_utilization_details (one entry
   per plan ARN, and the owning account is the ARN's account field) or cost-explorer
   getDimensionValues with SAVINGS_PLAN_ARN under context=SAVINGS_PLANS. Both read Cost Explorer,
   which lists a plan only where it has utilization records in the window, so pass an explicit
   12-month start_date and end_date: a shorter window drops retired and idle plans, and a member
   account's idle plan still displaces a new purchase.
2. describe_savings_plan_rates: The rates on one Savings Plan the customer already owns.
3. describe_savings_plans_offerings: The offerings available to purchase.
4. describe_savings_plans_offering_rates: The rates for offerings available to purchase.

USE THIS TOOL FOR:
- **What plans the calling account owns** — including plans in the queued, returned, and
  payment-failed states, which Cost Explorer does not report on
- **When a plan expires or can still be returned** — the end and returnableUntil fields
- **The rates locked in on an existing plan**
- **What is available to purchase and at what rate** — to compare the rate one plan type, term, and
  payment option gets against another for the same usage

DO NOT USE THIS TOOL FOR:
- Coverage or utilization of existing plans, which is sp-performance
- Recommended savings plans to purchase, which is sp-recommendation

Tags come back on each plan in describe_savings_plans, so there is no separate tag operation.

IMPORTANT: the vocabulary here differs from Cost Explorer's, so values carried over from a Cost
Explorer response or recommendation will be rejected. See the individual parameter descriptions.

PAGINATION (all four operations):
- max_items is the total number of items returned. If it is omitted, the tool fetches every page for """
    + PAGINATION_LIMIT_TEXT
    + """, then returns a partial result. Pass it,
  or narrow the filters, for queries that can be large (an unfiltered offering or offering-rate
  query runs to thousands of entries).
- If the response has complete_dataset: false, call again with a larger max_items, continue with
  next_token, or state in the answer that the result is partial.

A large result from any of these operations is automatically offloaded to session SQL to save
tokens: the response carries data_stored=True and a table_name (one row per plan, rate, or
offering) instead of the inline list, and the rows are queried with the session-sql tool. A small
result is returned inline unchanged.""",
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
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
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
        service_codes: The service codes as a list. describe_savings_plans_offerings takes
            the plan's own code: ComputeSavingsPlans (Compute and EC2Instance plans),
            MachineLearningSavingsPlans (SageMaker plans), or DatabaseSavingsPlans (Database
            plans), as in the serviceCode field of a returned offering. Any other value,
            including a rate code such as AmazonSageMaker, matches nothing and returns an empty
            result, not an error. The exception is a value containing EC2 in upper or lower
            case, such as AmazonEC2, ec2 or EC2InstanceSavingsPlans: it fails the whole request,
            even alongside a valid code, with a ValidationException whose message lists
            AmazonEC2 as allowed. For EC2Instance plans use ComputeSavingsPlans.
            describe_savings_plans_offering_rates takes the code of the service the rate
            applies to: AmazonEC2, AmazonECS, AmazonEKS, AWSLambda, AmazonSageMaker, AmazonRDS,
            AuroraDSQL, AmazonDynamoDB, AmazonElastiCache, AmazonDocDB, AmazonNeptune,
            AmazonTimestream, AmazonMCS, AWSDatabaseMigrationSvc, and AmazonES.
        usage_types: The usage types as a list. The two offering operations use different
            usage types, and a value from one matches nothing on the other. An offering's usage
            type names the plan, such as ComputeSP:1yrNoUpfront, or EC2SP:m5.1yrNoUpfront for a
            regional plan. A rate's usage type names the usage it covers, such as
            BoxUsage:m5.large.
            Outside us-east-1 a regional usage type carries a region prefix
            (AFS1-EC2SP:c5.1yrAllUpfront, USW2-BoxUsage:m5.large). In us-east-1 most have none,
            but some rates carry one (USE1-Fargate-GB-Hours). A value that matches nothing
            returns an empty result, not an error, so copy values from the usageType field of
            a returned offering or rate.
        operations: The operations as a list.
        filters: The filters as a list of {"name": ..., "values": [...]} objects. The
            accepted names differ per operation: describe_savings_plans takes region,
            ec2-instance-family, commitment, upfront, term, savings-plan-type, payment-option,
            start, end, and instance-family; describe_savings_plan_rates takes region, instanceType,
            productDescription, tenancy, productType, serviceCode, usageType, and operation;
            describe_savings_plans_offerings takes region and instanceFamily; and
            describe_savings_plans_offering_rates takes region, instanceFamily, instanceType,
            productDescription, and tenancy. For describe_savings_plans the values are strings, numbers included, matched exactly and case-sensitively, and a value that
            matches no plan returns an empty list, not an error: savings-plan-type is Compute,
            EC2Instance, SageMaker, or Database; payment-option is 'All Upfront', 'Partial
            Upfront', or 'No Upfront', with the spaces; term is the duration in seconds as a
            string, "31536000" or "94608000"; upfront and commitment are decimal strings such as
            "4.38", with no currency sign; start and end are exact timestamps such as
            "2025-01-01T00:00:00.000Z", matched to the millisecond rather than as a range; region
            is a region code such as us-east-1; and ec2-instance-family and instance-family are an
            instance family such as m5. The two rate operations use the pricing vocabulary, not
            Cost Explorer's, and a value in another spelling also returns an empty list: tenancy
            is lower case, shared or dedicated (Cost Explorer's Shared matches nothing); and
            productDescription is the full operating system name such as Linux/UNIX, Windows, or
            Red Hat Enterprise Linux (Linux alone matches nothing).
        max_items: Total number of items to return across all pages. Omit it to fetch every
            page.
        next_token: The pagination.next_token from a previous response; continue with otherwise
            identical parameters.

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
                max_items,
                next_token,
            )
        elif operation == 'describe_savings_plan_rates':
            return await describe_savings_plan_rates(
                ctx, sp_client, savings_plan_id, filters, max_items, next_token
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
                max_items,
                next_token,
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
                max_items,
                next_token,
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


SP_DESCRIBE_SAVINGS_PLANS = PageSpec(
    result_key='savingsPlans',
    token_param='nextToken',
    token_key_in_response='nextToken',
    page_max=1000,
    page_size_param='maxResults',
    # The service reports a bad caller next_token as ValidationException.
    caller_token_error_codes=frozenset({'ValidationException'}),
)


async def describe_savings_plans(
    ctx: Context,
    sp_client: Any,
    savings_plan_arns: Optional[List[str]],
    savings_plan_ids: Optional[List[str]],
    states: Optional[List[str]],
    filters: Optional[List[Dict[str, Any]]],
    max_items: Optional[int],
    next_token: Optional[str],
) -> Dict[str, Any]:
    """Describes the specified Savings Plans.

    Args:
        ctx: The MCP context
        sp_client: Savings Plans client
        savings_plan_arns: The Savings Plan ARNs as a list.
        savings_plan_ids: The Savings Plan IDs as a list.
        states: The current states of the Savings Plans as a list.
        filters: The filters as a list.
        max_items: Total number of items to return. None fetches every page.
        next_token: The token from a previous response.

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

        all_plans, _, pagination = await paginate_aws_items(
            ctx,
            'DescribeSavingsPlans',
            sp_client.describe_savings_plans,
            request_params,
            SP_DESCRIBE_SAVINGS_PLANS,
            max_items=max_items,
            next_token=next_token,
        )

        # An empty list is the live behaviour for a management account whose plans were all bought
        # in member accounts: DescribeSavingsPlans is scoped to the calling account and returns
        # none of them, even when asked for by id or ARN. Say so in the result itself, not only in
        # the tool description, so a caller reading the response cannot take [] for "owns none".
        # An empty result is never large enough to offload, so it returns directly.
        if not all_plans:
            # A filter value spelled differently from the API's (ComputeSavingsPlans for Compute,
            # PARTIAL_UPFRONT for 'Partial Upfront') also returns [] with no error, and then the
            # account-scope text alone points the caller at the wrong cause. states needs no note:
            # the API validates it and rejects a misspelled state with a ValidationException.
            filter_note = (
                (
                    'The request was narrowed by filters, and a filter value that matches no '
                    'plan returns this same empty list rather than an error. Values are matched '
                    'exactly and are case-sensitive (for example savings-plan-type Compute, '
                    'payment-option \'Partial Upfront\', term "31536000"), so check them against '
                    'the filters parameter description. An unfiltered call tells the two causes '
                    'apart. '
                )
                if filters
                else ''
            )
            return format_response(
                'success',
                with_pagination(
                    {
                        'savingsPlans': [],
                        'message': 'No Savings Plans found for the calling account. '
                        + filter_note
                        + (
                            'This operation '
                            'returns only plans the calling account bought, so an empty result '
                            'does not mean the organization owns none: from a management '
                            'account, member-account plans are never returned. For an '
                            'organization-wide inventory call sp-performance '
                            'get_savings_plans_utilization_details (the owning account is the '
                            "plan ARN's account field) or cost-explorer getDimensionValues with "
                            'SAVINGS_PLAN_ARN under context=SAVINGS_PLANS, passing an explicit '
                            '12-month window, since both list a plan only where it has '
                            'utilization records inside it.'
                        ),
                    },
                    pagination,
                ),
            )

        # A large inventory is offloaded to session SQL (one row per plan)
        # instead of returned inline; a small result passes through unchanged.
        # An offloaded table is queried with the session-sql tool.
        converted = await convert_response_if_needed(
            ctx,
            with_pagination({'savingsPlans': all_plans}, pagination),
            'sp_explorer_describe_savings_plans',
        )

        return format_response('success', converted)

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'describe_savings_plans', 'Savings Plans')


SP_DESCRIBE_SAVINGS_PLAN_RATES = PageSpec(
    result_key='searchResults',
    token_param='nextToken',
    token_key_in_response='nextToken',
    page_max=1000,
    page_size_param='maxResults',
    # The service reports a bad caller next_token as ValidationException.
    caller_token_error_codes=frozenset({'ValidationException'}),
)


async def describe_savings_plan_rates(
    ctx: Context,
    sp_client: Any,
    savings_plan_id: Optional[str],
    filters: Optional[List[Dict[str, Any]]],
    max_items: Optional[int],
    next_token: Optional[str],
) -> Dict[str, Any]:
    """Describes the rates for a specific, existing Savings Plan.

    Args:
        ctx: The MCP context
        sp_client: Savings Plans client
        savings_plan_id: The ID of the Savings Plan.
        filters: The filters as a list.
        max_items: Total number of items to return. None fetches every page.
        next_token: The token from a previous response.

    Returns:
        Dict containing the Savings Plan rates
    """
    # Get context logger for consistent logging
    ctx_logger = get_context_logger(ctx, __name__)

    try:
        await ctx_logger.info(f'Describing rates for Savings Plan {savings_plan_id}')

        # Create request parameters
        # savingsPlanId is required. Sending it as None makes botocore report a type error on the
        # value; omitting it makes botocore name the missing field, which is the more useful
        # failure for a caller that forgot it.
        request_params: dict = {}

        # Add optional parameters if provided
        if savings_plan_id:
            request_params['savingsPlanId'] = savings_plan_id
        if filters:
            request_params['filters'] = filters

        all_rates, _, pagination = await paginate_aws_items(
            ctx,
            'DescribeSavingsPlanRates',
            sp_client.describe_savings_plan_rates,
            request_params,
            SP_DESCRIBE_SAVINGS_PLAN_RATES,
            max_items=max_items,
            next_token=next_token,
        )

        # savingsPlanId is echoed at the top level of each page. Carry it through
        # so the merged result still says which plan these rates belong to.
        #
        # A large rate list is offloaded to session SQL (one row per rate)
        # instead of returned inline; a small result passes through unchanged.
        # An offloaded table is queried with the session-sql tool. The records
        # converter keeps the first list field (searchResults), so savingsPlanId
        # is passed as metadata to stay on the offloaded sentinel too.
        converted = await convert_response_if_needed(
            ctx,
            with_pagination(
                {'savingsPlanId': savings_plan_id, 'searchResults': all_rates}, pagination
            ),
            'sp_explorer_describe_savings_plan_rates',
            savingsPlanId=savings_plan_id,
        )

        return format_response('success', converted)

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'describe_savings_plan_rates', 'Savings Plans')


SP_DESCRIBE_SAVINGS_PLANS_OFFERINGS = PageSpec(
    result_key='searchResults',
    token_param='nextToken',
    token_key_in_response='nextToken',
    page_max=1000,
    page_size_param='maxResults',
    # The service reports a bad caller next_token as ValidationException.
    caller_token_error_codes=frozenset({'ValidationException'}),
)


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
    max_items: Optional[int],
    next_token: Optional[str],
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
        max_items: Total number of items to return. None fetches every page.
        next_token: The token from a previous response.

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

        # The offering catalog runs to thousands of entries for an unfiltered
        # query. Page through it here: the token key is lowercase `nextToken` on
        # this service and `NextToken` or `NextPageToken` on Cost Explorer, and a
        # caller that threads the wrong one silently re-reads the first page.
        all_offerings, _, pagination = await paginate_aws_items(
            ctx,
            'DescribeSavingsPlansOfferings',
            sp_client.describe_savings_plans_offerings,
            request_params,
            SP_DESCRIBE_SAVINGS_PLANS_OFFERINGS,
            max_items=max_items,
            next_token=next_token,
        )

        # A large offering catalog is offloaded to session SQL (one row per
        # offering) instead of returned inline; a small result passes through
        # unchanged. An offloaded table is queried with the session-sql tool.
        converted = await convert_response_if_needed(
            ctx,
            with_pagination({'searchResults': all_offerings}, pagination),
            'sp_explorer_describe_savings_plans_offerings',
        )

        return format_response('success', converted)

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, 'describe_savings_plans_offerings', 'Savings Plans')


SP_DESCRIBE_SAVINGS_PLANS_OFFERING_RATES = PageSpec(
    result_key='searchResults',
    token_param='nextToken',
    token_key_in_response='nextToken',
    page_max=1000,
    page_size_param='maxResults',
    # The service reports a bad caller next_token as ValidationException.
    caller_token_error_codes=frozenset({'ValidationException'}),
)


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
    max_items: Optional[int],
    next_token: Optional[str],
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
        max_items: Total number of items to return. None fetches every page.
        next_token: The token from a previous response.

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

        all_rates, _, pagination = await paginate_aws_items(
            ctx,
            'DescribeSavingsPlansOfferingRates',
            sp_client.describe_savings_plans_offering_rates,
            request_params,
            SP_DESCRIBE_SAVINGS_PLANS_OFFERING_RATES,
            max_items=max_items,
            next_token=next_token,
        )

        # A large offering-rate result is offloaded to session SQL (one row per
        # rate) instead of returned inline; a small result passes through
        # unchanged. An offloaded table is queried with the session-sql tool.
        converted = await convert_response_if_needed(
            ctx,
            with_pagination({'searchResults': all_rates}, pagination),
            'sp_explorer_describe_savings_plans_offering_rates',
        )

        return format_response('success', converted)

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(
            ctx, e, 'describe_savings_plans_offering_rates', 'Savings Plans'
        )
