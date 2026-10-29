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

"""AWS Invoicing operations for the AWS Billing and Cost Management MCP server.

This module contains the operation handlers for the Invoicing tools. Each
operation performs the AWS API call, normalizes epoch timestamps to ISO 8601
strings for the agent, and returns a standardized response envelope.
"""

from ..utilities.aws_service_base import (
    PageSpec,
    create_aws_client,
    format_response,
    handle_aws_error,
    paginate_aws_items,
    with_pagination,
)
from ..utilities.time_utils import (
    timestamp_to_utc_iso_string,
    utc_datetime_string_to_epoch_seconds,
)
from calendar import monthrange
from datetime import datetime, timezone
from fastmcp import Context
from typing import Any, Dict, List, Literal, Optional


# InvoiceSummary fields that AWS returns as timestamps. We normalize these to
# human-readable ISO 8601 UTC strings so the values are JSON-serializable and
# self-explanatory to the agent, while leaving every other field untouched.
_TIMESTAMP_FIELDS = ('IssuedDate', 'DueDate')

_SECONDS_PER_DAY = 86400

# Setting Filter.ReceiverRole raises the TimeInterval cap from one month to
# five years.
_RECEIVER_ROLE_MAX_YEARS = 5

# Classification for local parameter-validation failures, mirroring the
# top-level fields handle_aws_error sets on AWS-side errors so callers can
# tell a bad parameter apart from a service failure without parsing messages.
_LIST_INVOICE_SUMMARIES_OPERATION = 'ListInvoiceSummaries'
INVOICING_SERVICE_NAME = 'Invoicing'

# ListInvoiceSummaries returns up to 100 summaries per page.
LIST_INVOICE_SUMMARIES_PAGE_SPEC = PageSpec(
    result_key='InvoiceSummaries',
    token_param='NextToken',
    token_key_in_response='NextToken',
    page_max=100,
    page_size_param='MaxResults',
    # The service reports a bad caller next_token as ValidationException.
    caller_token_error_codes=frozenset({'ValidationException'}),
)


def _validation_error(data: Dict[str, Any]) -> Dict[str, Any]:
    """Return an error response for a list_invoice_summaries validation failure."""
    return format_response(
        'error',
        data,
        error_type='validation_error',
        operation=_LIST_INVOICE_SUMMARIES_OPERATION,
        service=INVOICING_SERVICE_NAME,
    )


def _max_time_interval_days(start_epoch: int) -> int:
    """Widest ``TimeInterval`` span, in whole days, accepted for a given start.

    The Invoicing service rejects a longer range with "TimePeriod cannot last
    more than a month", comparing the span against the number of days in the
    *start* date's month rather than clamping to the same day of the next month.
    Verified against the live API: a range starting 2026-01-31 is accepted up to
    2026-03-03 (31 days, the length of January), while one starting 2026-02-15
    is rejected past 2026-03-15 (28 days, the length of February).

    Args:
        start_epoch: Range start as epoch seconds (UTC).

    Returns:
        The maximum span in whole days, i.e. the length of the start date's month.
    """
    start = datetime.fromtimestamp(start_epoch, tz=timezone.utc)
    return monthrange(start.year, start.month)[1]


def _receiver_role_span_limit(start_epoch: int) -> int:
    """First instant a ``TimeInterval`` may NOT reach with a receiver role.

    Setting ``Filter.ReceiverRole`` raises the cap from one month to five
    years, and the service requires the range to be *less than* five years:
    verified live, a start of 2021-10-01 with an end of exactly 2026-10-01 is
    rejected with "TimePeriod must be less than 5 years", while one day short
    of it is accepted. The bound is therefore exclusive, and is compared on the
    exact instants rather than on whole days -- the service compares instants
    too, so flooring to days would admit a range up to five years plus 23:59:59.

    The limit is derived from the start date rather than a fixed day count, so
    leap years inside the window do not shift it. A 29 February start has no
    counterpart five years on, and the service resolves it FORWARD to 1 March
    rather than back to 28 February: verified live, a start of 2024-02-29
    accepts an end of 2029-02-28T23:59:59 and rejects 2029-03-01, and a start
    of 2024-02-29T12:00:00 accepts 2029-03-01T11:59:59 and rejects
    2029-03-01T12:00:00. Clamping to 28 February would refuse a day of ranges
    the service accepts.

    Args:
        start_epoch: Range start as epoch seconds (UTC).

    Returns:
        The exclusive upper bound as epoch seconds: the same calendar instant
        five years after the start, or the same time of day on 1 March for a
        29 February start.
    """
    start = datetime.fromtimestamp(start_epoch, tz=timezone.utc)
    try:
        limit = start.replace(year=start.year + _RECEIVER_ROLE_MAX_YEARS)
    except ValueError:
        limit = start.replace(year=start.year + _RECEIVER_ROLE_MAX_YEARS, month=3, day=1)
    return int(limit.timestamp())


def _format_range_bound(moment: datetime) -> str:
    """Render a range boundary in the format ``start_date``/``end_date`` accept."""
    if (moment.hour, moment.minute, moment.second) == (0, 0, 0):
        return moment.strftime('%Y-%m-%d')
    return moment.strftime('%Y-%m-%dT%H:%M:%S')


def _split_range_by_month(start_epoch: int, end_epoch: int) -> List[Dict[str, str]]:
    """Split an over-long range into per-month sub-ranges the service accepts.

    Used to turn an over-long ``start_date``/``end_date`` range into the exact
    set of calls that together cover it. Sub-ranges are deliberately expressed
    as dates rather than billing periods: a ``TimeInterval`` selects invoices by
    their *issued date* while a ``BillingPeriod`` selects by *billing month*, so
    substituting one for the other would silently answer a different question.

    The caller's own endpoints are preserved and internal boundaries fall on the
    first of each month, shared by the sub-ranges on either side so the union
    covers the original range with no gap. Issued timestamps carry sub-second
    precision, so landing exactly on a midnight boundary -- the only way a single
    invoice could surface in two adjacent sub-ranges -- is a theoretical edge
    rather than something seen in practice; de-duplicate by invoice ID if it
    matters.

    Args:
        start_epoch: Range start as epoch seconds (UTC).
        end_epoch: Range end as epoch seconds (UTC), later than ``start_epoch``.

    Returns:
        ``start_date``/``end_date`` pairs in chronological order, each spanning
        at most one month.
    """
    start = datetime.fromtimestamp(start_epoch, tz=timezone.utc)
    end = datetime.fromtimestamp(end_epoch, tz=timezone.utc)

    bounds: List[datetime] = [start]
    year, month = start.year, start.month
    while True:
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
        month_start = datetime(year, month, 1, tzinfo=timezone.utc)
        if month_start >= end:
            break
        bounds.append(month_start)
    bounds.append(end)

    return [
        {'start_date': _format_range_bound(lower), 'end_date': _format_range_bound(upper)}
        for lower, upper in zip(bounds, bounds[1:])
    ]


def _create_invoicing_client() -> Any:
    """Create an AWS Invoicing client.

    The Region is intentionally not hard-coded. ``create_aws_client`` resolves
    it from the ``AWS_REGION`` environment variable and falls back to
    ``us-east-1`` (the home Region of the global Invoicing service).

    Returns:
        boto3.client: AWS Invoicing client.
    """
    return create_aws_client('invoicing')


def _normalize_invoice_summary(summary: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a raw InvoiceSummary for agent consumption.

    Converts the epoch timestamp fields (``IssuedDate`` and ``DueDate``) into
    ISO 8601 UTC strings so they are JSON-serializable and human-readable. All
    other fields are returned exactly as provided by the AWS API to preserve
    fidelity (for example, monetary amounts remain decimal strings).

    Args:
        summary: A single ``InvoiceSummary`` object from the Invoicing API.

    Returns:
        The summary with its timestamp fields converted to ISO 8601 strings.
    """
    for field in _TIMESTAMP_FIELDS:
        value = summary.get(field)
        # Guard against double-normalization: only convert raw timestamps
        # (epoch numbers or datetime objects), never an already-ISO string.
        if value is not None and not isinstance(value, str):
            summary[field] = timestamp_to_utc_iso_string(value)
    return summary


async def list_invoice_summaries(
    ctx: Context,
    account_id: Optional[str] = None,
    invoice_id: Optional[str] = None,
    billing_period: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    invoicing_entity: Optional[str] = None,
    receiver_role: Optional[Literal['SELLER', 'RESELLER', 'BUYER']] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List AWS invoice summaries for an account or a single invoice.

    Retrieves invoice-level (header) details without line items. The required
    API selector is resolved from ``invoice_id`` when provided, otherwise from
    ``account_id`` (auto-detected from the caller's identity via STS when
    omitted). An optional time filter can be either a single ``billing_period``
    or a ``start_date``/``end_date`` range, but not both.

    Args:
        ctx: The MCP context object.
        account_id: 12-digit AWS account ID to list invoices for. Auto-detected
            from the caller identity (STS) when omitted. Mutually exclusive with
            ``invoice_id``.
        invoice_id: Retrieve the summary for a single invoice instead of an
            account. Mutually exclusive with ``account_id``.
        billing_period: Single calendar month in ``YYYY-MM`` format (for
            example ``"2026-05"``). Mutually exclusive with
            ``start_date``/``end_date``.
        start_date: Range start in ``YYYY-MM-DD`` or ``YYYY-MM-DDTHH:MM:SS``
            (UTC) format. Must be paired with ``end_date``.
        end_date: Range end in ``YYYY-MM-DD`` or ``YYYY-MM-DDTHH:MM:SS`` (UTC)
            format. Must be paired with ``start_date``. A date-only bound is
            00:00:00 UTC, so covering a whole final day requires the following
            day here -- ``"2026-06-30"`` excludes invoices issued during June 30.
        invoicing_entity: Filter by the AWS legal selling entity name (for
            example ``"Amazon Web Services, Inc."``).
        receiver_role: Restrict to invoices where the selected account holds
            this role. Account queries only -- it cannot be combined with
            ``invoice_id``. Raises the ``start_date``/``end_date`` cap from one
            month to less than five years, and is the only way estimated
            invoices are returned. Not a superset of an unrestricted query:
            invoices issued to invoice-unit receivers billed from the selected
            account can be absent, so run the query without a role as well and
            de-duplicate on ``InvoiceId``.
        max_items: Most invoice summaries to return. None fetches every page.
        next_token: Pagination token from a previous response to resume from.

    Returns:
        Dict containing ``invoice_summaries`` (with ISO 8601 timestamps), the
        ``selector`` the request resolved to (its ``type``, its ``value``, and
        ``auto_detected`` when the account came from the caller's identity),
        and a ``pagination`` metadata block, or a standardized error response.
    """
    try:
        # --- Selector: ACCOUNT_ID or INVOICE_ID, not both ---
        if account_id and invoice_id:
            return _validation_error(
                {'message': 'Provide either account_id or invoice_id, not both.'},
            )

        # A receiver role makes the service treat the request as an account
        # query, which an INVOICE_ID selector cannot satisfy. Verified live:
        # the role alone is rejected ("BillingPeriod and TimePeriod cannot both
        # be null when retrieve invoice summary by account ID"), and the role
        # with a time filter returns 0 rows for an invoice that exists, which
        # reads as "not found". Refuse the combination here instead.
        if invoice_id and receiver_role:
            return _validation_error(
                {
                    'message': (
                        'receiver_role applies to account queries only, and cannot be '
                        'combined with invoice_id. Drop receiver_role to retrieve this '
                        'invoice, or select by account_id with a time filter.'
                    )
                },
            )

        # --- Time filter: billing_period XOR start_date/end_date ---
        if billing_period and (start_date or end_date):
            return _validation_error(
                {
                    'message': (
                        'billing_period and start_date/end_date are mutually '
                        'exclusive. Provide one or the other.'
                    )
                },
            )
        if bool(start_date) != bool(end_date):
            return _validation_error(
                {'message': 'start_date and end_date must be provided together.'},
            )

        # The ACCOUNT_ID selector flow requires a time filter -- the service
        # rejects the request on arrival when both BillingPeriod and
        # TimeInterval are absent. The INVOICE_ID flow takes a different path
        # and needs no filter, so only guard the account case.
        if not invoice_id and not billing_period and not start_date and not end_date:
            return _validation_error(
                {
                    'message': (
                        'A time filter is required when listing invoice summaries for an '
                        'account. Provide billing_period="YYYY-MM" for a single calendar '
                        'month, or start_date and end_date for a range spanning '
                        + (
                            'less than five years, which receiver_role allows in one call.'
                            if receiver_role
                            else 'at most one month. To cover several months, make one '
                            'call per month.'
                        )
                    )
                },
            )

        # Parse and validate the billing period (YYYY-MM) if provided.
        month: Optional[int] = None
        year: Optional[int] = None
        if billing_period:
            parts = billing_period.split('-')
            if len(parts) != 2:
                return _validation_error(
                    {'message': 'billing_period must be in YYYY-MM format (e.g. "2026-05").'},
                )
            try:
                year = int(parts[0])
                month = int(parts[1])
            except ValueError:
                return _validation_error(
                    {'message': 'billing_period must be in YYYY-MM format (e.g. "2026-05").'},
                )
            if month < 1 or month > 12:
                return _validation_error(
                    {'message': 'billing_period month must be between 1 and 12.'},
                )

        # --- Resolve the required Selector ---
        # Whether the account came from the caller's identity rather than the
        # request is echoed back: a row's AccountId cannot stand in for it,
        # because an account query also returns invoices issued to invoice-unit
        # receivers billed from that account.
        auto_detected = False
        if invoice_id:
            selector = {'ResourceType': 'INVOICE_ID', 'Value': invoice_id}
        else:
            if not account_id:
                sts_client = create_aws_client('sts')
                account_id = sts_client.get_caller_identity()['Account']
                auto_detected = True
                await ctx.info(f'Auto-detected account ID: {account_id}')
            selector = {'ResourceType': 'ACCOUNT_ID', 'Value': account_id}

        request_params: Dict[str, Any] = {'Selector': selector}

        # --- Build the optional Filter ---
        api_filter: Dict[str, Any] = {}
        if billing_period:
            api_filter['BillingPeriod'] = {'Month': month, 'Year': year}
        elif start_date and end_date:
            try:
                start_epoch = utc_datetime_string_to_epoch_seconds(start_date)
                end_epoch = utc_datetime_string_to_epoch_seconds(end_date)
            except ValueError as parse_error:
                return _validation_error({'message': str(parse_error)})

            if end_epoch <= start_epoch:
                return _validation_error(
                    {
                        'message': (
                            'end_date must be later than start_date. The Invoicing service '
                            'rejects an empty or reversed range.'
                        )
                    },
                )

            # Reject a span the service is guaranteed to refuse, and name the
            # sub-ranges that together cover the request instead.
            span_days = (end_epoch - start_epoch) // _SECONDS_PER_DAY
            if receiver_role:
                # A receiver role lifts the cap to just under five years, so the
                # per-month split does not apply; there is nothing useful to
                # suggest. The bound is exclusive and compared on instants, as
                # the service compares them.
                limit_epoch = _receiver_role_span_limit(start_epoch)
                if end_epoch >= limit_epoch:
                    return _validation_error(
                        {
                            'message': (
                                f'start_date to end_date spans {span_days} days. With '
                                'receiver_role set a range must be less than five years, '
                                'which this tool checks before calling AWS, so end_date '
                                'must be earlier than '
                                f'{_format_range_bound(datetime.fromtimestamp(limit_epoch, tz=timezone.utc))}. '
                                'Narrow the range.'
                            )
                        },
                    )
            else:
                # The one-month cap is measured in whole days, so compare on the
                # same basis.
                max_days = _max_time_interval_days(start_epoch)
                if span_days > max_days:
                    return _validation_error(
                        {
                            'message': (
                                f'start_date to end_date spans {span_days} days. This tool '
                                'accepts at most one month per call, measured as the number '
                                f"of days in the start date's month ({max_days} here), and "
                                'rejects a longer range before calling AWS. '
                                'Issue one call per suggested_date_ranges entry instead of '
                                'widening the range, then combine the results. Setting '
                                'receiver_role raises the cap to less than five years, but '
                                'returns a different set of invoices.'
                            ),
                            'suggested_date_ranges': _split_range_by_month(start_epoch, end_epoch),
                        },
                    )

            api_filter['TimeInterval'] = {'StartDate': start_epoch, 'EndDate': end_epoch}
        if invoicing_entity:
            api_filter['InvoicingEntity'] = invoicing_entity
        if receiver_role:
            api_filter['ReceiverRole'] = receiver_role
        if api_filter:
            request_params['Filter'] = api_filter

        client = _create_invoicing_client()

        summaries, _, pagination = await paginate_aws_items(
            ctx,
            'ListInvoiceSummaries',
            client.list_invoice_summaries,
            request_params,
            LIST_INVOICE_SUMMARIES_PAGE_SPEC,
            max_items=max_items,
            next_token=next_token,
        )

        normalized = [_normalize_invoice_summary(summary) for summary in summaries]

        await ctx.info(f'Successfully listed {len(normalized)} invoice summaries')

        return format_response(
            'success',
            with_pagination(
                {
                    'invoice_summaries': normalized,
                    'selector': {
                        'type': selector['ResourceType'],
                        'value': selector['Value'],
                        'auto_detected': auto_detected,
                    },
                },
                pagination,
            ),
        )

    except Exception as e:
        return await handle_aws_error(
            ctx, e, _LIST_INVOICE_SUMMARIES_OPERATION, INVOICING_SERVICE_NAME
        )
