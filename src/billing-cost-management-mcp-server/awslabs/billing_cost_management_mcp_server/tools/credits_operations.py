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

"""AWS credits operations for the AWS Billing and Cost Management MCP server.

This module contains the operation handlers for the ``credits`` tool. Each
operation performs the AWS API call, converts calendar-date inputs into the
epoch timestamps the API expects, normalizes epoch timestamps for the agent,
and returns a standardized response envelope.
"""

from ..utilities.aws_service_base import (
    create_aws_client,
    format_response,
    handle_aws_error,
)
from ..utilities.sql_utils import convert_response_if_needed
from ..utilities.time_utils import (
    timestamp_to_utc_iso_string,
    utc_datetime_string_to_epoch_seconds,
)
from botocore.exceptions import ClientError
from calendar import monthrange
from datetime import datetime, timezone
from fastmcp import Context
from typing import Any, Dict, Optional


# CreditData fields that AWS returns as timestamps. We normalize these to
# human-readable strings so the values are JSON-serializable and
# self-explanatory to the agent, while leaving every other field untouched.
_CREDIT_TIMESTAMP_FIELDS = ('startDate', 'endDate', 'exhaustDate')

# GetCreditAllocationHistory rejects ranges longer than 24 months. Kept
# as a literal rather than computed so the enforced window is obvious
# at a glance and cannot drift with calendar arithmetic.
MAX_ALLOCATION_HISTORY_SECONDS = 63072000

# GetCredits rejects a start date more than one year before now, a tighter
# limit than the allocation ledger's. 365 days is used rather than a calendar
# year because it is never wider than the limit, including across a leap day.
MAX_CREDITS_LOOKBACK_SECONDS = 31536000

# IAM action required by each operation, used to build an actionable message
# when the caller's policy is missing it.
_REQUIRED_IAM_ACTIONS = {
    'GetCredits': 'billing:GetCredits',
    'GetCreditAllocationHistory': 'billing:GetCreditAllocationHistory',
}


def _create_billing_client() -> Any:
    """Create an AWS Billing client.

    Returns:
        boto3.client: AWS Billing client.
    """
    return create_aws_client('billing')


def _normalize_credit_data(credit: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a raw CreditData item for agent consumption.

    Converts the epoch timestamp fields (``startDate``, ``endDate`` and
    ``exhaustDate``) into human-readable strings. All other fields are returned
    exactly as provided by the AWS API to preserve fidelity, so monetary
    amounts remain decimal strings.

    Args:
        credit: A single ``CreditData`` object from the Billing API.

    Returns:
        The credit with its timestamp fields converted to ISO 8601 strings.
    """
    for field in _CREDIT_TIMESTAMP_FIELDS:
        value = credit.get(field)
        if value is not None and not isinstance(value, str):
            credit[field] = timestamp_to_utc_iso_string(value)
    return credit


def _parse_epoch_range(
    start_date: Optional[str], end_date: Optional[str], require_end: bool
) -> tuple:
    """Validate and convert a calendar-date range into epoch seconds.

    Rejects a missing start date, a missing end date when the operation requires
    one, an unparseable date, and an end date that precedes the start.

    Args:
        start_date: Inclusive range start in ``YYYY-MM-DD`` UTC format.
        end_date: Inclusive range end in the same format.
        require_end: Whether the operation requires an end date.

    Returns:
        Tuple of (start_epoch, end_epoch, error) where error is a standardized
        error response and the epochs are None when validation fails. end_epoch
        is None when the caller omitted an optional end date.
    """
    if not start_date or (require_end and not end_date):
        needed = (
            'start_date and end_date are both required'
            if require_end
            else 'start_date is required'
        )
        return (
            None,
            None,
            format_response('error', {'message': f'{needed} (YYYY-MM-DD, e.g. "2026-01-01").'}),
        )

    try:
        start_epoch = utc_datetime_string_to_epoch_seconds(start_date)
        end_epoch = utc_datetime_string_to_epoch_seconds(end_date) if end_date else None
    except ValueError as parse_error:
        return None, None, format_response('error', {'message': str(parse_error)})

    if end_epoch is not None and end_epoch < start_epoch:
        return (
            None,
            None,
            format_response('error', {'message': 'end_date must not precede start_date.'}),
        )

    return start_epoch, end_epoch, None


def _expand_billing_period(billing_period: str) -> tuple:
    """Expand a ``YYYY-MM`` billing period into the range covering that month.

    Args:
        billing_period: Calendar month in ``YYYY-MM`` format.

    Returns:
        Tuple of (start_epoch, end_epoch, error) spanning the first to the last
        day of the month, where error is a standardized error response when the
        value is not a valid calendar month.
    """
    invalid = format_response(
        'error',
        {'message': f'billing_period must be in YYYY-MM format, got {billing_period!r}.'},
    )

    parts = billing_period.split('-')
    if len(parts) != 2:
        return None, None, invalid

    try:
        year, month = int(parts[0]), int(parts[1])
        last_day = monthrange(year, month)[1]
        start_epoch = utc_datetime_string_to_epoch_seconds(f'{year:04d}-{month:02d}-01')
        end_epoch = utc_datetime_string_to_epoch_seconds(f'{year:04d}-{month:02d}-{last_day:02d}')
    except (ValueError, TypeError, OverflowError):
        return None, None, invalid

    return start_epoch, end_epoch, None


def _convert_credit_id(credit_id: Optional[Any]) -> tuple:
    """Convert a credit ID from a string to the integer the API expects.

    ``GetCreditAllocationHistory`` declares ``creditId`` as a long while
    ``GetCredits`` returns it as a string, so an agent chaining the two calls
    would otherwise send the wrong type and get a ValidationException.

    Args:
        credit_id: The caller-supplied credit ID, or None.

    Returns:
        Tuple of (converted_id, error) where error is a standardized error
        response when the value is not numeric.
    """
    if credit_id is None:
        return None, None

    try:
        return int(credit_id), None
    except (TypeError, ValueError):
        return None, format_response(
            'error',
            {
                'message': (
                    f'credit_id must be numeric, got {credit_id!r}. Use the '
                    'creditId value returned by get_credits.'
                )
            },
        )


def _build_get_credit_allocation_history_time_range(
    start_epoch: int, end_epoch: int, requested_start: int, requested_end: int
) -> Dict[str, Any]:
    """Describe the window actually queried alongside the one requested.

    Reporting both makes a narrowed window visible to the agent so a clamped
    result is never mistaken for a complete one.

    Args:
        start_epoch: Effective range start after clamping.
        end_epoch: Effective range end after clamping.
        requested_start: Range start as the caller supplied it.
        requested_end: Range end as the caller supplied it.

    Returns:
        Dict describing both windows and the enforced maximum.
    """
    return {
        'start_date': timestamp_to_utc_iso_string(start_epoch),
        'end_date': timestamp_to_utc_iso_string(end_epoch),
        'narrowed_from_request': (start_epoch != requested_start or end_epoch != requested_end),
        'requested_start_date': timestamp_to_utc_iso_string(requested_start),
        'requested_end_date': timestamp_to_utc_iso_string(requested_end),
        'max_range_months': 24,
    }


def _clamp_get_credit_allocation_history_range(start_epoch: int, end_epoch: int) -> tuple:
    """Narrow a range to the enforced 24-month window ending no later than now.

    Args:
        start_epoch: Requested range start in epoch seconds.
        end_epoch: Requested range end in epoch seconds.

    Returns:
        Tuple of (start_epoch, end_epoch) after clamping.
    """
    now_epoch = int(datetime.now(timezone.utc).timestamp())
    end_epoch = min(end_epoch, now_epoch)
    if end_epoch - start_epoch > MAX_ALLOCATION_HISTORY_SECONDS:
        start_epoch = end_epoch - MAX_ALLOCATION_HISTORY_SECONDS
    return start_epoch, end_epoch


async def _handle_billing_error(ctx: Context, error: Exception, api_name: str) -> Dict[str, Any]:
    """Handle a Billing API error, adding a permission hint for access denials.

    Billing operations raise ``AccessDeniedException`` when the caller's IAM
    policy omits the specific action. The failure names the missing permission
    instead of returning an opaque access error that could be mistaken for
    "no data". Operations absent from ``_REQUIRED_IAM_ACTIONS`` fall back to a
    derived action name. Every other failure falls through to the shared handler.

    Args:
        ctx: The MCP context object.
        error: The exception that was raised.
        api_name: The AWS API operation name (for example ``"GetCredits"``).

    Returns:
        Dict containing the standardized error response.
    """
    if isinstance(error, ClientError):
        aws_error = error.response.get('Error', {})
        error_code = aws_error.get('Code', '')
        if error_code in ('AccessDeniedException', 'AccessDenied'):
            required_action = _REQUIRED_IAM_ACTIONS.get(api_name, f'billing:{api_name}')
            return {
                'status': 'error',
                'service': 'Billing',
                'operation': api_name,
                'error_type': 'access_denied',
                'message': (
                    f'Access denied for Billing {api_name}. '
                    f'Ensure you have the {required_action} permission. '
                    'This is a permission failure, not an absence of credits.'
                ),
                'resolution': (
                    f'Add {required_action} to the caller IAM policy. Policies created '
                    'before the credit allocation-history launch may grant '
                    'billing:GetCredits without billing:GetCreditAllocationHistory.'
                ),
                'request_id': error.response.get('ResponseMetadata', {}).get(
                    'RequestId', 'Unknown'
                ),
                'http_status': error.response.get('ResponseMetadata', {}).get('HTTPStatusCode', 0),
            }

    return await handle_aws_error(ctx, error, api_name, 'Billing')


async def _resolve_account_id(ctx: Context, account_id: Optional[str]) -> str:
    """Return the account ID to query, auto-detecting the caller's when omitted.

    Billing operations that are account-scoped require ``accountId``, so the
    caller's own account is resolved via STS when the agent does not supply one.

    Args:
        ctx: The MCP context object.
        account_id: 12-digit AWS account ID, or None to auto-detect.

    Returns:
        The resolved 12-digit AWS account ID.
    """
    if account_id:
        return account_id

    sts_client = create_aws_client('sts')
    resolved = sts_client.get_caller_identity()['Account']
    await ctx.info(f'Auto-detected account ID: {resolved}')
    return resolved


async def _paginate_get_credit_allocation_history(
    ctx: Context,
    client: Any,
    request_params: Dict[str, Any],
    max_results: Optional[int],
    next_token: Optional[str],
    max_pages: Optional[int],
) -> tuple:
    """Page the allocation ledger with the SDK paginator, keeping completeness flags.

    The SDK declares ``partialResults`` and ``failedMonths`` as non-aggregate keys, so
    they appear on each page rather than being summed. Both are combined across pages
    here, because a total computed over an incomplete ledger would otherwise read as
    authoritative.

    The resume point is read from the page the caller stopped on rather than from the
    iterator, because the SDK only populates its own resume token when it applies its
    internal item limit, never when a consumer breaks out of the loop.

    Args:
        ctx: The MCP context object.
        client: The billing client.
        request_params: Operation parameters, without paging controls.
        max_results: Items per page, or None for the service default.
        next_token: Continuation token to resume from, or None.
        max_pages: Maximum pages to fetch, or None for all.

    Returns:
        Tuple of (rows, pagination_metadata, completeness).
    """
    started = datetime.now(timezone.utc)
    paging: Dict[str, Any] = {}
    if max_results is not None:
        paging['PageSize'] = max_results
    if next_token:
        paging['StartingToken'] = next_token

    paginator = client.get_paginator('get_credit_allocation_history')
    pages = paginator.paginate(**request_params, PaginationConfig=paging)

    rows: list = []
    failed_months: list = []
    partial_results = False
    pages_fetched = 0
    resume_token = None

    for page in pages:
        rows.extend(page.get('creditAllocationHistoryList') or [])
        partial_results = partial_results or bool(page.get('partialResults'))
        for month in page.get('failedMonths') or []:
            if month not in failed_months:
                failed_months.append(month)
        pages_fetched += 1
        resume_token = page.get('nextToken')
        if max_pages is not None and pages_fetched >= max_pages:
            break
    duration_ms = (datetime.now(timezone.utc) - started).total_seconds() * 1000
    await ctx.info(f'Fetched {pages_fetched} page(s), {len(rows)} allocation records')

    pagination = {
        'complete_dataset': resume_token is None,
        'pages_fetched': pages_fetched,
        'total_results': len(rows),
        'has_more': resume_token is not None,
        'next_token': resume_token,
        'duration_ms': int(duration_ms),
    }
    completeness = {'partial_results': partial_results, 'failed_months': failed_months}
    return rows, pagination, completeness


def _build_get_credits_request(
    account_id: str,
    start_epoch: int,
    end_epoch: Optional[int],
    payer_account_flag: Optional[bool],
) -> Dict[str, Any]:
    """Assemble GetCredits request parameters, omitting the optional ones.

    Args:
        account_id: Resolved 12-digit AWS account ID.
        start_epoch: Range start in epoch seconds.
        end_epoch: Range end in epoch seconds, or None.
        payer_account_flag: Whether to query at the payer-account level.

    Returns:
        Dict of API request parameters.
    """
    request_params: Dict[str, Any] = {'accountId': account_id, 'startDate': start_epoch}
    if end_epoch is not None:
        request_params['endDate'] = end_epoch
    if payer_account_flag is not None:
        request_params['payerAccountFlag'] = payer_account_flag
    return request_params


def _build_get_credit_allocation_history_request(
    account_id: str,
    start_epoch: int,
    end_epoch: int,
    credit_id: Optional[int],
) -> Dict[str, Any]:
    """Assemble GetCreditAllocationHistory request parameters.

    Args:
        account_id: Resolved 12-digit AWS account ID.
        start_epoch: Effective range start in epoch seconds.
        end_epoch: Effective range end in epoch seconds.
        credit_id: Single credit to restrict the ledger to, or None.

    Returns:
        Dict of API request parameters, without paging controls.
    """
    request_params: Dict[str, Any] = {
        'accountId': account_id,
        'startDate': start_epoch,
        'endDate': end_epoch,
    }
    if credit_id is not None:
        request_params['creditId'] = credit_id
    return request_params


def _clamp_get_credits_range(start_epoch: int, end_epoch: Optional[int]) -> tuple:
    """Narrow a range to the enforced one-year lookback ending no later than now.

    An omitted end date is left as None because the API defaults it to the
    current date, so supplying one would only restate the default.

    Args:
        start_epoch: Requested range start in epoch seconds.
        end_epoch: Requested range end in epoch seconds, or None when omitted.

    Returns:
        Tuple of (start_epoch, end_epoch) after clamping.
    """
    now_epoch = int(datetime.now(timezone.utc).timestamp())
    if end_epoch is not None:
        end_epoch = min(end_epoch, now_epoch)
    start_epoch = max(start_epoch, now_epoch - MAX_CREDITS_LOOKBACK_SECONDS)
    return start_epoch, end_epoch


def _reject_get_credits_pre_lookback_window(end_epoch: Optional[int]) -> Optional[Dict[str, Any]]:
    """Reject a window that ends before the earliest date GetCredits accepts.

    Such a window has no overlap with the supported lookback, so clamping the
    start forward would push it past the end and invert the range. A window that
    only partly predates the floor is clamped instead, since part of it is
    answerable.

    Args:
        end_epoch: Requested range end in epoch seconds, or None when omitted.

    Returns:
        A standardized error response, or None when the window is answerable.
    """
    if end_epoch is None:
        return None

    floor_epoch = int(datetime.now(timezone.utc).timestamp()) - MAX_CREDITS_LOOKBACK_SECONDS
    if end_epoch >= floor_epoch:
        return None

    return format_response(
        'error',
        {
            'message': (
                'GetCredits supports start dates within the last year, and the '
                f'requested window ends on {timestamp_to_utc_iso_string(end_epoch)}, '
                'before that limit. Request a window that reaches into the last year.'
            )
        },
    )


def _build_get_credits_time_range(
    start_epoch: int,
    end_epoch: Optional[int],
    requested_start: int,
    requested_end: Optional[int],
) -> Dict[str, Any]:
    """Describe the window actually queried alongside the one requested.

    Reporting both makes a narrowed window visible to the agent so a clamped
    result is never mistaken for a complete one. A null end date means the API
    default of the current date applies.

    Args:
        start_epoch: Effective range start after clamping.
        end_epoch: Effective range end after clamping, or None when omitted.
        requested_start: Range start as the caller supplied it.
        requested_end: Range end as the caller supplied it, or None when omitted.

    Returns:
        Dict describing both windows and the enforced maximum lookback.
    """
    return {
        'start_date': timestamp_to_utc_iso_string(start_epoch),
        'end_date': (timestamp_to_utc_iso_string(end_epoch) if end_epoch is not None else None),
        'narrowed_from_request': (start_epoch != requested_start or end_epoch != requested_end),
        'requested_start_date': timestamp_to_utc_iso_string(requested_start),
        'requested_end_date': (
            timestamp_to_utc_iso_string(requested_end) if requested_end is not None else None
        ),
        'max_lookback_months': 12,
    }


async def _resolve_get_credits_window(
    ctx: Context, start_epoch: int, end_epoch: Optional[int]
) -> tuple:
    """Clamp the requested range and describe both windows, logging any change.

    Args:
        ctx: The MCP context object.
        start_epoch: Requested range start in epoch seconds.
        end_epoch: Requested range end in epoch seconds, or None when omitted.

    Returns:
        Tuple of (start_epoch, end_epoch, time_range) after clamping.
    """
    requested_start, requested_end = start_epoch, end_epoch
    start_epoch, end_epoch = _clamp_get_credits_range(start_epoch, end_epoch)
    time_range = _build_get_credits_time_range(
        start_epoch, end_epoch, requested_start, requested_end
    )
    if time_range['narrowed_from_request']:
        await ctx.info('Requested range narrowed to the enforced one-year lookback ending now')
    return start_epoch, end_epoch, time_range


async def _finalize_response(
    ctx: Context, response: Dict[str, Any], api_name: str, **conversion_kwargs: Any
) -> Dict[str, Any]:
    """Offload an oversized response to session SQL and wrap it in the envelope.

    Args:
        ctx: The MCP context object.
        response: The assembled response body.
        api_name: Conversion key identifying the operation.
        **conversion_kwargs: Query context passed through to the converter.

    Returns:
        The standardized success envelope.
    """
    converted = await convert_response_if_needed(ctx, response, api_name, **conversion_kwargs)
    return format_response('success', converted)


def _reject_future_window(start_epoch: int) -> Optional[Dict[str, Any]]:
    """Reject a window that has not started yet.

    Clamping a future end date back to now would otherwise leave the start after
    the end, producing an inverted range and a time_range block that misreports
    the period queried.

    Args:
        start_epoch: Requested range start in epoch seconds.

    Returns:
        A standardized error response, or None when the window has started.
    """
    if start_epoch <= int(datetime.now(timezone.utc).timestamp()):
        return None

    return format_response(
        'error',
        {
            'message': (
                'The requested window starts in the future, so no credit data exists for it yet.'
            )
        },
    )


def _validate_get_credit_allocation_history_inputs(
    start_date: Optional[str],
    end_date: Optional[str],
    billing_period: Optional[str],
    credit_id: Optional[Any],
) -> tuple:
    """Validate the allocation-history inputs before any API call.

    The window may be given either as a single ``billing_period`` or as a
    ``start_date``/``end_date`` pair, but not both.

    Args:
        start_date: Inclusive range start in ``YYYY-MM-DD`` UTC format.
        end_date: Inclusive range end in the same format.
        billing_period: Single calendar month in ``YYYY-MM`` format.
        credit_id: Caller-supplied credit ID, or None.

    Returns:
        Tuple of (start_epoch, end_epoch, converted_credit_id, error) where error
        is a standardized error response when any input is invalid.
    """
    if billing_period and (start_date or end_date):
        return (
            None,
            None,
            None,
            format_response(
                'error',
                {
                    'message': (
                        'billing_period and start_date/end_date are mutually '
                        'exclusive. Provide one or the other.'
                    )
                },
            ),
        )

    if billing_period:
        start_epoch, end_epoch, error = _expand_billing_period(billing_period)
    else:
        start_epoch, end_epoch, error = _parse_epoch_range(start_date, end_date, True)
    if error:
        return None, None, None, error

    error = _reject_future_window(start_epoch)
    if error:
        return None, None, None, error

    converted_credit_id, error = _convert_credit_id(credit_id)
    if error:
        return None, None, None, error

    return start_epoch, end_epoch, converted_credit_id, None


async def _resolve_get_credit_allocation_history_window(
    ctx: Context, start_epoch: int, end_epoch: int
) -> tuple:
    """Clamp the requested range and describe both windows, logging any change.

    Args:
        ctx: The MCP context object.
        start_epoch: Requested range start in epoch seconds.
        end_epoch: Requested range end in epoch seconds.

    Returns:
        Tuple of (start_epoch, end_epoch, time_range) after clamping.
    """
    requested_start, requested_end = start_epoch, end_epoch
    start_epoch, end_epoch = _clamp_get_credit_allocation_history_range(start_epoch, end_epoch)
    time_range = _build_get_credit_allocation_history_time_range(
        start_epoch, end_epoch, requested_start, requested_end
    )
    if time_range['narrowed_from_request']:
        await ctx.info('Requested range narrowed to the enforced 24-month window ending now')
    return start_epoch, end_epoch, time_range


async def _fetch_get_credit_allocation_history(
    ctx: Context,
    client: Any,
    request_params: Dict[str, Any],
    time_range: Dict[str, Any],
    max_results: Optional[int],
    next_token: Optional[str],
    max_pages: Optional[int],
) -> Dict[str, Any]:
    """Page the allocation ledger and assemble the response body.

    Args:
        ctx: The MCP context object.
        client: The billing client.
        request_params: Operation parameters, without paging controls.
        time_range: Description of the window queried.
        max_results: Items per page, or None for the service default.
        next_token: Continuation token to resume from, or None.
        max_pages: Maximum pages to fetch, or None for all.

    Returns:
        The assembled response body.
    """
    allocations, pagination, completeness = await _paginate_get_credit_allocation_history(
        ctx, client, request_params, max_results, next_token, max_pages
    )
    await ctx.info(f'Successfully retrieved {len(allocations)} credit allocation records')
    return {
        'credit_allocation_history': allocations,
        'time_range': time_range,
        'completeness': completeness,
        'pagination': pagination,
    }


async def get_credits(
    ctx: Context,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    account_id: Optional[str] = None,
    payer_account_flag: Optional[bool] = None,
) -> Dict[str, Any]:
    """Get credit balance, expiration and applicability for an account.

    Returns every credit object visible to the account within the requested window,
    including initial and remaining amounts, expiration and exhaustion dates,
    applicable products, and credit-sharing configuration.

    A payer-level query can return a large credit portfolio, so the shared size
    threshold decides whether to offload to session SQL via convert_response_if_needed.

    Args:
        ctx: The MCP context object.
        start_date: Inclusive range start in ``YYYY-MM-DD`` (or
            ``YYYY-MM-DDTHH:MM:SS``) UTC format.
        end_date: Optional inclusive range end in the same format.
        account_id: 12-digit AWS account ID. Auto-detected from the caller
            identity via STS when omitted.
        payer_account_flag: Set True to query at the payer-account level rather
            than for the individual account.

    Returns:
        Dict containing ``credits`` with timestamps, or a standardized error
        response.
    """
    try:
        start_epoch, end_epoch, error = _parse_epoch_range(start_date, end_date, False)
        if error:
            return error

        error = _reject_future_window(start_epoch) or _reject_get_credits_pre_lookback_window(
            end_epoch
        )
        if error:
            return error

        start_epoch, end_epoch, time_range = await _resolve_get_credits_window(
            ctx, start_epoch, end_epoch
        )

        resolved_account_id = await _resolve_account_id(ctx, account_id)

        request_params = _build_get_credits_request(
            resolved_account_id, start_epoch, end_epoch, payer_account_flag
        )
        client = _create_billing_client()

        api_response = client.get_credits(**request_params)

        credits = [_normalize_credit_data(credit) for credit in api_response.get('credits', [])]

        await ctx.info(f'Successfully retrieved {len(credits)} credits')

        response = {
            'credits': credits,
            'time_range': time_range,
        }

        return await _finalize_response(
            ctx,
            response,
            'credits_get_credits',
            account_id=resolved_account_id,
            start_date=start_date,
            end_date=end_date,
            time_range=time_range,
        )

    except Exception as e:
        return await _handle_billing_error(ctx, e, 'GetCredits')


async def get_credit_allocation_history(
    ctx: Context,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    billing_period: Optional[str] = None,
    account_id: Optional[str] = None,
    credit_id: Optional[Any] = None,
    max_results: Optional[int] = None,
    next_token: Optional[str] = None,
    max_pages: Optional[int] = None,
) -> Dict[str, Any]:
    """Get credits ledger to show how credits were applied per service per billing period.

    Returns the credit-level allocation ledger.

    The API rejects ranges longer than 24 months. A longer request is narrowed to
    the most recent 24 months rather than failing, and the response reports the
    window actually queried so a narrowed result is never mistaken for a
    complete one.

    Multi-month allocation windows can exceed the inline size threshold,
    in which case the shared helper offloads the rows to session SQL via
    convert_response_if_needed.

    Args:
        ctx: The MCP context object.
        start_date: Inclusive range start in ``YYYY-MM-DD`` (or
            ``YYYY-MM-DDTHH:MM:SS``) UTC format. Required by the API.
        end_date: Inclusive range end in the same format. Required by the API.
        billing_period: Single calendar month in ``YYYY-MM`` format, expanded to
            cover that whole month. Mutually exclusive with
            ``start_date``/``end_date``.
        account_id: 12-digit AWS account ID. Auto-detected from the caller
            identity via STS when omitted.
        credit_id: Restrict the ledger to a single credit. The API declares this
            as a long, while ``GetCredits`` returns ``creditId`` as a string, so
            a string value is converted to an integer here.
        max_results: Maximum number of results per page.
        next_token: Pagination token from a previous response to resume from.
        max_pages: Maximum number of pages to auto-paginate through. Defaults to
            all pages.

    Returns:
        Dict containing ``credit_allocation_history``, the ``time_range``
        actually queried, completeness flags, and a ``pagination`` metadata
        block, or a standardized error response.
    """
    try:
        start_epoch, end_epoch, converted_credit_id, error = (
            _validate_get_credit_allocation_history_inputs(
                start_date, end_date, billing_period, credit_id
            )
        )
        if error:
            return error

        start_epoch, end_epoch, time_range = await _resolve_get_credit_allocation_history_window(
            ctx, start_epoch, end_epoch
        )

        resolved_account_id = await _resolve_account_id(ctx, account_id)

        request_params = _build_get_credit_allocation_history_request(
            resolved_account_id, start_epoch, end_epoch, converted_credit_id
        )
        client = _create_billing_client()

        response = await _fetch_get_credit_allocation_history(
            ctx, client, request_params, time_range, max_results, next_token, max_pages
        )

        return await _finalize_response(
            ctx,
            response,
            'credits_get_credit_allocation_history',
            pagination_token_key='nextToken',
            account_id=resolved_account_id,
            time_range=response['time_range'],
            completeness=response['completeness'],
            pagination=response['pagination'],
        )

    except Exception as e:
        return await _handle_billing_error(ctx, e, 'GetCreditAllocationHistory')
