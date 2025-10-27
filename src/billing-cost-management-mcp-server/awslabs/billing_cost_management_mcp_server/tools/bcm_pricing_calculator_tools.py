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
from ..utilities.aws_service_base import (
    create_aws_client,
    format_response,
    handle_aws_error,
    paginate_aws_response,
)
from datetime import datetime
from fastmcp import Context, FastMCP
from typing import Any, Dict, Optional


# Constants
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S UTC'
UTC_TIMEZONE_OFFSET = '+00:00'
BCM_PRICING_CALCULATOR_SERVICE_NAME = 'BCM Pricing Calculator'
PREFERENCES_NOT_CONFIGURED_ERROR = 'BCM Pricing Calculator preferences are not configured. Please configure preferences before using this service.'

bcm_pricing_calculator_server = FastMCP(
    name='bcm-pricing-calc-tools',
    instructions=f'{BCM_PRICING_CALCULATOR_SERVICE_NAME} tools for working with AWS Billing and Cost Management Pricing Calculator API',
)


async def bcm_pricing_calc_core(
    ctx: Context,
    operation: str,
    identifier: Optional[str] = None,
    created_after: Optional[str] = None,
    created_before: Optional[str] = None,
    expires_after: Optional[str] = None,
    expires_before: Optional[str] = None,
    status_filter: Optional[str] = None,
    name_filter: Optional[str] = None,
    name_match_option: str = 'CONTAINS',
    usage_account_id_filter: Optional[str] = None,
    service_code_filter: Optional[str] = None,
    usage_type_filter: Optional[str] = None,
    operation_filter: Optional[str] = None,
    location_filter: Optional[str] = None,
    usage_group_filter: Optional[str] = None,
    next_token: Optional[str] = None,
    max_results: Optional[int] = None,
    max_pages: Optional[int] = None,
) -> Dict[str, Any]:
    """Core business logic for BCM Pricing Calculator.

    Args:
        ctx: The MCP context object
        operation: The operation to perform
        identifier: Identifier for specific operations
        created_after: Filter estimates created after this timestamp
        created_before: Filter estimates created before this timestamp
        expires_after: Filter estimates expiring after this timestamp
        expires_before: Filter estimates expiring before this timestamp
        status_filter: Filter by status
        name_filter: Filter by name
        name_match_option: Match option for name filter
        usage_account_id_filter: Filter by AWS account ID
        service_code_filter: Filter by AWS service code
        usage_type_filter: Filter by usage type
        operation_filter: Filter by operation name
        location_filter: Filter by location/region
        usage_group_filter: Filter by usage group
        next_token: Token for pagination
        max_results: Maximum number of results to return
        max_pages: Maximum number of API calls to make

    Returns:
        Dict containing the response data
    """
    try:
        # Log the request
        await ctx.info(f'Received BCM Pricing Calculator operation: {operation}')

        # Check if the operation is valid
        if operation not in [
            'get_workload_estimate',
            'list_workload_estimates',
            'list_workload_estimate_usage',
            'get_preferences',
        ]:
            return format_response(
                'error',
                {'invalid_parameter': 'operation'},
                f'Invalid operation: {operation}. Valid operations are: get_workload_estimates, get_preferences, describe_workload_estimates',
            )

        # Call the appropriate operation
        if operation == 'get_workload_estimate':
            return await get_workload_estimate(ctx, identifier)
        elif operation == 'list_workload_estimates':
            return await list_workload_estimates(
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
                max_pages,
            )
        elif operation == 'list_workload_estimate_usage':
            return await list_workload_estimate_usage(
                ctx,
                identifier,
                usage_account_id_filter,
                service_code_filter,
                usage_type_filter,
                operation_filter,
                location_filter,
                usage_group_filter,
                next_token,
                max_results,
                max_pages,
            )
        elif operation == 'get_preferences':
            preferences_result = await get_preferences(ctx)
            if 'error' in preferences_result:
                return format_response(
                    'error',
                    {'error': preferences_result['error']},
                    preferences_result['error'],
                )
            else:
                return format_response(
                    'success',
                    {
                        'message': 'Preferences are properly configured',
                        'account_types': preferences_result['account_types'],
                    },
                )
        else:
            return format_response('error', {'message': f'Unknown operation: {operation}'})

    except Exception as e:
        # Use shared error handler for consistent error handling
        error_response = await handle_aws_error(
            ctx, e, operation, 'AWS Billing and Cost Management Pricing Calculator'
        )
        await ctx.error(
            f'Failed to process AWS Billing and Cost Management Pricing Calculator request: {error_response.get("data", {}).get("error", str(e))}'
        )
        return format_response(
            'error',
            {'error': error_response.get('data', {}).get('error', str(e))},
            f'Failed to process AWS Billing and Cost Management Pricing Calculator request: {error_response.get("data", {}).get("error", str(e))}',
        )


@bcm_pricing_calculator_server.tool(
    name='bcm-pricing-calc',
    description="""Allows working with workload estimates using the AWS Billing and Cost Management Pricing Calculator API.

IMPORTANT USAGE GUIDELINES:
- Always first check the rate preference setting for the authorized principal by calling the get_preferences operation.
- DO NOT state assumptions about Free Tier API

USE THIS TOOL FOR:
- Listing available **workload estimates** for the logged in account.
- **Filter list of available workload estimates** using name, status, created date, or expiration date.
- Get **details of a workload estimate**.
- Get the list of **services, usage type, operation, and usage amount** modeled within a workload estimate.
- Get **rate preferences** set for Pricing Calculator. These rate preferences denote what rate preferences can be used by each account type in your organization.

## OPERATIONS

1) list_workload_estimates - list of available workload estimates
   Required: operation="list_workload_estimates"
   Optional: created_after, created_before, expires_after, expires_before, status_filter, name_filter, name_match_option, next_token, max_results
   Returns: List of all workload estimates for the account.

2) get_workload_estimate - get details of a workload estimate
   Required: operation="get_workload_estimate", identifier
   Returns: Details of a specific workload estimate.

3) list_workload_estimate_usage - list of modeled usage lines within a workload estimate
   Required: operation="get_workload_estimate", identifier
   Optional: usage_account_id_filter, service_code_filter, usage_type_filter, operation_filter, location_filter, usage_group_filter, next_token, max_results
   Returns: List of usage associated with a workload estimate.

4) get_preferences - get the rate preferences available to an account
   Required: operation="get_preferences"
   Returns: Retrieves the current preferences for AWS Billing and Cost Management Pricing Calculator.
""",
)
async def bcm_pricing_calc(
    ctx: Context,
    operation: str,
    identifier: Optional[str] = None,
    created_after: Optional[str] = None,
    created_before: Optional[str] = None,
    expires_after: Optional[str] = None,
    expires_before: Optional[str] = None,
    status_filter: Optional[str] = None,
    name_filter: Optional[str] = None,
    name_match_option: str = 'CONTAINS',
    usage_account_id_filter: Optional[str] = None,
    service_code_filter: Optional[str] = None,
    usage_type_filter: Optional[str] = None,
    operation_filter: Optional[str] = None,
    location_filter: Optional[str] = None,
    usage_group_filter: Optional[str] = None,
    next_token: Optional[str] = None,
    max_results: Optional[int] = None,
    max_pages: Optional[int] = None,
) -> Dict[str, Any]:
    """FastMCP tool wrapper for BCM Pricing Calculator operations."""
    # need this wrapper to improve code coverage as FastMCP decorated methods cannot be tested directly.
    return await bcm_pricing_calc_core(
        ctx,
        operation,
        identifier,
        created_after,
        created_before,
        expires_after,
        expires_before,
        status_filter,
        name_filter,
        name_match_option,
        usage_account_id_filter,
        service_code_filter,
        usage_type_filter,
        operation_filter,
        location_filter,
        usage_group_filter,
        next_token,
        max_results,
        max_pages,
    )


async def get_preferences(ctx: Context) -> dict:
    """Check if BCM Pricing Calculator preferences are properly configured.

    Args:
        ctx: The MCP context object

    Returns:
        dict: Contains either 'account_types' list if preferences are valid,
              or 'error' message if not found or error occurred
    """
    try:
        # Get the BCM Pricing Calculator client
        bcm_client = create_aws_client('bcm-pricing-calculator', region_name='us-east-1')

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
            return {'account_types': account_types}
        else:
            error_msg = 'BCM Pricing Calculator preferences are not configured - no rate type selections found'
            await ctx.error(error_msg)
            return {'error': error_msg}  # the `error` moniker here is used in referenced method.

    except Exception as e:
        # Use shared error handler for consistent error handling
        error_response = await handle_aws_error(
            ctx, e, 'get_preferences', BCM_PRICING_CALCULATOR_SERVICE_NAME
        )
        error_msg = f'Failed to check BCM Pricing Calculator preferences: {error_response.get("data", {}).get("error", str(e))}'
        await ctx.error(error_msg)
        return {'error': error_msg}


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
    max_results: Optional[int] = None,
    max_pages: Optional[int] = None,
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
        max_results: Maximum number of results to return
        max_pages: Maximum number of API calls to make

    Returns:
        Dict containing the workload estimates information. This contains the following information about a workload estimate:
        id: The unique identifier of the workload estimate.
        name: The name of the workload estimate.
        status: The current status of the workload estimate. Possible values are UPDATIN, VALID, INVALID, ACTION_NEEDED
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
        preferences_result = await get_preferences(ctx)
        if 'error' in preferences_result:
            return format_response(
                'error',
                {
                    'error': preferences_result['error'],
                    'error_code': 'PREFERENCES_NOT_CONFIGURED',
                },
            )

        request_params: Dict[str, Any] = {}
        # Build request parameters
        if max_results:
            request_params['maxResults'] = max_results

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

        # Handle pagination using shared utility
        if max_pages:
            # For paginated requests, use the paginate utility
            results, pagination_metadata = await paginate_aws_response(
                ctx,
                'list_workload_estimates',
                lambda **params: bcm_client.list_workload_estimates(**params),
                request_params,
                'items',
                'nextToken',
                'nextToken',
                max_pages,
            )

            # Format the response
            formatted_estimates = [
                format_workload_estimate_response(estimate) for estimate in results
            ]

            await ctx.info(f'Retrieved {len(formatted_estimates)} workload estimates')

            # Return success response with pagination metadata
            return format_response(
                'success',
                {
                    'workload_estimates': formatted_estimates,
                    'pagination': pagination_metadata,
                },
            )
        else:
            # For single page, make direct call
            response = bcm_client.list_workload_estimates(**request_params)

            # Format the response
            formatted_estimates = [
                format_workload_estimate_response(estimate)
                for estimate in response.get('items', [])
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
        return await handle_aws_error(
            ctx, e, 'list_workload_estimates', BCM_PRICING_CALCULATOR_SERVICE_NAME
        )


async def get_workload_estimate(
    ctx: Context,
    identifier: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieves details of a specific workload estimate using the AWS Billing and Cost Management Pricing Calculator API.

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

    The tool provides formatted results with human-readable timestamps and cost information.
    """
    try:
        # The reason to have the following "unnecessary" check is because how each MCP tool is registered.
        # Each MCP tool is registered with a unique name, irrespective of operations it can perform.
        # Thereby there is a single entry point that accepts params required across all operations and routes the call flow to an operation.
        # So some paramters could required for one operation while not be required for some other operation.
        # Thereby all parameters to the entry point are optional, requiring this check.
        if identifier is None:
            await ctx.error('Identifier is required when calling get_workload_estimate')
            return format_response(
                'error',
                {
                    'error': 'Identifier is required when calling get_workload_estimate',
                    'error_code': 'MISSING_PARAMETER',
                },
            )

        # Log the request
        await ctx.info(f'Getting workload estimate details for identifier: {identifier}')

        # Create BCM Pricing Calculator client
        bcm_client = create_aws_client('bcm-pricing-calculator')

        # Check preferences before proceeding
        preferences_result = await get_preferences(ctx)
        if 'error' in preferences_result:
            return format_response(
                'error',
                {
                    'error': preferences_result['error'],
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
        return await handle_aws_error(
            ctx, e, 'get_workload_estimate', BCM_PRICING_CALCULATOR_SERVICE_NAME
        )


async def list_workload_estimate_usage(
    ctx: Context,
    workload_estimate_id: Optional[str] = None,
    usage_account_id_filter: Optional[str] = None,
    service_code_filter: Optional[str] = None,
    usage_type_filter: Optional[str] = None,
    operation_filter: Optional[str] = None,
    location_filter: Optional[str] = None,
    usage_group_filter: Optional[str] = None,
    next_token: Optional[str] = None,
    max_results: Optional[int] = None,
    max_pages: Optional[int] = None,
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
        max_results: Maximum number of results to return
        max_pages: Maximum number of API calls to make

    Returns:
        Dict containing the workload estimate usage information
    """
    try:
        # The reason to have the following "unnecessary" check is because how each MCP tool is registered.
        # Each MCP tool is registered with a unique name, irrespective of operations it can perform.
        # Thereby there is a single entry point that accepts params required across all operations and routes the call flow to an operation.
        # So some paramters could required for one operation while not be required for some other operation.
        # Thereby all parameters to the entry point are optional, requiring this check.
        if workload_estimate_id is None:
            await ctx.error(
                'workload_estimate_id is required when calling list_workload_estimate_usage'
            )
            return format_response(
                'error',
                {
                    'error': 'workload_estimate_id is required when calling list_workload_estimate_usage',
                    'error_code': 'MISSING_PARAMETER',
                },
            )

        # Log the request
        await ctx.info(
            f'Listing workload estimate usage (workload_estimate_id={workload_estimate_id}, '
            f'max_results={max_results}, service_code_filter={service_code_filter})'
        )

        # Create BCM Pricing Calculator client
        bcm_client = create_aws_client('bcm-pricing-calculator')

        # Check preferences before proceeding
        preferences_result = await get_preferences(ctx)
        if 'error' in preferences_result:
            return format_response(
                'error',
                {
                    'error': preferences_result['error'],
                    'error_code': 'PREFERENCES_NOT_CONFIGURED',
                },
            )

        request_params: Dict[str, Any] = {}
        # Build request parameters
        request_params['workloadEstimateId'] = workload_estimate_id

        if max_results:
            request_params['maxResults'] = max_results

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

        # Handle pagination using shared utility
        if max_pages:
            # For paginated requests, use the paginate utility
            results, pagination_metadata = await paginate_aws_response(
                ctx,
                'list_workload_estimate_usage',
                lambda **params: bcm_client.list_workload_estimate_usage(**params),
                request_params,
                'items',
                'nextToken',
                'nextToken',
                max_pages,
            )

            # Format the response
            formatted_usage_items = [format_usage_item_response(item) for item in results]

            await ctx.info(f'Retrieved {len(formatted_usage_items)} usage items')

            # Return success response with pagination metadata
            return format_response(
                'success',
                {
                    'usage_items': formatted_usage_items,
                    'pagination': pagination_metadata,
                    'workload_estimate_id': workload_estimate_id,
                },
            )
        else:
            # For single page, make direct call
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
            ctx, e, 'list_workload_estimate_usage', BCM_PRICING_CALCULATOR_SERVICE_NAME
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
