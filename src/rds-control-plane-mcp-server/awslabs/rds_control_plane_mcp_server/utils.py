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

"""Utility functions for the RDS Control Plane MCP Server."""

from .constants import ERROR_AWS_API, ERROR_UNEXPECTED
from botocore.exceptions import ClientError
from functools import wraps
from loguru import logger
from mcp.server.fastmcp import Context
from typing import Any, Callable, Dict, Optional


def format_aws_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """Format AWS API response for MCP.

    Args:
        response: Raw AWS API response

    Returns:
        Formatted response dictionary
    """
    # remove ResponseMetadata as it's not useful for LLMs
    if 'ResponseMetadata' in response:
        del response['ResponseMetadata']

    # convert datetime objects to strings
    return convert_datetime_to_string(response)


def convert_datetime_to_string(obj: Any) -> Any:
    """Recursively convert datetime objects to ISO format strings.

    Args:
        obj: Object to convert

    Returns:
        Object with datetime objects converted to strings
    """
    import datetime

    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: convert_datetime_to_string(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_datetime_to_string(item) for item in obj]
    return obj


def apply_docstring(docstring: str) -> Callable:
    """Decorator to apply an external docstring to a function.

    This decorator should be the innermost decorator applied to a function
    (below the @mcp.resource decorator) to ensure the MCP framework sees the
    updated docstring.

    Args:
        docstring: The docstring to apply to the function

    Returns:
        Decorator function that applies the docstring
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper.__doc__ = docstring
        return wrapper

    return decorator


async def handle_aws_error(
    operation: str, error: Exception, ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """Handle AWS API errors consistently.

    Args:
        operation: The operation that failed
        error: The exception that was raised
        ctx: MCP context for error reporting

    Returns:
        Error response dictionary
    """
    if isinstance(error, ClientError):
        error_code = error.response['Error']['Code']
        error_message = error.response['Error']['Message']
        logger.error(f'{operation} failed with AWS error {error_code}: {error_message}')

        error_response = {
            'error': ERROR_AWS_API.format(error_code),
            'error_code': error_code,
            'error_message': error_message,
            'operation': operation,
        }

        if ctx:
            await ctx.error(f'{error_code}: {error_message}')

    else:
        logger.exception(f'{operation} failed with unexpected error')
        error_response = {
            'error': ERROR_UNEXPECTED.format(str(error)),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'operation': operation,
        }

        if ctx:
            await ctx.error(str(error))

    return error_response
