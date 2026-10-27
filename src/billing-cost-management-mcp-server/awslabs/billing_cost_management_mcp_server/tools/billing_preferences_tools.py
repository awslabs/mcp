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

"""AWS billing preferences tools for the AWS Billing and Cost Management MCP server.

Provides MCP tool definitions for AWS Billing preference operations, one tool per
API operation (mirroring the billing-conductor and bvs tools).
"""

from .billing_preferences_operations import (
    get_billing_preferences as _get_billing_preferences,
)
from fastmcp import Context, FastMCP
from typing import Any, Dict, List, Optional, Union


billing_preferences_server = FastMCP(
    name='billing-preferences-tools',
    instructions='Tools for working with AWS billing preferences via the AWS Billing API',
)


@billing_preferences_server.tool(
    name='get-billing-preferences',
    description="""Retrieves billing preferences for the specified feature. Each feature controls a
distinct billing capability: which accounts can share Reserved Instances / Savings Plans or credits,
whether billing alerts are enabled, the historical record of sharing changes, and per-credit options.

RI_SHARING covers BOTH Reserved Instances and Savings Plans discounts.

`features` TAKES EXACTLY ONE VALUE. Current state and history are separate features, so "what is shared
now, and when did it change" is two calls: RI_SHARING then RI_SHARING_HISTORY (CREDIT_SHARING and
CREDIT_SHARING_HISTORY for credits). BILLING_ALERTS, CREDIT_LEVEL_SHARING and CREDIT_PREFERENCE_OPTIONS
are also valid.

Parameters:
- features: the single feature to retrieve (required).
- filters: JSON, PREFERENCE_KEY only, and accepted for CREDIT_PREFERENCE_OPTIONS alone, where values must
  match `credit/{creditId}`.
- max_items: total number of rows to return. Omit it to fetch every page (no limit); pass it
  when the organization is large.
- next_token: `pagination.next_token` from a previous partial response, to continue.

Returns `data.billing_preferences`, the AWS rows unchanged: `feature`, `key`, `value` (ENABLED|DISABLED),
plus `accountId`/`accountName` on current account rows (`accountId` only in history) and `billingPeriod`
on history rows.

EXAMPLE OUTPUT for {"features": "RI_SHARING"} (CREDIT_SHARING uses the same keys, for credits):

  {"feature": "RI_SHARING", "key": "default", "value": "ENABLED"}
  {"feature": "RI_SHARING", "key": "costcategory-prioritized/arn:aws:ce::123456789012:costcategory/abcd1234",
   "value": "ENABLED"}
  {"feature": "RI_SHARING", "key": "account/123456789012", "value": "DISABLED",
   "accountId": "123456789012", "accountName": "example-linked-account"}

From the management account, rows come in this order across pages: `default`, at most one
GROUP-SHARING row, then `account/<id>` rows. A current-state page fetched with `next_token` continues
that order and has no `default` row. `default` and the group row are ORGANIZATION-WIDE settings, NOT
accounts: count only `account/` keys.
- `default`: the baseline. New accounts get it, and so does every account a history period does not list.
- The group row (value always ENABLED; the key is the mode) says where a discount goes after its owner:
  - `open-sharing`: to any sharing account in the organization.
  - `costcategory-prioritized/<cost category ARN>` (RI_SHARING may say `benefitgroup-prioritized/`):
    the owner's group first, then the rest of the organization.
  - `costcategory-restricted/<cost category ARN>` (RI_SHARING may say `benefitgroup-restricted/`): only
    inside the owner's group, never outside it.
  Groups are the values of that cost category's rules (describe-cost-category-definition); accounts left
  to its default value, and the management account, are in no group. If a result fetched without
  `next_token` is complete (`complete_dataset: true`) and has `default` but no group row, no group mode
  is reported, which normally means organization-wide sharing; say the mode was inferred from the
  missing row. Any other result without a group row (partial, or fetched with `next_token`) says nothing
  about the mode.
- `account/<id>`: that account's setting; DISABLED excludes it from sharing.
The rows above read as: baseline ENABLED, discounts going to the owner's cost-category group before the
rest of the organization, one account excluded. CREDIT_LEVEL_SHARING can narrow where one credit goes.

From a member account: one row, key `account` and no `accountId`, saying whether that account shares.
The group mode is not visible there, so do not infer it; the *_HISTORY features need the management
account.

RI_SHARING_HISTORY and CREDIT_SHARING_HISTORY prefix each key, the group row included, with `<yyyy-MM>/`
and add `billingPeriod`. They always write `costcategory-` (a history key with the same mode and ARN
as a current `benefitgroup-` key is the same setting) and list only accounts that differ from that period's
`default`. A period can lack its group row even when group sharing applied, so a missing history group
row is not evidence of open sharing. A history page fetched with `next_token` can start mid-period,
without that period's `default` and group rows:

  {"feature": "RI_SHARING_HISTORY", "key": "2025-09/costcategory-prioritized/arn:aws:ce::...",
   "value": "ENABLED", "billingPeriod": {"year": 2025, "month": 9}}

`data.pagination` accompanies every response:

  {"complete_dataset": true, "has_more": false, "next_token": null, "items_returned": 13}

A partial result leads with `complete_dataset: false` and a `warning`: call again with a larger
`max_items`, continue by passing `pagination.next_token` back as `next_token`, or say in the answer that
the result is partial. `items_returned` counts the rows in this response, not every row that exists.

Example 1: {"features": "RI_SHARING"}
Example 2 (history): {"features": "RI_SHARING_HISTORY"}
Example 3 (credit sharing): {"features": "CREDIT_SHARING"}
Example 4 (one credit): {"features": "CREDIT_PREFERENCE_OPTIONS",
  "filters": "[{\\"name\\": \\"PREFERENCE_KEY\\", \\"value\\": [\\"credit/4242\\"]}]"}""",
)
async def get_billing_preferences(
    ctx: Context,
    features: Union[str, List[str]],
    filters: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """FastMCP wrapper for the AWS Billing GetBillingPreferences operation.

    Args:
        ctx: The MCP context object.
        features: The single billing feature to retrieve (required).
        filters: Filters as a JSON string.
        max_items: Optional total number of rows to return. Omit it to fetch every page.
        next_token: Pagination token from a previous response.

    Returns:
        Dict containing the billing preferences.
    """
    return await _get_billing_preferences(
        ctx,
        features=features,
        filters=filters,
        max_items=max_items,
        next_token=next_token,
    )
