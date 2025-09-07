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

"""AWS Billing and Cost Management Pricing Calculator tools for the AWS Billing and Cost Management MCP server.

Updated to use shared utility functions.
"""

import json
from ..utilities.aws_service_base import create_aws_client, format_response, handle_aws_error
from datetime import datetime
from fastmcp import Context, FastMCP
from typing import Any, Dict, Optional


# Constants
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S UTC'
UTC_TIMEZONE_OFFSET = '+00:00'
PREFERENCES_NOT_CONFIGURED_ERROR = 'BCM Pricing Calculator preferences are not configured. Please configure preferences before using this service.'

bcm_pricing_calculator_server = FastMCP(
    name='bcm-pricing-calculator-tools',
    instructions='BCM Pricing Calculator tools for working with AWS Billing and Cost Management Pricing Calculator API',
)


async def get_preferences(ctx: Context, bcm_client) -> bool:
    """Check if BCM Pricing Calculator preferences are properly configured.

    Args:
        ctx: The MCP context object
        bcm_client: The BCM Pricing Calculator client

    Returns:
        bool: True if preferences are valid, False otherwise
    """
    try:
        await ctx.info('Checking BCM Pricing Calculator preferences...')
        response = bcm_client.get_preferences()

        # Check if the response contains valid preferences for any account type
        if response and (
            'managementAccountRateTypeSelections' in response
            or 'memberAccountRateTypeSelections' in response
            or 'standaloneAccountRateTypeSelections' in response
        ):
            # Log which type of account preferences were found
            account_types = []
            if 'managementAccountRateTypeSelections' in response:
                account_types.append('management account')
            if 'memberAccountRateTypeSelections' in response:
                account_types.append('member account')
            if 'standaloneAccountRateTypeSelections' in response:
                account_types.append('standalone account')

            await ctx.info(
                f'BCM Pricing Calculator preferences are properly configured for: {", ".join(account_types)}'
            )
            return True
        else:
            await ctx.error(
                'BCM Pricing Calculator preferences are not configured - no rate type selections found'
            )
            return False

    except Exception as e:
        # Use shared error handler for consistent error handling
        error_response = await handle_aws_error(
            ctx, e, 'get_preferences', 'BCM Pricing Calculator'
        )
        await ctx.error(
            f'Failed to check BCM Pricing Calculator preferences: {error_response.get("data", {}).get("error", str(e))}'
        )
        return False


async def describe_workload_estimates(
    ctx: Context,
    created_after: Optional[str] = None,
    created_before: Optional[str] = None,
    expires_after: Optional[str] = None,
    expires_before: Optional[str] = None,
    status_filter: Optional[str] = None,
    name_filter: Optional[str] = None,
    name_match_option: str = 'CONTAINS',
    next_token: Optional[str] = None,
    max_results: int = 25,
) -> Dict[str, Any]:
    """Core business logic for listing workload estimates.

    Args:
        ctx: The MCP context object
        created_after: Filter estimates created after this timestamp (ISO format: YYYY-MM-DDTHH:MM:SS)
        created_before: Filter estimates created before this timestamp (ISO format: YYYY-MM-DDTHH:MM:SS)
        expires_after: Filter estimates expiring after this timestamp (ISO format: YYYY-MM-DDTHH:MM:SS)
        expires_before: Filter estimates expiring before this timestamp (ISO format: YYYY-MM-DDTHH:MM:SS)
        status_filter: Filter by status (UPDATING, VALID, INVALID, ACTION_NEEDED)
        name_filter: Filter by name (supports partial matching)
        name_match_option: Match option for name filter (EQUALS, STARTS_WITH, CONTAINS)
        next_token: Token for pagination
        max_results: Maximum number of results to return (1-100, default: 100)

    Returns:
        Dict containing the workload estimates information
    """
    try:
        # Log the request
        await ctx.info(
            f'Listing workload estimates (max_results={max_results}, '
            f'status_filter={status_filter}, name_filter={name_filter})'
        )

        # Create BCM Pricing Calculator client
        bcm_client = create_aws_client('bcm-pricing-calculator')

        # Check preferences before proceeding
        if not await get_preferences(ctx, bcm_client):
            return format_response(
                'error',
                {
                    'error': PREFERENCES_NOT_CONFIGURED_ERROR,
                    'error_code': 'PREFERENCES_NOT_CONFIGURED',
                },
            )

        # Build request parameters
        request_params: Dict[str, Any] = {'maxResults': int(max_results)}

        if next_token:
            request_params['nextToken'] = next_token

        # Add created at filter
        if created_after or created_before:
            created_filter = {}
            if created_after:
                created_filter['afterTimestamp'] = datetime.fromisoformat(
                    created_after.replace('Z', UTC_TIMEZONE_OFFSET)
                )
            if created_before:
                created_filter['beforeTimestamp'] = datetime.fromisoformat(
                    created_before.replace('Z', UTC_TIMEZONE_OFFSET)
                )
            request_params['createdAtFilter'] = created_filter

        # Add expires at filter
        if expires_after or expires_before:
            expires_filter = {}
            if expires_after:
                expires_filter['afterTimestamp'] = datetime.fromisoformat(
                    expires_after.replace('Z', UTC_TIMEZONE_OFFSET)
                )
            if expires_before:
                expires_filter['beforeTimestamp'] = datetime.fromisoformat(
                    expires_before.replace('Z', UTC_TIMEZONE_OFFSET)
                )
            request_params['expiresAtFilter'] = expires_filter

        # Add additional filters
        filters = []
        if status_filter:
            filters.append({'name': 'STATUS', 'values': [status_filter], 'matchOption': 'EQUALS'})

        if name_filter:
            filters.append(
                {'name': 'NAME', 'values': [name_filter], 'matchOption': name_match_option}
            )

        if filters:
            request_params['filters'] = filters

        await ctx.info(
            f'Making API call with parameters: {json.dumps(request_params, default=str)}'
        )

        # Call the API
        response = bcm_client.list_workload_estimates(**request_params)

        # Format the response
        formatted_estimates = [
            format_workload_estimate_response(estimate) for estimate in response.get('items', [])
        ]

        await ctx.info(f'Retrieved {len(formatted_estimates)} workload estimates')

        # Return success response using shared format_response utility
        return format_response(
            'success',
            {
                'workload_estimates': formatted_estimates,
                'total_count': len(formatted_estimates),
                'next_token': response.get('nextToken'),
                'has_more_results': bool(response.get('nextToken')),
            },
        )

    except Exception as e:
        # Use shared error handler for all exceptions (ClientError and others)
        return await handle_aws_error(ctx, e, 'list_workload_estimates', 'BCM Pricing Calculator')


@bcm_pricing_calculator_server.tool(
    name='list_workload_estimates',
    description="""Lists all workload estimates for the account using the AWS Billing and Cost Management Pricing Calculator API.
    The AWS Billing and Cost Management Pricing Calculator is available within an AWS account. This is NOT the same as AWS
    Pricing Calculator available at https://calculator.aws

This tool uses the ListWorkloadEstimates API to retrieve workload estimates with optional filtering capabilities.

The API returns information about:
- Workload estimate IDs and names
- Creation and expiration timestamps
- Rate types and timestamps. Possible rate types are BEFORE_DISCOUNTS, AFTER_DISCOUNTS, AFTER_DISCOUNTS_AND_COMMITMENTS
- Current status of estimates. Possible values are UPDATIN, VALID, INVALID, ACTION_NEEDED
- Total estimated costs and currency
- Failure messages if applicable

FILTERING OPTIONS:
- createdAtFilter: Filter by creation date (afterTimestamp, beforeTimestamp)
- expiresAtFilter: Filter by expiration date (afterTimestamp, beforeTimestamp)
- filters: Additional filters by STATUS or NAME with match options (EQUALS, STARTS_WITH, CONTAINS)

PAGINATION:
- Use nextToken for pagination through large result sets
- maxResults controls the number of results per page (default: 25)

The tool automatically handles pagination and provides formatted results for easy analysis.""",
)
async def list_workload_estimates(
    ctx: Context,
    created_after: Optional[str] = None,
    created_before: Optional[str] = None,
    expires_after: Optional[str] = None,
    expires_before: Optional[str] = None,
    status_filter: Optional[str] = None,
    name_filter: Optional[str] = None,
    name_match_option: str = 'CONTAINS',
    next_token: Optional[str] = None,
    max_results: int = 25,
) -> Dict[str, Any]:
    """Lists all workload estimates for the account.

    Args:
        ctx: The MCP context object
        created_after: Filter estimates created after this timestamp (ISO format: YYYY-MM-DDTHH:MM:SS)
        created_before: Filter estimates created before this timestamp (ISO format: YYYY-MM-DDTHH:MM:SS)
        expires_after: Filter estimates expiring after this timestamp (ISO format: YYYY-MM-DDTHH:MM:SS)
        expires_before: Filter estimates expiring before this timestamp (ISO format: YYYY-MM-DDTHH:MM:SS)
        status_filter: Filter by status (UPDATING, VALID, INVALID, ACTION_NEEDED)
        name_filter: Filter by name (supports partial matching)
        name_match_option: Match option for name filter (EQUALS, STARTS_WITH, CONTAINS)
        next_token: Token for pagination
        max_results: Maximum number of results to return (1-100, default: 100)

    Returns:
        Dict containing the workload estimates information. This contains the following information about a workload estimate:
        id: The unique identifier of the workload estimate.
        name: The name of the workload estimate.
        status: The current status of the workload estimate. Possible values are UPDATIN, VALID, INVALID, ACTION_NEEDED
    """
    return await describe_workload_estimates(
        ctx,
        created_after,
        created_before,
        expires_after,
        expires_before,
        status_filter,
        name_filter,
        name_match_option,
        next_token,
        max_results,
    )


async def describe_workload_estimate(
    ctx: Context,
    identifier: str,
) -> Dict[str, Any]:
    """Core business logic for retrieving details of a specific workload estimate.

    Args:
        ctx: The MCP context object
        identifier: The unique identifier of the workload estimate to retrieve

    Returns:
        Dict containing the workload estimate details
    """
    try:
        # Log the request
        await ctx.info(f'Getting workload estimate details for identifier: {identifier}')

        # Create BCM Pricing Calculator client
        bcm_client = create_aws_client('bcm-pricing-calculator')

        # Check preferences before proceeding
        if not await get_preferences(ctx, bcm_client):
            return format_response(
                'error',
                {
                    'error': PREFERENCES_NOT_CONFIGURED_ERROR,
                    'error_code': 'PREFERENCES_NOT_CONFIGURED',
                },
            )

        # Build request parameters
        request_params: Dict[str, Any] = {'identifier': identifier}

        await ctx.info(
            f'Making API call with parameters: {json.dumps(request_params, default=str)}'
        )

        # Call the API
        response = bcm_client.get_workload_estimate(**request_params)

        # Format the single workload estimate response
        formatted_estimate = format_workload_estimate_response(response)

        await ctx.info(f'Retrieved workload estimate: {formatted_estimate.get("name", "Unknown")}')

        # Return success response using shared format_response utility
        return format_response(
            'success',
            {
                'workload_estimate': formatted_estimate,
                'identifier': identifier,
            },
        )

    except Exception as e:
        # Use shared error handler for all exceptions (ClientError and others)
        return await handle_aws_error(ctx, e, 'get_workload_estimate', 'BCM Pricing Calculator')


@bcm_pricing_calculator_server.tool(
    name='get_workload_estimate',
    description="""Retrieves details of a specific workload estimate using the AWS Billing and Cost Management Pricing Calculator API.

This tool uses the GetWorkloadEstimate API to retrieve detailed information about a single workload estimate.

The API returns comprehensive information about:
- Workload estimate ID and name
- Creation and expiration timestamps
- Rate type and timestamp
- Current status of the estimate
- Total estimated cost and currency
- Failure message if applicable

REQUIRED PARAMETER:
- identifier: The unique identifier of the workload estimate to retrieve

POSSIBLE STATUSES:
- UPDATING: The estimate is being updated
- VALID: The estimate is valid and up-to-date
- INVALID: The estimate is invalid
- ACTION_NEEDED: User action is required

The tool provides formatted results with human-readable timestamps and cost information.""",
)
async def get_workload_estimate(
    ctx: Context,
    identifier: str,
) -> Dict[str, Any]:
    """Retrieves details of a specific workload estimate.

    Args:
        ctx: The MCP context object
        identifier: The unique identifier of the workload estimate to retrieve

    Returns:
        Dict containing the workload estimate details
    """
    return await describe_workload_estimate(ctx, identifier)


async def describe_workload_estimate_usage(
    ctx: Context,
    workload_estimate_id: str,
    usage_account_id_filter: Optional[str] = None,
    service_code_filter: Optional[str] = None,
    usage_type_filter: Optional[str] = None,
    operation_filter: Optional[str] = None,
    location_filter: Optional[str] = None,
    usage_group_filter: Optional[str] = None,
    next_token: Optional[str] = None,
    max_results: int = 25,
) -> Dict[str, Any]:
    """Core business logic for listing usage entries for a specific workload estimate.

    Args:
        ctx: The MCP context object
        workload_estimate_id: The unique identifier of the workload estimate
        usage_account_id_filter: Filter by AWS account ID
        service_code_filter: Filter by AWS service code (e.g., AmazonEC2, AmazonS3)
        usage_type_filter: Filter by usage type
        operation_filter: Filter by operation name
        location_filter: Filter by location/region
        usage_group_filter: Filter by usage group
        next_token: Token for pagination
        max_results: Maximum number of results to return (1-300, default: 25)

    Returns:
        Dict containing the workload estimate usage information
    """
    try:
        # Log the request
        await ctx.info(
            f'Listing workload estimate usage (workload_estimate_id={workload_estimate_id}, '
            f'max_results={max_results}, service_code_filter={service_code_filter})'
        )

        # Create BCM Pricing Calculator client
        bcm_client = create_aws_client('bcm-pricing-calculator')

        # Check preferences before proceeding
        if not await get_preferences(ctx, bcm_client):
            return format_response(
                'error',
                {
                    'error': PREFERENCES_NOT_CONFIGURED_ERROR,
                    'error_code': 'PREFERENCES_NOT_CONFIGURED',
                },
            )

        # Build request parameters
        request_params: Dict[str, Any] = {
            'workloadEstimateId': workload_estimate_id,
            'maxResults': int(max_results),
        }

        if next_token:
            request_params['nextToken'] = next_token

        # Add filters
        filters = []
        if usage_account_id_filter:
            filters.append(
                {
                    'name': 'USAGE_ACCOUNT_ID',
                    'values': [usage_account_id_filter],
                    'matchOption': 'EQUALS',
                }
            )

        if service_code_filter:
            filters.append(
                {'name': 'SERVICE_CODE', 'values': [service_code_filter], 'matchOption': 'EQUALS'}
            )

        if usage_type_filter:
            filters.append(
                {'name': 'USAGE_TYPE', 'values': [usage_type_filter], 'matchOption': 'CONTAINS'}
            )

        if operation_filter:
            filters.append(
                {'name': 'OPERATION', 'values': [operation_filter], 'matchOption': 'CONTAINS'}
            )

        if location_filter:
            filters.append(
                {'name': 'LOCATION', 'values': [location_filter], 'matchOption': 'EQUALS'}
            )

        if usage_group_filter:
            filters.append(
                {'name': 'USAGE_GROUP', 'values': [usage_group_filter], 'matchOption': 'EQUALS'}
            )

        if filters:
            request_params['filters'] = filters

        await ctx.info(
            f'Making API call with parameters: {json.dumps(request_params, default=str)}'
        )

        # Call the API
        response = bcm_client.list_workload_estimate_usage(**request_params)

        # Format the response
        formatted_usage_items = [
            format_usage_item_response(item) for item in response.get('items', [])
        ]

        await ctx.info(f'Retrieved {len(formatted_usage_items)} usage items')

        # Return success response using shared format_response utility
        return format_response(
            'success',
            {
                'usage_items': formatted_usage_items,
                'total_count': len(formatted_usage_items),
                'next_token': response.get('nextToken'),
                'has_more_results': bool(response.get('nextToken')),
                'workload_estimate_id': workload_estimate_id,
            },
        )

    except Exception as e:
        # Use shared error handler for all exceptions (ClientError and others)
        return await handle_aws_error(
            ctx, e, 'list_workload_estimate_usage', 'BCM Pricing Calculator'
        )


@bcm_pricing_calculator_server.tool(
    name='list_workload_estimate_usage',
    description="""Lists usage entries for a specific workload estimate using the AWS Billing and Cost Management Pricing Calculator API.

This tool uses the ListWorkloadEstimateUsage API to retrieve detailed usage information for a workload estimate.

The API returns information about:
- Usage entries with service codes and operation details
- Usage amounts and units
- Cost estimates for each usage entry
- Historical usage data if available
- Usage account IDs and locations

REQUIRED PARAMETER:
- workload_estimate_id: The unique identifier of the workload estimate

OPTIONAL PARAMETERS:
- filters: Filter usage entries by various criteria
- next_token: Token for pagination through large result sets
- max_results: Maximum number of results to return (default: 25, max: 100)

FILTERING OPTIONS:
- USAGE_ACCOUNT_ID: Filter by AWS account ID
- SERVICE_CODE: Filter by AWS service code (e.g., AmazonEC2, AmazonS3)
- USAGE_TYPE: Filter by usage type
- OPERATION: Filter by operation name
- LOCATION: Filter by location/region
- USAGE_GROUP: Filter by usage group
- HISTORICAL_*: Filter by historical usage criteria

The tool automatically handles pagination and provides formatted results for easy analysis.""",
)
async def list_workload_estimate_usage(
    ctx: Context,
    workload_estimate_id: str,
    usage_account_id_filter: Optional[str] = None,
    service_code_filter: Optional[str] = None,
    usage_type_filter: Optional[str] = None,
    operation_filter: Optional[str] = None,
    location_filter: Optional[str] = None,
    usage_group_filter: Optional[str] = None,
    next_token: Optional[str] = None,
    max_results: int = 25,
) -> Dict[str, Any]:
    """Lists usage entries for a specific workload estimate.

    Args:
        ctx: The MCP context object
        workload_estimate_id: The unique identifier of the workload estimate
        usage_account_id_filter: Filter by AWS account ID
        service_code_filter: Filter by AWS service code (e.g., AmazonEC2, AmazonS3)
        usage_type_filter: Filter by usage type
        operation_filter: Filter by operation name
        location_filter: Filter by location/region
        usage_group_filter: Filter by usage group
        next_token: Token for pagination
        max_results: Maximum number of results to return (1-300, default: 25)

    Returns:
        Dict containing the workload estimate usage information
    """
    return await describe_workload_estimate_usage(
        ctx,
        workload_estimate_id,
        usage_account_id_filter,
        service_code_filter,
        usage_type_filter,
        operation_filter,
        location_filter,
        usage_group_filter,
        next_token,
        max_results,
    )


def format_usage_item_response(usage_item: Dict[str, Any]) -> Dict[str, Any]:
    """Formats a single usage item object from the list_workload_estimate_usage API response.

    Args:
        usage_item: Single usage item object from AWS Billing and Cost Management Pricing Calculator.

    Returns:
        Formatted usage item object.
    """
    formatted_item = {
        'id': usage_item.get('id'),
        'service_code': usage_item.get('serviceCode'),
        'usage_type': usage_item.get('usageType'),
        'operation': usage_item.get('operation'),
        'location': usage_item.get('location'),
        'usage_account_id': usage_item.get('usageAccountId'),
        'group': usage_item.get('group'),
        'status': usage_item.get('status'),
        'currency': usage_item.get('currency', 'USD'),
    }

    # Add quantity information
    if 'quantity' in usage_item and usage_item['quantity']:
        quantity = usage_item['quantity']
        formatted_item['quantity'] = {
            'amount': quantity.get('amount'),
            'unit': quantity.get('unit'),
            'formatted': f'{quantity.get("amount", 0):,.2f} {quantity.get("unit", "")}'
            if quantity.get('amount') is not None
            else None,
        }

    # Add cost information
    if 'cost' in usage_item and usage_item['cost'] is not None:
        cost = usage_item['cost']
        currency = usage_item.get('currency', 'USD')
        formatted_item['cost'] = {
            'amount': cost,
            'currency': currency,
            'formatted': f'{currency} {cost:,.2f}',
        }

    # Add historical usage information if present
    if 'historicalUsage' in usage_item and usage_item['historicalUsage']:
        historical = usage_item['historicalUsage']
        formatted_historical = {
            'service_code': historical.get('serviceCode'),
            'usage_type': historical.get('usageType'),
            'operation': historical.get('operation'),
            'location': historical.get('location'),
            'usage_account_id': historical.get('usageAccountId'),
        }

        # Add bill interval if present
        if 'billInterval' in historical and historical['billInterval']:
            interval = historical['billInterval']
            formatted_historical['bill_interval'] = {
                'start': interval.get('start').isoformat() if interval.get('start') else None,
                'end': interval.get('end').isoformat() if interval.get('end') else None,
            }

        formatted_item['historical_usage'] = formatted_historical

    # Add status indicator
    status = usage_item.get('status')
    if status:
        status_indicators = {
            'VALID': 'Valid',
            'INVALID': 'Invalid',
            'STALE': 'Stale',
        }
        formatted_item['status_indicator'] = status_indicators.get(status, f'❓ {status}')

    return formatted_item


def format_workload_estimate_response(estimate: Dict[str, Any]) -> Dict[str, Any]:
    """Formats a single workload estimate object from the get_workload_estimate API response.

    Args:
        estimate: Single workload estimate object from the AWS API.

    Returns:
        Formatted workload estimate object.
    """
    formatted_estimate = {
        'id': estimate.get('id'),
        'name': estimate.get('name'),
        'status': estimate.get('status'),
        'rate_type': estimate.get('rateType'),
    }

    # Add timestamps with formatting
    if 'createdAt' in estimate:
        created_at = estimate['createdAt']
        formatted_estimate['created_at'] = {
            'timestamp': created_at.isoformat()
            if isinstance(created_at, datetime)
            else created_at,
            'formatted': (
                created_at.strftime(DATETIME_FORMAT)
                if isinstance(created_at, datetime)
                else created_at
            ),
        }

    if 'expiresAt' in estimate:
        expires_at = estimate['expiresAt']
        formatted_estimate['expires_at'] = {
            'timestamp': expires_at.isoformat()
            if isinstance(expires_at, datetime)
            else expires_at,
            'formatted': (
                expires_at.strftime(DATETIME_FORMAT)
                if isinstance(expires_at, datetime)
                else expires_at
            ),
        }

    if 'rateTimestamp' in estimate:
        rate_timestamp = estimate['rateTimestamp']
        formatted_estimate['rate_timestamp'] = {
            'timestamp': rate_timestamp.isoformat()
            if isinstance(rate_timestamp, datetime)
            else rate_timestamp,
            'formatted': (
                rate_timestamp.strftime(DATETIME_FORMAT)
                if isinstance(rate_timestamp, datetime)
                else rate_timestamp
            ),
        }

    # Add cost information
    if 'totalCost' in estimate:
        total_cost = estimate['totalCost']
        cost_currency = estimate.get('costCurrency', 'USD')
        formatted_estimate['cost'] = {
            'amount': total_cost,
            'currency': cost_currency,
            'formatted': f'{cost_currency} {total_cost:,.2f}' if total_cost is not None else None,
        }

    # Add failure message if present
    if 'failureMessage' in estimate and estimate['failureMessage']:
        formatted_estimate['failure_message'] = estimate['failureMessage']

    # Add status indicator
    status = estimate.get('status')
    if status:
        status_indicators = {
            'VALID': 'Valid',
            'UPDATING': 'Updating',
            'INVALID': 'Invalid',
            'ACTION_NEEDED': 'Action Needed',
        }
        formatted_estimate['status_indicator'] = status_indicators.get(status, f'❓ {status}')

    return formatted_estimate
