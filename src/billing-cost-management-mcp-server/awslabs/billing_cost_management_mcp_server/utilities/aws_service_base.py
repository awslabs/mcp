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

"""Base utility functions for AWS service operations.

This module provides common utilities for AWS service operations
used across the AWS Billing and Cost Management MCP Server tools.

These functions focus on common operations like:
- Creating AWS service clients
- Handling dates and time ranges
- Validating and parsing JSON inputs
- Standardizing error handling
- Handling pagination for AWS API responses
"""

import boto3
import inspect
import json
import os
import re
import time
from . import constants
from .error_contract import DO_NOT_RETRY, MODIFY_REQUEST, InvalidNextTokenError
from .logging_utils import get_context_logger, get_logger
from botocore.config import Config
from botocore.exceptions import (
    BotoCoreError,
    CapacityNotAvailableError,
    ChecksumError,
    ClientError,
    ConfigNotFound,
    ConfigParseError,
    CredentialRetrievalError,
    FlexibleChecksumError,
    HTTPClientError,
    IncompleteReadError,
    InvalidConfigError,
    LoginError,
    MetadataRetrievalError,
    NoAuthTokenError,
    NoCredentialsError,
    NoRegionError,
    ParamValidationError,
    PartialCredentialsError,
    ProfileNotFound,
    RefreshWithMFAUnsupportedError,
    SSOError,
    TokenRetrievalError,
    UnknownCredentialError,
    UnknownServiceError,
)
from botocore.exceptions import ConnectionError as BotoConnectionError
from botocore.exceptions import ValidationError as BotoValidationError
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from fastmcp import Context
from typing import Any, Callable, Dict, FrozenSet, List, Optional, Sequence, Tuple, Union


# Configure logger for this module
logger = get_logger(__name__)

# The only BotoCoreError subclasses that are transient: the classes botocore's own
# standard retry mode retries (ConnectionError: endpoint, connect timeout, proxy, SSL;
# HTTPClientError: read timeout, connection closed, response streaming),
# CapacityNotAvailableError (botocore's client-side token bucket on a non-blocking
# acquire; botocore does not raise it in the standard retry mode this server uses, so it
# is kept retryable defensively), and a response body cut short or corrupted in transit
# (raised while reading the body, after botocore's retries; FlexibleChecksumError is
# also raised for request checksum settings, which no tool sets). botocore's
# ValidationError family is modify_request. Every other BotoCoreError is raised the
# same way on every attempt (credentials, configuration, an SDK-side check), so
# handle_aws_error keeps error_type='aws_connection_error' (stable for callers) but sets
# retry_strategy explicitly; ErrorSignalingMiddleware keeps a retry_strategy that is
# already set. botocore tries a container-metadata credential fetch 3 times (2 retries)
# before it raises CredentialRetrievalError; an instance-metadata fetch is tried once by
# default (metadata_service_num_attempts) and a failure usually ends as
# NoCredentialsError.
_TRANSIENT_BOTOCORE_ERRORS = (
    BotoConnectionError,
    HTTPClientError,
    CapacityNotAvailableError,
    IncompleteReadError,
    ChecksumError,
    FlexibleChecksumError,
)

# Non-transient BotoCoreErrors the user can fix in their AWS setup: the credential source
# (e.g. a credential_process or SSO session that expired), the region, or an outdated
# botocore that does not know the service.
_CONFIGURATION_BOTOCORE_ERRORS = (
    NoCredentialsError,
    PartialCredentialsError,
    CredentialRetrievalError,
    TokenRetrievalError,
    SSOError,
    LoginError,
    MetadataRetrievalError,
    NoAuthTokenError,
    RefreshWithMFAUnsupportedError,
    UnknownCredentialError,
    NoRegionError,
    ProfileNotFound,
    ConfigNotFound,
    ConfigParseError,
    InvalidConfigError,
    UnknownServiceError,
)

_HINT_AWS_CONFIGURATION = (
    'AWS credentials or client configuration are missing or invalid. Do not retry; '
    'ask the user to check the credential source (profile, SSO session, credential_process, '
    'or instance/container role) or the region, or to upgrade boto3/botocore if the '
    'service is unknown.'
)
_HINT_BOTO_VALIDATION = (
    'The AWS SDK rejected the request arguments before sending them. Correct them using '
    'details, then retry.'
)
_HINT_AWS_SDK = (
    'The AWS SDK raised a client-side error; this is not a network failure, and the same '
    'request fails the same way. Do not retry; report the details to the user.'
)


# Version for user agent tracking
__version__ = '1.0.0'


def create_aws_client(service_name: str, region_name: Optional[str] = None) -> Any:
    """Create and return an AWS service client with appropriate security constraints.

    Args:
        service_name: AWS service name (e.g., "ce", "pricing")
        region_name: AWS region name (e.g., "us-east-1"). If None, will use the
                     AWS_REGION environment variable or default to "us-east-1".

    Returns:
        boto3.client: AWS service client with security constraints applied

    Raises:
        ValueError: If attempting to use a disallowed service
    """
    # List of services explicitly allowed for cost management operations
    allowed_services = [
        'ce',  # Cost Explorer
        'budgets',  # AWS Budgets
        'pricing',  # AWS Pricing
        'athena',  # Amazon Athena (for CUR queries)
        'compute-optimizer',  # Compute Optimizer
        'compute-optimizer-automation',  # Compute Optimizer Automation
        'cost-optimization-hub',  # Cost Optimization Hub
        'sts',  # STS (for account validation)
        'freetier',  # AWS Free Tier Usage
        's3',  # AWS S3
        'bcm-pricing-calculator',  # BCM Pricing Calculator
        'billingconductor',  # AWS Billing Conductor
        'billing',  # AWS Billing
        'invoicing',  # AWS Invoicing
        'savingsplans',  # AWS Savings Plans
    ]

    # Validate requested service
    if service_name not in allowed_services:
        raise ValueError(
            f"Service '{service_name}' is not allowed. Allowed services: {', '.join(allowed_services)}"
        )

    region = region_name or os.environ.get('AWS_REGION', 'us-east-1')

    # Create AWS session
    profile_name = os.environ.get('AWS_PROFILE')
    if profile_name:
        session = boto3.Session(profile_name=profile_name, region_name=region)
    else:
        session = boto3.Session(region_name=region)

    # Configure the client with user agent and security settings
    config = Config(
        region_name=region,
        user_agent_extra=f'md/awslabs#mcp#billing-cost-management-mcp-server#{__version__}',
        retries={'max_attempts': 3, 'mode': 'standard'},
    )

    return session.client(service_name, config=config)


def parse_json(
    json_str: Optional[Union[str, List[Any], Dict[str, Any]]], parameter_name: str
) -> Any:
    """Parse a JSON string into a Python object.

    Args:
        json_str: JSON string to parse, or an already-parsed list or dict (returned as-is)
        parameter_name: Name of the parameter (for error messages)

    Returns:
        Parsed JSON object

    Raises:
        ValueError: If the JSON string is invalid
    """
    if not json_str:
        return None

    if isinstance(json_str, (list, dict)):
        return json_str

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        raise ValueError(
            f'Invalid JSON format for {parameter_name} parameter: {json_str}. Pass valid JSON, '
            'with double quotes around strings (single quotes, as in a Python repr, are not '
            'JSON).'
        )


def parse_filter(
    filter_expr: Optional[Union[str, Dict[str, Any]]], parameter_name: str = 'filter'
) -> Any:
    """Parse a filter expression, rejecting an empty one.

    An empty filter (``''``, ``{}``, ``[]``, ``null``) is an error rather than "no filter":
    dropping it would run the query unfiltered, and the result would read as a filtered one.

    Args:
        filter_expr: The filter, as an object or a JSON string. None means no filter.
        parameter_name: Name of the parameter (for error messages)

    Returns:
        The parsed filter (not shape-checked; the service validates it), or None when
        ``filter_expr`` is None

    Raises:
        ValueError: If the filter is empty or not valid JSON
    """
    if filter_expr is None:
        return None
    if isinstance(filter_expr, str):
        filter_expr = filter_expr.strip()
    parsed = parse_json(filter_expr, parameter_name)
    if parsed is None or parsed == {} or parsed == []:
        raise ValueError(
            f'{parameter_name} is empty. Omit {parameter_name} to query without one, or pass '
            'a filter expression.'
        )
    return parsed


DEFAULT_COST_METRICS = ['UnblendedCost']


def parse_metrics(metrics: Optional[Union[str, List[str]]]) -> List[str]:
    """Parse a Cost Explorer ``metrics`` argument into a list of metric names.

    Args:
        metrics: Metric names, as a list or a JSON array string

    Returns:
        The metric names, or ``['UnblendedCost']`` when ``metrics`` is not set or is empty

    Raises:
        ValueError: If ``metrics`` is not a list of non-empty metric names
    """
    if metrics is not None and not isinstance(metrics, (str, list)):
        raise ValueError('metrics must be a list of metric names or a JSON array string')
    parsed = parse_json(metrics, 'metrics')
    if not parsed:
        return list(DEFAULT_COST_METRICS)
    if not isinstance(parsed, list) or not all(isinstance(m, str) and m for m in parsed):
        raise ValueError('metrics must be a list of metric names or a JSON array string')
    return parsed


def get_date_range(
    start_date: Optional[str] = None, end_date: Optional[str] = None, default_days_ago: int = 30
) -> Tuple[str, str]:
    """Get start and end dates with defaults.

    Args:
        start_date: Optional start date in YYYY-MM-DD format
        end_date: Optional end date in YYYY-MM-DD format (exclusive)
        default_days_ago: Default number of days to look back if start_date is not provided

    Returns:
        Tuple of (start_date, end_date) in YYYY-MM-DD format
    """
    today = datetime.now().strftime('%Y-%m-%d')
    days_ago = (datetime.now() - timedelta(days=default_days_ago)).strftime('%Y-%m-%d')

    return start_date or days_ago, end_date or today


def validate_date_format(date_str: Optional[str]) -> bool:
    """Validate if a string is in YYYY-MM-DD format.

    Args:
        date_str: Date string to validate

    Returns:
        True if the date is valid, False otherwise
    """
    if not date_str:
        return False

    date_pattern = r'^\d{4}-\d{2}-\d{2}$'
    if not re.match(date_pattern, date_str):
        return False

    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False


async def handle_aws_error(
    ctx: Context, error: Exception, operation: str, service_name: str, debug: bool = False
) -> Dict[str, Any]:
    """Handle AWS service errors in a standardized way.

    Args:
        ctx: The MCP context object
        error: The exception that was raised
        operation: The AWS operation that failed
        service_name: The AWS service name
        debug: Whether to include debug information in the response
        operation: Description of the operation being performed
        service_name: Name of the AWS service

    Returns:
        Dict containing the error response
    """
    # Get context logger for consistent logging
    ctx_logger = get_context_logger(ctx, __name__)

    # Log detailed error for debugging
    error_message = str(error)
    error_context = f"Error in {service_name} operation '{operation}': {error_message}"

    if debug:
        # Print more detailed diagnostic information
        await ctx_logger.warning(f'DEBUG - Error type: {type(error)}')
        await ctx_logger.warning(f'DEBUG - Error dir: {dir(error)}')
        await ctx_logger.warning(f'DEBUG - Error repr: {repr(error)}')

    # Initialize error response
    error_response = {
        'status': 'error',
        'service': service_name,
        'operation': operation,
    }

    # Log with appropriate level and context
    if isinstance(error, ClientError):
        # Get AWS error details
        aws_error = error.response.get('Error', {})
        error_code = aws_error.get('Code', 'UnknownError')
        aws_message = aws_error.get('Message') or (
            # Cost Explorer sends DataUnavailableException with an empty Message.
            f'{service_name} has no data for this request '
            '(DataUnavailableException; the service sent no message).'
            if error_code == 'DataUnavailableException'
            else 'No error message provided'
        )
        request_id = error.response.get('ResponseMetadata', {}).get('RequestId', 'Unknown')
        http_status = error.response.get('ResponseMetadata', {}).get('HTTPStatusCode', 0)

        # Just pass through the AWS error code and message directly
        error_response.update(
            {
                'error_type': error_code,
                'message': aws_message,
                'request_id': request_id,
                'http_status': http_status,
                'full_error': str(error),
                'full_response': str(getattr(error, 'response', '{}')),
            }
        )

        # Log with appropriate severity based on error code
        if error_code in ('AccessDenied', 'UnauthorizedOperation', 'AuthFailure'):
            await ctx_logger.error(f'Access error: {error_context}', exc_info=True)
        else:
            await ctx_logger.error(error_context, exc_info=True)

    elif isinstance(error, InvalidNextTokenError):
        # Retry guidance (restart without next_token) comes from error_contract.
        error_response.update(
            {
                'error_type': 'invalid_next_token',
                'message': (
                    f'The next_token was rejected ({error.error_code}). It is expired or no '
                    'longer matches the request.'
                ),
            }
        )
        await ctx_logger.warning(error_context)

    elif isinstance(error, ValueError):
        error_type = 'validation_error'
        user_message = str(error)
        await ctx_logger.warning(f'Validation error: {error_context}')

        error_response.update(
            {'error_type': error_type, 'message': user_message, 'details': str(error)}
        )

    elif isinstance(error, ParamValidationError):
        # ParamValidationError is a client-side botocore validation failure (unknown kwargs,
        # bad parameter shape, missing required keys, type mismatches). It subclasses
        # BotoCoreError, but it is a validation failure, not a connection failure — surface
        # it that way so callers (and skills) see "fix the parameters", not "AWS is
        # unreachable". Must be matched BEFORE the BotoCoreError branch below.
        error_type = 'validation_error'
        user_message = str(error) or 'Invalid parameters'
        await ctx_logger.warning(f'Validation error (ParamValidationError): {error_context}')

        error_response.update(
            {
                'error_type': error_type,
                'boto_error_type': 'ParamValidationError',
                'message': user_message,
                'details': str(error),
            }
        )

    elif isinstance(error, BotoCoreError):
        error_type = 'aws_connection_error'
        error_code = error.__class__.__name__
        transient = isinstance(error, _TRANSIENT_BOTOCORE_ERRORS)
        user_message = (
            f'AWS service connection error: {error_code}'
            if transient
            else f'AWS SDK error (not a connection failure): {error_code}'
        )
        await ctx_logger.error(f'Connection error: {error_context}', exc_info=True)

        error_response.update(
            {
                'error_type': error_type,
                'boto_error_type': error_code,
                'message': user_message,
                'details': str(error),
            }
        )

        if isinstance(error, BotoValidationError):
            # botocore's ValidationError family (UnknownParameterError, RangeError, ...):
            # the arguments are wrong, as for ParamValidationError above.
            error_response['retry_strategy'] = MODIFY_REQUEST
            error_response['hint'] = _HINT_BOTO_VALIDATION
        elif not transient:
            error_response['retry_strategy'] = DO_NOT_RETRY
            error_response['hint'] = (
                _HINT_AWS_CONFIGURATION
                if isinstance(error, _CONFIGURATION_BOTOCORE_ERRORS)
                else _HINT_AWS_SDK
            )

    else:
        error_type = 'unknown_error'
        error_class = error.__class__.__name__
        error_message = str(error)

        # Preserve the actual error message instead of generic text
        user_message = (
            error_message if error_message else f'An unexpected error occurred: {error_class}'
        )

        await ctx_logger.error(
            f'Unexpected error: {error_context}\nError type: {type(error)}\nError attributes: {dir(error)}',
            exc_info=True,
        )

        # Create a more detailed response that shows the actual exception type and details
        error_response.update(
            {
                'error_type': f'unknown_{error_class.lower()}',
                'exception_type': error_class,
                'message': user_message,
                'details': str(error),
                'full_error_context': error_context,
            }
        )

    return error_response


# Error codes meaning the caller's next_token can no longer be used. AWS Pricing raises
# ExpiredNextTokenException for an expired token. CE raises
# RequestChangedException when any request parameter differs from the first call and
# BillExpirationException when the bill updated between pages.
TOKEN_ERROR_CODES: FrozenSet[str] = frozenset(
    {
        'InvalidNextTokenException',
        'ExpiredNextTokenException',
        'RequestChangedException',
        'BillExpirationException',
    }
)


@dataclass(frozen=True)
class PageSpec:
    """How one AWS operation pages.

    Attributes:
        result_key: Response key holding the page's items, or a tuple path to a
            nested list (e.g. ``('SavingsPlansPurchaseRecommendation', 'Details')``).
        token_param: Request field that carries the continuation token.
        token_key_in_response: Response field that returns the continuation token.
        page_max: Largest number of items one page can hold.
        page_size_param: Request field that sets the page size, or None when the
            service chooses the page size.
        page_min: Smallest page size the service accepts. A smaller request is raised
            to it, so near ``max_items`` a page can hold up to ``page_min`` items.
        fixed_page_size: Always request ``page_max``. For services whose token is bound
            to the page size, so a continuation must repeat it.
        items_per_page_unit: Items each unit of page size can return. For APIs whose
            page size counts a parent object (e.g. budgets, each with up to 10
            notifications), so one unit can hold several items.
        count_items: Counts the items in one page's result list.
        token_error_codes: Error codes meaning a token is no longer usable, on any page.
            On the first request they map to ``invalid_next_token``; on a later page they
            end the call as partial and drop the token.
        caller_token_error_codes: Codes that mean a rejected token only on the first
            request of a continuation, i.e. when the caller's own next_token was sent.
            For services that report a bad token with a generic code (e.g.
            ``ValidationException`` or ``InternalServerException``); on a later page that
            code is an ordinary failure. Because such a code also reports other invalid
            arguments, it counts as a rejected token only when the error message names the
            token (contains "token"), unless ``caller_token_message_required`` is False.
        caller_token_message_required: Require the error message to name the token before
            a ``caller_token_error_codes`` code is treated as a rejected token. Set False
            only for a service whose token errors do not name the token.
    """

    result_key: Union[str, Tuple[str, ...]]
    token_param: str
    token_key_in_response: str
    page_max: int
    page_size_param: Optional[str] = None
    page_min: int = 1
    fixed_page_size: bool = False
    items_per_page_unit: int = 1
    count_items: Callable[[List[Any]], int] = len
    token_error_codes: FrozenSet[str] = field(default=TOKEN_ERROR_CODES)
    caller_token_error_codes: FrozenSet[str] = frozenset()
    caller_token_message_required: bool = True


def partial_data_warning(items_returned: int, limit_param: str = 'max_items') -> str:
    """Build the warning attached to a result that stopped before the last page.

    Args:
        items_returned: Items in the result.
        limit_param: The parameter that stopped paging (``max_items`` or ``max_pages``).
    """
    return (
        f'Partial data: returned {items_returned} items and more remain. Totals, counts and '
        'top-N computed from this result undercount the real data. Call again with a larger '
        f'{limit_param}, continue with next_token, or state in the answer that the result is '
        'partial. Do not report the number of items returned as a total count.'
    )


def failure_warning(items_returned: int, error_code: str, restart: bool) -> str:
    """Build the warning for a result cut short by a failed page."""
    next_step = (
        'The continuation token is no longer valid. Call again without next_token to restart '
        'from the first page, and use only the new result: it repeats the items in this one, '
        'so do not combine them.'
        if restart
        else 'Continue with next_token to retry from the failed page.'
    )
    return (
        f'Partial data: returned {items_returned} items, then the service failed with '
        f'{error_code}. Totals and counts computed from this result undercount the real '
        f'data. {next_step}'
    )


def paging_limit_warning(items_returned: int, limit: str) -> str:
    """Build the warning for a result stopped by the server's time or size limit."""
    return (
        f"Partial data: returned {items_returned} items, then paging stopped at the server's "
        f'{limit} limit and more remain. Totals and counts computed from this result undercount '
        'the real data. Continue with next_token, or pass max_items or narrow the filters, or '
        'state in the answer that the result is partial.'
    )


def paging_limit_reached(started: float) -> Optional[str]:
    """Name the paging limit a call has reached, or None."""
    if time.monotonic() - started >= constants.PAGINATION_MAX_SECONDS:
        return f'{constants.PAGINATION_MAX_SECONDS}-second'
    return None


def _error_code(error: Exception) -> str:
    if isinstance(error, ClientError):
        return error.response.get('Error', {}).get('Code', 'UnknownError')
    return type(error).__name__


def _is_caller_token_error(error: Exception, code: str, spec: PageSpec) -> bool:
    """Whether a generic error code on the first request means the caller's token was rejected."""
    if code not in spec.caller_token_error_codes:
        return False
    if not spec.caller_token_message_required:
        return True
    message = (
        error.response.get('Error', {}).get('Message') if isinstance(error, ClientError) else ''
    )
    return 'token' in (message or '').lower()


def _items_of(response: Dict[str, Any], result_key: Union[str, Tuple[str, ...]]) -> List[Any]:
    path = (result_key,) if isinstance(result_key, str) else result_key
    value: Any = response
    for key in path:
        if not isinstance(value, dict):
            return []
        value = value.get(key)
    return value if isinstance(value, list) else []


def _page_size(spec: PageSpec, max_items: Optional[int], collected: int) -> Optional[int]:
    """Choose the page size to request, or None when the service chooses it."""
    if spec.page_size_param is None:
        return None
    unit = spec.items_per_page_unit
    largest = spec.page_max // unit
    if spec.fixed_page_size or max_items is None:
        return largest
    # Never request a page of 0, which some services reject, or one below page_min.
    return max(min(largest, (max_items - collected) // unit), spec.page_min, 1)


async def paginate_aws_items(
    ctx: Context,
    operation: str,
    api_call: Callable[..., Any],
    request_params: Dict[str, Any],
    spec: PageSpec,
    *,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
    max_pages: Optional[int] = None,
) -> Tuple[List[Any], List[Dict[str, Any]], Dict[str, Any]]:
    """Fetch pages until the data ends or the next page could exceed ``max_items``.

    ``max_pages`` limits the call to a number of pages instead, each at the spec's page
    size, and returns every item fetched. It is for operations whose token only works
    with the same page size (``fixed_page_size``), where a page cannot shrink to fit
    ``max_items``.

    Every request repeats ``request_params`` unchanged, apart from the token and,
    where the API allows, the page size: several services bind their token to the
    whole request.

    Args:
        ctx: The MCP context object.
        operation: Operation name, for logging.
        api_call: Calls the API with keyword arguments. May return an awaitable.
        request_params: Request parameters, without token or page size.
        spec: How the operation pages.
        max_items: Most items to return. None fetches every page.
        next_token: The caller's token from a previous response.
        max_pages: Most pages to fetch, instead of ``max_items``. None fetches every page.

    Returns:
        ``(items, pages, pagination)``: every kept item, the raw responses the items
        came from (for merging fields outside the result list), and the pagination
        block (see ``with_pagination``).

    Raises:
        ValueError: ``max_items`` or ``max_pages`` is less than 1, both are set, or
            ``next_token`` is empty.
        InvalidNextTokenError: The first page failed because ``next_token`` was rejected.
        Exception: Any other failure on the first page, unchanged.
    """
    if max_items is not None and max_items < 1:
        raise ValueError('max_items must be at least 1. Omit it to fetch every page.')
    if max_pages is not None and max_items is not None:
        raise ValueError('max_pages and max_items cannot be used together. Pass only one.')
    if max_pages is not None and max_pages < 1:
        raise ValueError('max_pages must be at least 1. Omit it to fetch every page.')
    if next_token is not None and not next_token.strip():
        # An empty token would silently restart from page 1 while the caller
        # believes the result continues a previous one.
        raise ValueError(
            'next_token must be a non-empty token from a previous response. '
            'Omit it to start from the first page.'
        )
    ctx_logger = get_context_logger(ctx, __name__)

    items: List[Any] = []
    pages: List[Dict[str, Any]] = []
    collected = 0
    token = next_token
    seen_tokens = {next_token} if next_token else set()
    failure: Optional[Tuple[str, bool]] = None
    limit_reached: Optional[str] = None
    started = time.monotonic()

    while True:
        if max_items is not None and pages and collected >= max_items:
            break
        if max_pages is not None and len(pages) >= max_pages:
            break
        if pages:
            limit_reached = paging_limit_reached(started)
            if limit_reached:
                await ctx_logger.warning(
                    f'{operation} stopped at the {limit_reached} paging limit'
                )
                break

        size = _page_size(spec, max_items, collected)
        worst_case = size * spec.items_per_page_unit if size is not None else spec.page_max
        if max_items is not None and pages and collected + worst_case > max_items:
            break

        params = dict(request_params)
        if token:
            params[spec.token_param] = token
        if size is not None and spec.page_size_param is not None:
            params[spec.page_size_param] = size

        await ctx_logger.info(f'Fetching {operation} page {len(pages) + 1}')
        try:
            response = api_call(**params)
            if inspect.isawaitable(response):
                response = await response
        except Exception as error:
            code = _error_code(error)
            is_token_error = bool(token) and code in spec.token_error_codes
            if not pages:
                if next_token and (is_token_error or _is_caller_token_error(error, code, spec)):
                    raise InvalidNextTokenError(operation, code) from error
                raise
            # Keep what was fetched. The token that requested the failed page lets a
            # continuation retry exactly that page, unless the token itself was rejected.
            await ctx_logger.warning(
                f'{operation} stopped after {collected} items: {type(error).__name__} ({code})'
            )
            failure = (code, is_token_error)
            if is_token_error:
                token = None
            break

        page_items = _items_of(response, spec.result_key)
        count = spec.count_items(page_items)
        if count > spec.page_max or (size is not None and count > size * spec.items_per_page_unit):
            # The bound was wrong. The call is already paid for, so keep the page.
            await ctx_logger.warning(
                f'{operation} returned {count} items in one page, above its page_max of '
                f'{spec.page_max}'
            )
        items.extend(page_items)
        pages.append(response)
        collected += count

        token = response.get(spec.token_key_in_response) or None
        if token is None:
            break
        if token in seen_tokens:
            # The service returned a token it already used, so paging would never end, and
            # continuing with that token would repeat the same pages.
            await ctx_logger.warning(f'{operation} returned a repeated continuation token')
            failure = ('RepeatedNextToken', True)
            token = None
            break
        seen_tokens.add(token)

    # has_more means a call with next_token can continue. A token failure leaves the
    # result partial with no token, so complete_dataset alone reports that.
    has_more = token is not None
    pagination: Dict[str, Any] = {
        'complete_dataset': not has_more and failure is None,
        'has_more': has_more,
        'next_token': token,
        'items_returned': collected,
    }
    if failure is not None:
        pagination['warning'] = failure_warning(collected, failure[0], restart=failure[1])
    elif limit_reached and has_more:
        pagination['warning'] = paging_limit_warning(collected, limit_reached)
    elif has_more:
        limit_param = 'max_pages' if max_pages is not None else 'max_items'
        pagination['warning'] = partial_data_warning(collected, limit_param)
    return items, pages, pagination


def with_pagination(data: Dict[str, Any], pagination: Dict[str, Any]) -> Dict[str, Any]:
    """Attach the pagination block to a tool's response data.

    The block goes under lowercase ``pagination``, ahead of the data, so a reader (or a
    trim of an oversized result) sees whether the result is complete and the token to
    continue before the data itself. A partial result also leads with
    ``complete_dataset: false`` and ``warning``.

    Args:
        data: The tool's response data.
        pagination: The pagination block from ``paginate_aws_items``.

    Returns:
        The response data with the pagination block attached.
    """
    block = {key: value for key, value in pagination.items() if key != 'warning'}
    lead: Dict[str, Any] = {}
    if not pagination.get('complete_dataset', True):
        lead = {'complete_dataset': False, 'warning': pagination.get('warning')}
    rest = {key: value for key, value in data.items() if key != 'pagination'}
    return {**lead, 'pagination': block, **rest}


def first_page_fields(pages: Sequence[Dict[str, Any]], keys: Sequence[str]) -> Dict[str, Any]:
    """Return fields that only the first page carries (e.g. totals, group definitions)."""
    first = pages[0] if pages else {}
    return {key: first[key] for key in keys if key in first}


def whole_query_in_one_page(
    pages: Sequence[Dict[str, Any]], next_token: Optional[str], pagination: Dict[str, Any]
) -> bool:
    """Whether the result is the whole query in one page.

    Some APIs (e.g. Cost Explorer Savings Plans utilization details, and grouped Reserved
    Instance coverage and utilization) sum a page's Total from only the rows on that page, so
    such a Total covers the query only when this returns True.

    Args:
        pages: The pages from ``paginate_aws_items``.
        next_token: The caller's token. A continuation's first page is not the query's.
        pagination: The pagination block from ``paginate_aws_items``.
    """
    return len(pages) == 1 and next_token is None and pagination['complete_dataset']


def format_response(
    status: str,
    data: Any,
    message: Optional[str] = None,
    *,
    error_type: Optional[str] = None,
    operation: Optional[str] = None,
    service: Optional[str] = None,
    retry_strategy: Optional[str] = None,
    hint: Optional[str] = None,
) -> Dict[str, Any]:
    """Format a standard API response.

    Args:
        status: Response status ("success" or "error")
        data: Response data payload
        message: Optional message to include. For errors, defaults to a string
            data['message'] so the documented top-level message is set
        error_type: Optional error classification, set at the top level like handle_aws_error
        operation: Optional name of the operation that produced the response
        service: Optional AWS service name
        retry_strategy: Optional override of the strategy ErrorSignalingMiddleware derives
            from error_type (see utilities/error_contract.py)
        hint: Optional fixed recovery guidance for the caller

    Returns:
        Dict containing a standardized response format
    """
    response = {'status': status, 'data': data}

    # Many error sites put their text in data['message'] instead of passing message.
    # Lift it (data is left unchanged) so the error carries the top-level message.
    if not message and status == 'error' and isinstance(data, dict):
        nested = data.get('message')
        if isinstance(nested, str):
            message = nested

    if message:
        response['message'] = message

    # Only added when supplied, so existing callers keep the same shape
    if error_type is not None:
        response['error_type'] = error_type
    if operation is not None:
        response['operation'] = operation
    if service is not None:
        response['service'] = service
    if retry_strategy is not None:
        response['retry_strategy'] = retry_strategy
    if hint is not None:
        response['hint'] = hint

    return response
