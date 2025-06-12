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

"""Tool for describing CloudWatch Logs log groups."""

from ...common.connection import CloudWatchLogsConnectionManager
from ...common.decorators import handle_exceptions
from ...common.server import mcp
from typing import Any, Dict, List, Optional


@mcp.tool(name='describe-log-groups')
@handle_exceptions
async def describe_log_groups(
    account_identifiers: Optional[List[str]] = None,
    log_group_name_prefix: Optional[str] = None,
    log_group_name_pattern: Optional[str] = None,
    include_linked_accounts: Optional[bool] = None,
    log_group_class: Optional[str] = None,
    log_group_identifiers: Optional[List[str]] = None,
    starting_token: Optional[str] = None,
    page_size: Optional[int] = None,
    max_items: Optional[int] = None,
) -> Dict[str, Any]:
    """Describe CloudWatch Logs log groups.

    Args:
        account_identifiers: List of account IDs to filter log groups
        log_group_name_prefix: Prefix to filter log groups by name
        log_group_name_pattern: Pattern to match log group names
        include_linked_accounts: Whether to include log groups from linked accounts
        log_group_class: Filter by log group class (STANDARD or INFREQUENT_ACCESS)
        log_group_identifiers: List of log group identifiers to describe
        starting_token: Token for starting the list from a specific page
        page_size: Number of records to include in each page
        max_items: Maximum number of records to return in total

    Returns:
        Dict containing log groups information or error details
    """
    client = CloudWatchLogsConnectionManager.get_connection()

    # Build request parameters
    params: Dict[str, Any] = {}

    # Add optional parameters
    if account_identifiers:
        params['accountIdentifiers'] = account_identifiers
    if log_group_name_prefix:
        params['logGroupNamePrefix'] = log_group_name_prefix
    if log_group_name_pattern:
        params['logGroupNamePattern'] = log_group_name_pattern
    if include_linked_accounts is not None:
        params['includeLinkedAccounts'] = include_linked_accounts
    if log_group_class:
        params['logGroupClass'] = log_group_class
    if log_group_identifiers:
        params['logGroupIdentifiers'] = log_group_identifiers
    if starting_token:
        params['nextToken'] = starting_token
    if page_size:
        params['limit'] = page_size

    # If max_items is set, we need to handle pagination manually
    if max_items is not None:
        log_groups = []
        items_remaining = max_items

        while True:
            # Adjust limit if we're close to max_items
            if page_size and items_remaining < page_size:
                params['limit'] = items_remaining

            # Make API call
            response = client.describe_log_groups(**params)
            current_groups = response.get('logGroups', [])

            # Add groups up to max_items
            if len(current_groups) > items_remaining:
                log_groups.extend(current_groups[:items_remaining])
                next_token = response.get('nextToken')  # Save for result
                break
            else:
                log_groups.extend(current_groups)
                items_remaining -= len(current_groups)

            # Check if we need to continue
            if 'nextToken' not in response or items_remaining <= 0:
                next_token = response.get('nextToken')
                break

            # Update token for next iteration
            params['nextToken'] = response['nextToken']

        result = {'logGroups': log_groups}
        if next_token:
            result['nextToken'] = next_token
        return result

    # If max_items is not set, make a single API call
    response = client.describe_log_groups(**params)

    # Extract relevant information
    log_groups = response.get('logGroups', [])
    next_token = response.get('nextToken')

    result = {'logGroups': log_groups}

    if next_token:
        result['nextToken'] = next_token

    return result
