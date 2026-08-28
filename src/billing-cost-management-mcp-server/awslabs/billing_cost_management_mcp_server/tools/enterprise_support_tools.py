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

"""Enterprise Support tools for the AWS Billing and Cost Management MCP server.

Exposes a single ``enterprise_support`` tool that routes by ``operation`` across
the Enterprise Support APIs, so the charge summary, the contract details
and the per-linked-account charge breakdown are reached through one tool rather
than three (mirroring the credits and cost-explorer tools). The rich tool
description is the primary vehicle that gives the agent semantic context about
every request parameter and response field.
"""

from ..utilities.aws_service_base import format_response
from .enterprise_support_operations import get_charge_summary as _get_charge_summary
from .enterprise_support_operations import get_contract_details as _get_contract_details
from .enterprise_support_operations import (
    list_linked_account_charges as _list_linked_account_charges,
)
from fastmcp import Context, FastMCP
from typing import Any, Dict, Optional


enterprise_support_server = FastMCP(
    name='enterprise-support-tools',
    instructions='Tools for working with AWS Enterprise Support charges via the AWS Billing API',
)


async def _enterprise_support(
    ctx: Context,
    operation: str,
    billing_month: Optional[str] = None,
    account_id: Optional[str] = None,
    max_results: Optional[int] = None,
    next_token: Optional[str] = None,
    max_pages: Optional[int] = None,
) -> Dict[str, Any]:
    """Route an Enterprise Support ``operation`` to its handler.

    Kept separate from the FastMCP-decorated wrapper so the routing can be unit
    tested directly (decorated tools cannot be invoked as plain functions).

    Args:
        ctx: The MCP context object.
        operation: The Enterprise Support operation to perform (for example
            ``"get_charge_summary"``).
        billing_month: Single calendar month in ``YYYY-MM`` format.
        account_id: Linked account to filter to (list_linked_account_charges only).
        max_results: Results per page (list_linked_account_charges only).
        next_token: Pagination token from a previous response.
        max_pages: Maximum pages to auto-paginate through (default: all).

    Returns:
        The operation's response, or a standardized error for an unknown
        operation.
    """
    await ctx.info(f'Enterprise Support operation: {operation}')

    if operation == 'get_charge_summary':
        return await _get_charge_summary(ctx, billing_month=billing_month)

    if operation == 'get_contract_details':
        return await _get_contract_details(ctx, billing_month=billing_month)

    if operation == 'list_linked_account_charges':
        return await _list_linked_account_charges(
            ctx,
            billing_month=billing_month,
            account_id=account_id,
            max_results=max_results,
            next_token=next_token,
            max_pages=max_pages,
        )

    return format_response(
        'error',
        {
            'message': (
                f"Unsupported operation: '{operation}'. Supported operations: "
                'get_charge_summary, get_contract_details, list_linked_account_charges.'
            )
        },
    )


@enterprise_support_server.tool(
    name='enterprise_support',
    description="""Access AWS Enterprise Support charge data: the Support charge for a billing period, the Support-eligible spend it was calculated from, the effective pricing plan, the contract terms that govern how the charge is allocated, and the per-linked-account breakdown. Choose an action with the required `operation` parameter.

## OPERATIONS

1) get_charge_summary - the Enterprise Support charge for one billing period, aggregated across every account in the Support profile
   Required: operation="get_charge_summary", billing_month.
   billing_month is a single calendar month "YYYY-MM" (e.g. "2026-06") and it selects the billing period the answer covers. State that period using the billingPeriodStartDate and billingPeriodEndDate the charge summary returns rather than assuming the first and last day of the calendar month. It cannot be earlier than 2025-01, the oldest month with Enterprise Support data. It also cannot be the current month or later: Enterprise Support data is only published once a billing period has closed, so the newest answerable month is always the previous calendar month. Both bounds are rejected locally without spending a call.
   Not paginated: the API returns one summary object per billing period.
   Returns: `data.charge_summary`, containing:
     - payerAccountId: the payer account authorized to view Enterprise Support data for its Support profile
     - billingMonth: echoed back in YYYY-MM
     - billingPeriodStartDate, billingPeriodEndDate, billDate: dates (normalized from timestamps). billDate is when the bill was generated, NOT a due date.
     - isEstimated: true means the Support charge is still estimated because the bill is not finalized; false means finalized. Always state which, because an estimated figure can still change.
     - supportCharge: the Support charge for the account. totalSupportCharge: the total across every account in the Support profile. These differ for a multi-account profile, so name which one you are reporting.
     - supportDiscount: a discount applied against the Support charge itself.
     - totalSupportEligibleSpend: total Support-eligible spend across the profile, which already includes the usage, Reserved Instance and Savings Plan figures below. Do not add the three breakdown values to this total; they decompose it.
     - totalSupportEligibleUsageSpend, totalSupportEligibleReservedInstanceSpend, totalSupportEligibleSavingsPlanSpend: the breakdown of that total.
     - supportChargePercentage: this payer's share of totalSupportCharge, as a decimal fraction where 1.0 means 100 percent. It is NOT a rate applied to Support-eligible spend and must never be presented as an effective rate. Derive an effective rate from supportCharge against totalSupportEligibleSpend instead.
     - supportEffectivePricingPlan: the plan used for the calculation, with pricingPlanId, name, description, startDate, endDate, minimumCharge, planDiscountPercent, discountAppliesToMinimumCharge, tiered, and tiers[]. Each tier carries tierMinimum, tierMaximum, baseCharge, additionalPercentageOfAggregateCharges, aggregateChargesAdjustment, incremental, increment and incrementCharge.

2) get_contract_details - the Enterprise Support contract terms in effect for one billing period
   Required: operation="get_contract_details", billing_month. Same billing_month rules as above.
   Not paginated: the API returns one contract view per billing period.
   Returns: `data.contract_details`, containing:
     - isContractActive: whether the Enterprise Support contract was active for that billing period
     - supportAllocationMethod: how the total Support charge is distributed across accounts in the profile. Valid values: Proportional (each account's share is proportional to its eligible spend) and Fixed_Percentage (shares come from pre-configured contract percentages). This is the field that explains why a given account was charged the share it was.
     - supportReservedInstanceTreatmentMethod and supportSavingsPlansTreatmentMethod: how Reserved Instance and Savings Plan fees enter Support-eligible spend. Valid values for each: None (fees excluded), Upfront (full upfront fee counted in the purchase month), Amortized (fee spread over the commitment term for purchases on or after the Support subscription start), AmortizedCustom (same, but only from a specified custom start date), AmortizedAll (amortized for all active commitments including those purchased before the subscription started).
     - supportReservedInstanceAmortizationStartDate and supportSavingsPlansAmortizationStartDate: dates. Populated only for the custom and amortized treatments named above, and null for the others, so a null here is expected rather than missing data.
     - supportProrateStartDate: date. The start date applied when accounts subscribed or unsubscribed to Support partway through the billing period.
     - contractPayerAccountIds: the payer accounts the contract covers, each with accountId and isGdn.
     - chargedPayerAccountIds: the payer accounts that are actually billed, each with accountId and chargePercentage. These two lists can differ, because being covered by the contract and being charged for it are separate things. Do not treat either as the full picture on its own. The service declares accountId required on both structures, but it can be absent in practice. When it is, report that the account identifiers were not returned rather than describing the list as empty, and never substitute account IDs from elsewhere in the response or from the caller's credentials.
     - additionalSupportCharge and additionalSupportEligibleUsageSpend: contract-specific adjustments, each with description, amount and chargeType. chargeType is free-form text with no published value set, so quote it and the description verbatim. An empty or absent list means no adjustments were applied.
     - pricingPlans: every pricing plan attached to the contract, in the same shape as supportEffectivePricingPlan above. get_charge_summary returns the single plan that was actually applied for the billing period, while this returns all plans on the contract, so do not present the first entry here as the effective plan.

3) list_linked_account_charges - the per-linked-account Enterprise Support charge breakdown for one billing period
   Required: operation="list_linked_account_charges", billing_month. Same billing_month rules as above.
   Optional:
     - account_id: filter to ONE linked account. This narrows the results to that account inside the payer's Support profile. Omit it to get every linked account, which is what "break down my Support charge by account" asks for. Do not pass the payer's own account id here expecting the whole organization. Omitting it sends no account filter at all and the tool never infers one from the caller credentials, so never report that a filter was applied when you left it out. An account id that appears in an error message is the caller's payer account, not a filter that was used.
     - max_results: results per page, 1 to 100. next_token: resume from a previous response. max_pages: pages to auto-paginate through, default all.
   Paginated: this is the only operation that pages. The tool follows nextToken for you.
   Returns: `data.linked_account_charges`, a list where each item contains:
     - accountId and payerAccountId: the linked account and the payer it belongs to
     - accountType: the account's role in the Support profile. Free-form text with no published value set, so report it verbatim rather than mapping it to values you expect or filtering on a guessed one.
     - totalSupportEligibleSpend: that account's Support-eligible spend for the billing period
     - proratedTotalSupportEligibleSpend: the spend after proration for a partial-period subscription. Use this, not totalSupportEligibleSpend, when explaining the account's contribution to the charge, and say when the two differ because the difference IS the proration.
     - billableSeconds and totalSeconds: the time basis for that proration. billableSeconds below totalSeconds means the account was only subscribed to Support for part of the billing period.
     - linkedTimePeriods and subscriptionTimePeriods: dates for when the account was linked to the payer and when it was subscribed to Support. These are different things and an account can be linked without being subscribed for the whole period.
     - totalSupportEligibleReservedInstanceSpend and totalSupportEligibleSavingsPlanSpend: the commitment portion of that account's eligible spend
     - supportEligibleSpendByService: per-service breakdown, each with serviceCode and totalSupportEligibleSpend
   Also returns `data.pagination`, which must be read before summarizing (see below).

## READING THE RESPONSE CORRECTLY

- MONETARY AMOUNTS ARE STRINGS to preserve decimal precision. Parse as decimals, never floats. Report them exactly as returned.
- TWO INDEPENDENT DISCOUNT FIELDS. NEVER CONFLATE THEM. `supportDiscount` is a discount against the Support charge itself. `supportEffectivePricingPlan.planDiscountPercent` is a percentage built into the pricing plan and already reflected in the charge, expressed as a decimal fraction rather than a percentage figure: 0.05 means 5 percent, so multiply by 100 before presenting it. Report each by name, and do NOT state that no discounts apply unless supportDiscount is zero AND planDiscountPercent is zero or absent. A zero supportDiscount alone does not mean the customer received no discount.
- CHECK `isEstimated` BEFORE PRESENTING A FIGURE AS FINAL. An estimated charge belongs to an in-flight bill and can still change.
- THE SPEND BREAKDOWN DECOMPOSES THE TOTAL, it does not add to it. totalSupportEligibleSpend already contains usage, Reserved Instance and Savings Plan spend.
- TIER CHARGES ARE INCREMENTAL, not a flat rate on total spend. For the tier the customer falls in: charge = baseCharge + (additionalPercentageOfAggregateCharges * (totalSupportEligibleSpend - aggregateChargesAdjustment)). The percentage applies only to spend above aggregateChargesAdjustment, matching the bracket structure AWS publishes for Support pricing. Never describe a tier's rate as applying to the customer's full eligible spend.
- isGdn IS THE GROSS VERSUS NET BILLING BASIS for that payer account. true means the account's Support charge is computed on a Gross basis, false means it is computed on the contract's Net basis. Answer basis questions from this field. Do NOT say the Gross or Net basis is unavailable, and do NOT claim isGdn is unrelated to it. The name is misleading, so report the basis in Gross or Net terms and NEVER expand the GDN acronym or attach any other meaning to it. There are multiple Net variants and this response cannot tell them apart, so say "the contract's Net basis" and never name a specific one. isGdn appears only on contractPayerAccountIds entries, so the response says nothing about the basis of linked accounts and you must never imply that accounts absent from that list are on a different basis. Explaining WHY a contract is on a given basis is out of scope, the same as pricing rationale.
- THIS TOOL NEVER RESOLVES AN ACCOUNT ID FROM CREDENTIALS, unlike some other billing tools. When account_id is omitted no account filter is sent and the results cover every linked account in the Support profile. NEVER state that the tool auto-detected, inferred or looked up the caller's account. An account id inside an error message is the payer the credentials belong to, reported by AWS, not a filter this tool applied.
- CHECK `data.pagination` BEFORE TOTALLING LINKED ACCOUNTS. When `has_more` is true the walk stopped early, usually because max_pages was reached, so any sum over the returned accounts is partial. Report the total AND say it covers `total_results` accounts with more available. `complete_dataset` true means every account was fetched.
- ONE BILLING PERIOD PER CALL. There is no date range. Answering "how did my Support charge change since March" means one call per billing period, then comparing the results.
- An access_denied error means the caller's IAM policy is missing the named permission, or the caller is not the payer account authorized for the Support profile. It does NOT mean the account has no Enterprise Support charges, and a linked account cannot read these operations at all.

## SCOPE BOUNDARY

This tool reports what Enterprise Support was charged and the spend it was derived from. It does not explain Enterprise Support pricing policy. For questions about why Support is priced a particular way, or why a specific charge type behaves as it does, point the customer to the public AWS Support plan FAQ at https://aws.amazon.com/premiumsupport/faqs/ rather than speculating. Questions about the overall bill, general discounts, or credits belong to the cost-explorer, invoicing and credits tools respectively.

EXAMPLES
- {"operation": "get_charge_summary", "billing_month": "2026-06"}
- {"operation": "get_contract_details", "billing_month": "2026-06"}
- {"operation": "list_linked_account_charges", "billing_month": "2026-06"}
- {"operation": "list_linked_account_charges", "billing_month": "2026-06", "account_id": "111122223333"}""",
)
async def enterprise_support(
    ctx: Context,
    operation: str,
    billing_month: Optional[str] = None,
    account_id: Optional[str] = None,
    max_results: Optional[int] = None,
    next_token: Optional[str] = None,
    max_pages: Optional[int] = None,
) -> Dict[str, Any]:
    """FastMCP wrapper for Enterprise Support operations.

    Thin wrapper so the routing logic in ``_enterprise_support`` can be unit
    tested directly (FastMCP-decorated tools cannot be invoked as plain
    functions).

    Args:
        ctx: The MCP context object.
        operation: The Enterprise Support operation to perform (for example
            ``"get_charge_summary"``).
        billing_month: Single calendar month in ``YYYY-MM`` format.
        account_id: Linked account to filter to (list_linked_account_charges only).
        max_results: Results per page (list_linked_account_charges only).
        next_token: Pagination token from a previous response.
        max_pages: Maximum pages to auto-paginate through (default: all).

    Returns:
        Dict containing the operation result.
    """
    return await _enterprise_support(
        ctx,
        operation,
        billing_month=billing_month,
        account_id=account_id,
        max_results=max_results,
        next_token=next_token,
        max_pages=max_pages,
    )
