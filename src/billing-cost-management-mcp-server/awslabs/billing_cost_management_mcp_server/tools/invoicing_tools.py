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

"""AWS Invoicing tools for the AWS Billing and Cost Management MCP server.

Exposes a single ``invoicing`` tool that routes by ``operation`` so additional
AWS Invoicing APIs can be added later as new operations under one tool
(mirroring the cost-explorer and bcm-pricing-calculator tools). The rich tool
description is the primary vehicle that gives the agent semantic context about
every request parameter and response field.
"""

from ..utilities.aws_service_base import format_response
from .invoicing_operations import list_invoice_summaries as _list_invoice_summaries
from fastmcp import Context, FastMCP
from typing import Any, Dict, Optional


invoicing_server = FastMCP(
    name='invoicing-tools',
    instructions='Tools for working with the AWS Invoicing API',
)


async def _invoicing(
    ctx: Context,
    operation: str,
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
    """Route an AWS Invoicing ``operation`` to its handler.

    Kept separate from the FastMCP-decorated wrapper so the routing can be unit
    tested directly (decorated tools cannot be invoked as plain functions).

    Args:
        ctx: The MCP context object.
        operation: The invoicing operation to perform (e.g.
            ``"list_invoice_summaries"``).
        account_id: 12-digit AWS account ID. Auto-detected via STS when omitted.
        invoice_id: Retrieve a single invoice's summary.
        billing_period: Single calendar month in ``YYYY-MM`` format.
        start_date: Inclusive range start (``YYYY-MM-DD`` UTC).
        end_date: Inclusive range end (``YYYY-MM-DD`` UTC).
        invoicing_entity: Filter by AWS legal selling entity name.
        max_results: Maximum results per page (1-100).
        next_token: Pagination token from a previous response.
        max_pages: Maximum pages to auto-paginate through (default: all).

    Returns:
        The operation's response, or a standardized error for an unknown
        operation.
    """
    await ctx.info(f'Invoicing operation: {operation}')

    if operation == 'list_invoice_summaries':
        return await _list_invoice_summaries(
            ctx,
            account_id=account_id,
            invoice_id=invoice_id,
            billing_period=billing_period,
            start_date=start_date,
            end_date=end_date,
            invoicing_entity=invoicing_entity,
            max_results=max_results,
            next_token=next_token,
            max_pages=max_pages,
        )

    return format_response(
        'error',
        {
            'message': (
                f"Unsupported operation: '{operation}'. "
                'Supported operations: list_invoice_summaries.'
            )
        },
    )


@invoicing_server.tool(
    name='invoicing',
    description="""Access AWS Invoicing data. Choose an action with the required `operation` parameter; the remaining parameters apply to specific operations. Additional AWS Invoicing APIs are added here as new operations.

## OPERATIONS

1) list_invoice_summaries - invoice-level summaries (no line items) for an account or a single invoice
   Required: operation="list_invoice_summaries"
   Selector (choose one; the account is auto-detected if neither is given):
     - account_id: 12-digit AWS account ID; lists all invoices for that account. Auto-detected via STS GetCallerIdentity when omitted.
     - invoice_id: retrieve one specific invoice's summary. Mutually exclusive with account_id.
   Time filter (optional; provide at most one):
     - billing_period: a single calendar month "YYYY-MM" (e.g. "2026-05")
     - start_date + end_date: an inclusive UTC range "YYYY-MM-DD" (or "YYYY-MM-DDTHH:MM:SS"); required together and mutually exclusive with billing_period
     - invoicing_entity: filter by the AWS legal selling entity (seller of record) name. Examples: "Amazon Web Services, Inc." (US), "Amazon Web Services EMEA SARL" (Europe/Middle East/Africa), "Amazon Web Services Australia Pty Ltd" (Australia), "Amazon Web Services Japan G.K." (Japan).
   Pagination: max_results caps items per page (1-100); max_pages caps pages fetched (default: all). The response `pagination` block reports total_results, pages_fetched, has_more, and next_token.
   Returns: `data.invoice_summaries`, a list where each item contains:
     - AccountId; InvoiceId; InvoiceType ("INVOICE" or "CREDIT_MEMO"); OriginalInvoiceId (the invoice a CREDIT_MEMO adjusts); PurchaseOrderNumber
     - IssuedDate / DueDate: ISO 8601 UTC timestamps (converted from epoch)
     - BillingPeriod {Month, Year}; Entity {InvoicingEntity}
     - BaseCurrencyAmount, PaymentCurrencyAmount, TaxCurrencyAmount: the invoice total in the product-and-service currency, the customer's configured payment currency, and the tax currency respectively. For single-currency accounts (e.g. USD-only) these coincide; when they differ, an amount carries CurrencyExchangeDetails describing the conversion. Each contains CurrencyCode (ISO 4217), TotalAmount, TotalAmountBeforeTax, AmountBreakdown { SubTotalAmount, Discounts, Taxes, Fees (each a TotalAmount plus a Breakdown[] of {Description, Amount, Rate}) }, and CurrencyExchangeDetails { SourceCurrencyCode, TargetCurrencyCode, Rate }.
   IMPORTANT: monetary amounts are strings to preserve decimal precision — parse as decimals, never floats.

EXAMPLES
- {"operation": "list_invoice_summaries", "billing_period": "2026-05"}
- {"operation": "list_invoice_summaries", "account_id": "123456789012", "start_date": "2026-01-01", "end_date": "2026-06-30"}
- {"operation": "list_invoice_summaries", "invoice_id": "1234567890"}
- {"operation": "list_invoice_summaries", "billing_period": "2026-05", "invoicing_entity": "Amazon Web Services EMEA SARL"}""",
)
async def invoicing(
    ctx: Context,
    operation: str,
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
    """FastMCP wrapper for AWS Invoicing operations.

    Thin wrapper so the routing logic in ``_invoicing`` can be unit tested
    directly (FastMCP-decorated tools cannot be invoked as plain functions).

    Args:
        ctx: The MCP context object.
        operation: The invoicing operation to perform (e.g.
            ``"list_invoice_summaries"``).
        account_id: 12-digit AWS account ID (auto-detected via STS when omitted).
        invoice_id: Retrieve a single invoice's summary.
        billing_period: Single calendar month in ``YYYY-MM`` format.
        start_date: Inclusive range start (``YYYY-MM-DD`` UTC).
        end_date: Inclusive range end (``YYYY-MM-DD`` UTC).
        invoicing_entity: Filter by AWS legal selling entity name.
        max_results: Maximum results per page (1-100).
        next_token: Pagination token from a previous response.
        max_pages: Maximum pages to auto-paginate through (default: all).

    Returns:
        Dict containing the operation result.
    """
    return await _invoicing(
        ctx,
        operation,
        account_id=account_id,
        invoice_id=invoice_id,
        billing_period=billing_period,
        start_date=start_date,
        end_date=end_date,
        invoicing_entity=invoicing_entity,
        max_results=max_results,
        next_token=next_token,
        max_pages=max_pages,
    )
