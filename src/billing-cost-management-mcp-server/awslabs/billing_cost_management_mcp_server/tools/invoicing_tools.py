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

Provides MCP tool definitions for the AWS Invoicing API. The rich tool
description is the primary vehicle that gives the agent semantic context about
every request parameter and response field.
"""

from ..utilities.aws_service_base import handle_aws_error
from .invoicing_operations import list_invoice_summaries as _list_invoice_summaries
from fastmcp import Context, FastMCP
from typing import Any, Dict, Optional


invoicing_server = FastMCP(
    name='invoicing-tools',
    instructions='Tools for working with the AWS Invoicing API',
)


@invoicing_server.tool(
    name='list-invoice-summaries',
    description="""Lists AWS invoice summaries (invoice-level details, without line items) for an account or a single invoice.

WHEN TO USE THIS TOOL:
- "Show me my invoices for May 2026" or "what invoices were issued last quarter?"
- Look up an invoice's total, tax, due date, or issuing entity
- Reconcile invoice totals across a date range or find credit memos
This returns SUMMARY (header) level data only. For per-service line items, use Cost Explorer or the AWS Billing console.

SELECTOR (required — the tool picks one for you):
- account_id: 12-digit AWS account ID. Lists all invoices linked to that account. Auto-detected from your caller identity (STS GetCallerIdentity) when omitted.
- invoice_id: Retrieve the summary for one specific invoice instead of a whole account. Mutually exclusive with account_id.

TIME FILTER (optional — provide at most one):
- billing_period: A single calendar month as "YYYY-MM" (e.g. "2026-05"). Valid years: 2005-2050.
- start_date + end_date: An inclusive range as "YYYY-MM-DD" (or "YYYY-MM-DDTHH:MM:SS") in UTC, for multi-month queries. Both are required together and are mutually exclusive with billing_period.
- invoicing_entity: Filter by the AWS legal selling entity name (e.g. "Amazon Web Services, Inc.").

PAGINATION:
- Results are auto-paginated. max_results caps items per page (1-100); max_pages caps how many pages are fetched (default: all pages). The response `pagination` block reports total_results, pages_fetched, has_more, and next_token so you know whether more data exists.

RESPONSE — `data.invoice_summaries` is a list; each item contains:
- AccountId: The AWS account the invoice was issued to.
- InvoiceId: Unique AWS invoice identifier (reusable with other invoicing tools).
- InvoiceType: "INVOICE" (a standard charge) or "CREDIT_MEMO" (a credit/adjustment document).
- OriginalInvoiceId: For a CREDIT_MEMO, the InvoiceId of the invoice it adjusts; absent otherwise.
- PurchaseOrderNumber: Customer purchase-order number tied to the invoice, if any.
- IssuedDate / DueDate: ISO 8601 UTC timestamps (already converted from epoch) for when the invoice was issued and when payment is due.
- BillingPeriod: {Month, Year} the invoice covers.
- Entity: {InvoicingEntity} — the AWS legal entity that issued the invoice.
- BaseCurrencyAmount, PaymentCurrencyAmount, TaxCurrencyAmount: the invoice total expressed in three currencies — respectively the product-and-service currency, the customer's configured payment currency, and the tax currency. For single-currency accounts (e.g. USD-only) these coincide; when they differ, an amount carries CurrencyExchangeDetails describing the conversion applied. Each contains:
    - CurrencyCode: ISO 4217 currency code (3 letters, e.g. "USD").
    - TotalAmount / TotalAmountBeforeTax: invoice total with and without tax.
    - AmountBreakdown: { SubTotalAmount, Discounts, Taxes, Fees }, where Discounts/Taxes/Fees each have a TotalAmount plus a Breakdown[] list of {Description, Amount, Rate} line entries.
    - CurrencyExchangeDetails: { SourceCurrencyCode, TargetCurrencyCode, Rate }, present only when a currency conversion was applied.
IMPORTANT: All monetary amounts are strings to preserve decimal precision — parse them as decimals, never as floats.

EXAMPLES:
1. Current account, one month: {"billing_period": "2026-05"}
2. Explicit account + range: {"account_id": "123456789012", "start_date": "2026-01-01", "end_date": "2026-06-30"}
3. Single invoice: {"invoice_id": "1234567890"}
4. Filter by entity: {"billing_period": "2026-05", "invoicing_entity": "Amazon Web Services, Inc."}""",
)
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
    """List AWS invoice summaries by account or invoice, month or date range.

    Args:
        ctx: The MCP context object.
        account_id: 12-digit AWS account ID. Auto-detected via STS when omitted.
            Mutually exclusive with ``invoice_id``.
        invoice_id: Retrieve a single invoice's summary. Mutually exclusive with
            ``account_id``.
        billing_period: Single calendar month in ``YYYY-MM`` format. Mutually
            exclusive with ``start_date``/``end_date``.
        start_date: Inclusive range start (``YYYY-MM-DD`` UTC). Pair with
            ``end_date``.
        end_date: Inclusive range end (``YYYY-MM-DD`` UTC). Pair with
            ``start_date``.
        invoicing_entity: Filter by AWS legal selling entity name.
        max_results: Maximum results per page (1-100).
        next_token: Pagination token from a previous response.
        max_pages: Maximum pages to auto-paginate through (default: all).

    Returns:
        Dict containing the invoice summaries and pagination metadata.
    """
    try:
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
    except Exception as e:
        return await handle_aws_error(ctx, e, 'ListInvoiceSummaries', 'Invoicing')
