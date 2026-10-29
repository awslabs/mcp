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

"""Business Support tools for the AWS Billing and Cost Management MCP server.

Exposes a single ``business-support`` tool that routes by ``operation`` across
the Business Support APIs, so the per-account charge breakdown and the
subscription contract history are reached through one tool rather than two
(mirroring the enterprise-support, credits and cost-explorer tools). The rich
tool description is the primary vehicle that gives the agent semantic context
about every request parameter and response field.
"""

from ..utilities.aws_service_base import format_response
from .business_support_operations import list_account_charges as _list_account_charges
from .business_support_operations import list_subscription_history as _list_subscription_history
from fastmcp import Context, FastMCP
from typing import Any, Dict, Optional


business_support_server = FastMCP(
    name='business-support-tools',
    instructions='Tools for working with AWS Business Support charges via the AWS Billing API',
)


async def _business_support(
    ctx: Context,
    operation: str,
    billing_month: Optional[str] = None,
    account_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Route a Business Support ``operation`` to its handler.

    Kept separate from the FastMCP-decorated wrapper so the routing can be unit
    tested directly (decorated tools cannot be invoked as plain functions).

    Args:
        ctx: The MCP context object.
        operation: The Business Support operation to perform (for example
            ``"list_account_charges"``).
        billing_month: Single calendar month in ``YYYY-MM`` format. Required for
            list_account_charges, optional for list_subscription_history.
        account_id: 12-digit account id to filter to (both operations).
        start_date: Lower timestamp bound (list_subscription_history only).
        end_date: Upper timestamp bound (list_subscription_history only).
        max_items: Most items to return across pages.
        next_token: Pagination token from a previous response.

    Returns:
        The operation's response, or a standardized error for an unknown
        operation.
    """
    await ctx.info(f'Business Support operation: {operation}')

    if operation == 'list_account_charges':
        return await _list_account_charges(
            ctx,
            billing_month=billing_month,
            account_id=account_id,
            max_items=max_items,
            next_token=next_token,
        )

    if operation == 'list_subscription_history':
        return await _list_subscription_history(
            ctx,
            billing_month=billing_month,
            account_id=account_id,
            start_date=start_date,
            end_date=end_date,
            max_items=max_items,
            next_token=next_token,
        )

    return format_response(
        'error',
        {
            'message': (
                f"Unsupported operation: '{operation}'. Supported operations: "
                'list_account_charges, list_subscription_history.'
            )
        },
        error_type='invalid_operation',
        operation=operation,
        service='Billing',
    )


@business_support_server.tool(
    name='business-support',
    description="""Access AWS Business Support charge data: the per-account Business Support charge for a billing period together with the Support-eligible spend it was derived from, and the Business Support subscription contract history showing which accounts were subscribed and when. Choose an action with the required `operation` parameter.

## OPERATIONS

1) list_account_charges - the per-account Business Support charge breakdown for one billing period
   Required: operation="list_account_charges", billing_month.
   billing_month is a single calendar month "YYYY-MM" (e.g. "2026-06") and it selects the billing period the answer covers. It cannot be earlier than 2024-01, the oldest month with Business Support data. You can request the current month, in which case the charges will be estimated (isEstimated=true in the response). Future months (after the current month) are rejected. Both bounds are rejected locally without spending a call.
   Optional:
     - account_id: a 12-digit AWS account number that filters to ONE account inside the payer's Support profile. Omit it to get every account, which is what "break down my Business Support charge by account" asks for. Omitting it sends no account filter at all and the tool never infers one from the caller credentials, so never report that a filter was applied when you left it out. An account id that appears in an error message is the caller's payer account, not a filter that was used.
     - max_items: total rows to return across pages. Omit it to fetch every page (no limit). next_token: resume from a previous response.
   Paginated: the tool follows nextToken for you.
   Returns: `data.account_charges`, a list where each item contains:
     - accountId: the 12-digit AWS account number this charge row belongs to.
     - supportPlanName: the Support plan the account was on for the period: AWSSupportBusiness (Business), AWSSupportDeveloper (Developer) or AWSSupportEssential (Basic). Report it verbatim.
     - supportDiscount: present only when a discount applies. An object with discountAmount (negative, representing a reduction in the charge), discountPercentage (a decimal such as "0.12" for 12%), discountType (Distributor_Discount or SPP_Discount) and discountSource.
     - totalCharge: this account's Business Support charge for the billing period.
     - totalUsageBasis: the Support-eligible spend the charge was calculated from.
     - supportEligibleSpendByService: per-service breakdown, each with contributingService, itemType ("Usage"), chargeAmount (the Support-eligible spend for that service), currency (ISO 4217, e.g. "USD") and an optional description. This decomposes totalUsageBasis; do not add it on top.
     - tierCharges: the incremental tier charges that make up totalCharge, each with tierDescription, tierRate (the percentage applied within the tier), usageSlice (the spend that falls in the tier), tierCharge, and optional chargePeriodStartDate/chargePeriodEndDate. These are bracketed, not a flat rate on total spend, so never describe one tier's rate as applying to the account's whole eligible spend.
   Also returns the profile-wide figures the API reports alongside the rows, carried through verbatim in `data`: accountCount, billingMonth, isEstimated, totalSupportCharge and totalSupportEligibleSpend. And `data.pagination`, which must be read before summarizing (see below).

2) list_subscription_history - the Business Support subscription contract history
   Required: operation="list_subscription_history". Everything else is optional.
   Optional:
     - billing_month: a single calendar month "YYYY-MM" to scope the history to contracts in effect that month. When omitted, the API defaults to the CURRENT month (UTC), not the full history; to cover several months pass start_date/end_date. A month with no Business Support data returns a not_found error, not an empty list. Same 2024-01 and future-month bounds as above, applied only when supplied.
     - account_id: a 12-digit AWS account number to filter to one account. Same omit-means-no-filter rule as above.
     - start_date, end_date: ISO-8601 dates or timestamps bounding the contract window (e.g. "2025-01-01" or "2025-01-01T00:00:00Z"). They are validated locally (format, and start_date on or before end_date) and then sent as given.
     - max_items, next_token: paging, as above.
   Paginated: the tool follows nextToken for you.
   Returns: `data.subscription_contracts`, a list where each item contains:
     - accountId: the account the contract belongs to.
     - planName: the Support plan for the contract: AWSSupportBusiness (Business), AWSSupportDeveloper (Developer) or AWSSupportEssential (Basic). Report it verbatim.
     - contractStartDate, contractEndDate: the contract period as recorded for that billing month (normalized from timestamps). It can be just that month, giving one row per month, and a contract spanning several months can appear in each month's result. When combining months, drop duplicate rows and merge back-to-back rows for the same account and plan before reporting a contract term. The API model marks both as required.
   Also returns `data.pagination`.

## READING THE RESPONSE CORRECTLY

- MONETARY AMOUNTS ARE STRINGS to preserve decimal precision. Parse as decimals, never floats. Report them exactly as returned.
- CHECK `isEstimated` BEFORE PRESENTING A FIGURE AS FINAL. true means the Business Support charge is still estimated because the bill is not finalized and can still change (this is normal for the current month); false means finalized. Always state which.
- PER-ACCOUNT VERSUS PROFILE TOTAL. totalCharge is one account's charge; totalSupportCharge is the total across every account in the profile; accountCount is how many accounts the profile holds. Name which one you are reporting and never present a single account's totalCharge as the profile total.
- THE SPEND BREAKDOWN DECOMPOSES THE BASIS, it does not add to it. supportEligibleSpendByService sums to totalUsageBasis for that account; totalSupportEligibleSpend is the profile-wide equivalent.
- TIER CHARGES ARE INCREMENTAL, not a flat rate on total spend. Report each tier charge as returned rather than multiplying a single rate across the whole eligible spend.
- THIS TOOL NEVER RESOLVES AN ACCOUNT ID FROM CREDENTIALS, unlike some other billing tools. When account_id is omitted no account filter is sent and the results cover every account in the Support profile. NEVER state that the tool auto-detected, inferred or looked up the caller's account. An account id inside an error message is the payer the credentials belong to, reported by AWS, not a filter this tool applied.
- CHECK `data.pagination` BEFORE TOTALLING ROWS. When `has_more` is true the walk stopped early, usually because max_items was reached, so any sum over the returned rows is partial. Report the total AND say it covers `items_returned` rows with more available. `complete_dataset` true means every row was fetched.
- ONE BILLING PERIOD PER list_account_charges CALL. There is no date range on it. Answering "how did my Business Support charge change since March" means one call per billing period, then comparing the results. Only list_subscription_history takes a start_date/end_date window, and that window describes contract terms, not charges.
- An access_denied error means the caller's IAM policy is missing the named permission, or the caller is not the payer account authorized for the Support profile. It does NOT mean the account has no Business Support charges, and a linked account cannot read these operations at all.

## SCOPE BOUNDARY

This tool reports what Business Support was charged, the spend it was derived from, and the subscription contracts behind it. It does not explain Business Support pricing policy. For questions about why Support is priced a particular way, point the customer to the public AWS Support plan FAQ at https://aws.amazon.com/premiumsupport/faqs/ rather than speculating. Enterprise Support charges belong to the enterprise-support tool; questions about the overall bill, general discounts, or credits belong to the cost-explorer, invoicing and credits tools respectively.

EXAMPLES
- {"operation": "list_account_charges", "billing_month": "2026-06"}
- {"operation": "list_account_charges", "billing_month": "2026-06", "account_id": "111122223333"}
- {"operation": "list_subscription_history"}  (current month only)
- {"operation": "list_subscription_history", "start_date": "2025-01-01", "end_date": "2026-06-30"}
- {"operation": "list_subscription_history", "account_id": "111122223333", "billing_month": "2026-06"}""",
)
async def business_support(
    ctx: Context,
    operation: str,
    billing_month: Optional[str] = None,
    account_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """FastMCP wrapper for Business Support operations.

    Thin wrapper so the routing logic in ``_business_support`` can be unit tested
    directly (FastMCP-decorated tools cannot be invoked as plain functions).

    Args:
        ctx: The MCP context object.
        operation: The Business Support operation to perform (for example
            ``"list_account_charges"``).
        billing_month: Single calendar month in ``YYYY-MM`` format. Required for
            list_account_charges, optional for list_subscription_history.
        account_id: 12-digit account id to filter to (both operations).
        start_date: Lower timestamp bound (list_subscription_history only).
        end_date: Upper timestamp bound (list_subscription_history only).
        max_items: Most items to return across pages.
        next_token: Pagination token from a previous response.

    Returns:
        Dict containing the operation result.
    """
    return await _business_support(
        ctx,
        operation,
        billing_month=billing_month,
        account_id=account_id,
        start_date=start_date,
        end_date=end_date,
        max_items=max_items,
        next_token=next_token,
    )
