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
    PageSpec,
    create_aws_client,
    format_response,
    handle_aws_error,
    paginate_aws_items,
    with_pagination,
)
from ..utilities.constants import PAGINATION_LIMIT_TEXT
from ..utilities.error_contract import add_retry_guidance
from datetime import datetime, timezone
from fastmcp import Context, FastMCP
from typing import Any, Dict, List, Optional, Union


# Constants
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S UTC'
UTC_TIMEZONE_OFFSET = '+00:00'
BCM_PRICING_CALCULATOR_SERVICE_NAME = 'BCM Pricing Calculator'
# The operations this tool supports, in the order presented to callers.
VALID_OPERATIONS = [
    'get_workload_estimate',
    'list_workload_estimates',
    'list_workload_estimate_usage',
    'get_preferences',
]
# WorkloadEstimateStatus values. The service matches the STATUS filter exactly and
# case-sensitively, and returns no estimates (not an error) for any other value.
VALID_WORKLOAD_ESTIMATE_STATUSES = ('UPDATING', 'VALID', 'INVALID', 'ACTION_NEEDED')
# ListWorkloadEstimates returns up to 25 estimates per page.
LIST_WORKLOAD_ESTIMATES_PAGE_SPEC = PageSpec(
    result_key='items',
    token_param='nextToken',
    token_key_in_response='nextToken',
    page_max=25,
    page_size_param='maxResults',
    # The service reports a bad caller next_token as ValidationException.
    caller_token_error_codes=frozenset({'ValidationException'}),
)
# ListWorkloadEstimateUsage returns up to 300 usage lines per page.
LIST_WORKLOAD_ESTIMATE_USAGE_PAGE_SPEC = PageSpec(
    result_key='items',
    token_param='nextToken',
    token_key_in_response='nextToken',
    page_max=300,
    page_size_param='maxResults',
    # The service reports a bad caller next_token as ValidationException.
    caller_token_error_codes=frozenset({'ValidationException'}),
)
# MatchOption values. The service rejects any other value, including other casings.
VALID_MATCH_OPTIONS = ('EQUALS', 'STARTS_WITH', 'CONTAINS')
PREFERENCES_NOT_CONFIGURED_ERROR = 'BCM Pricing Calculator preferences are not configured. Please configure preferences before using this service.'

bcm_pricing_calculator_server = FastMCP(
    name='bcm-pricing-calc-tools',
    instructions=f'{BCM_PRICING_CALCULATOR_SERVICE_NAME} tools for working with AWS Billing and Cost Management Pricing Calculator API',
)


def _preferences_error_response(preferences_result: Dict[str, Any]) -> Dict[str, Any]:
    """Build the error response for a failed get_preferences check.

    Keeps the legacy data payload and adds top-level error_type, operation, and
    service, so an AWS failure (e.g. AccessDenied) is not reported only as
    PREFERENCES_NOT_CONFIGURED.

    Args:
        preferences_result: The dict returned by get_preferences on failure.

    Returns:
        Dict containing the error response
    """
    return format_response(
        'error',
        {'error': preferences_result['error'], 'error_code': 'PREFERENCES_NOT_CONFIGURED'},
        preferences_result['error'],
        error_type=preferences_result.get('error_type', 'PREFERENCES_NOT_CONFIGURED'),
        operation='get_preferences',
        service=BCM_PRICING_CALCULATOR_SERVICE_NAME,
        retry_strategy=preferences_result.get('retry_strategy'),
        hint=preferences_result.get('hint'),
    )


async def bcm_pricing_calc_core(
    ctx: Context,
    operation: str,
    identifier: Optional[str] = None,
    created_after: Optional[str] = None,
    created_before: Optional[str] = None,
    expires_after: Optional[str] = None,
    expires_before: Optional[str] = None,
    status_filter: Optional[Union[str, List[str]]] = None,
    name_filter: Optional[str] = None,
    name_match_option: str = 'CONTAINS',
    usage_account_id_filter: Optional[str] = None,
    service_code_filter: Optional[str] = None,
    usage_type_filter: Optional[str] = None,
    operation_filter: Optional[str] = None,
    location_filter: Optional[str] = None,
    usage_group_filter: Optional[str] = None,
    next_token: Optional[str] = None,
    max_items: Optional[int] = None,
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
        status_filter: Filter by status, or a list of statuses (any of them matches)
        name_filter: Filter by name
        name_match_option: Match option for name filter (EQUALS, STARTS_WITH, CONTAINS)
        usage_account_id_filter: Filter by AWS account ID
        service_code_filter: Filter by AWS service code
        usage_type_filter: Filter by usage type
        operation_filter: Filter by operation name
        location_filter: Filter by location: usually a region code (e.g. us-east-1), or a
            Local Zone or Wavelength Zone code
        usage_group_filter: Filter by usage group
        next_token: Continuation token from a previous response (list operations only)
        max_items: Total items to return (list operations only). None fetches every page.

    Returns:
        Dict containing the response data
    """
    try:
        # Log the request
        await ctx.info(f'Received BCM Pricing Calculator operation: {operation}')

        # Check if the operation is valid
        if operation not in VALID_OPERATIONS:
            return format_response(
                'error',
                {'invalid_parameter': 'operation'},
                f'Invalid operation: {operation}. Valid operations are: {", ".join(VALID_OPERATIONS)}',
                error_type='validation_error',
                operation=operation,
                service=BCM_PRICING_CALCULATOR_SERVICE_NAME,
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
                max_items,
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
                max_items,
            )
        elif operation == 'get_preferences':
            preferences_result = await get_preferences(ctx)
            if 'error' in preferences_result:
                return _preferences_error_response(preferences_result)
            else:
                return format_response(
                    'success',
                    {
                        'message': 'Preferences are properly configured',
                        'account_types': preferences_result['account_types'],
                    },
                )
        else:
            return format_response(
                'error',
                {'message': f'Unknown operation: {operation}'},
                error_type='validation_error',
                operation=operation,
                service=BCM_PRICING_CALCULATOR_SERVICE_NAME,
            )

    except Exception as e:
        # Use shared error handler for consistent error handling
        # The guidance is derived before repackaging: it can depend on fields
        # (retry_strategy, http_status) the rebuilt response does not keep.
        error_response = add_retry_guidance(
            await handle_aws_error(ctx, e, operation, BCM_PRICING_CALCULATOR_SERVICE_NAME)
        )
        # handle_aws_error puts the message and classification at the top level.
        error_message = error_response.get('message', str(e))
        full_message = f'Failed to process AWS Billing and Cost Management Pricing Calculator request: {error_message}'
        await ctx.error(full_message)
        return format_response(
            'error',
            {'error': error_message},
            full_message,
            error_type=error_response.get('error_type', 'unknown_error'),
            operation=operation,
            service=BCM_PRICING_CALCULATOR_SERVICE_NAME,
            retry_strategy=error_response.get('retry_strategy'),
            hint=error_response.get('hint'),
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
   Optional: created_after, created_before, expires_after, expires_before, status_filter, name_filter, name_match_option, max_items, next_token
   Returns: List of all workload estimates for the account (see PAGINATION).

2) get_workload_estimate - get details of a workload estimate
   Required: operation="get_workload_estimate", identifier
   Returns: Details of a specific workload estimate.

3) list_workload_estimate_usage - list of modeled usage lines within a workload estimate
   Required: operation="list_workload_estimate_usage", identifier
   Optional: usage_account_id_filter, service_code_filter, usage_type_filter, operation_filter, location_filter, usage_group_filter, max_items, next_token
   Returns: List of usage associated with a workload estimate (see PAGINATION).

4) get_preferences - get the rate preferences available to an account
   Required: operation="get_preferences"
   Returns: Retrieves the current preferences for AWS Billing and Cost Management Pricing Calculator.

## PAGINATION (list_workload_estimates, list_workload_estimate_usage only)
- max_items: total items returned. If it is omitted, the tool fetches every page for """
    + PAGINATION_LIMIT_TEXT
    + """, then returns a partial result. Pass it, or narrow the filters, when an estimate can have many usage lines.
- A partial result has `complete_dataset: false` and a warning. Call again with a larger max_items, continue with next_token (the `pagination.next_token` from that response, sent with every other parameter unchanged), or state in the answer that the result is partial.
- Counts cover only the items in that response; a continuation call does not repeat earlier items.
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
    status_filter: Optional[Union[str, List[str]]] = None,
    name_filter: Optional[str] = None,
    name_match_option: str = 'CONTAINS',
    usage_account_id_filter: Optional[str] = None,
    service_code_filter: Optional[str] = None,
    usage_type_filter: Optional[str] = None,
    operation_filter: Optional[str] = None,
    location_filter: Optional[str] = None,
    usage_group_filter: Optional[str] = None,
    next_token: Optional[str] = None,
    max_items: Optional[int] = None,
) -> Dict[str, Any]:
    """FastMCP tool wrapper for BCM Pricing Calculator operations.

    Args:
        ctx: The MCP context object.
        operation: The operation to perform. One of: get_workload_estimate,
            list_workload_estimates, list_workload_estimate_usage, get_preferences.
        identifier: The workload estimate identifier. Required for get_workload_estimate
            and list_workload_estimate_usage.
        created_after: Filter estimates created after this timestamp
            (ISO format: YYYY-MM-DDTHH:MM:SS). Must not be later than created_before.
        created_before: Filter estimates created before this timestamp
            (ISO format: YYYY-MM-DDTHH:MM:SS).
        expires_after: Filter estimates expiring after this timestamp
            (ISO format: YYYY-MM-DDTHH:MM:SS). Must not be later than expires_before.
        expires_before: Filter estimates expiring before this timestamp
            (ISO format: YYYY-MM-DDTHH:MM:SS).
        status_filter: Filter by status: one of UPDATING, VALID, INVALID, ACTION_NEEDED
            (case-insensitive), or a list of them; a list matches any of them. Any other
            value, or an empty list, is rejected.
        name_filter: Filter by name (supports partial matching).
            Matched using name_match_option; always case-sensitive: Demo does not
            match DEMO.
        name_match_option: How name_filter is matched: EQUALS, STARTS_WITH or CONTAINS.
            Defaults to CONTAINS. The option may be given in any case; when name_filter
            is set, any other value is rejected.
        usage_account_id_filter: Filter usage lines by AWS account ID (EQUALS).
        service_code_filter: Filter usage lines by AWS service code (EQUALS,
            case-sensitive), e.g. AmazonEC2 or AmazonS3; amazonec2 matches nothing.
        usage_type_filter: Filter usage lines whose usage type contains this text
            (CONTAINS, case-sensitive), e.g. BoxUsage.
        operation_filter: Filter usage lines whose operation contains this text
            (CONTAINS, case-sensitive). RunInstances also matches RunInstances:0002
            and the other platform variants; an exact match is not available.
        location_filter: Filter usage lines by location (EQUALS, case-sensitive):
            usually a region code such as us-east-1, but a Local Zone or Wavelength
            Zone code (e.g. us-east-1-lim-1) for usage there. A region code does not
            match its Local Zones' lines. Global usage such as CloudFront or Global
            Accelerator has an empty location, which this tool cannot select (an empty
            location_filter means no filter). An Availability Zone (us-east-1a) or a
            location name such as US East (N. Virginia), as used by aws-pricing,
            matches nothing.
        usage_group_filter: Filter usage lines by usage group (EQUALS, case-sensitive).
        next_token: Continuation token from a previous response (list operations only).
        max_items: Total items to return (list operations only). None fetches every page.

    Returns:
        Dict containing the response data.
    """
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
        max_items,
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
        error_response = add_retry_guidance(
            await handle_aws_error(ctx, e, 'get_preferences', BCM_PRICING_CALCULATOR_SERVICE_NAME)
        )
        error_msg = f'Failed to check BCM Pricing Calculator preferences: {error_response.get("message", str(e))}'
        await ctx.error(error_msg)
        # Keep the retry_strategy and hint derived from the full error response
        return {
            'error': error_msg,
            'error_type': error_response.get('error_type', 'unknown_error'),
            **{
                key: error_response[key]
                for key in ('retry_strategy', 'hint')
                if key in error_response
            },
        }


async def list_workload_estimates(
    ctx: Context,
    created_after: Optional[str] = None,
    created_before: Optional[str] = None,
    expires_after: Optional[str] = None,
    expires_before: Optional[str] = None,
    status_filter: Optional[Union[str, List[str]]] = None,
    name_filter: Optional[str] = None,
    name_match_option: str = 'CONTAINS',
    next_token: Optional[str] = None,
    max_items: Optional[int] = None,
) -> Dict[str, Any]:
    """Lists all workload estimates for the account.

    Args:
        ctx: The MCP context object
        created_after: Filter estimates created after this timestamp (ISO format: YYYY-MM-DDTHH:MM:SS).
            Must not be later than created_before.
        created_before: Filter estimates created before this timestamp (ISO format: YYYY-MM-DDTHH:MM:SS)
        expires_after: Filter estimates expiring after this timestamp (ISO format: YYYY-MM-DDTHH:MM:SS).
            Must not be later than expires_before.
        expires_before: Filter estimates expiring before this timestamp (ISO format: YYYY-MM-DDTHH:MM:SS)
        status_filter: Filter by status: one of UPDATING, VALID, INVALID, ACTION_NEEDED
            (case-insensitive), or a list of them; a list matches any of them. Any other
            value, or an empty list, is rejected.
        name_filter: Filter by name (supports partial matching)
            Matching is case-sensitive.
        name_match_option: Match option for name filter (EQUALS, STARTS_WITH, CONTAINS),
            in any case. Checked only when name_filter is set.
        next_token: Continuation token from a previous response
        max_items: Total items to return. None fetches every page.

    Returns:
        Dict containing the workload estimates information. This contains the following information about a workload estimate:
        id: The unique identifier of the workload estimate.
        name: The name of the workload estimate.
        status: The current status of the workload estimate. Possible values are UPDATING, VALID, INVALID, ACTION_NEEDED
    """
    try:
        # The service accepts only upper-case match options; reject others before any AWS call.
        if name_filter:
            normalized_match_option = (name_match_option or '').strip().upper()
            if normalized_match_option not in VALID_MATCH_OPTIONS:
                return format_response(
                    'error',
                    {'invalid_parameter': 'name_match_option', 'value': name_match_option},
                    f'Invalid name_match_option: {name_match_option}. '
                    f'Must be one of: {", ".join(VALID_MATCH_OPTIONS)}.',
                    error_type='validation_error',
                    operation='list_workload_estimates',
                    service=BCM_PRICING_CALCULATOR_SERVICE_NAME,
                )
            name_match_option = normalized_match_option

        await ctx.info('Listing workload estimates')

        # Validate before any AWS call: an unknown or wrongly cased status matches nothing.
        statuses: List[str] = []
        if isinstance(status_filter, list) or status_filter:
            statuses, status_error = _normalize_statuses(status_filter)
            if status_error:
                return status_error

        # Check each date bound before any AWS call: an unparseable value names its
        # parameter, and an after bound later than its before bound is rejected here since
        # the service's message names the bounds the wrong way round.
        bounds = {
            'created_after': created_after,
            'created_before': created_before,
            'expires_after': expires_after,
            'expires_before': expires_before,
        }
        timestamps: Dict[str, datetime] = {}
        for name, value in bounds.items():
            if value:
                try:
                    timestamps[name] = _parse_timestamp(value)
                except (ValueError, OverflowError):
                    return format_response(
                        'error',
                        {'invalid_parameter': name, 'value': value},
                        f'Invalid {name}: {value}. Use an ISO 8601 timestamp such as '
                        f'2026-01-31T00:00:00 (UTC when no offset is given).',
                        error_type='validation_error',
                        operation='list_workload_estimates',
                        service=BCM_PRICING_CALCULATOR_SERVICE_NAME,
                    )
        for prefix in ('created', 'expires'):
            after = timestamps.get(f'{prefix}_after')
            before = timestamps.get(f'{prefix}_before')
            if after and before and after > before:
                return format_response(
                    'error',
                    {'invalid_parameter': f'{prefix}_after', 'value': bounds[f'{prefix}_after']},
                    f'Invalid date range: {prefix}_after ({bounds[f"{prefix}_after"]}) is later '
                    f'than {prefix}_before ({bounds[f"{prefix}_before"]}). {prefix}_after must be '
                    f'earlier than or equal to {prefix}_before.',
                    error_type='validation_error',
                    operation='list_workload_estimates',
                    service=BCM_PRICING_CALCULATOR_SERVICE_NAME,
                )
        created_filter = _timestamp_filter(timestamps, 'created')
        expires_filter = _timestamp_filter(timestamps, 'expires')

        # Create BCM Pricing Calculator client
        bcm_client = create_aws_client('bcm-pricing-calculator')

        # Check preferences before proceeding
        preferences_result = await get_preferences(ctx)
        if 'error' in preferences_result:
            return _preferences_error_response(preferences_result)

        # Build request parameters. The token and page size are added per page.
        request_params: Dict[str, Any] = {}
        if created_filter:
            request_params['createdAtFilter'] = created_filter
        if expires_filter:
            request_params['expiresAtFilter'] = expires_filter

        # Add additional filters
        filters = []
        if statuses:
            # Several values in one STATUS filter are ORed by the service; separate filters are ANDed.
            filters.append({'name': 'STATUS', 'values': statuses, 'matchOption': 'EQUALS'})

        if name_filter:
            filters.append(
                {'name': 'NAME', 'values': [name_filter], 'matchOption': name_match_option}
            )

        if filters:
            request_params['filters'] = filters

        results, _, pagination = await paginate_aws_items(
            ctx,
            'ListWorkloadEstimates',
            bcm_client.list_workload_estimates,
            request_params,
            LIST_WORKLOAD_ESTIMATES_PAGE_SPEC,
            max_items=max_items,
            next_token=next_token,
        )

        formatted_estimates = [format_workload_estimate_response(estimate) for estimate in results]

        await ctx.info(f'Retrieved {len(formatted_estimates)} workload estimates')

        return format_response(
            'success', with_pagination({'workload_estimates': formatted_estimates}, pagination)
        )

    except Exception as e:
        # Use shared error handler for all exceptions (ClientError and others)
        return await handle_aws_error(
            ctx, e, 'list_workload_estimates', BCM_PRICING_CALCULATOR_SERVICE_NAME
        )


def _normalize_statuses(
    status_filter: Union[str, List[str], None],
) -> tuple[List[str], Optional[Dict[str, Any]]]:
    """Upper-case and check status_filter (one status or a list), keeping order without repeats.

    A JSON array string such as '["VALID", "INVALID"]' is read as a list, since some clients
    send lists that way. Returns (statuses, None) when every value is a known status, or
    ([], error response).
    """
    if isinstance(status_filter, str) and status_filter.strip().startswith('['):
        try:
            parsed = json.loads(status_filter)
        except ValueError:
            parsed = None
        if isinstance(parsed, list):
            status_filter = parsed
    values = status_filter if isinstance(status_filter, list) else [status_filter]
    if not values:
        return [], format_response(
            'error',
            {'invalid_parameter': 'status_filter', 'value': []},
            'Invalid status_filter: give at least one status, or omit it for no filter. '
            f'Must be one of: {", ".join(VALID_WORKLOAD_ESTIMATE_STATUSES)}.',
            error_type='validation_error',
            operation='list_workload_estimates',
            service=BCM_PRICING_CALCULATOR_SERVICE_NAME,
        )
    statuses: List[str] = []
    invalid: List[Any] = []
    for value in values:
        status = value.strip().upper() if isinstance(value, str) else None
        if status not in VALID_WORKLOAD_ESTIMATE_STATUSES:
            invalid.append(value)
        elif status not in statuses:
            statuses.append(status)
    if invalid:
        # repr shows a blank or non-string list entry; a single string is shown as given.
        shown = (
            ', '.join(repr(v) for v in invalid) if isinstance(status_filter, list) else invalid[0]
        )
        return [], format_response(
            'error',
            {
                'invalid_parameter': 'status_filter',
                'value': invalid if isinstance(status_filter, list) else status_filter,
            },
            f'Invalid status_filter: {shown}. '
            f'Must be one of: {", ".join(VALID_WORKLOAD_ESTIMATE_STATUSES)}.',
            error_type='validation_error',
            operation='list_workload_estimates',
            service=BCM_PRICING_CALCULATOR_SERVICE_NAME,
        )
    return statuses, None


def _parse_timestamp(value: str) -> datetime:
    """Parse an ISO 8601 bound as a UTC instant, so two bounds compare.

    A value without an offset is taken as UTC, which is how botocore sends it.
    Raises ValueError for a value that is not ISO 8601, and OverflowError for one whose
    offset moves it outside the datetime range.
    """
    parsed = datetime.fromisoformat(value.replace('Z', UTC_TIMEZONE_OFFSET))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _timestamp_filter(timestamps: Dict[str, datetime], prefix: str) -> Dict[str, datetime]:
    """Build a FilterTimestamp from the parsed <prefix>_after and <prefix>_before bounds."""
    timestamp_filter: Dict[str, datetime] = {}
    for key, suffix in (('afterTimestamp', 'after'), ('beforeTimestamp', 'before')):
        if f'{prefix}_{suffix}' in timestamps:
            timestamp_filter[key] = timestamps[f'{prefix}_{suffix}']
    return timestamp_filter


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
                'Identifier is required when calling get_workload_estimate',
                error_type='validation_error',
                operation='get_workload_estimate',
                service=BCM_PRICING_CALCULATOR_SERVICE_NAME,
            )

        # Log the request
        await ctx.info(f'Getting workload estimate details for identifier: {identifier}')

        # Create BCM Pricing Calculator client
        bcm_client = create_aws_client('bcm-pricing-calculator')

        # Check preferences before proceeding
        preferences_result = await get_preferences(ctx)
        if 'error' in preferences_result:
            return _preferences_error_response(preferences_result)

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
    max_items: Optional[int] = None,
) -> Dict[str, Any]:
    """Core business logic for listing usage entries for a specific workload estimate.

    Args:
        ctx: The MCP context object
        workload_estimate_id: The unique identifier of the workload estimate
        usage_account_id_filter: Filter by AWS account ID (EQUALS)
        service_code_filter: Filter by AWS service code (EQUALS, e.g. AmazonEC2, AmazonS3)
        usage_type_filter: Filter by usage type (CONTAINS)
        operation_filter: Filter by operation name (CONTAINS)
        location_filter: Filter by location (EQUALS): usually a region code (e.g. us-east-1),
            or a Local Zone or Wavelength Zone code
        usage_group_filter: Filter by usage group (EQUALS)
        next_token: Continuation token from a previous response
        max_items: Total items to return. None fetches every page.

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
                'workload_estimate_id is required when calling list_workload_estimate_usage',
                error_type='validation_error',
                operation='list_workload_estimate_usage',
                service=BCM_PRICING_CALCULATOR_SERVICE_NAME,
            )

        await ctx.info('Listing workload estimate usage')

        # Create BCM Pricing Calculator client
        bcm_client = create_aws_client('bcm-pricing-calculator')

        # Check preferences before proceeding
        preferences_result = await get_preferences(ctx)
        if 'error' in preferences_result:
            return _preferences_error_response(preferences_result)

        # Build request parameters. The token and page size are added per page.
        request_params: Dict[str, Any] = {'workloadEstimateId': workload_estimate_id}

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

        results, _, pagination = await paginate_aws_items(
            ctx,
            'ListWorkloadEstimateUsage',
            bcm_client.list_workload_estimate_usage,
            request_params,
            LIST_WORKLOAD_ESTIMATE_USAGE_PAGE_SPEC,
            max_items=max_items,
            next_token=next_token,
        )

        formatted_usage_items = [format_usage_item_response(item) for item in results]

        await ctx.info(f'Retrieved {len(formatted_usage_items)} usage items')

        return format_response(
            'success',
            with_pagination(
                {
                    'usage_items': formatted_usage_items,
                    'workload_estimate_id': workload_estimate_id,
                },
                pagination,
            ),
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
