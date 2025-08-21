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
import json
import os
import re
from .logging_utils import get_context_logger, get_logger
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from datetime import datetime, timedelta
from fastmcp import Context
from typing import Any, Dict, List, Optional, Tuple


# Configure logger for this module
logger = get_logger(__name__)


# Version for user agent tracking
__version__ = '1.0.0'

# Supported AWS Pricing API regions
PRICING_API_REGIONS = {
    'classic': ['us-east-1', 'eu-central-1', 'ap-southeast-1'],
    'china': ['cn-northwest-1'],
}


def get_pricing_region(requested_region: Optional[str] = None) -> str:
    """Determine the appropriate AWS Pricing API region.

    The AWS Pricing API is only available in specific regions:
    - Classic partition: us-east-1, eu-central-1, ap-southeast-1
    - China partition: cn-northwest-1

    Args:
        requested_region: The AWS region requested by the user (default: None)

    Returns:
        str: The closest AWS Pricing API region
    """
    if not requested_region:
        requested_region = os.environ.get('AWS_REGION', 'us-east-1')

    all_pricing_regions = PRICING_API_REGIONS['classic'] + PRICING_API_REGIONS['china']
    if requested_region in all_pricing_regions:
        return requested_region

    # Map the requested region to the nearest pricing API region
    if requested_region.startswith('cn-'):
        pricing_region = 'cn-northwest-1'
    elif requested_region.startswith(('eu-', 'me-', 'af-')):
        pricing_region = 'eu-central-1'
    elif requested_region.startswith('ap-'):
        pricing_region = 'ap-southeast-1'
    else:
        pricing_region = 'us-east-1'

    return pricing_region


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
        'cost-optimization-hub',  # Cost Optimization Hub
        'sts',  # STS (for account validation)
        'freetier',  # AWS Free Tier Usage
        's3',  # AWS S3
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
        user_agent_extra=f'awslabs/mcp/aws-finops-mcp-server/{__version__}',
        retries={'max_attempts': 3, 'mode': 'standard'},
    )

    return session.client(service_name, config=config)


def parse_json(json_str: Optional[str], parameter_name: str) -> Any:
    """Parse a JSON string into a Python object.

    Args:
        json_str: JSON string to parse
        parameter_name: Name of the parameter (for error messages)

    Returns:
        Parsed JSON object

    Raises:
        ValueError: If the JSON string is invalid
    """
    if not json_str:
        return None

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        raise ValueError(f'Invalid JSON format for {parameter_name} parameter: {json_str}')


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
        aws_message = aws_error.get('Message', 'No error message provided')
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

    elif isinstance(error, ValueError):
        error_type = 'validation_error'
        user_message = str(error)
        await ctx_logger.warning(f'Validation error: {error_context}')

        error_response.update(
            {'error_type': error_type, 'message': user_message, 'details': str(error)}
        )

    elif isinstance(error, BotoCoreError):
        error_type = 'aws_connection_error'
        error_code = error.__class__.__name__
        user_message = f'AWS service connection error: {error_code}'
        await ctx_logger.error(f'Connection error: {error_context}', exc_info=True)

        error_response.update(
            {
                'error_type': error_type,
                'boto_error_type': error_code,
                'message': user_message,
                'details': str(error),
            }
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


async def paginate_aws_response(
    ctx: Context,
    operation_name: str,
    api_function: Any,
    request_params: Dict[str, Any],
    result_key: str,
    token_param: str = 'NextToken',
    token_key: str = 'NextToken',
    max_pages: Optional[int] = None,
) -> Tuple[List[Any], Dict[str, Any]]:
    """Handle pagination for AWS API calls.

    Args:
        ctx: The MCP context object
        operation_name: Name of the operation (for logging)
        api_function: Function to call for each page
        request_params: Parameters to pass to the API function
        result_key: Key in the response that contains the results list
        token_param: Parameter name for the pagination token in the request
        token_key: Key name for the pagination token in the response
        max_pages: Maximum number of pages to fetch (optional)

    Returns:
        Tuple of (combined_results, pagination_metadata)
    """
    # Get context logger for consistent logging
    ctx_logger = get_context_logger(ctx, __name__)

    all_results = []
    current_token = None
    pages_fetched = 0

    # For performance timing
    start_time = datetime.now()

    # Fetch all pages
    while True:
        # Add token if we have one
        if current_token:
            request_params[token_param] = current_token

        # Make API call for current page
        page_info = f'Fetching {operation_name} page {pages_fetched + 1}{" using next_token" if current_token else ""}'
        await ctx_logger.info(page_info)

        try:
            # Make the API call
            response = api_function(**request_params)

            # Get the results and add to combined list
            results = response.get(result_key, [])
            all_results.extend(results)

            # Count pages
            pages_fetched += 1
            await ctx_logger.info(f'Received {len(results)} results (total: {len(all_results)})')

            # Check if we have more pages
            current_token = response.get(token_key)

            # Stop conditions
            if not current_token:
                await ctx_logger.info('No more pages available')
                break

            if max_pages and pages_fetched >= max_pages:
                await ctx_logger.info(f'Reached maximum pages limit ({max_pages})')
                break

        except Exception as e:
            # Log error with both context and Loguru for consistent handling
            error_msg = f'Error fetching page {pages_fetched + 1} of {operation_name}: {str(e)}'
            await ctx_logger.error(error_msg, exc_info=True)
            raise

    # Log performance information
    end_time = datetime.now()
    duration_ms = (end_time - start_time).total_seconds() * 1000

    # Create pagination metadata
    pagination_metadata = {
        'complete_dataset': current_token is None,
        'pages_fetched': pages_fetched,
        'total_results': len(all_results),
        'has_more': current_token is not None,
        'next_token': current_token,
        'duration_ms': int(duration_ms),
    }

    # Log completion with timing info
    await ctx_logger.info(
        f'Completed {operation_name} pagination: {pages_fetched} pages, {len(all_results)} results in {duration_ms:.1f}ms'
    )

    return all_results, pagination_metadata


def format_response(status: str, data: Any, message: Optional[str] = None) -> Dict[str, Any]:
    """Format a standard API response.

    Args:
        status: Response status ("success" or "error")
        data: Response data payload
        message: Optional message to include

    Returns:
        Dict containing a standardized response format
    """
    response = {'status': status, 'data': data}

    if message:
        response['message'] = message

    return response
