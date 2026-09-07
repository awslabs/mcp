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

"""Enterprise Support operations for the AWS Billing and Cost Management MCP server.

This module contains the operation handlers for the ``enterprise_support`` tool.
Each operation validates the requested billing month, performs the AWS API call,
normalizes timestamps for the agent, and returns a standardized response
envelope. Every other field is passed through exactly as the API returned it so
monetary amounts remain decimal strings.
"""

import re
from ..utilities.aws_service_base import (
    create_aws_client,
    format_response,
    handle_aws_error,
    paginate_aws_response,
)
from ..utilities.sql_utils import convert_response_if_needed
from ..utilities.time_utils import normalize_datetimes_to_iso
from botocore.exceptions import ClientError
from datetime import datetime, timezone
from fastmcp import Context
from typing import Any, Dict, List, Optional, Tuple, cast


# The billing month format the API accepts, used for both validation and the
# messages that tell the agent how to correct a bad value.
# The pattern the API declares for billingMonth, applied as a full match. Stating
# it explicitly avoids relying on strptime, which accepts an unpadded month such
# as 2026-6 and would then compare wrongly against a zero-padded bound.
BILLING_MONTH_PATTERN = re.compile(r'\d{4}-(0[1-9]|1[0-2])')

# Oldest billing month the Enterprise Support APIs serve. Requests earlier than
# this are rejected locally rather than spending a call that cannot return data.
EARLIEST_BILLING_MONTH = '2025-01'


def _create_billing_client() -> Any:
    """Create an AWS Billing client for the Enterprise Support operations.

    Returns:
        boto3.client: AWS Billing client.
    """
    return create_aws_client('billing')


def _classify_enterprise_support_error(
    error_code: str, api_name: str
) -> Optional[Tuple[str, str, str]]:
    """Classify the two Enterprise Support failures that need their own guidance.

    Both are routinely misread. ``AccessDeniedException`` has two independent
    causes: the caller's IAM policy omits the action, or the caller is not the
    payer account authorized for the Support profile. Either alone is enough, so
    a correct policy does not rule it out and it must not be reported as an
    absence of charges. ``ResourceNotFoundException`` is the opposite: the call was
    authorized and simply found no Enterprise Support data for that account and
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
            'authorization failure, not an absence of Enterprise Support charges.',
            f'Confirm the caller IAM policy grants {required_action}, and that the '
            'caller is the payer account authorized to view Enterprise Support data '
            'for its Support profile. A linked account cannot read these operations.',
        )
    if error_code == 'ResourceNotFoundException':
        return (
            'not_found',
            f'Billing {api_name} found no Enterprise Support data for the requested '
            'account and billing period. The call was authorized, so this is not a '
            'permission problem.',
            'Report that no Enterprise Support data exists for that account and billing '
            'period, and do not retry the same period. The usual causes are that the '
            'account is not an Enterprise Support customer, was not subscribed during '
            'that period, or is not the payer account for the Support profile.',
        )
    return None


async def _handle_enterprise_support_error(
    ctx: Context, error: Exception, api_name: str
) -> Dict[str, Any]:
    """Handle an Enterprise Support API error, explaining the ones that mislead.

    Failures this module classifies are returned with their own guidance; every
    other failure falls through to the shared handler. The AWS message is carried
    through verbatim in ``aws_message`` because it names the account and billing
    period that were not found.

    Args:
        ctx: The MCP context object.
        error: The exception that was raised.
        api_name: The AWS API operation name (for example
            ``"GetEnterpriseSupportChargeSummary"``).

    Returns:
        Dict containing the standardized error response.
    """
    if isinstance(error, ClientError):
        aws_error = error.response.get('Error', {})
        classified = _classify_enterprise_support_error(aws_error.get('Code', ''), api_name)
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
                f'Enterprise Support data ({EARLIEST_BILLING_MONTH}). Request '
                f'{EARLIEST_BILLING_MONTH} or later.'
            )
        },
    )


def _reject_month_not_yet_closed(billing_month: str) -> Optional[Dict[str, Any]]:
    """Reject a billing month whose billing period has not closed yet.

    These APIs only serve a billing month once its billing period has closed, so
    the current month is never available and the newest answerable month is the
    previous one. That boundary is computed on each call rather than stored so it
    stays correct as time passes, and January rolls back to December of the prior
    year.

    Args:
        billing_month: The requested billing month, already known to parse.

    Returns:
        None when the month is available, otherwise a standardized error response.
    """
    now = datetime.now(timezone.utc)
    if now.month == 1:
        latest_month = f'{now.year - 1}-12'
    else:
        latest_month = f'{now.year}-{now.month - 1:02d}'

    if billing_month <= latest_month:
        return None

    return format_response(
        'error',
        {
            'message': (
                f'Billing month {billing_month} is not available. Enterprise Support data '
                'is only published for billing periods that have closed, so the most '
                f'recent available month is {latest_month}.'
            )
        },
    )


def _validate_billing_month(billing_month: Optional[str]) -> Optional[Dict[str, Any]]:
    r"""Validate a billing month against the format and the available data range.

    A rejected month is returned as an error rather than adjusted to a nearby
    one. Each Enterprise Support request targets a single billing month, so
    silently substituting a different month would answer a question the caller
    did not ask.

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

    return _reject_month_before_earliest(billing_month) or _reject_month_not_yet_closed(
        billing_month
    )


def _strip_response_metadata(api_response: Dict[str, Any]) -> Dict[str, Any]:
    """Return the API response without botocore's ``ResponseMetadata`` envelope.

    Args:
        api_response: The raw boto3 response.

    Returns:
        The response fields without transport metadata.
    """
    return {key: value for key, value in api_response.items() if key != 'ResponseMetadata'}


def _build_linked_account_charges_request(
    billing_month: str,
    account_id: Optional[str],
    max_results: Optional[int],
    next_token: Optional[str],
) -> Dict[str, Any]:
    """Build the ListEnterpriseSupportLinkedAccountCharges request parameters.

    ``accountId`` is a filter narrowing the result to one linked account inside
    the payer's Support profile, not the identity of the caller, so it is only
    sent when the caller asked for it. Defaulting it to the caller's own account
    would silently reduce an organization-wide breakdown to a single row.

    Args:
        billing_month: The billing month in ``YYYY-MM`` format.
        account_id: Optional linked account to filter to.
        max_results: Optional page size.
        next_token: Optional pagination token from a previous response.

    Returns:
        The request parameters to send.
    """
    request_params: Dict[str, Any] = {'billingMonth': billing_month}
    if account_id:
        request_params['accountId'] = account_id
    if max_results is not None:
        request_params['maxResults'] = max_results
    if next_token:
        request_params['nextToken'] = next_token
    return request_params


async def _finalize_linked_account_charges(
    ctx: Context,
    charges: List[Dict[str, Any]],
    pagination: Dict[str, Any],
    billing_month: str,
    account_id: Optional[str],
) -> Dict[str, Any]:
    """Shape the paged linked-account charges and offload them if oversized.

    A large organization returns more rows than fit comfortably in context, so the
    assembled result goes through the shared size threshold, which either returns
    it inline or stores it for the session SQL tool and returns a table
    reference. The pagination block travels alongside either way.

    Args:
        ctx: The MCP context object.
        charges: The linked account charges gathered across pages.
        pagination: The paginator's report of what it fetched.
        billing_month: The billing month the charges cover.
        account_id: The linked account filter that was applied, if any.

    Returns:
        The standardized success envelope.
    """
    response = {
        'linked_account_charges': normalize_datetimes_to_iso(charges),
        'pagination': pagination,
    }
    converted = await convert_response_if_needed(
        ctx,
        response,
        'enterprise_support_list_linked_account_charges',
        billing_month=billing_month,
        account_id=account_id,
    )
    return format_response('success', converted)


async def get_charge_summary(ctx: Context, billing_month: Optional[str] = None) -> Dict[str, Any]:
    """Get the Enterprise Support charge summary for a billing period.

    Returns the Support charge for the billing period alongside the Support-eligible spend
    it was calculated from, broken out by usage, Reserved Instance and Savings
    Plan spend, plus the effective pricing plan and its tiers.

    The payer account is derived from the caller's credentials, so there is no
    account parameter. Timestamps are normalized to ISO 8601 strings and all
    other fields, including the monetary decimal strings, are passed through
    unchanged.

    Args:
        ctx: The MCP context object.
        billing_month: The billing month in ``YYYY-MM`` format.

    Returns:
        Dict containing ``charge_summary``, or a standardized error response.
    """
    error = _validate_billing_month(billing_month)
    if error:
        return error

    try:
        client = _create_billing_client()

        api_response = client.get_enterprise_support_charge_summary(billingMonth=billing_month)

        charge_summary = normalize_datetimes_to_iso(_strip_response_metadata(api_response))

        await ctx.info(
            f'Successfully retrieved Enterprise Support charge summary for {billing_month}'
        )

        return format_response('success', {'charge_summary': charge_summary})

    except Exception as e:
        return await _handle_enterprise_support_error(ctx, e, 'GetEnterpriseSupportChargeSummary')


async def get_contract_details(
    ctx: Context, billing_month: Optional[str] = None
) -> Dict[str, Any]:
    """Get the Enterprise Support contract details for a billing period.

    Returns the contract terms that were in effect for the billing period: how the total
    Support charge is allocated across the profile, how Reserved Instance and
    Savings Plan fees are treated when computing Support-eligible spend, which
    payer accounts the contract covers, which payer accounts are charged and at
    what percentage, any contract-specific adjustments, and every pricing plan
    attached to the contract.

    The payer account is derived from the caller's credentials, so there is no
    account parameter. Timestamps are normalized to ISO 8601 strings and all
    other fields, including the monetary decimal strings, are passed through
    unchanged.

    Args:
        ctx: The MCP context object.
        billing_month: The billing month in ``YYYY-MM`` format.

    Returns:
        Dict containing ``contract_details``, or a standardized error response.
    """
    error = _validate_billing_month(billing_month)
    if error:
        return error

    try:
        client = _create_billing_client()

        api_response = client.get_enterprise_support_contract_details(billingMonth=billing_month)

        contract_details = normalize_datetimes_to_iso(_strip_response_metadata(api_response))

        await ctx.info(
            f'Successfully retrieved Enterprise Support contract details for {billing_month}'
        )

        return format_response('success', {'contract_details': contract_details})

    except Exception as e:
        return await _handle_enterprise_support_error(
            ctx, e, 'GetEnterpriseSupportContractDetails'
        )


async def list_linked_account_charges(
    ctx: Context,
    billing_month: Optional[str] = None,
    account_id: Optional[str] = None,
    max_results: Optional[int] = None,
    next_token: Optional[str] = None,
    max_pages: Optional[int] = None,
) -> Dict[str, Any]:
    """List the per-linked-account Enterprise Support charges for a billing period.

    Returns each linked account's Support-eligible spend, its prorated share, the
    billable and total seconds behind that proration, and the per-service
    breakdown. This is the operation that answers which accounts drove the
    Support charge.

    Pagination goes through the shared paginator, which follows ``nextToken``
    until the results are exhausted or ``max_pages`` is reached, and reports what
    it fetched so a partial walk is visible rather than silent. A large
    organization can return more rows than fit in context, so the assembled
    result goes through the shared size threshold that offloads to session SQL.

    Args:
        ctx: The MCP context object.
        billing_month: The billing month in ``YYYY-MM`` format.
        account_id: Optional linked account ID to filter to a single account.
        max_results: Optional maximum results per page (1-100).
        next_token: Optional pagination token from a previous response.
        max_pages: Optional maximum number of pages to fetch. Defaults to all.

    Returns:
        Dict containing ``linked_account_charges`` and ``pagination``, or a
        standardized error response.
    """
    error = _validate_billing_month(billing_month)
    if error:
        return error

    try:
        client = _create_billing_client()
        request_params = _build_linked_account_charges_request(
            cast(str, billing_month), account_id, max_results, next_token
        )

        charges, pagination = await paginate_aws_response(
            ctx,
            'ListEnterpriseSupportLinkedAccountCharges',
            lambda **params: client.list_enterprise_support_linked_account_charges(**params),
            request_params,
            'linkedAccount',
            token_param='nextToken',
            token_key='nextToken',
            max_pages=max_pages,
        )

        await ctx.info(
            f'Successfully retrieved Enterprise Support charges for {len(charges)} '
            f'linked accounts in {billing_month}'
        )

        return await _finalize_linked_account_charges(
            ctx, charges, pagination, str(billing_month), account_id
        )

    except Exception as e:
        return await _handle_enterprise_support_error(
            ctx, e, 'ListEnterpriseSupportLinkedAccountCharges'
        )
