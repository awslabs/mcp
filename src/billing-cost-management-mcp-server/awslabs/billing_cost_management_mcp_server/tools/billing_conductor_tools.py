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

"""AWS Billing Conductor tools for the AWS Billing and Cost Management MCP server.

Provides MCP tool definitions for AWS Billing Conductor operations including
billing groups, account associations, cost reports, pricing rules/plans,
custom line items, and billing transfer preferences.
"""

from ..utilities.aws_service_base import handle_aws_error
from ..utilities.constants import PAGINATION_LIMIT_TEXT
from .billing_conductor_operations import (
    get_billing_group_cost_report as _get_billing_group_cost_report,
)
from .billing_conductor_operations import (
    get_billing_transfer_preference as _get_billing_transfer_preference,
)
from .billing_conductor_operations import (
    list_account_associations as _list_account_associations,
)
from .billing_conductor_operations import (
    list_billing_group_cost_reports as _list_billing_group_cost_reports,
)
from .billing_conductor_operations import (
    list_billing_groups as _list_billing_groups,
)
from .billing_conductor_operations import (
    list_custom_line_item_versions as _list_custom_line_item_versions,
)
from .billing_conductor_operations import (
    list_custom_line_items as _list_custom_line_items,
)
from .billing_conductor_operations import (
    list_pricing_plans as _list_pricing_plans,
)
from .billing_conductor_operations import (
    list_pricing_plans_associated_with_pricing_rule as _list_plans_for_rule,
)
from .billing_conductor_operations import (
    list_pricing_rules as _list_pricing_rules,
)
from .billing_conductor_operations import (
    list_pricing_rules_associated_to_pricing_plan as _list_rules_for_plan,
)
from .billing_conductor_operations import (
    list_resources_associated_to_custom_line_item as _list_resources_associated_to_cli,
)
from fastmcp import Context, FastMCP
from typing import Any, Dict, Optional


billing_conductor_server = FastMCP(
    name='billing-conductor-tools',
    instructions='Tools for working with AWS Billing Conductor API',
)


@billing_conductor_server.tool(
    name='list-billing-groups',
    description="""Retrieves a list of billing groups from AWS Billing Conductor.

This tool retrieve billing groups for a given billing period.
If no billing period is provided, the current billing period is used.
A billing_period after the current month (UTC) is a projection, not a record: the response sets
`billing_period_is_future: true` and lists what is recorded today as in effect that month.

The tool returns information about:
- Billing group ARN, name, and description
- Billing group type (STANDARD or TRANSFER_BILLING)
- Billing group status (ACTIVE, PRIMARY_ACCOUNT_MISSING, or PENDING)
- Primary account ID
- Computation preference (pricing plan ARN)
- Account grouping settings (auto-associate, responsibility transfer ARN)
- Group size (number of member accounts)
- Creation and last modified timestamps

You can filter billing groups by:
- ARNs: Filter by specific billing group ARNs
- Names: exactly one name search, a case-sensitive prefix match:
  [{"SearchOption": "STARTS_WITH", "SearchValue": "<prefix>"}]
- Statuses: at most 2 of ACTIVE, PRIMARY_ACCOUNT_MISSING, PENDING (omit it for every status)
- Billing group types: Filter by type (STANDARD, TRANSFER_BILLING)
- Primary account IDs: Filter by primary account ID
- PricingPlan: a full pricing plan ARN (arn:aws:billingconductor::<account>:pricingplan/<id>),
  not a bare ID
- Auto-associate: Filter by auto-associate setting
- Responsibility transfer ARNs: Filter by responsibility transfer ARNs

Pagination: `max_items` is the total number of items to return. If it is omitted, the tool fetches every page for """
    + PAGINATION_LIMIT_TEXT
    + """, then returns a partial result; pass it, or narrow the filters, when the result can be large. A partial result leads
with `complete_dataset: false` and a `warning`: call again with a larger `max_items`, continue by
passing `pagination.next_token` back as `next_token`, or say in the answer that the result is
partial. `pagination.items_returned` counts the items in this response, not every item that exists.

Example 1: {"billing_period": "2025-01"}
Example 2 (with filter): {"filters": "{\"Statuses\": [\"ACTIVE\"], \"BillingGroupTypes\": [\"STANDARD\"]}", "billing_period": "2025-01"}""",
)
async def list_billing_groups(
    ctx: Context,
    billing_period: Optional[str] = None,
    filters: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve a list of billing groups from AWS Billing Conductor.

    Args:
        ctx: The MCP context object
        billing_period: Optional billing period in YYYY-MM format (e.g., "2025-01").
            If not provided, the current billing period is used.
            A month after the current month (UTC) returns a projection (billing_period_is_future).
        filters: Optional JSON string containing filter criteria. Supported filters:
            - Arns: List of billing group ARNs to retrieve
            - Names: Exactly one name search object with SearchOption "STARTS_WITH" and
              SearchValue (a case-sensitive prefix)
            - Statuses: Up to 2 of "ACTIVE", "PRIMARY_ACCOUNT_MISSING", "PENDING"
            - BillingGroupTypes: List of types ("STANDARD", "TRANSFER_BILLING")
            - PrimaryAccountIds: List of primary account IDs
            - PricingPlan: Full pricing plan ARN, not a bare ID
            - AutoAssociate: Boolean for auto-associate filter
            - ResponsibilityTransferArns: List of responsibility transfer ARNs
        max_items: Optional total number of items to return. Omit it to fetch every page.
        next_token: Optional pagination token from a previous response.

    Returns:
        Dict containing the billing group information.
    """
    try:
        return await _list_billing_groups(ctx, billing_period, filters, max_items, next_token)
    except Exception as e:
        return await handle_aws_error(ctx, e, 'listBillingGroups', 'Billing Conductor')


@billing_conductor_server.tool(
    name='list-account-associations',
    description="""Lists linked accounts associated with the payer account from AWS Billing Conductor.

This tool retrieve linked accounts for a given billing period.
If no billing period is provided, the current billing period is used.
A billing_period after the current month (UTC) is a projection, not a record: the response sets
`billing_period_is_future: true` and lists what is recorded today as in effect that month.

The tool returns information about each linked account:
- Account ID
- Account name
- Account email
- Billing group ARN (if associated to a billing group)

You can filter account associations by:
- AccountId: Filter by a specific AWS account ID
- AccountIds: Filter by a list of AWS account IDs (up to 30)
- Association: Filter by association status:
  - MONITORED: linked accounts associated to billing groups
  - UNMONITORED: linked accounts not associated to billing groups
  - A full billing group ARN (arn:aws:billingconductor::<account>:billinggroup/<id>): linked
    accounts associated to that billing group
  MONITORED and UNMONITORED are upper case.
Use AccountId or AccountIds, not both. Either can be combined with Association to narrow the
result.

Pagination: `max_items` is the total number of items to return. If it is omitted, the tool fetches every page for """
    + PAGINATION_LIMIT_TEXT
    + """, then returns a partial result; pass it, or narrow the filters, when the result can be large. A partial result leads
with `complete_dataset: false` and a `warning`: call again with a larger `max_items`, continue by
passing `pagination.next_token` back as `next_token`, or say in the answer that the result is
partial. `pagination.items_returned` counts the items in this response, not every item that exists.
The service returns up to 100 accounts per page, so a `max_items` below 100 still returns the
whole first page.

Example 1: {"billing_period": "2025-01"}
Example 2 (monitored only): {"filters": "{\"Association\": \"MONITORED\"}", "billing_period": "2025-01"}
Example 3 (by account IDs): {"filters": "{\"AccountIds\": [\"123456789012\", \"234567890123\"]}"}""",
)
async def list_account_associations(
    ctx: Context,
    billing_period: Optional[str] = None,
    filters: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve linked account associations from AWS Billing Conductor.

    Args:
        ctx: The MCP context object
        billing_period: Optional billing period in YYYY-MM format (e.g., "2025-01").
            If not provided, the current billing period is used.
            A month after the current month (UTC) returns a projection (billing_period_is_future).
        filters: Optional JSON string containing filter criteria. Supported filters:
            - AccountId: A single AWS account ID (12 digits). Not with AccountIds.
            - AccountIds: List of AWS account IDs (up to 30, each 12 digits). Not with AccountId.
            - Association: One of "MONITORED", "UNMONITORED", or a full billing group ARN
        max_items: Optional total number of items to return. Omit it to fetch every page.
        next_token: Optional pagination token from a previous response.

    Returns:
        Dict containing the account association information.
    """
    try:
        return await _list_account_associations(
            ctx, billing_period, filters, max_items, next_token
        )
    except Exception as e:
        return await handle_aws_error(ctx, e, 'listAccountAssociations', 'Billing Conductor')


@billing_conductor_server.tool(
    name='list-billing-group-cost-reports',
    description="""Retrieves a summary report of actual AWS charges and calculated AWS charges
based on the associated pricing plan of a billing group.

This tool retrieve cost reports for billing groups.
If no billing period is provided, the current billing period is used.
A billing_period after the current month (UTC) fails with validation_error before any AWS call;
the service would return $0 for every billing group.
A past month with no billing group in effect returns an empty list, not an error.

The tool returns cost report information for each billing group:
- Billing group ARN
- AWS cost (actual AWS charges)
- Proforma cost (hypothetical charges based on the associated pricing plan)
- Margin (proforma cost minus AWS cost; negative means the proforma cost is below the AWS cost)
- Margin percentage (margin divided by AWS cost, as a fraction, not a percent: -0.25 means -25%;
  "0.0" when the AWS cost is 0)
- Currency (displayed currency)
- `decimal_values` (aws_cost, proforma_cost, margin and margin_percentage, digit for digit, as
  strings in plain decimal notation)
- MONETARY AMOUNTS ARE STRINGS. They can come in exponent form ("5.0E-7") and with floating-point
  rounding digits ("-12.340000000000003"). `decimal_values` removes the exponent but keeps every
  digit; parse them as decimals, never floats, and round only for display.

You can filter cost reports by:
- BillingGroupArns: Filter by specific billing group ARNs (1 to 100 ARNs)

Pagination: `max_items` is the total number of items to return. If it is omitted, the tool fetches every page for """
    + PAGINATION_LIMIT_TEXT
    + """, then returns a partial result; pass it, or narrow the filters, when the result can be large. A partial result leads
with `complete_dataset: false` and a `warning`: call again with a larger `max_items`, continue by
passing `pagination.next_token` back as `next_token`, or say in the answer that the result is
partial. `pagination.items_returned` counts the items in this response, not every item that exists.

Example 1: {"billing_period": "2025-01"}
Example 2 (with filter): {"filters": "{\"BillingGroupArns\": [\"arn:aws:billingconductor::123456789012:billinggroup/abc\"]}", "billing_period": "2025-01"}""",
)
async def list_billing_group_cost_reports(
    ctx: Context,
    billing_period: Optional[str] = None,
    filters: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve a summary report of actual and calculated AWS charges for billing groups.

    Args:
        ctx: The MCP context object
        billing_period: Optional billing period in YYYY-MM format (e.g., "2025-01").
            If not provided, the current billing period is used.
            A month after the current month (UTC) fails with validation_error.
        filters: Optional JSON string containing filter criteria. Supported filters:
            - BillingGroupArns: List of billing group ARNs (minimum 1, maximum 100)
        max_items: Optional total number of items to return. Omit it to fetch every page.
        next_token: Optional pagination token from a previous response.

    Returns:
        Dict containing the billing group cost report information.
    """
    try:
        return await _list_billing_group_cost_reports(
            ctx, billing_period, filters, max_items, next_token
        )
    except Exception as e:
        return await handle_aws_error(ctx, e, 'listBillingGroupCostReports', 'Billing Conductor')


@billing_conductor_server.tool(
    name='get-billing-group-cost-report',
    description="""Retrieves the margin summary report for a specific billing group, which includes
the AWS cost and charged amount (pro forma cost) broken down by attributes such as AWS service
name or billing period.

This tool retrieve detailed cost reports for a
single billing group, optionally broken down by product name and/or billing period.
A BillingPeriodRange whose InclusiveStartBillingPeriod is after the current month (UTC) fails
with validation_error before any AWS call; the service would return no results.
A range with no data for the billing group (for example, months before it took effect) returns
no results, not an error.

The tool returns margin summary report results for the billing group:
- Billing group ARN
- Attributes (key-value pairs for grouping, e.g., PRODUCT_NAME: "S3", BILLING_PERIOD: "2025-01")
- AWS cost (actual AWS charges)
- Proforma cost (hypothetical charges based on the associated pricing plan)
- Margin (proforma cost minus AWS cost; negative means the proforma cost is below the AWS cost)
- Margin percentage (margin divided by AWS cost, as a fraction, not a percent: -0.25 means -25%;
  "0.0" when the AWS cost is 0)
- Currency (displayed currency)
- `decimal_values` (aws_cost, proforma_cost, margin and margin_percentage, digit for digit, as
  strings in plain decimal notation)
- MONETARY AMOUNTS ARE STRINGS. They can come in exponent form ("5.0E-7") and with floating-point
  rounding digits ("-12.340000000000003"). `decimal_values` removes the exponent but keeps every
  digit; parse them as decimals, never floats, and round only for display.

You can customize the report by:
- BillingPeriodRange: JSON string {"InclusiveStartBillingPeriod": "YYYY-MM",
  "ExclusiveEndBillingPeriod": "YYYY-MM"}, up to 12 months. The end month is excluded:
  2025-01 to 2025-04 covers January to March. Without it, the report covers only the current
  month, month-to-date (still changing).
- GroupBy: JSON array string with values "PRODUCT_NAME" and/or "BILLING_PERIOD". Without
  BILLING_PERIOD, the months of a range are summed: no GroupBy gives one row for the whole
  range, PRODUCT_NAME alone one row per product. Include BILLING_PERIOD in GroupBy to get one
  row per month.

Pagination: `max_items` is the total number of items to return. If it is omitted, the tool fetches every page for """
    + PAGINATION_LIMIT_TEXT
    + """, then returns a partial result; pass it, or narrow the filters, when the result can be large. A partial result leads
with `complete_dataset: false` and a `warning`: call again with a larger `max_items`, continue by
passing `pagination.next_token` back as `next_token`, or say in the answer that the result is
partial. `pagination.items_returned` counts the items in this response, not every item that exists.
Results come in pages of up to 300; the service returns at least 200 per page, so a `max_items`
below 200 can return up to 200.
The next_token expires shortly after the first call; after that, call again without next_token.

Example 1: {"arn": "arn:aws:billingconductor::123456789012:billinggroup/abc", "group_by": "[\"PRODUCT_NAME\"]"}
Example 2: {"arn": "arn:aws:billingconductor::123456789012:billinggroup/abc", "group_by": "[\"PRODUCT_NAME\", \"BILLING_PERIOD\"]", "billing_period_range": "{\"InclusiveStartBillingPeriod\": \"2025-01\", \"ExclusiveEndBillingPeriod\": \"2025-07\"}"}""",
)
async def get_billing_group_cost_report(
    ctx: Context,
    arn: str,
    billing_period_range: Optional[str] = None,
    group_by: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve the margin summary report for a specific billing group.

    Args:
        ctx: The MCP context object
        arn: The ARN that uniquely identifies the billing group.
        billing_period_range: Optional JSON string with InclusiveStartBillingPeriod and
            ExclusiveEndBillingPeriod (YYYY-MM, end month excluded, up to 12 months). Omitted:
            the current month, month-to-date.
        group_by: Optional JSON string with attributes to group by ("PRODUCT_NAME", "BILLING_PERIOD").
            Include "BILLING_PERIOD" for one row per month; without it a multi-month range is summed.
        max_items: Optional total number of items to return. Omit it to fetch every page.
            A max_items below 200 can return up to 200, the service's smallest page.
        next_token: Optional pagination token from a previous response.

    Returns:
        Dict containing the billing group cost report results.
    """
    try:
        return await _get_billing_group_cost_report(
            ctx, arn, billing_period_range, group_by, max_items, next_token
        )
    except Exception as e:
        return await handle_aws_error(ctx, e, 'getBillingGroupCostReport', 'Billing Conductor')


@billing_conductor_server.tool(
    name='list-custom-line-items',
    description="""Retrieves a list of custom line items (FFLIs) from AWS Billing Conductor.

Custom line items let you allocate costs and discounts to designated AWS accounts within a
billing group. Common use cases include allocating support fees, shared service costs, managed
service fees, taxes, credits, and distributing RI/Savings Plans savings.

This tool retrieve custom line items for a given billing period.
If no billing period is provided, the current billing period is used.
A billing_period after the current month (UTC) is a projection, not a record: the response sets
`billing_period_is_future: true` and lists what is recorded today as in effect that month.

The tool returns information about:
- Custom line item ARN, name, and description
- Account ID, billing group ARN
- Charge details (type: CREDIT or FEE, flat or percentage)
- Computation rule (CONSOLIDATED or ITEMIZED)
- Currency code, association size, product code
- Presentation details, creation and last modified timestamps

You can filter custom line items by:
- AccountIds: Filter by AWS account IDs (up to 30)
- Arns: Filter by specific custom line item ARNs (up to 100)
- BillingGroups: Filter by billing group ARNs (up to 100)
- Names: Filter by custom line item names (up to 100)

Pagination: `max_items` is the total number of items to return. If it is omitted, the tool fetches every page for """
    + PAGINATION_LIMIT_TEXT
    + """, then returns a partial result; pass it, or narrow the filters, when the result can be large. A partial result leads
with `complete_dataset: false` and a `warning`: call again with a larger `max_items`, continue by
passing `pagination.next_token` back as `next_token`, or say in the answer that the result is
partial. `pagination.items_returned` counts the items in this response, not every item that exists.

Example 1: {"billing_period": "2025-01"}
Example 2 (with filter): {"filters": "{\"Names\": [\"MyCustomLineItem\"]}", "billing_period": "2025-01"}""",
)
async def list_custom_line_items(
    ctx: Context,
    billing_period: Optional[str] = None,
    filters: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve a list of custom line items from AWS Billing Conductor.

    Args:
        ctx: The MCP context object
        billing_period: Optional billing period in YYYY-MM format (e.g., "2025-01").
            A month after the current month (UTC) returns a projection (billing_period_is_future).
        filters: Optional JSON string with filter criteria (AccountIds, Arns, BillingGroups, Names).
        max_items: Optional total number of items to return. Omit it to fetch every page.
        next_token: Optional pagination token from a previous response.

    Returns:
        Dict containing the custom line item information.
    """
    try:
        return await _list_custom_line_items(ctx, billing_period, filters, max_items, next_token)
    except Exception as e:
        return await handle_aws_error(ctx, e, 'listCustomLineItems', 'Billing Conductor')


@billing_conductor_server.tool(
    name='list-custom-line-item-versions',
    description="""Retrieves a list of versions for a specific custom line item from AWS Billing Conductor.

This tool retrieve all versions of a custom line item.
If no billing period is provided, the current billing period is used.

The tool returns information about each version including charge details, computation rule,
billing periods, and timestamps.

You can filter versions by:
- BillingPeriodRange: Filter by start and/or end billing period

Pagination: `max_items` is the total number of items to return. If it is omitted, the tool fetches every page for """
    + PAGINATION_LIMIT_TEXT
    + """, then returns a partial result; pass it, or narrow the filters, when the result can be large. A partial result leads
with `complete_dataset: false` and a `warning`: call again with a larger `max_items`, continue by
passing `pagination.next_token` back as `next_token`, or say in the answer that the result is
partial. `pagination.items_returned` counts the items in this response, not every item that exists.

Example 1: {"arn": "arn:aws:billingconductor::123456789012:customlineitem/abcdef1234"}
Example 2: {"arn": "...", "filters": "{\"BillingPeriodRange\": {\"StartBillingPeriod\": \"2025-01\", \"EndBillingPeriod\": \"2025-06\"}}"}""",
)
async def list_custom_line_item_versions(
    ctx: Context,
    arn: str,
    filters: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve a list of versions for a specific custom line item.

    Args:
        ctx: The MCP context object
        arn: The ARN for the custom line item. Required.
        filters: Optional JSON string with filter criteria (BillingPeriodRange).
        max_items: Optional total number of items to return. Omit it to fetch every page.
        next_token: Optional pagination token from a previous response.

    Returns:
        Dict containing the custom line item version information.
    """
    try:
        return await _list_custom_line_item_versions(ctx, arn, filters, max_items, next_token)
    except Exception as e:
        return await handle_aws_error(ctx, e, 'listCustomLineItemVersions', 'Billing Conductor')


@billing_conductor_server.tool(
    name='list-resources-associated-to-custom-line-item',
    description="""Lists the resources associated to a custom line item from AWS Billing Conductor.

This tool retrieve resources associated with a specific custom line item.
If no billing period is provided, the current billing period is used.
A billing_period after the current month (UTC) is a projection, not a record: the response sets
`billing_period_is_future: true` and lists what is recorded today as in effect that month.
A billing_period in which the custom line item was not in effect (before it started or after it
ended) fails with ResourceNotFoundException ("Custom line item does not exist."), not an empty
list. A mistyped ARN can return the same error: confirm the ARN with list-custom-line-items for
a recent month.

The tool returns information about each associated resource:
- Resource ARN (can be a billing group or custom line item)
- End billing period of the association
- Relationship type (PARENT or CHILD)

You can filter associated resources by:
- Relationship: Filter by relationship type ("PARENT" or "CHILD")

Pagination: `max_items` is the total number of items to return. If it is omitted, the tool fetches every page for """
    + PAGINATION_LIMIT_TEXT
    + """, then returns a partial result; pass it, or narrow the filters, when the result can be large. A partial result leads
with `complete_dataset: false` and a `warning`: call again with a larger `max_items`, continue by
passing `pagination.next_token` back as `next_token`, or say in the answer that the result is
partial. `pagination.items_returned` counts the items in this response, not every item that exists.

Example 1: {"arn": "arn:aws:billingconductor::123456789012:customlineitem/abcdef1234"}
Example 2: {"arn": "...", "filters": "{\"Relationship\": \"CHILD\"}", "billing_period": "2025-01"}""",
)
async def list_resources_associated_to_custom_line_item(
    ctx: Context,
    arn: str,
    billing_period: Optional[str] = None,
    filters: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List resources associated to a custom line item.

    Args:
        ctx: The MCP context object
        arn: The ARN of the custom line item. Required.
        billing_period: Optional billing period in YYYY-MM format.
            A month after the current month (UTC) returns a projection (billing_period_is_future).
        filters: Optional JSON string with filter criteria (Relationship).
        max_items: Optional total number of items to return. Omit it to fetch every page.
        next_token: Optional pagination token from a previous response.

    Returns:
        Dict containing the associated resource information.
    """
    try:
        return await _list_resources_associated_to_cli(
            ctx, arn, billing_period, filters, max_items, next_token
        )
    except Exception as e:
        return await handle_aws_error(
            ctx, e, 'listResourcesAssociatedToCustomLineItem', 'Billing Conductor'
        )


@billing_conductor_server.tool(
    name='list-pricing-rules',
    description="""Retrieves a list of pricing rules from AWS Billing Conductor.

This tool retrieve pricing rules for a given billing period.
A billing_period after the current month (UTC) is a projection, not a record: the response sets
`billing_period_is_future: true` and lists what is recorded today as in effect that month.

The tool returns information about:
- Pricing rule ARN, name, and description
- Type (MARKUP, DISCOUNT, or TIERING)
- Scope (GLOBAL, SERVICE, BILLING_ENTITY, or SKU)
- Modifier percentage, associated pricing plan count
- Service, operation, usage type, billing entity
- Tiering configuration, creation and last modified timestamps

You can filter pricing rules by:
- Arns: Filter by specific pricing rule ARNs

Pagination: `max_items` is the total number of items to return. If it is omitted, the tool fetches every page for """
    + PAGINATION_LIMIT_TEXT
    + """, then returns a partial result; pass it, or narrow the filters, when the result can be large. A partial result leads
with `complete_dataset: false` and a `warning`: call again with a larger `max_items`, continue by
passing `pagination.next_token` back as `next_token`, or say in the answer that the result is
partial. `pagination.items_returned` counts the items in this response, not every item that exists.

Example 1: {"billing_period": "2025-01"}
Example 2: {"filters": "{\"Arns\": [\"arn:aws:billingconductor::123456789012:pricingrule/abc\"]}", "billing_period": "2025-01"}""",
)
async def list_pricing_rules(
    ctx: Context,
    billing_period: Optional[str] = None,
    filters: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve a list of pricing rules from AWS Billing Conductor.

    Args:
        ctx: The MCP context object
        billing_period: Optional billing period in YYYY-MM format.
            A month after the current month (UTC) returns a projection (billing_period_is_future).
        filters: Optional JSON string with filter criteria (Arns).
        max_items: Optional total number of items to return. Omit it to fetch every page.
        next_token: Optional pagination token from a previous response.

    Returns:
        Dict containing the pricing rule information.
    """
    try:
        return await _list_pricing_rules(ctx, billing_period, filters, max_items, next_token)
    except Exception as e:
        return await handle_aws_error(ctx, e, 'listPricingRules', 'Billing Conductor')


@billing_conductor_server.tool(
    name='list-pricing-plans',
    description="""Retrieves a list of pricing plans from AWS Billing Conductor.

This tool retrieve pricing plans for a given billing period.
If no billing period is provided, the current billing period is used.
A billing_period after the current month (UTC) is a projection, not a record: the response sets
`billing_period_is_future: true` and lists what is recorded today as in effect that month.

The tool returns information about:
- Pricing plan ARN, name, and description
- Number of associated pricing rules (size)
- Creation and last modified timestamps

You can filter pricing plans by:
- Arns: Filter by specific pricing plan ARNs

Pagination: `max_items` is the total number of items to return. If it is omitted, the tool fetches every page for """
    + PAGINATION_LIMIT_TEXT
    + """, then returns a partial result; pass it, or narrow the filters, when the result can be large. A partial result leads
with `complete_dataset: false` and a `warning`: call again with a larger `max_items`, continue by
passing `pagination.next_token` back as `next_token`, or say in the answer that the result is
partial. `pagination.items_returned` counts the items in this response, not every item that exists.

Example 1: {"billing_period": "2025-01"}
Example 2: {"filters": "{\"Arns\": [\"arn:aws:billingconductor::123456789012:pricingplan/abc\"]}", "billing_period": "2025-01"}""",
)
async def list_pricing_plans(
    ctx: Context,
    billing_period: Optional[str] = None,
    filters: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve a list of pricing plans from AWS Billing Conductor.

    Args:
        ctx: The MCP context object
        billing_period: Optional billing period in YYYY-MM format.
            A month after the current month (UTC) returns a projection (billing_period_is_future).
        filters: Optional JSON string with filter criteria (Arns).
        max_items: Optional total number of items to return. Omit it to fetch every page.
        next_token: Optional pagination token from a previous response.

    Returns:
        Dict containing the pricing plan information.
    """
    try:
        return await _list_pricing_plans(ctx, billing_period, filters, max_items, next_token)
    except Exception as e:
        return await handle_aws_error(ctx, e, 'listPricingPlans', 'Billing Conductor')


@billing_conductor_server.tool(
    name='list-pricing-rules-for-plan',
    description="""Lists the pricing rules associated with a specific pricing plan.

This tool retrieve pricing rules associated with a specific pricing plan
If no billing period is provided, the current billing period is used.
A billing_period after the current month (UTC) is a projection, not a record: the response sets
`billing_period_is_future: true` and lists what is recorded today as in effect that month.
A billing_period in which the pricing plan was not in effect (for example, before it
started) fails with ResourceNotFoundException ("Pricing plan does not exist."), not an empty list.
A mistyped ARN can return the same error: confirm the ARN with list-pricing-plans for a recent month.

The tool returns information about:
- The billing period for which the pricing rule associations are listed.
- The optional pagination token to be used on subsequent calls.
- The ARN of the pricing plan for which associations are listed.
- A list containing pricing rules that are associated with the requested pricing plan

Pagination: `max_items` is the total number of items to return. If it is omitted, the tool fetches every page for """
    + PAGINATION_LIMIT_TEXT
    + """, then returns a partial result; pass it, or narrow the filters, when the result can be large. A partial result leads
with `complete_dataset: false` and a `warning`: call again with a larger `max_items`, continue by
passing `pagination.next_token` back as `next_token`, or say in the answer that the result is
partial. `pagination.items_returned` counts the items in this response, not every item that exists.

Example: {"pricing_plan_arn": "arn:aws:billingconductor::123456789012:pricingplan/abc"}""",
)
async def list_pricing_rules_associated_to_pricing_plan(
    ctx: Context,
    pricing_plan_arn: str,
    billing_period: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List pricing rules associated with a pricing plan.

    Args:
        ctx: The MCP context object
        pricing_plan_arn: The ARN of the pricing plan. Required.
        billing_period: Optional billing period in YYYY-MM format.
            A month after the current month (UTC) returns a projection (billing_period_is_future).
        max_items: Optional total number of items to return. Omit it to fetch every page.
        next_token: Optional pagination token from a previous response.

    Returns:
        Dict containing the pricing rule ARNs associated with the pricing plan.
    """
    try:
        return await _list_rules_for_plan(
            ctx, pricing_plan_arn, billing_period, max_items, next_token
        )
    except Exception as e:
        return await handle_aws_error(
            ctx, e, 'listPricingRulesAssociatedToPricingPlan', 'Billing Conductor'
        )


@billing_conductor_server.tool(
    name='list-pricing-plans-for-rule',
    description="""Lists the pricing plans associated with a specific pricing rule.

This tool retrieve pricing plans associated with a specific pricing rule
If no billing period is provided, the current billing period is used.
A billing_period after the current month (UTC) is a projection, not a record: the response sets
`billing_period_is_future: true` and lists what is recorded today as in effect that month.
A billing_period in which the pricing rule was not in effect (for example, before it
started) fails with ResourceNotFoundException ("Pricing rule does not exist."), not an empty list.
A mistyped ARN can return the same error: confirm the ARN with list-pricing-rules for a recent month.

The tool returns information about:
- The billing period for which the pricing rule associations are listed.
- The optional pagination token to be used on subsequent calls.
- The ARN of the pricing rule for which associations are listed.
- The list containing pricing plans that are associated with the requested pricing rule.

Pagination: `max_items` is the total number of items to return. If it is omitted, the tool fetches every page for """
    + PAGINATION_LIMIT_TEXT
    + """, then returns a partial result; pass it, or narrow the filters, when the result can be large. A partial result leads
with `complete_dataset: false` and a `warning`: call again with a larger `max_items`, continue by
passing `pagination.next_token` back as `next_token`, or say in the answer that the result is
partial. `pagination.items_returned` counts the items in this response, not every item that exists.

Example: {"pricing_rule_arn": "arn:aws:billingconductor::123456789012:pricingrule/abc"}""",
)
async def list_pricing_plans_associated_with_pricing_rule(
    ctx: Context,
    pricing_rule_arn: str,
    billing_period: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List pricing plans associated with a pricing rule.

    Args:
        ctx: The MCP context object
        pricing_rule_arn: The ARN of the pricing rule. Required.
        billing_period: Optional billing period in YYYY-MM format.
            A month after the current month (UTC) returns a projection (billing_period_is_future).
        max_items: Optional total number of items to return. Omit it to fetch every page.
        next_token: Optional pagination token from a previous response.

    Returns:
        Dict containing the pricing plan ARNs associated with the pricing rule.
    """
    try:
        return await _list_plans_for_rule(
            ctx, pricing_rule_arn, billing_period, max_items, next_token
        )
    except Exception as e:
        return await handle_aws_error(
            ctx, e, 'listPricingPlansAssociatedWithPricingRule', 'Billing Conductor'
        )


@billing_conductor_server.tool(
    name='get-billing-transfer-preference',
    description="""Retrieves the auto billing group creation preference for an inbound billing transfer.

The preference belongs to one inbound billing transfer (responsibility_transfer_arn): a bill
source account transferring its bill to the caller's account. In a two-level billing transfer,
that bill source account also receives bills from its own end customers. When the preference is
enabled, AWS Billing Conductor automatically creates, in the caller's account, a billing group
for the indirect relationship with each NEW end customer that transfers its bill to that bill
source account, using the pricing plan selected in the preference.

How to read the preference:
- It applies only to two-level transfers. On a one-level transfer it can be enabled but has no
  effect.
- It is set per inbound billing transfer and is disabled by default.
- It applies only to end customers added AFTER it was enabled. It does not create billing groups
  for indirect transfers accepted before that; those need a billing group created manually.
- Disabling it, or changing its pricing plan, does not change billing groups it already created;
  only billing groups created afterward are affected.

The tool returns:
- responsibility_transfer_arn: the billing transfer the preference applies to
- auto_billing_transfer_billing_group_creation.enabled: whether billing groups are created
  automatically for new end customers in this billing transfer
- auto_billing_transfer_billing_group_creation.pricing_plan_arn: the pricing plan applied to
  the billing groups it creates
- last_modified_time: when the preference was last changed (UTC ISO 8601). Absent if the
  preference has never been set for this billing transfer.

responsibility_transfer_arn (the inbound billing transfer) is required.

The call can fail, for example when the billing transfer doesn't exist, is no longer active,
belongs to another account, or the caller lacks permission. In that case, report that the
preference cannot be read for this billing transfer, not that auto creation is disabled.

EXAMPLE OUTPUT:

  {"responsibility_transfer_arn":
     "arn:aws:organizations::123456789012:transfer/o-exampleorgid/billing/inbound/rt-exampleid",
   "auto_billing_transfer_billing_group_creation": {"enabled": true,
     "pricing_plan_arn": "arn:aws:billingconductor::123456789012:pricingplan/abcdef1234"},
   "last_modified_time": "2026-09-01T12:00:00"}

Example: {"responsibility_transfer_arn": "arn:aws:organizations::123456789012:transfer/o-exampleorgid/billing/inbound/rt-exampleid"}""",
)
async def get_billing_transfer_preference(
    ctx: Context,
    responsibility_transfer_arn: str,
) -> Dict[str, Any]:
    """Retrieve the auto billing group creation preference for a billing transfer.

    Args:
        ctx: The MCP context object
        responsibility_transfer_arn: The ARN of the billing transfer. Required.

    Returns:
        Dict containing the billing transfer preference.
    """
    try:
        return await _get_billing_transfer_preference(ctx, responsibility_transfer_arn)
    except Exception as e:
        return await handle_aws_error(ctx, e, 'getBillingTransferPreference', 'Billing Conductor')
