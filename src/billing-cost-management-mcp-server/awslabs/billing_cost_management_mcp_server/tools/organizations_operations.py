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

"""AWS Organizations operations for the AWS Billing and Cost Management MCP server.

This module contains the read-only operation handlers for the AWS Organizations
tools. They expose account membership metadata — most importantly each member
account's ``JoinedTimestamp`` (when the account joined the organization) and
``JoinedMethod`` (``CREATED`` vs ``INVITED``). That join date is the authoritative
answer to "when did this linked account join the consolidated-billing family",
which billing surfaces cannot report on their own.

Only read operations are wrapped. Write operations in the same API model
(``CreateAccount``, ``MoveAccount``, ``RemoveAccountFromOrganization``, ...) are
deliberately not exposed, because this server is read-only.

AWS Organizations is a global service reached through the us-east-1 endpoint, and
these calls succeed only from the organization's management account or a member
account registered as a delegated administrator; from any other account the
service returns ``AccessDeniedException`` (or ``AWSOrganizationsNotInUseException``
when the caller is not in an organization), which the shared error handler
surfaces as an error rather than an empty result.
"""

from ..utilities.aws_service_base import (
    create_aws_client,
    format_response,
    handle_aws_error,
    paginate_aws_response,
)
from ..utilities.constants import REGION_US_EAST_1
from ..utilities.sql_utils import convert_response_if_needed
from ..utilities.time_utils import timestamp_to_utc_iso_string
from fastmcp import Context
from typing import Any, Dict, List, Optional


# AWS Organizations is a global service that operates in us-east-1
ORGANIZATIONS_DEFAULT_REGION = REGION_US_EAST_1


def _create_organizations_client() -> Any:
    """Create an AWS Organizations client for the global (us-east-1) endpoint.

    Returns:
        boto3.client: AWS Organizations client.
    """
    return create_aws_client('organizations', region_name=ORGANIZATIONS_DEFAULT_REGION)


def _format_accounts(accounts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Format Organizations ``Account`` objects from the AWS API response.

    boto3 returns ``JoinedTimestamp`` as a Python ``datetime``, which is not
    JSON-serializable, so it is converted to an ISO 8601 UTC string. Every other
    field is passed through unchanged. Both ``state`` and ``status`` are surfaced;
    prefer ``state`` because the ``Status`` field is being retired by AWS.

    Args:
        accounts: List of ``Account`` objects from the AWS API.

    Returns:
        List of formatted account objects.
    """
    formatted: List[Dict[str, Any]] = []
    for account in accounts:
        formatted_account: Dict[str, Any] = {
            'id': account.get('Id'),
            'arn': account.get('Arn'),
            'name': account.get('Name'),
            'email': account.get('Email'),
            'joined_method': account.get('JoinedMethod'),
            'state': account.get('State'),
            'status': account.get('Status'),
        }
        if account.get('JoinedTimestamp') is not None:
            formatted_account['joined_timestamp'] = timestamp_to_utc_iso_string(
                account['JoinedTimestamp']
            )
        formatted.append(formatted_account)
    return formatted


async def list_accounts(
    ctx: Context,
    max_results: Optional[int] = 20,
    next_token: Optional[str] = None,
    max_pages: Optional[int] = 10,
) -> Dict[str, Any]:
    """List the accounts in the AWS organization with their join metadata.

    Args:
        ctx: The MCP context object.
        max_results: Maximum number of accounts per page (1-20, the API maximum).
            Defaults to the API maximum so the list arrives in as few calls as
            possible. Pass None to let the service apply its own default.
        next_token: Pagination token from a previous response to resume from.
        max_pages: Maximum number of pages to auto-paginate through. Bounded by
            default so a very large organization cannot fill the agent's context
            unprompted; the ``pagination`` block reports the truncation. Pass None
            to fetch every page.

    Returns:
        Dict containing ``accounts`` and a ``pagination`` metadata block, or a
        standardized error response.
    """
    try:
        request_params: Dict[str, Any] = {}
        if max_results is not None:
            request_params['MaxResults'] = max_results
        if next_token:
            request_params['NextToken'] = next_token

        client = _create_organizations_client()

        accounts, pagination = await paginate_aws_response(
            ctx,
            'ListAccounts',
            client.list_accounts,
            request_params,
            'Accounts',
            max_pages=max_pages,
        )

        formatted_accounts = _format_accounts(accounts)
        await ctx.info(f'Successfully retrieved {len(formatted_accounts)} organization accounts')

        # A large organization can return many accounts, so the shared size
        # threshold decides whether to offload the list to session SQL.
        converted = await convert_response_if_needed(
            ctx,
            {'accounts': formatted_accounts, 'pagination': pagination},
            'organizations_list_accounts',
            pagination_token_key='NextToken',
            pagination=pagination,
        )
        return format_response('success', converted)

    except Exception as e:
        return await handle_aws_error(ctx, e, 'ListAccounts', 'Organizations')


async def describe_account(
    ctx: Context,
    account_id: str,
) -> Dict[str, Any]:
    """Describe a single organization account, including its join metadata.

    Args:
        ctx: The MCP context object.
        account_id: The 12-digit ID of the account to describe (required).

    Returns:
        Dict containing the single ``account``, or a standardized error response.
    """
    try:
        client = _create_organizations_client()
        response = client.describe_account(AccountId=account_id)
        formatted = _format_accounts([response.get('Account', {})])
        await ctx.info(f'Successfully described account {account_id}')
        return format_response('success', {'account': formatted[0] if formatted else {}})

    except Exception as e:
        return await handle_aws_error(ctx, e, 'DescribeAccount', 'Organizations')
