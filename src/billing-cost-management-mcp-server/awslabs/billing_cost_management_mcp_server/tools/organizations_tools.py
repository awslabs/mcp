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

"""AWS Organizations tools for the AWS Billing and Cost Management MCP server.

Provides MCP tool definitions for read-only AWS Organizations account-metadata
operations, one tool per API operation (mirroring the billing-conductor and
billing-preferences tools).
"""

from .organizations_operations import (
    describe_account as _describe_account,
)
from .organizations_operations import (
    list_accounts as _list_accounts,
)
from fastmcp import Context, FastMCP
from typing import Any, Dict, Optional


organizations_server = FastMCP(
    name='organizations-tools',
    instructions='Tools for reading AWS Organizations account metadata via the AWS Organizations API',
)


@organizations_server.tool(
    name='list-organization-accounts',
    description="""Lists the accounts in the AWS organization, each with the metadata that says WHEN and
HOW it joined. This is the authoritative source for a linked account's organization-join date.

Returns `data.accounts`, one row per member account:
- `id`, `arn`, `name`, `email`: account identity.
- `joined_timestamp`: ISO 8601 UTC time the account joined the organization. For an INVITED account
  this is when the invitation was ACCEPTED, not when the account was created — do not treat it as a
  creation date.
- `joined_method`: `CREATED` (opened inside this organization) or `INVITED` (an existing account that
  accepted an invitation).
- `state` / `status`: account state (e.g. ACTIVE). Prefer `state`; AWS is retiring `status`.

Only accounts that are CURRENTLY members are returned; a removed or closed account does not appear,
and after an org move / re-invite the timestamp reflects the current membership, which can be later
than the account's original consolidated-billing link date.

This call succeeds only from the organization's MANAGEMENT (payer) account or a registered DELEGATED
ADMINISTRATOR. From any other account it returns an error (AccessDenied / not-in-organization) rather
than an empty list — surface that as "cannot determine from this account", not "no accounts".

Parameters:
- max_results: accounts per page, 1-20 (default 20, the API maximum). max_pages: pages to auto-fetch
  (default 10). When `data.pagination.has_more` is true the list is TRUNCATED — say so, and pass
  `next_token` back or raise `max_pages` rather than presenting it as the complete organization.

EXAMPLE OUTPUT for {} — one row per member account:

  {"id": "123456789012", "arn": "arn:aws:organizations::111111111111:account/o-exampleorgid/123456789012",
   "name": "example-linked-account", "email": "linked@example.com", "joined_method": "INVITED",
   "state": "ACTIVE", "status": "ACTIVE", "joined_timestamp": "2024-01-15T12:00:00.123000"}

`data.pagination` accompanies every response:

  {"complete_dataset": true, "pages_fetched": 1, "total_results": 12, "has_more": false,
   "next_token": null}

If you already have a specific account ID, use `describe-organization-account` for a single cheaper call.

Example 1 (whole organization): {}
Example 2 (first page only): {"max_results": 20, "max_pages": 1}
Example 3 (resume): {"next_token": "<next_token from a previous response>"}""",
)
async def list_organization_accounts(
    ctx: Context,
    max_results: Optional[int] = 20,
    next_token: Optional[str] = None,
    max_pages: Optional[int] = 10,
) -> Dict[str, Any]:
    """FastMCP wrapper for the AWS Organizations ListAccounts operation.

    Args:
        ctx: The MCP context object.
        max_results: Maximum number of accounts per page (1-20).
        next_token: Pagination token from a previous response.
        max_pages: Maximum pages to auto-paginate through.

    Returns:
        Dict containing the organization accounts.
    """
    return await _list_accounts(
        ctx,
        max_results=max_results,
        next_token=next_token,
        max_pages=max_pages,
    )


@organizations_server.tool(
    name='describe-organization-account',
    description="""Describes ONE account in the AWS organization by ID, returning the metadata that says
WHEN and HOW it joined. Use this when you already know the account ID; use `list-organization-accounts`
to enumerate the whole organization.

Returns `data.account`:
- `id`, `arn`, `name`, `email`: account identity.
- `joined_timestamp`: ISO 8601 UTC time the account joined the organization — the authoritative
  organization-join date. For an INVITED account this is when the invitation was ACCEPTED, not the
  account creation time.
- `joined_method`: `CREATED` or `INVITED`.
- `state` / `status`: account state. Prefer `state`; AWS is retiring `status`.

This call succeeds only from the organization's MANAGEMENT (payer) account or a registered DELEGATED
ADMINISTRATOR. A non-member ID returns AccountNotFoundException, and calling from a non-management
account returns an access error — surface either as "cannot determine", not "no data".

Parameters:
- account_id: the 12-digit account ID to describe (required).

EXAMPLE OUTPUT for {"account_id": "123456789012"}:

  {"account": {"id": "123456789012",
   "arn": "arn:aws:organizations::111111111111:account/o-exampleorgid/123456789012",
   "name": "example-linked-account", "email": "linked@example.com", "joined_method": "INVITED",
   "state": "ACTIVE", "status": "ACTIVE", "joined_timestamp": "2024-01-15T12:00:00.123000"}}

Read that as: the account joined the organization on 2024-01-15 at 12:00 UTC by accepting an
invitation.

Example 1: {"account_id": "123456789012"}""",
)
async def describe_organization_account(
    ctx: Context,
    account_id: str,
) -> Dict[str, Any]:
    """FastMCP wrapper for the AWS Organizations DescribeAccount operation.

    Args:
        ctx: The MCP context object.
        account_id: The 12-digit ID of the account to describe (required).

    Returns:
        Dict containing the single account.
    """
    return await _describe_account(ctx, account_id=account_id)
