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
    create_aws_client,
    format_response,
    handle_aws_error,
    paginate_aws_response,
)
from ..utilities.time_utils import (
    timestamp_to_utc_iso_string,
    utc_datetime_string_to_epoch_seconds,
)
from fastmcp import Context
from typing import Any, Dict, Optional


# InvoiceSummary fields that AWS returns as timestamps. We normalize these to
# human-readable ISO 8601 UTC strings so the values are JSON-serializable and
# self-explanatory to the agent, while leaving every other field untouched.
_TIMESTAMP_FIELDS = ('IssuedDate', 'DueDate')


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
    max_results: Optional[int] = None,
    next_token: Optional[str] = None,
    max_pages: Optional[int] = None,
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
        start_date: Inclusive range start in ``YYYY-MM-DD`` or
            ``YYYY-MM-DDTHH:MM:SS`` (UTC) format. Must be paired with
            ``end_date``.
        end_date: Inclusive range end in ``YYYY-MM-DD`` or
            ``YYYY-MM-DDTHH:MM:SS`` (UTC) format. Must be paired with
            ``start_date``.
        invoicing_entity: Filter by the AWS legal selling entity name (for
            example ``"Amazon Web Services, Inc."``).
        max_results: Maximum number of results per page (1-100).
        next_token: Pagination token from a previous response to resume from.
        max_pages: Maximum number of pages to auto-paginate through. Defaults to
            all pages.

    Returns:
        Dict containing ``invoice_summaries`` (with ISO 8601 timestamps) and a
        ``pagination`` metadata block, or a standardized error response.
    """
    try:
        # --- Selector: ACCOUNT_ID or INVOICE_ID, not both ---
        if account_id and invoice_id:
            return format_response(
                'error',
                {'message': 'Provide either account_id or invoice_id, not both.'},
            )

        # --- Time filter: billing_period XOR start_date/end_date ---
        if billing_period and (start_date or end_date):
            return format_response(
                'error',
                {
                    'message': (
                        'billing_period and start_date/end_date are mutually '
                        'exclusive. Provide one or the other.'
                    )
                },
            )
        if bool(start_date) != bool(end_date):
            return format_response(
                'error',
                {'message': 'start_date and end_date must be provided together.'},
            )

        # Parse and validate the billing period (YYYY-MM) if provided.
        month: Optional[int] = None
        year: Optional[int] = None
        if billing_period:
            parts = billing_period.split('-')
            if len(parts) != 2:
                return format_response(
                    'error',
                    {'message': 'billing_period must be in YYYY-MM format (e.g. "2026-05").'},
                )
            try:
                year = int(parts[0])
                month = int(parts[1])
            except ValueError:
                return format_response(
                    'error',
                    {'message': 'billing_period must be in YYYY-MM format (e.g. "2026-05").'},
                )
            if month < 1 or month > 12:
                return format_response(
                    'error',
                    {'message': 'billing_period month must be between 1 and 12.'},
                )

        # --- Resolve the required Selector ---
        if invoice_id:
            selector = {'ResourceType': 'INVOICE_ID', 'Value': invoice_id}
        else:
            if not account_id:
                sts_client = create_aws_client('sts')
                account_id = sts_client.get_caller_identity()['Account']
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
                return format_response('error', {'message': str(parse_error)})
            api_filter['TimeInterval'] = {'StartDate': start_epoch, 'EndDate': end_epoch}
        if invoicing_entity:
            api_filter['InvoicingEntity'] = invoicing_entity
        if api_filter:
            request_params['Filter'] = api_filter

        if max_results is not None:
            request_params['MaxResults'] = max_results
        if next_token:
            request_params['NextToken'] = next_token

        client = _create_invoicing_client()

        # Use the shared paginator so pagination metadata is accurate across
        # pages (total_results, has_more, next_token, pages_fetched, ...).
        summaries, pagination = await paginate_aws_response(
            ctx,
            'ListInvoiceSummaries',
            client.list_invoice_summaries,
            request_params,
            'InvoiceSummaries',
            token_param='NextToken',
            token_key='NextToken',
            max_pages=max_pages,
        )

        normalized = [_normalize_invoice_summary(summary) for summary in summaries]

        await ctx.info(f'Successfully listed {len(normalized)} invoice summaries')

        response_data: Dict[str, Any] = {
            'invoice_summaries': normalized,
            'pagination': pagination,
        }

        return format_response('success', response_data)

    except Exception as e:
        return await handle_aws_error(ctx, e, 'ListInvoiceSummaries', 'Invoicing')
