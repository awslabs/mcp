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
from .bvs_operations import (
    get_billing_view as _get_billing_view,
)
from .bvs_operations import (
    get_resource_policy as _get_resource_policy,
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
There are four types of billing views:
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
- Data filter expression (dimensions, tags, cost categories, time range)
- Health status (status code and reasons)
- Derived view count and source view count
- Creation, update, and view definition last updated timestamps

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
- active_after_inclusive / active_before_inclusive: UTC time range for listing billing views
  (must be within one calendar month, both must be provided together).
  Format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS (all times are in UTC).
  PRIMARY billing views are always listed. BILLING_GROUP billing views are listed for time
  ranges when the associated billing group resource in AWS Billing Conductor is active.
- arns: Filter by specific billing view ARNs (maximum 10 items)
- billing_view_types: Filter by type (PRIMARY, BILLING_GROUP, CUSTOM, BILLING_TRANSFER,
  BILLING_TRANSFER_SHOWBACK)
- names: Filter by name using search criteria (supports STARTS_WITH search option)
- owner_account_id: Filter by owner account ID (12-digit AWS account ID)
- source_account_id: Filter by source account ID (12-digit AWS account ID)
- max_results: Maximum number of billing views per page (1-100, default 100)

The tool paginates through results up to max_pages pages (default 10).
If more results are available after reaching the page limit, a next_token is returned.
Pass the next_token back to this tool to continue fetching from where you left off.

Example 1: {}
Example 2 (filter by type): {"billing_view_types": "[\"PRIMARY\", \"CUSTOM\"]"}
Example 3 (filter by owner): {"owner_account_id": "123456789012"}
Example 4 (filter by name): {"names": "[{\"searchOption\": \"STARTS_WITH\", \"searchValue\": \"MyView\"}]"}
Example 5 (with time range, date only): {"active_after_inclusive": "2024-01-01", "active_before_inclusive": "2024-01-31"}
Example 6 (with time range, second precision): {"active_after_inclusive": "2024-01-01T00:00:00", "active_before_inclusive": "2024-01-31T23:59:59"}
Example 7 (filter by ARNs): {"arns": "[\"arn:aws:billing::123456789012:billingview/custom-view-abc123\"]"}""",
)
async def list_billing_views(
    ctx: Context,
    active_after_inclusive: Optional[str] = None,
    active_before_inclusive: Optional[str] = None,
    arns: Optional[str] = None,
    billing_view_types: Optional[str] = None,
    max_results: Optional[int] = None,
    names: Optional[str] = None,
    owner_account_id: Optional[str] = None,
    source_account_id: Optional[str] = None,
    max_pages: int = 10,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List the billing views available for a given time period.

    Args:
        ctx: The MCP context object
        active_after_inclusive: Optional inclusive start of the active time range in UTC.
            Format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS (UTC).
            Must be provided together with active_before_inclusive.
            The time range must be within one calendar month.
        active_before_inclusive: Optional inclusive end of the active time range in UTC.
            Format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS (UTC).
            Must be provided together with active_after_inclusive.
            The time range must be within one calendar month.
        arns: Optional JSON string containing a list of billing view ARNs to filter by.
            Maximum 10 items.
        billing_view_types: Optional JSON string containing a list of billing view types.
            Valid values: PRIMARY, BILLING_GROUP, CUSTOM, BILLING_TRANSFER,
            BILLING_TRANSFER_SHOWBACK.
        max_results: Optional maximum number of billing views to retrieve per page.
            Valid range: 1-100. Default is 100.
        names: Optional JSON string containing a list of StringSearch objects.
            Each object has searchOption (valid value: STARTS_WITH) and searchValue
            (1-128 characters). Fixed number of 1 item.
        owner_account_id: Optional owner account ID to filter by (12-digit AWS account ID).
        source_account_id: Optional source account ID to filter by (12-digit AWS account ID).
        max_pages: Maximum number of API pages to fetch. Defaults to 10.
        next_token: Optional pagination token from a previous response.

    Returns:
        Dict containing the list of billing views.
    """
    try:
        return await _list_billing_views(
            ctx,
            active_after_inclusive,
            active_before_inclusive,
            arns,
            billing_view_types,
            max_results,
            names,
            owner_account_id,
            source_account_id,
            max_pages,
            next_token,
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

The tool paginates through results up to max_pages pages (default 10).
If more results are available after reaching the page limit, a next_token is returned.
Pass the next_token back to this tool to continue fetching from where you left off.

Example 1: {"arn": "arn:aws:billing::123456789012:billingview/custom-view-abc123"}
Example 2 (with max_results): {"arn": "arn:aws:billing::123456789012:billingview/custom-view-abc123", "max_results": 5}
Example 3 (with next_token): {"arn": "arn:aws:billing::123456789012:billingview/custom-view-abc123", "next_token": "token123"}""",
)
async def list_source_views_for_billing_view(
    ctx: Context,
    arn: str,
    max_results: Optional[int] = None,
    max_pages: int = 10,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List the source views (managed AWS billing views) associated with the billing view.

    Args:
        ctx: The MCP context object
        arn: The Amazon Resource Name (ARN) that can be used to uniquely identify
            the billing view. Required.
        max_results: Optional maximum number of entries a paginated response contains.
            Valid range: 1-100.
        max_pages: Maximum number of API pages to fetch. Defaults to 10.
        next_token: Optional pagination token from a previous response.

    Returns:
        Dict containing the list of source view ARNs associated with the billing view.
    """
    try:
        return await _list_source_views_for_billing_view(
            ctx,
            arn,
            max_results,
            max_pages,
            next_token,
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
