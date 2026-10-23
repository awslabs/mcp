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

"""Business Support operations for the AWS Billing and Cost Management MCP server.

This module contains the operation handlers for the ``business-support`` tool.
Each operation validates its inputs, performs the AWS Billing API call,
normalizes timestamps for the agent, and returns a standardized response
envelope. Every other field is passed through exactly as the API returned it so
monetary amounts remain decimal strings.
"""

import re
from ..utilities.aws_service_base import (
    PageSpec,
    create_aws_client,
    format_response,
    handle_aws_error,
    paginate_aws_items,
    with_pagination,
)
from ..utilities.sql_utils import convert_response_if_needed
from ..utilities.time_utils import normalize_datetimes_to_iso
from botocore.exceptions import ClientError
from datetime import datetime, timezone
from fastmcp import Context
from typing import Any, Dict, List, Optional, Tuple, cast


# The pattern the API declares for billingMonth, applied as a full match. Stating
# it explicitly avoids relying on strptime, which accepts an unpadded month such
# as 2026-6 and would then compare wrongly against a zero-padded bound.
BILLING_MONTH_PATTERN = re.compile(r'\d{4}-(0[1-9]|1[0-2])')

# Account id the API accepts: a 12-digit AWS account number. Validated locally so
# a malformed id is rejected before a call is spent on it.
ACCOUNT_ID_PATTERN = re.compile(r'\d{12}')

# Oldest billing month the Business Support APIs serve. Requests earlier than
# this are rejected locally rather than spending a call that cannot return data.
EARLIEST_BILLING_MONTH = '2025-01'


# How ListBusinessSupportAccountCharges pages: the per-account charge rows come
# back under ``accountCharges``, continued by ``nextToken``, at up to 100 per
# page sized by ``maxResults``.
LIST_ACCOUNT_CHARGES_PAGE_SPEC = PageSpec(
    result_key='accountCharges',
    token_param='nextToken',
    token_key_in_response='nextToken',
    page_max=100,
    page_size_param='maxResults',
)

# How ListBusinessSupportSubscriptionHistory pages: the contract rows come back
# under ``subscriptionContracts``, continued by ``nextToken``, at up to 100 per
# page sized by ``maxResults``.
LIST_SUBSCRIPTION_HISTORY_PAGE_SPEC = PageSpec(
    result_key='subscriptionContracts',
    token_param='nextToken',
    token_key_in_response='nextToken',
    page_max=100,
    page_size_param='maxResults',
)


def _create_billing_client() -> Any:
    """Create an AWS Billing client for the Business Support operations.

    Returns:
        boto3.client: AWS Billing client.
    """
    return create_aws_client('billing')


def _classify_business_support_error(
    error_code: str, api_name: str
) -> Optional[Tuple[str, str, str]]:
    """Classify the two Business Support failures that need their own guidance.

    Both are routinely misread. ``AccessDeniedException`` has two independent
    causes: the caller's IAM policy omits the action, or the caller is not the
    payer account authorized for the Support profile. Either alone is enough, so
    a correct policy does not rule it out and it must not be reported as an
    absence of charges. ``ResourceNotFoundException`` is the opposite: the call was
    authorized and simply found no Business Support data for that account and
    billing period, so it must not be reported as a permission problem or retried
    against the same period. Any other code is left to the shared handler.

    Args:
        error_code: The AWS error code from the client error.
        api_name: The AWS API operation name.

    Returns:
        An (error_type, message, resolution) triple, or None when the code is not
        one this module explains itself.
    """
    if error_code in ('AccessDeniedException', 'AccessDenied'):
        required_action = f'billing:{api_name}'
        return (
            'access_denied',
            f'Access denied for Billing {api_name}. This is a permission or '
            'authorization failure, not an absence of Business Support charges.',
            f'Confirm the caller IAM policy grants {required_action}, and that the '
            'caller is the payer account authorized to view Business Support data '
            'for its Support profile. A linked account cannot read these operations.',
        )
    if error_code == 'ResourceNotFoundException':
        return (
            'not_found',
            f'Billing {api_name} found no Business Support data for the requested '
            'account and billing period. The call was authorized, so this is not a '
            'permission problem.',
            'Report that no Business Support data exists for that account and billing '
            'period, and do not retry the same period. The usual causes are that the '
            'account is not a Business Support customer, was not subscribed during '
            'that period, or is not the payer account for the Support profile.',
        )
    return None


async def _handle_business_support_error(
    ctx: Context, error: Exception, api_name: str
) -> Dict[str, Any]:
    """Handle a Business Support API error, explaining the ones that mislead.

    Failures this module classifies are returned with their own guidance; every
    other failure falls through to the shared handler. The AWS message is carried
    through verbatim in ``aws_message`` because it names the account and billing
    period that were not found.

    Args:
        ctx: The MCP context object.
        error: The exception that was raised.
        api_name: The AWS API operation name (for example
            ``"ListBusinessSupportAccountCharges"``).

    Returns:
        Dict containing the standardized error response.
    """
    if isinstance(error, ClientError):
        aws_error = error.response.get('Error', {})
        classified = _classify_business_support_error(aws_error.get('Code', ''), api_name)
        if classified:
            error_type, message, resolution = classified
            metadata = error.response.get('ResponseMetadata', {})
            return {
                'status': 'error',
                'service': 'Billing',
                'operation': api_name,
                'error_type': error_type,
                'message': message,
                'resolution': resolution,
                'aws_message': aws_error.get('Message', ''),
                'request_id': metadata.get('RequestId', 'Unknown'),
                'http_status': metadata.get('HTTPStatusCode', 0),
            }

    return await handle_aws_error(ctx, error, api_name, 'Billing')


def _reject_month_before_earliest(billing_month: str) -> Optional[Dict[str, Any]]:
    """Reject a billing month older than the earliest month with data.

    Zero-padded ``YYYY-MM`` strings compare correctly as strings, so no date
    arithmetic is needed.

    Args:
        billing_month: The requested billing month, already known to parse.

    Returns:
        None when the month is in range, otherwise a standardized error response.
    """
    if billing_month >= EARLIEST_BILLING_MONTH:
        return None

    return format_response(
        'error',
        {
            'message': (
                f'Billing month {billing_month} predates the earliest available '
                f'Business Support data ({EARLIEST_BILLING_MONTH}). Request '
                f'{EARLIEST_BILLING_MONTH} or later.'
            )
        },
    )


def _reject_future_month(billing_month: str) -> Optional[Dict[str, Any]]:
    """Reject a billing month that is in the future.

    The current month is allowed because the API returns estimated charges for it
    (``isEstimated=true``). Only months strictly after the current month are
    rejected. The boundary is computed on each call so it stays correct as time
    passes.

    Args:
        billing_month: The requested billing month, already known to parse.

    Returns:
        None when the month is the current month or earlier, otherwise a
        standardized error response.
    """
    now = datetime.now(timezone.utc)
    current_month = f'{now.year}-{now.month:02d}'

    if billing_month <= current_month:
        return None

    return format_response(
        'error',
        {
            'message': (
                f'Billing month {billing_month} is in the future. You can request '
                f'up to the current month ({current_month}); the current month '
                'returns estimated charges (isEstimated=true).'
            )
        },
    )


def _validate_billing_month(billing_month: Optional[str]) -> Optional[Dict[str, Any]]:
    r"""Validate a required billing month against the format and data range.

    A rejected month is returned as an error rather than adjusted to a nearby
    one. ``list_business_support_account_charges`` targets a single billing
    month, so silently substituting a different month would answer a question the
    caller did not ask.

    The format is checked first because the range checks compare strings and so
    assume a fixed width. It is enforced with an explicit full-match pattern
    rather than ``strptime``, which accepts non-canonical spellings such as an
    unpadded ``2026-6`` that would then compare wrongly against a zero-padded
    bound. Only a four-digit year and a zero-padded month 01 through 12 are
    accepted, matching the pattern the API declares for this field.

    Args:
        billing_month: The requested billing month in ``YYYY-MM`` format.

    Returns:
        None when the month is usable, otherwise a standardized error response.
    """
    if not billing_month:
        return format_response(
            'error',
            {
                'message': (
                    'billing_month is required. Provide a single calendar month in '
                    'YYYY-MM format, for example "2026-06".'
                )
            },
        )

    if not BILLING_MONTH_PATTERN.fullmatch(billing_month):
        return format_response(
            'error',
            {
                'message': (
                    f"Invalid billing_month '{billing_month}'. Expected a single calendar "
                    'month in YYYY-MM format, for example "2026-06".'
                )
            },
        )

    return _reject_month_before_earliest(billing_month) or _reject_future_month(billing_month)


def _validate_optional_billing_month(
    billing_month: Optional[str],
) -> Optional[Dict[str, Any]]:
    """Validate a billing month that is OPTIONAL for the subscription history call.

    ``list_business_support_subscription_history`` does not require a billing
    month, so an absent value is accepted and sends no filter. A value that IS
    supplied is held to the same format and data-range rules as the required
    case, because a malformed or out-of-range month filter would silently return
    nothing.

    Args:
        billing_month: The requested billing month in ``YYYY-MM`` format, or None.

    Returns:
        None when the month is usable or absent, otherwise a standardized error
        response.
    """
    if not billing_month:
        return None

    if not BILLING_MONTH_PATTERN.fullmatch(billing_month):
        return format_response(
            'error',
            {
                'message': (
                    f"Invalid billing_month '{billing_month}'. Expected a single calendar "
                    'month in YYYY-MM format, for example "2026-06".'
                )
            },
        )

    return _reject_month_before_earliest(billing_month) or _reject_future_month(billing_month)


def _validate_account_id(account_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """Validate an optional 12-digit AWS account id filter.

    ``accountId`` narrows a result to one account inside the payer's Support
    profile; it is never the identity of the caller. An absent value is accepted
    and sends no filter. A supplied value must be exactly twelve digits, which is
    the shape the API declares, so a malformed id is rejected before a call.

    Args:
        account_id: The requested account id, or None.

    Returns:
        None when the account id is usable or absent, otherwise a standardized
        error response.
    """
    if account_id is None:
        return None

    if not ACCOUNT_ID_PATTERN.fullmatch(account_id):
        return format_response(
            'error',
            {
                'message': (
                    f"Invalid account_id '{account_id}'. Expected a 12-digit AWS account "
                    'number, for example "111122223333".'
                )
            },
        )

    return None


def _build_account_charges_request(
    billing_month: str,
    account_id: Optional[str],
) -> Dict[str, Any]:
    """Build the ListBusinessSupportAccountCharges request parameters.

    ``accountId`` is a filter narrowing the result to one account inside the
    payer's Support profile, not the identity of the caller, so it is only sent
    when the caller asked for it. Defaulting it to the caller's own account would
    silently reduce a profile-wide breakdown to a single row.

    Args:
        billing_month: The billing month in ``YYYY-MM`` format.
        account_id: Optional account to filter to.

    Returns:
        The request parameters to send, without the token and page size, which
        the paginator adds per page.
    """
    request_params: Dict[str, Any] = {'billingMonth': billing_month}
    if account_id:
        request_params['accountId'] = account_id
    return request_params


def _build_subscription_history_request(
    billing_month: Optional[str],
    account_id: Optional[str],
    start_date: Optional[str],
    end_date: Optional[str],
) -> Dict[str, Any]:
    """Build the ListBusinessSupportSubscriptionHistory request parameters.

    Every input is optional for this operation. Each filter is sent only when the
    caller supplied it, so an omitted filter is never inferred from the caller
    credentials. ``startDate`` and ``endDate`` are passed through verbatim as the
    caller provided them; the API accepts timestamps for these bounds.

    Args:
        billing_month: Optional billing month in ``YYYY-MM`` format.
        account_id: Optional account to filter to.
        start_date: Optional lower timestamp bound for the contract window.
        end_date: Optional upper timestamp bound for the contract window.

    Returns:
        The request parameters to send, without the token and page size, which
        the paginator adds per page.
    """
    request_params: Dict[str, Any] = {}
    if billing_month:
        request_params['billingMonth'] = billing_month
    if account_id:
        request_params['accountId'] = account_id
    if start_date:
        request_params['startDate'] = start_date
    if end_date:
        request_params['endDate'] = end_date
    return request_params


async def _finalize_account_charges(
    ctx: Context,
    charges: List[Dict[str, Any]],
    pagination: Dict[str, Any],
    billing_month: str,
    account_id: Optional[str],
) -> Dict[str, Any]:
    """Shape the paged account charges and offload them if oversized.

    A large organization returns more rows than fit comfortably in context, so the
    assembled result goes through the shared size threshold, which either returns
    it inline or stores it for the session SQL tool and returns a table
    reference. The pagination block travels alongside either way.

    Args:
        ctx: The MCP context object.
        charges: The account charges gathered across pages.
        pagination: The paginator's report of what it fetched.
        billing_month: The billing month the charges cover.
        account_id: The account filter that was applied, if any.

    Returns:
        The standardized success envelope.
    """
    response = with_pagination(
        {'account_charges': normalize_datetimes_to_iso(charges)}, pagination
    )
    converted = await convert_response_if_needed(
        ctx,
        response,
        'business_support_list_account_charges',
        billing_month=billing_month,
        account_id=account_id,
    )
    return format_response('success', converted)


async def _finalize_subscription_history(
    ctx: Context,
    contracts: List[Dict[str, Any]],
    pagination: Dict[str, Any],
    billing_month: Optional[str],
    account_id: Optional[str],
) -> Dict[str, Any]:
    """Shape the paged subscription contracts and offload them if oversized.

    The history can span many contracts across accounts, so the assembled result
    goes through the shared size threshold that either returns it inline or
    stores it for the session SQL tool and returns a table reference. The
    pagination block travels alongside either way.

    Args:
        ctx: The MCP context object.
        contracts: The subscription contracts gathered across pages.
        pagination: The paginator's report of what it fetched.
        billing_month: The billing month filter that was applied, if any.
        account_id: The account filter that was applied, if any.

    Returns:
        The standardized success envelope.
    """
    response = with_pagination(
        {'subscription_contracts': normalize_datetimes_to_iso(contracts)}, pagination
    )
    converted = await convert_response_if_needed(
        ctx,
        response,
        'business_support_list_subscription_history',
        billing_month=billing_month,
        account_id=account_id,
    )
    return format_response('success', converted)


async def list_account_charges(
    ctx: Context,
    billing_month: Optional[str] = None,
    account_id: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List the per-account Business Support charges for a billing period.

    Returns each account's Business Support charge for the billing period: the
    Support charge, the discount applied, the Support-eligible spend it was
    calculated from, the per-service breakdown of that spend, and the tier
    charges that make up the total. Also returns the profile-wide totals the API
    reports alongside the per-account rows.

    Pagination goes through the shared paginator, which follows ``nextToken``
    until the results are exhausted or ``max_items`` is reached, and reports what
    it fetched so a partial walk is visible rather than silent. A large
    organization can return more rows than fit in context, so the assembled
    result goes through the shared size threshold that offloads to session SQL.

    Args:
        ctx: The MCP context object.
        billing_month: The billing month in ``YYYY-MM`` format (required).
        account_id: Optional 12-digit account id to filter to a single account.
        max_items: Optional maximum number of items to return across pages.
        next_token: Optional pagination token from a previous response.

    Returns:
        Dict containing ``account_charges`` and ``pagination``, or a standardized
        error response.
    """
    error = _validate_billing_month(billing_month) or _validate_account_id(account_id)
    if error:
        return error

    try:
        client = _create_billing_client()
        request_params = _build_account_charges_request(cast(str, billing_month), account_id)

        charges, _, pagination = await paginate_aws_items(
            ctx,
            'ListBusinessSupportAccountCharges',
            client.list_business_support_account_charges,
            request_params,
            LIST_ACCOUNT_CHARGES_PAGE_SPEC,
            max_items=max_items,
            next_token=next_token,
        )

        await ctx.info(
            f'Successfully retrieved Business Support charges for {len(charges)} '
            f'accounts in {billing_month}'
        )

        return await _finalize_account_charges(
            ctx, charges, pagination, str(billing_month), account_id
        )

    except Exception as e:
        return await _handle_business_support_error(ctx, e, 'ListBusinessSupportAccountCharges')


async def list_subscription_history(
    ctx: Context,
    billing_month: Optional[str] = None,
    account_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List the Business Support subscription contract history.

    Returns the subscription contracts that governed Business Support over the
    requested window: each contract's account, plan name, and the start and end
    dates of the contract term. Every input is optional, so with no filters it
    returns the full contract history visible to the payer's Support profile.

    Pagination goes through the shared paginator, which follows ``nextToken``
    until the results are exhausted or ``max_items`` is reached, and reports what
    it fetched so a partial walk is visible rather than silent. The history can
    span many contracts, so the assembled result goes through the shared size
    threshold that offloads to session SQL.

    Args:
        ctx: The MCP context object.
        billing_month: Optional billing month in ``YYYY-MM`` format.
        account_id: Optional 12-digit account id to filter to a single account.
        start_date: Optional lower timestamp bound for the contract window.
        end_date: Optional upper timestamp bound for the contract window.
        max_items: Optional maximum number of items to return across pages.
        next_token: Optional pagination token from a previous response.

    Returns:
        Dict containing ``subscription_contracts`` and ``pagination``, or a
        standardized error response.
    """
    error = _validate_optional_billing_month(billing_month) or _validate_account_id(account_id)
    if error:
        return error

    try:
        client = _create_billing_client()
        request_params = _build_subscription_history_request(
            billing_month, account_id, start_date, end_date
        )

        contracts, _, pagination = await paginate_aws_items(
            ctx,
            'ListBusinessSupportSubscriptionHistory',
            client.list_business_support_subscription_history,
            request_params,
            LIST_SUBSCRIPTION_HISTORY_PAGE_SPEC,
            max_items=max_items,
            next_token=next_token,
        )

        await ctx.info(
            f'Successfully retrieved {len(contracts)} Business Support subscription contracts'
        )

        return await _finalize_subscription_history(
            ctx, contracts, pagination, billing_month, account_id
        )

    except Exception as e:
        return await _handle_business_support_error(
            ctx, e, 'ListBusinessSupportSubscriptionHistory'
        )
