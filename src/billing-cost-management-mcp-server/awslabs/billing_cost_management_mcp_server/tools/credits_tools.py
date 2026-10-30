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

"""AWS credits tools for the AWS Billing and Cost Management MCP server.

Exposes a single ``credits`` tool that routes by ``operation`` so additional AWS
credits APIs can be added later as new operations under one tool (mirroring the
cost-explorer and invoicing tools). The rich tool description is the primary
vehicle that gives the agent semantic context about every request parameter and
response field.
"""

from ..utilities.aws_service_base import format_response
from ..utilities.constants import PAGINATION_LIMIT_TEXT
from .credits_operations import get_credit_allocation_history as _get_credit_allocation_history
from .credits_operations import get_credits as _get_credits
from fastmcp import Context, FastMCP
from typing import Any, Dict, Optional


credits_server = FastMCP(
    name='credits-tools',
    instructions='Tools for working with AWS credits via the AWS Billing API',
)


async def _credits(
    ctx: Context,
    operation: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    billing_period: Optional[str] = None,
    account_id: Optional[str] = None,
    payer_account_flag: Optional[bool] = None,
    credit_id: Optional[Any] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Route an AWS credits ``operation`` to its handler.

    Kept separate from the FastMCP-decorated wrapper so the routing can be unit
    tested directly (decorated tools cannot be invoked as plain functions).

    Args:
        ctx: The MCP context object.
        operation: The credits operation to perform (e.g. ``"get_credits"``).
        start_date: Inclusive range start in ``YYYY-MM-DD`` UTC format.
        end_date: Inclusive range end in ``YYYY-MM-DD`` UTC format.
        billing_period: Single calendar month in ``YYYY-MM`` format (allocation
            history only). Mutually exclusive with start_date/end_date.
        account_id: 12-digit AWS account ID. Auto-detected via STS when omitted.
        payer_account_flag: Query at the payer-account level (get_credits only).
        credit_id: Restrict the ledger to one credit (allocation history only).
        max_items: Most ledger rows to return (allocation history only; get_credits
            ignores it). None fetches every page.
        next_token: Pagination token from a previous allocation-history response
            (get_credits ignores it).

    Returns:
        The operation's response, or a standardized error for an unknown
        operation.
    """
    await ctx.info(f'Credits operation: {operation}')

    if operation == 'get_credits':
        return await _get_credits(
            ctx,
            start_date=start_date,
            end_date=end_date,
            account_id=account_id,
            payer_account_flag=payer_account_flag,
        )

    if operation == 'get_credit_allocation_history':
        return await _get_credit_allocation_history(
            ctx,
            start_date=start_date,
            end_date=end_date,
            billing_period=billing_period,
            account_id=account_id,
            credit_id=credit_id,
            max_items=max_items,
            next_token=next_token,
        )

    return format_response(
        'error',
        {
            'message': (
                f"Unsupported operation: '{operation}'. Supported operations: "
                'get_credits, get_credit_allocation_history.'
            )
        },
    )


@credits_server.tool(
    name='credits',
    description="""Access AWS credits data: balance, expiration, product applicability, sharing configuration, and the per-service allocation ledger. Choose an action with the required `operation` parameter; the remaining parameters apply to specific operations.

## OPERATIONS

1) get_credits - the credits objects held by an account: balance, expiration, applicability and sharing
   Required: operation="get_credits", start_date. start_date is accepted only within one year before today; a request reaching further back is limited to that boundary.
   Optional:
     - end_date: inclusive range end. A future end is limited to now; check `data.time_range`. Omit it to send no end date: the service then applies no upper bound, so the result also includes credits that start after today.
     - account_id: 12-digit AWS account ID. Auto-detected via STS GetCallerIdentity when omitted.
     - payer_account_flag: set true only when the caller is the management account (the payer account of a consolidated billing family). When true and the caller is the management account, the response aggregates credits across the entire family; use this for "credits across my organization" questions. When false, omitted, or when the caller is a member account, the response covers only the account in `account_id`. Setting it true from a member account does NOT error: the call succeeds and returns just that account's credits, so an empty or small result must not be read as the organization having no credits, only as the caller not being the management account.
   Not paginated: the API returns the complete set in one call, and max_items / next_token are ignored.
   Returns: `data.credits`, a list where each item contains:
     - creditId; accountId; creditType; description
     - initialAmount, remainingAmount, estimatedAmount: each {currencyCode, currencyAmount}. remainingAmount is the unused balance. It is not zeroed when a credit expires: an expired credit can still show its full remainingAmount. estimatedAmount is the estimated remaining balance including in-flight (open) bills not yet finalized, so the two can differ. For "how much credit do I have left", omit end_date, then total remainingAmount only over credits whose validityStatus is ACTIVE and whose creditStatus is not DISABLED, per currencyCode. Report the balance of EXPIRED credits separately as expired (a credit that expired during the current month can still be applied to that month's bill until it is finalized), and NOT_YET_ACTIVE credits separately as future credits with their startDate. Leave UNKNOWN credits out of the total and say that their dates could not be read. Name estimatedAmount only alongside what it includes.
     - validityStatus (ACTIVE|EXPIRED|NOT_YET_ACTIVE|UNKNOWN): added by this tool from startDate and endDate, evaluated at `data.validity_evaluated_at`. EXPIRED means endDate has been reached; NOT_YET_ACTIVE means startDate is still in the future; ACTIVE means startDate has been reached and endDate has not; UNKNOWN means a date needed to decide was present but could not be read. A credit with no endDate does not expire and is ACTIVE once its startDate is reached. An endDate in 2099 or later (for example 2099-12-31) means the credit effectively does not expire: report it as not expiring, not as expiring in that year. The response can include credits that expired before today. It also includes credits that start after today when end_date is omitted, because the service then applies no upper bound.
     - startDate, endDate, exhaustDate: dates (converted to UTC ISO 8601). endDate is the expiration date, except when it is missing or in 2099 or later (see validityStatus). exhaustDate is the date the balance reached zero, a past event and NOT a forecast. Do not report exhaustDate as an expiration, and do not present it as a projection of when credit will run out.
     - applicableProductNames: services the credit can apply to. An empty list means no product restriction was surfaced, not that the credit applies to nothing.
     - creditStatus (ENABLED|DISABLED): whether the credit participates in billing runs; a DISABLED credit is not applied. It is not an expiration indicator: expired credits still read ENABLED, so use validityStatus for expiry.
     - applicationType (BEFORE_CROSS_SERVICE_DISCOUNTS|AFTER_DISCOUNTS); purchaseTypeApplications: restricts which purchase types the credit applies to. Null or omitted means all purchase types, not none.
     - creditSharingType (DEFAULT|DISABLED|CUSTOM|COST_CATEGORY_RULE); shareableAccounts; accountHasCreditSharingEnabled; costCategoryArn; ruleName
     - creditConsoleVisibility
   Also returns `data.time_range`, which must be read before stating a period (see below), and `data.validity_evaluated_at`, the UTC time validityStatus was computed at.

2) get_credit_allocation_history - the ledger of how credits were applied, per service per billing month
   Required: operation="get_credit_allocation_history", and a window (choose one form):
     - billing_period: a single calendar month "YYYY-MM" (e.g. "2026-06"), expanded to cover that whole month. PREFER THIS for single-month questions such as "how were my credits applied in June 2026" so no date arithmetic is needed.
     - start_date + end_date: an inclusive range, required together and mutually exclusive with billing_period.
   Optional:
     - account_id: as above.
     - credit_id: restrict the ledger to one credit. Pass the `creditId` string from get_credits unchanged; the tool converts it to the numeric type this API requires.
     - max_items: total ledger rows returned. If it is omitted, the tool fetches every page for """
    + PAGINATION_LIMIT_TEXT
    + """, then returns a partial result. Pass it, or narrow the window (billing_period, credit_id), when the ledger can be large.
     - next_token: the `pagination.next_token` from a previous allocation-history response, to continue where it stopped. Send every other parameter unchanged, and continue within the same billing month: the token is a position in a newest-first list of bills, so once a new month's bill appears the positions shift. After a month boundary, call again without next_token.
   Returns: `data.credit_allocation_history`, sorted by billingMonth descending, a list where each item contains creditId, creditAmount {currencyCode, currencyAmount} where a negative value means the credit reduced that bill, description, accountId, appliedServiceName, billingMonth (YYYY-MM), and isEstimatedBill (true when the entry applied to an in-flight bill that is not yet finalized).
   Also returns `data.completeness`, `data.time_range` and `data.pagination`, all of which must be read before summarizing (see below).

## READING THE RESPONSE CORRECTLY

- MONETARY AMOUNTS ARE STRINGS to preserve decimal precision. Parse as decimals, never floats. Report them exactly as returned.
- CHECK `data.completeness` BEFORE TOTALLING. When `partial_results` is true, some months failed and are listed in `failed_months`. Any sum over the returned rows is incomplete: report the total AND name the months missing from it. Never present a partial total as the full picture.
- CHECK `complete_dataset` BEFORE TOTALLING THE LEDGER. When it is false (with a warning), the call stopped at max_items or a page failed, so any sum over the returned rows is partial. Call again with a larger max_items, continue with next_token, or state in the answer that the result is partial. `completeness` and every count cover only the rows in that response; a continuation call does not repeat earlier rows.
- CHECK `data.time_range` BEFORE STATING A PERIOD. Both operations limit a window they cannot serve, and a future end_date is limited to now. The limits differ: get_credit_allocation_history caps the range at 24 months, while get_credits caps the lookback at one year before today. When `limited_from_request` is true, the answer covers `start_date` to `end_date`, NOT `requested_start_date` to `requested_end_date`. Say which window was actually used. A window with no answerable overlap at all, entirely in the future or entirely before the lookback limit, returns an error rather than a limited result.
- Dates go in as YYYY-MM-DD. Never compute an epoch timestamp yourself; the tool converts.
- A LARGE LEDGER IS OFFLOADED TO SQL. When the response carries `data_stored: true` and a `table_name` instead of an inline list, query it with the session-sql tool. Nested values are stored as JSON text, so aggregate money with json_extract, not directly: `SELECT appliedServiceName, SUM(CAST(json_extract(creditAmount, '$.currencyAmount') AS REAL)) FROM <table_name> GROUP BY appliedServiceName`. A bare `SUM(creditAmount)` returns 0, silently. The `time_range` and `completeness` blocks and the pagination fields (`complete_dataset`, `has_more`, `next_token`, `items_returned`) are still present alongside the table reference.
- A LARGE CREDIT LIST IS OFFLOADED THE SAME WAY, with `table_name` queried through the session-sql tool. validityStatus, creditStatus and the dates are plain columns, so filter on them before totalling: `SELECT json_extract(remainingAmount, '$.currencyCode') AS currency, SUM(CAST(json_extract(remainingAmount, '$.currencyAmount') AS REAL)) FROM <table_name> WHERE validityStatus = 'ACTIVE' AND COALESCE(creditStatus, 'ENABLED') != 'DISABLED' GROUP BY currency`.
- An empty result is a real answer. Zero allocation rows for a month means no credits were applied in that month, which is different from having no credits.
- An access_denied error means the caller's IAM policy is missing the named permission. It does NOT mean the account has no credits, and it must not be reported as an absence of data or worked around with Cost Explorer.

## CHOOSING BETWEEN THIS TOOL AND COST EXPLORER

get_credit_allocation_history is authoritative for "how were my credits applied". Cost Explorer's RECORD_TYPE=Credit reports the aggregated effect of credits on billed cost, which is a different figure: one credit split across several services in a month appears as multiple rows here and as one adjustment per service there. Cost Explorer also cannot return credit-level metadata such as source, expiration or sharing status. Prefer this tool for the ledger, and when reconciling against a Cost Explorer figure, state which cost metric was used and surface both numbers rather than forcing them to agree.

EXAMPLES
- {"operation": "get_credits", "start_date": "2026-01-01"}
- {"operation": "get_credits", "start_date": "2026-01-01", "end_date": "2026-06-30", "payer_account_flag": true}
- {"operation": "get_credit_allocation_history", "billing_period": "2026-06"}
- {"operation": "get_credit_allocation_history", "start_date": "2026-06-01", "end_date": "2026-06-30"}
- {"operation": "get_credit_allocation_history", "start_date": "2026-01-01", "end_date": "2026-06-30", "credit_id": "1234567890"}""",
)
async def credits(
    ctx: Context,
    operation: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    billing_period: Optional[str] = None,
    account_id: Optional[str] = None,
    payer_account_flag: Optional[bool] = None,
    credit_id: Optional[Any] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """FastMCP wrapper for AWS credits operations.

    Thin wrapper so the routing logic in ``_credits`` can be unit tested
    directly (FastMCP-decorated tools cannot be invoked as plain functions).

    Args:
        ctx: The MCP context object.
        operation: The credits operation to perform (e.g. ``"get_credits"``).
        start_date: Inclusive range start in ``YYYY-MM-DD`` UTC format.
        end_date: Inclusive range end in ``YYYY-MM-DD`` UTC format.
        billing_period: Single calendar month in ``YYYY-MM`` format (allocation
            history only). Mutually exclusive with start_date/end_date.
        account_id: 12-digit AWS account ID. Auto-detected via STS when omitted.
        payer_account_flag: Query at the payer-account level (get_credits only).
        credit_id: Restrict the ledger to one credit (allocation history only).
        max_items: Most ledger rows to return (allocation history only; get_credits
            ignores it). None fetches every page.
        next_token: Pagination token from a previous allocation-history response
            (get_credits ignores it).

    Returns:
        Dict containing the operation result.
    """
    return await _credits(
        ctx,
        operation,
        start_date=start_date,
        end_date=end_date,
        billing_period=billing_period,
        account_id=account_id,
        payer_account_flag=payer_account_flag,
        credit_id=credit_id,
        max_items=max_items,
        next_token=next_token,
    )
