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

"""AWS Invoice Unit operations for the AWS Billing and Cost Management MCP server.

This module contains the read-only operation handlers for the ``invoice-units``
tool (AWS Invoice Configuration). Each operation performs the AWS API call,
normalizes epoch/``datetime`` timestamps to ISO 8601 strings for the agent, and
returns a standardized response envelope.
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
from datetime import datetime
from fastmcp import Context
from typing import Any, Dict, List, Optional


def _create_invoicing_client() -> Any:
    """Create an AWS Invoicing client.

    The Region is intentionally not hard-coded. ``create_aws_client`` resolves
    it from the ``AWS_REGION`` environment variable and falls back to
    ``us-east-1`` (the home Region of the global Invoicing service).

    Returns:
        boto3.client: AWS Invoicing client.
    """
    return create_aws_client('invoicing')


def _normalize_timestamps(obj: Any) -> Any:
    """Recursively convert ``datetime`` values to ISO 8601 UTC strings.

    boto3 returns Python ``datetime`` objects for AWS timestamp fields (for
    example ``LastModified``). These are not JSON-serializable, so we walk the
    response and convert every ``datetime`` to a human-readable ISO 8601 string
    while leaving all other values untouched. Walking the structure (rather than
    normalizing named fields) keeps this correct as the API adds nested
    timestamp fields.

    Args:
        obj: An arbitrary value from an AWS response (dict, list, or scalar).

    Returns:
        The value with any ``datetime`` instances converted to ISO 8601 strings.
    """
    if isinstance(obj, dict):
        return {key: _normalize_timestamps(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [_normalize_timestamps(item) for item in obj]
    if isinstance(obj, datetime):
        return timestamp_to_utc_iso_string(obj)
    return obj


async def list_invoice_units(
    ctx: Context,
    names: Optional[List[str]] = None,
    invoice_receivers: Optional[List[str]] = None,
    accounts: Optional[List[str]] = None,
    bill_source_accounts: Optional[List[str]] = None,
    as_of: Optional[str] = None,
    max_results: Optional[int] = None,
    next_token: Optional[str] = None,
    max_pages: Optional[int] = None,
) -> Dict[str, Any]:
    """List AWS invoice unit definitions for the caller's organization.

    Retrieves the invoice units (groups of accounts that receive a separate
    invoice) visible to the management account. All filters are optional and
    combine as an AND across filter types; within a single filter the list
    values are an OR (match any).

    Args:
        ctx: The MCP context object.
        names: Return only invoice units whose name matches one of these values.
        invoice_receivers: Return only invoice units whose receiver account is
            one of these 12-digit account IDs.
        accounts: Return only invoice units that contain one of these member
            account IDs.
        bill_source_accounts: Return only invoice units with one of these bill
            source account IDs.
        as_of: Return the invoice unit definitions as they existed at this
            UTC instant (``YYYY-MM-DD`` or ``YYYY-MM-DDTHH:MM:SS``). Defaults to
            the current definitions when omitted.
        max_results: Maximum number of results per page (1-100).
        next_token: Pagination token from a previous response to resume from.
        max_pages: Maximum number of pages to auto-paginate through. Defaults to
            all pages.

    Returns:
        Dict containing ``invoice_units`` (with ISO 8601 timestamps) and a
        ``pagination`` metadata block, or a standardized error response.
    """
    try:
        request_params: Dict[str, Any] = {}

        # --- Build the optional Filters (flattened, per BCM convention) ---
        filters: Dict[str, Any] = {}
        if names:
            filters['Names'] = names
        if invoice_receivers:
            filters['InvoiceReceivers'] = invoice_receivers
        if accounts:
            filters['Accounts'] = accounts
        if bill_source_accounts:
            filters['BillSourceAccounts'] = bill_source_accounts
        if filters:
            request_params['Filters'] = filters

        if as_of:
            try:
                request_params['AsOf'] = utc_datetime_string_to_epoch_seconds(as_of)
            except ValueError as parse_error:
                return format_response('error', {'message': str(parse_error)})

        if max_results is not None:
            request_params['MaxResults'] = max_results
        if next_token:
            request_params['NextToken'] = next_token

        client = _create_invoicing_client()

        units, pagination = await paginate_aws_response(
            ctx,
            'ListInvoiceUnits',
            client.list_invoice_units,
            request_params,
            'InvoiceUnits',
            token_param='NextToken',
            token_key='NextToken',
            max_pages=max_pages,
        )

        normalized = _normalize_timestamps(units)

        await ctx.info(f'Successfully listed {len(normalized)} invoice units')

        return format_response(
            'success',
            {'invoice_units': normalized, 'pagination': pagination},
        )

    except Exception as e:
        return await handle_aws_error(ctx, e, 'ListInvoiceUnits', 'Invoicing')


async def get_invoice_unit(
    ctx: Context,
    invoice_unit_arn: str,
    as_of: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve the definition of a single AWS invoice unit.

    Args:
        ctx: The MCP context object.
        invoice_unit_arn: The ARN of the invoice unit to retrieve (required).
        as_of: Return the invoice unit definition as it existed at this UTC
            instant (``YYYY-MM-DD`` or ``YYYY-MM-DDTHH:MM:SS``). Defaults to the
            current definition when omitted.

    Returns:
        Dict containing the ``invoice_unit`` definition (with ISO 8601
        timestamps), or a standardized error response.
    """
    try:
        if not invoice_unit_arn:
            return format_response(
                'error', {'message': 'invoice_unit_arn is required for get_invoice_unit.'}
            )

        request_params: Dict[str, Any] = {'InvoiceUnitArn': invoice_unit_arn}
        if as_of:
            try:
                request_params['AsOf'] = utc_datetime_string_to_epoch_seconds(as_of)
            except ValueError as parse_error:
                return format_response('error', {'message': str(parse_error)})

        client = _create_invoicing_client()
        response = client.get_invoice_unit(**request_params)
        response.pop('ResponseMetadata', None)

        await ctx.info(f'Successfully retrieved invoice unit: {invoice_unit_arn}')

        return format_response('success', {'invoice_unit': _normalize_timestamps(response)})

    except Exception as e:
        return await handle_aws_error(ctx, e, 'GetInvoiceUnit', 'Invoicing')


async def batch_get_invoice_profile(
    ctx: Context,
    account_ids: List[str],
) -> Dict[str, Any]:
    """Retrieve invoice receiver profiles for a set of linked accounts.

    Returns high-level invoice receiver information (legal name, address,
    email, issuer, tax registration number) for each requested account. The
    accounts must be linked accounts under the requester's management account
    organization.

    Args:
        ctx: The MCP context object.
        account_ids: The 12-digit account IDs to retrieve invoice profiles for
            (required, non-empty).

    Returns:
        Dict containing ``profiles``, or a standardized error response.
    """
    try:
        if not account_ids:
            return format_response(
                'error',
                {'message': 'account_ids must be a non-empty list for batch_get_invoice_profile.'},
            )

        client = _create_invoicing_client()
        response = client.batch_get_invoice_profile(AccountIds=account_ids)
        response.pop('ResponseMetadata', None)

        profiles = _normalize_timestamps(response.get('Profiles', []))

        await ctx.info(f'Successfully retrieved {len(profiles)} invoice profiles')

        return format_response('success', {'profiles': profiles})

    except Exception as e:
        return await handle_aws_error(ctx, e, 'BatchGetInvoiceProfile', 'Invoicing')
