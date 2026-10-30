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

"""AWS Billing tools for the AWS Billing and Cost Management MCP server.

Provides MCP tool definitions for AWS Billing View operations including
retrieving billing view metadata, listing billing views, listing source views,
and retrieving resource-based policies.
"""

from ..utilities.aws_service_base import handle_aws_error
from ..utilities.constants import PAGINATION_LIMIT_TEXT
from .bvs_operations import (
    get_billing_view as _get_billing_view,
)
from .bvs_operations import (
    get_resource_policy as _get_resource_policy,
)
from .bvs_operations import (
    list_billing_view_segments as _list_billing_view_segments,
)
from .bvs_operations import (
    list_billing_views as _list_billing_views,
)
from .bvs_operations import (
    list_source_views_for_billing_view as _list_source_views_for_billing_view,
)
from fastmcp import Context, FastMCP
from typing import Any, Dict, Optional


bvs_server = FastMCP(
    name='bvs-tools',
    instructions='Tools for working with AWS Billing API',
)


@bvs_server.tool(
    name='get-billing-view',
    description="""Returns the metadata associated to the specified billing view ARN.

A billing view is an AWS resource that defines a segment of AWS cost management data.
Billing view types:
- PRIMARY: The default billing view containing all cost management data for an account.
  For management accounts in an organization, this includes all data across the organization.
- BILLING_GROUP: Billing views corresponding to billing groups created in AWS Billing Conductor.
- CUSTOM: Customer-created billing views that provide filtered cost visibility across organizations.
  These can be shared with other accounts.
- BILLING_TRANSFER: Views available when using billing transfer, including "My view" and
  "Showback/chargeback view".
- BILLING_TRANSFER_SHOWBACK: Shows billing data configured for showback or chargeback purposes.

The tool returns information about:
- Billing view ARN, name, and description
- Billing view type (PRIMARY, BILLING_GROUP, CUSTOM, BILLING_TRANSFER, BILLING_TRANSFER_SHOWBACK)
- Owner account ID and source account ID
- Data filter expression (see below)
- Health status (status code and reasons)
- Derived view count and source view count
- Creation, update, and view definition last updated timestamps

data_filter_expression is the filter a CUSTOM view applies to its source views' data.
It holds at most one of:
- dimensions: key LINKED_ACCOUNT and a list of account IDs
- tags: one tag key and a list of its values
- cost_categories: one cost category name and a list of its values
plus an optional time_range (begin_date_inclusive, end_date_inclusive; one of them can
be absent, meaning open-ended on that side). There are no match options and no
And/Or/Not. An empty or missing expression means the view is unfiltered: it shows all
data of its source views.

Example: {"arn": "arn:aws:billing::123456789012:billingview/custom-view-abc123"}""",
)
async def get_billing_view(
    ctx: Context,
    arn: str,
) -> Dict[str, Any]:
    """Retrieve the metadata associated to the specified billing view.

    Args:
        ctx: The MCP context object
        arn: The Amazon Resource Name (ARN) that can be used to uniquely identify
            the billing view. Required.

    Returns:
        Dict containing the billing view metadata.
    """
    try:
        return await _get_billing_view(ctx, arn)
    except Exception as e:
        return await handle_aws_error(ctx, e, 'getBillingView', 'Billing')


@bvs_server.tool(
    name='list-billing-views',
    description="""Lists the billing views available for a given time period.

Every AWS account has a unique PRIMARY billing view that represents the billing data
available by default. Accounts that use AWS Billing Conductor also have BILLING_GROUP
billing views representing pro forma costs associated with each created billing group.

If activeTimeRange is provided, only billing views that were active during that time window are returned.
Else, all billing views that ever existed are returned, including views for deleted billing groups and ended billing transfers.

The tool returns a list of billing views with information about:
- Billing view ARN, name, and description
- Billing view type (PRIMARY, BILLING_GROUP, CUSTOM, BILLING_TRANSFER, BILLING_TRANSFER_SHOWBACK)
- Owner account ID and source account ID
- Health status (status code and reasons)

You can filter billing views by:
- active_after_inclusive / active_before_inclusive: UTC time range for listing billing views.
  Both must be provided together, both are inclusive, the end must be later than the start,
  and both must fall in the same UTC calendar month (make one call per month).
  Format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS (all times are in UTC).
  A date-only active_before_inclusive means 00:00:00 of that day, so to cover a whole
  month end it with YYYY-MM-DDT23:59:59 (for example 2024-01-31T23:59:59).
  PRIMARY billing views are always listed. BILLING_GROUP billing views are listed for time
  ranges when the associated billing group resource in AWS Billing Conductor is active.
- arns: Filter by specific billing view ARNs (maximum 10 items)
- billing_view_types: Filter by type (PRIMARY, BILLING_GROUP, CUSTOM, BILLING_TRANSFER,
  BILLING_TRANSFER_SHOWBACK)
- names: Filter by name using search criteria (supports STARTS_WITH search option).
  The prefix match is case-sensitive: "myview" does not match "MyView".
- owner_account_id: Filter by owner account ID (12-digit AWS account ID)
- source_account_id: 12-digit AWS account ID. Not an account membership search: it returns
  only BILLING_GROUP views whose billing group's primary account is this ID, and
  BILLING_TRANSFER and BILLING_TRANSFER_SHOWBACK views whose source account is this ID.
  PRIMARY and CUSTOM views are never returned with it. With a time range it matches the
  billing groups of that period; without one it matches billing groups from all periods, so
  an account that was a primary account in an earlier period returns that group's view.
  For the period queried, an account that is in a billing group but is not its primary
  account returns no views, and the calling account's own ID returns views only if it is a
  billing group's primary account or a billing transfer source.
  No filter of this tool lists the views that include a given account. To find the billing
  group view that covers an account, get its billing group's primary account (from the payer
  account, list-account-associations gives the account's billing group ARN for a billing
  period, the current one by default, and list-billing-groups gives that group's primary
  account), then pass that ID here.

Pagination: `max_items` is the total number of items to return. If it is omitted, the tool fetches every page for """
    + PAGINATION_LIMIT_TEXT
    + """, then returns a partial result; pass it, or narrow the filters, when the result can be large. A partial result leads
with `complete_dataset: false` and a `warning`: call again with a larger `max_items`, continue by
passing `pagination.next_token` back as `next_token`, or say in the answer that the result is
partial. `pagination.items_returned` counts the items in this response, not every item that exists.

Example 1: {}
Example 2 (filter by type): {"billing_view_types": "[\"PRIMARY\", \"CUSTOM\"]"}
Example 3 (filter by owner): {"owner_account_id": "123456789012"}
Example 4 (filter by name): {"names": "[{\"searchOption\": \"STARTS_WITH\", \"searchValue\": \"MyView\"}]"}
Example 5 (time range covering all of January 2024): {"active_after_inclusive": "2024-01-01", "active_before_inclusive": "2024-01-31T23:59:59"}
Example 6 (filter by ARNs): {"arns": "[\"arn:aws:billing::123456789012:billingview/custom-view-abc123\"]"}""",
)
async def list_billing_views(
    ctx: Context,
    active_after_inclusive: Optional[str] = None,
    active_before_inclusive: Optional[str] = None,
    arns: Optional[str] = None,
    billing_view_types: Optional[str] = None,
    names: Optional[str] = None,
    owner_account_id: Optional[str] = None,
    source_account_id: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List the billing views available for a given time period.

    Args:
        ctx: The MCP context object
        active_after_inclusive: Optional inclusive start of the active time range in UTC.
            Format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS (UTC).
            Must be provided together with active_before_inclusive.
            The time range must be within one UTC calendar month.
        active_before_inclusive: Optional inclusive end of the active time range in UTC.
            Format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS (UTC).
            Must be provided together with active_after_inclusive, later than it and in
            the same UTC calendar month. A date-only value means 00:00:00 of that day;
            use YYYY-MM-DDT23:59:59 to include the whole day.
        arns: Optional JSON string containing a list of billing view ARNs to filter by.
            Maximum 10 items.
        billing_view_types: Optional JSON string containing a list of billing view types.
            Valid values: PRIMARY, BILLING_GROUP, CUSTOM, BILLING_TRANSFER,
            BILLING_TRANSFER_SHOWBACK.
        names: Optional JSON string containing a list of StringSearch objects.
            Each object has searchOption (valid value: STARTS_WITH) and searchValue
            (1-128 characters). Fixed number of 1 item. The prefix match is case-sensitive.
        owner_account_id: Optional owner account ID to filter by (12-digit AWS account ID).
        source_account_id: Optional 12-digit AWS account ID. Not an account membership
            search: returns only BILLING_GROUP views whose billing group's primary account is
            this ID and BILLING_TRANSFER / BILLING_TRANSFER_SHOWBACK views whose source
            account is this ID, never PRIMARY or CUSTOM views. With a time range, only that
            period's billing groups match.
        max_items: Optional total number of items to return. Omit it to fetch every page.
        next_token: Optional pagination token from a previous response.

    Returns:
        Dict containing the list of billing views.
    """
    try:
        return await _list_billing_views(
            ctx,
            active_after_inclusive=active_after_inclusive,
            active_before_inclusive=active_before_inclusive,
            arns=arns,
            billing_view_types=billing_view_types,
            names=names,
            owner_account_id=owner_account_id,
            source_account_id=source_account_id,
            max_items=max_items,
            next_token=next_token,
        )
    except Exception as e:
        return await handle_aws_error(ctx, e, 'listBillingViews', 'Billing')


@bvs_server.tool(
    name='list-source-views-for-billing-view',
    description="""Lists the source views (managed AWS billing views) that a custom billing view
is built from.

A custom billing view is created as a "multi-source view" by combining cost management data
from up to 20 source views. Source views are managed billing views (typically PRIMARY or other
CUSTOM billing views) from the same or different AWS organizations. This enables consolidation
of cost management data across multiple organizations into a single custom billing view.

Use this tool to:
- Understand the data lineage of a custom billing view (which source views feed its data)
- Debug health issues: if a custom view is UNHEALTHY with SOURCE_VIEW_UNHEALTHY or
  SOURCE_VIEW_ACCESS_DENIED, inspect its source views to identify the problem
- Audit cross-organization data consolidation (which orgs/accounts contribute to this view)
- Determine if the custom billing view aggregates data from a single org or multiple orgs

Pagination: `max_items` is the total number of items to return. If it is omitted, the tool fetches every page for """
    + PAGINATION_LIMIT_TEXT
    + """, then returns a partial result; pass it, or narrow the filters, when the result can be large. A partial result leads
with `complete_dataset: false` and a `warning`: call again with a larger `max_items`, continue by
passing `pagination.next_token` back as `next_token`, or say in the answer that the result is
partial. `pagination.items_returned` counts the items in this response, not every item that exists.

Example 1: {"arn": "arn:aws:billing::123456789012:billingview/custom-view-abc123"}
Example 2 (with max_items): {"arn": "arn:aws:billing::123456789012:billingview/custom-view-abc123", "max_items": 5}
Example 3 (with next_token): {"arn": "arn:aws:billing::123456789012:billingview/custom-view-abc123", "next_token": "token123"}""",
)
async def list_source_views_for_billing_view(
    ctx: Context,
    arn: str,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List the source views (managed AWS billing views) associated with the billing view.

    Args:
        ctx: The MCP context object
        arn: The Amazon Resource Name (ARN) that can be used to uniquely identify
            the billing view. Required.
        max_items: Optional total number of items to return. Omit it to fetch every page.
        next_token: Optional pagination token from a previous response.

    Returns:
        Dict containing the list of source view ARNs associated with the billing view.
    """
    try:
        return await _list_source_views_for_billing_view(
            ctx,
            arn,
            max_items=max_items,
            next_token=next_token,
        )
    except Exception as e:
        return await handle_aws_error(ctx, e, 'listSourceViewsForBillingView', 'Billing')


@bvs_server.tool(
    name='get-resource-policy',
    description="""Returns the resource-based policy document attached to the resource in JSON format.

Resource-based policies are used to control access to billing view resources. When a custom
billing view is shared with other accounts (within or outside the organization) using AWS
Resource Access Manager (AWS RAM), a resource-based policy is attached to the billing view
resource defining the access permissions.

Use this tool to:
- Inspect the sharing permissions of a billing view to understand which accounts have access
- Audit resource-based policy configurations for compliance or security review
- Debug access issues by examining the policy document attached to a billing view
- Verify that sharing was configured correctly after sharing a custom billing view

The tool returns:
- The resource-based policy document in JSON format
- The ARN of the billing view resource the policy is attached to

Example: {"resource_arn": "arn:aws:billing::123456789012:billingview/custom-view-abc123"}""",
)
async def get_resource_policy(
    ctx: Context,
    resource_arn: str,
) -> Dict[str, Any]:
    """Retrieve the resource-based policy document attached to the billing view resource.

    Args:
        ctx: The MCP context object
        resource_arn: The Amazon Resource Name (ARN) of the billing view resource
            to which the policy is attached to. Required.

    Returns:
        Dict containing the resource-based policy document and resource ARN.
    """
    try:
        return await _get_resource_policy(ctx, resource_arn)
    except Exception as e:
        return await handle_aws_error(ctx, e, 'getResourcePolicy', 'Billing')


@bvs_server.tool(
    name='list-billing-view-segments',
    description="""Lists the segments of a billing view over a given time period. Each segment identifies
the billing domain (PRO_FORMA or BILLABLE) and the account relationships that apply during its time range.

A billing view segment represents a time range during which the billing domain and account relationships
for a billing view remained unchanged. If a mid-period change occurs (for example, an account joins or
leaves a billing group), the response includes multiple segments, each with its own time range. Hidden
segments are omitted, so the returned segments might not cover the entire requested time period.

Use this tool to:
- Determine whether an account's costs are BILLABLE (real charges owed to AWS) or PRO_FORMA (shaped by
  AWS Billing Conductor, not final charges)
- Identify mid-period changes in billing relationships (e.g., an account moving between billing groups)
- Audit the billing group or billing transfer account relationships that applied during a specific period
- Understand the management account hierarchy for organization member accounts

Parameters:
- arn: Optional billing view ARN. If omitted, the caller's PRIMARY billing view is used.
  Must reference a primary billing view; custom billing views are not supported.
- begin_date_inclusive / end_date_exclusive: Optional UTC time range for the billing period.
  Format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS (UTC). Both must be provided together.
  If omitted, the current billing period (calendar month in UTC) is used.
- max_items / next_token: see Pagination below.

Each segment in `data.segments` contains:
- domain: BILLABLE or PRO_FORMA
- management_account_id: The management account of the organization (for org member accounts)
- billing_group_primary_account_id: The billing group primary account (for billing group members)
- billing_transfer_account_id: The billing transfer account (only for billing transfer source accounts)
- time_range: begin_date_inclusive and end_date_exclusive in UTC ISO format

Pagination: `max_items` is the total number of items to return. If it is omitted, the tool fetches every page for """
    + PAGINATION_LIMIT_TEXT
    + """, then returns a partial result; pass it, or narrow the filters, when the result can be large. A partial result leads
with `complete_dataset: false` and a `warning`: call again with a larger `max_items`, continue by
passing `pagination.next_token` back as `next_token`, or say in the answer that the result is
partial. `pagination.items_returned` counts the items in this response, not every item that exists.

Example 1 (current billing period, caller's PRIMARY view): {}
Example 2 (specific billing view): {"arn": "arn:aws:billing::123456789012:billingview/primary"}
Example 3 (specific time range): {"begin_date_inclusive": "2024-09-01", "end_date_exclusive": "2024-10-01"}
Example 4 (first 10 segments): {"max_items": 10}""",
)
async def list_billing_view_segments(
    ctx: Context,
    arn: Optional[str] = None,
    begin_date_inclusive: Optional[str] = None,
    end_date_exclusive: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """FastMCP wrapper for the AWS Billing ListBillingViewSegments operation.

    Args:
        ctx: The MCP context object.
        arn: Optional billing view ARN. If omitted, the caller's PRIMARY billing view is used.
        begin_date_inclusive: Optional UTC datetime string for the inclusive start of the
            billing period. Format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS.
        end_date_exclusive: Optional UTC datetime string for the exclusive end of the
            billing period. Format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS.
        max_items: Optional total number of segments to return. Omit it to fetch every page.
        next_token: Pagination token from a previous response.

    Returns:
        Dict containing the billing view segments.
    """
    try:
        return await _list_billing_view_segments(
            ctx,
            arn=arn,
            begin_date_inclusive=begin_date_inclusive,
            end_date_exclusive=end_date_exclusive,
            max_items=max_items,
            next_token=next_token,
        )
    except Exception as e:
        return await handle_aws_error(ctx, e, 'listBillingViewSegments', 'Billing')
