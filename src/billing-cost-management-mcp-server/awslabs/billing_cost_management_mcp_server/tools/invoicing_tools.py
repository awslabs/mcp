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
from typing import Any, Dict, Literal, Optional


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
    receiver_role: Optional[Literal['SELLER', 'RESELLER', 'BUYER']] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
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
        start_date: Range start (``YYYY-MM-DD`` UTC, i.e. 00:00:00 that day).
        end_date: Range end (``YYYY-MM-DD`` UTC, i.e. 00:00:00 that day, so use
            the day after the last one you want).
        invoicing_entity: Filter by AWS legal selling entity name.
        receiver_role: Restrict to invoices where the selected account holds
            this role (account queries only), raising the date-range cap from one
            month to less than five years.
        max_items: Most items to return (list operation only). None fetches every page.
        next_token: Pagination token from a previous response (list operation only).

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
            receiver_role=receiver_role,
            max_items=max_items,
            next_token=next_token,
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
     - account_id: 12-digit AWS account ID; lists the invoices billed to that account. This includes invoices issued to invoice-unit receivers billed from it, whose rows carry a different AccountId, so the result is not necessarily "this account's own invoices". Auto-detected via STS GetCallerIdentity when omitted.
     - invoice_id: retrieve one specific invoice's summary. Mutually exclusive with account_id, and cannot be combined with receiver_role.
   Time filter — REQUIRED when selecting by account_id, and IGNORED for invoice_id: the service returns that invoice whatever window is passed, so a time filter cannot narrow an invoice_id lookup and there is no reason to send one. When selecting by account_id, provide exactly one:
     - billing_period: a single calendar month "YYYY-MM" (e.g. "2026-05")
     - start_date + end_date: a UTC range "YYYY-MM-DD" (or "YYYY-MM-DDTHH:MM:SS"); required together and mutually exclusive with billing_period. A date-only bound means 00:00:00 UTC, so end_date must be the day AFTER the last day you want: all of June 2026 is start_date "2026-06-01" with end_date "2026-07-01". Using "2026-06-30" silently drops invoices issued during June 30.
   IMPORTANT — ONE MONTH MAXIMUM per call. A start_date/end_date range may span at most the number of days in the START date's month (31 from a January start, 28 from a February start). A longer range is rejected by this tool before any AWS call: status "error", error_type "validation_error", with `data.suggested_date_ranges` naming the exact per-month calls to make. Calendar alignment is NOT required: "2026-05-14" to "2026-06-13" is valid. For a longer period issue ONE CALL PER MONTH and combine the results yourself — never widen the range — and de-duplicate on InvoiceId, since an invoice issued exactly on a boundary midnight can appear in two adjacent sub-ranges. Setting receiver_role raises this cap to less than five years (an exact five-year span is rejected by this tool before any AWS call), but it also changes which invoices come back, so it is not a way to widen an unrestricted query.
   NOTE — the two time filters are not interchangeable: billing_period selects by BILLING MONTH, start_date/end_date select by ISSUED DATE. Pick whichever the question asks for, and keep using that same one when splitting a multi-month request.
   Other filters (optional):
     - invoicing_entity: filter by the AWS legal selling entity (seller of record) name. The name must match EXACTLY, case included: a lowercased or misspelled name is rejected with "Input invoice entity is not supported", while a correctly spelled entity that does not bill this account returns an empty list rather than an error. Examples: "Amazon Web Services, Inc." (US), "Amazon Web Services EMEA SARL" (Europe/Middle East/Africa), "Amazon Web Services Australia Pty Ltd" (Australia), "Amazon Web Services Japan G.K." (Japan).
     - receiver_role: "SELLER", "RESELLER" or "BUYER" — restrict to invoices where the selected account holds that role. ACCOUNT QUERIES ONLY: it cannot be combined with invoice_id, and this tool rejects that combination locally. "BUYER" is the ordinary customer role; "SELLER" and "RESELLER" return an empty list for an account that holds neither, which is not an error and does not mean the account has no invoices. It has two effects beyond filtering. It raises the start_date/end_date cap from one month to LESS THAN five years (an exact five-year span is rejected by this tool before any AWS call). And it is the only way estimated invoices are returned — see "Estimated invoices" below. IMPORTANT — it is NOT a superset of the same query without it: invoices issued to invoice-unit receivers billed from the selected account can be absent from a receiver_role result. To cover both, run the query without receiver_role as well and de-duplicate on InvoiceId.
   Estimated invoices (returned only with receiver_role): an estimate's InvoiceId is prefixed "Estimate-" and its IssuedDate is the epoch (1970-01-01), meaning unset. THE PREFIX IS THE ONLY MARKER: an estimate reports InvoiceType "INVOICE", BillType "ANNIVERSARY" and TaxAuthorityStatus "ISSUED", exactly as an issued invoice does. Estimates are NOT limited to billing periods that are still open — a closed month can return its issued invoices and its estimates together, with different amounts. So NEVER add an estimate to the issued invoices of the same month: once that month's invoice exists, report the invoice and not the estimate. Never report the epoch IssuedDate as an issue date.
   Pagination:
     - max_items: total invoice summaries returned. Omit it to fetch every page (no limit). Pass it, or narrow the filters, for queries that can be large.
     - next_token: the `pagination.next_token` from a previous response, to continue where it stopped. Send every other parameter unchanged.
     - A partial result has `complete_dataset: false` and a warning. Call again with a larger max_items, continue with next_token, or state in the answer that the result is partial. `pagination.items_returned` counts only this response, and a continuation call does not repeat earlier items.
   Returns `data.selector` and `data.invoice_summaries`.
   `data.selector` — the account or invoice this result was read for, as {type: "ACCOUNT_ID" | "INVOICE_ID", value, auto_detected}. `auto_detected` is true when account_id was omitted and resolved from the caller's identity. Take the queried account from here, never from a row's AccountId: an account query also returns invoices issued to invoice-unit receivers billed from that account, and those rows carry a different AccountId.
   `data.invoice_summaries` — a list where each item contains:
     - AccountId (the account the invoice was issued to, which need not be the account queried); InvoiceId; CommercialInvoiceId; PurchaseOrderNumber
     - InvoiceType ("INVOICE", "CREDIT_MEMO" or "PAYMENT_RECEIPT"); OriginalInvoiceId (the invoice a CREDIT_MEMO adjusts); BillType ("ANNIVERSARY", "PURCHASE" or "REFUND"); InvoiceFrequency ("ONE_TIME" or "RECURRING")
     - IssuedDate / DueDate: ISO 8601 UTC timestamps (converted from epoch)
     - BillingPeriod {Month, Year}; Entity {InvoicingEntity, BillingEntity ("AWS" or "AWS_MARKETPLACE")}
     - ReceiverRole: the role AccountId holds for this invoice. BillSourceAccounts and BillSourceAccountsTotalCount: the accounts the invoice was billed from, which is how a row issued to an invoice-unit receiver names the account that paid for it.
     - EinvoiceDeliveryStatus ("DELIVERED" or "NOT_DELIVERED"); TaxAuthorityStatus ("ISSUED" or "CANCELLED")
     - BaseCurrencyAmount, PaymentCurrencyAmount, TaxCurrencyAmount: the invoice total in the product-and-service currency, the customer's configured payment currency, and the tax currency respectively. For single-currency accounts (e.g. USD-only) these coincide; when they differ, an amount carries CurrencyExchangeDetails describing the conversion. Each contains CurrencyCode (ISO 4217), TotalAmount, TotalAmountBeforeTax, AmountBreakdown { SubTotalAmount, Discounts, Taxes, Fees (each a TotalAmount plus a Breakdown[] of {Description, Amount, Rate}) }, and CurrencyExchangeDetails { SourceCurrencyCode, TargetCurrencyCode, Rate }.
   Fields the API returns but this list does not name are passed through unchanged.
   IMPORTANT: monetary amounts are strings to preserve decimal precision — parse as decimals, never floats.
   IMPORTANT — InvoiceType decides whether a row is money owed. Only "INVOICE" is, excluding rows whose InvoiceId starts with "Estimate-" (those report InvoiceType "INVOICE" but are estimates, not charges — see receiver_role above). A "CREDIT_MEMO" is a credit against the invoice named in OriginalInvoiceId, and its TotalAmount is reported POSITIVE, so adding it to a total overstates what is due — subtract it, or report it separately. A CREDIT_MEMO can also carry a DueDate, so filtering by due date does not exclude it. A "PAYMENT_RECEIPT" records a payment rather than a charge and belongs in no amount-due total either. Check InvoiceType before summing anything.

EXAMPLES
- {"operation": "list_invoice_summaries", "billing_period": "2026-05"}
- {"operation": "list_invoice_summaries", "account_id": "123456789012", "start_date": "2026-06-01", "end_date": "2026-07-01"}
- {"operation": "list_invoice_summaries", "invoice_id": "1234567890"}
- {"operation": "list_invoice_summaries", "billing_period": "2026-05", "invoicing_entity": "Amazon Web Services EMEA SARL"}
- "the last 3 billing months" -> three calls, one billing_period each: "2026-06", then "2026-07", then "2026-08"
- "invoices issued Jan 15 through Mar 10" -> three calls by issued date, split on month boundaries, end_date one day past Mar 10: 2026-01-15/2026-02-01, then 2026-02-01/2026-03-01, then 2026-03-01/2026-03-11""",
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
    receiver_role: Optional[Literal['SELLER', 'RESELLER', 'BUYER']] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
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
        start_date: Range start (``YYYY-MM-DD`` UTC, i.e. 00:00:00 that day).
        end_date: Range end (``YYYY-MM-DD`` UTC, i.e. 00:00:00 that day, so use
            the day after the last one you want).
        invoicing_entity: Filter by AWS legal selling entity name.
        receiver_role: Restrict to invoices where the selected account holds
            this role (account queries only), raising the date-range cap from one
            month to less than five years.
        max_items: Most items to return (list operation only). None fetches every page.
        next_token: Pagination token from a previous response (list operation only).

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
        receiver_role=receiver_role,
        max_items=max_items,
        next_token=next_token,
    )
