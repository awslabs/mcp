# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not
# use this file except in compliance with the License. A copy of the License is
# located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on
# an 'AS IS' BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied. See the License for the specific language governing
# permissions and limitations under the License.

"""Error handling utilities for the AWS Support MCP Server."""

import time
from typing import Any, Dict, Optional, Union

from botocore.exceptions import ClientError
from loguru import logger
from pydantic import ValidationError

from awslabs.aws_support_mcp_server.consts import (
    ERROR_CODE_MAP
)



async def handle_client_error(ctx: Any, e: ClientError, operation: str) -> Dict[str, Any]:
    """Handle boto3 ClientError exceptions.

    Args:
        ctx: The MCP context
        e: The ClientError exception
        operation: The operation that was being performed

    Returns:
        A standardized error response

    Raises:
        Exception: The original exception is re-raised after logging and
        reporting
    """
    error_code = e.response["Error"]["Code"]
    error_message = e.response["Error"]["Message"]

    if error_code in ERROR_CODE_MAP:
        message = ERROR_CODE_MAP[error_code]
    else:
        message = f"AWS Support API error: {error_message}"

    logger.error(f"Error in {operation}: {error_code} - {error_message}")
    await ctx.error(message)

    return create_error_response(message, status_code=get_error_status_code(e))


async def handle_validation_error(ctx: Any, e: ValidationError, operation: str) -> Dict[str, Any]:
    """Handle Pydantic ValidationError exceptions.

    Args:
        ctx: The MCP context
        e: The ValidationError exception
        operation: The operation that was being performed

    Returns:
        A standardized error response

    Raises:
        Exception: The original exception is re-raised after logging and reporting
    """
    errors = []
    for error in e.errors():
        location = " -> ".join(str(loc) for loc in error["loc"])
        errors.append(f"{location}: {error['msg']}")

    message = f"Validation error in {operation}: {'; '.join(errors)}"

    logger.error(message)
    await ctx.error(message)

    return create_error_response(message, status_code=get_error_status_code(e))


async def handle_general_error(ctx: Any, e: Exception, operation: str) -> Dict[str, Any]:
    """Handle general exceptions.

    Args:
        ctx: The MCP context
        e: The exception
        operation: The operation that was being performed

    Returns:
        A standardized error response

    Raises:
        Exception: The original exception is re-raised after logging and reporting
    """
    error_type = type(e).__name__
    message = format_error_message(error_type, str(e), operation)

    logger.error(message, exc_info=True)
    await ctx.error(message)

    # Include error type in response for better error tracking
    return create_error_response(
        message,
        details={
            "error_type": error_type
        },
        status_code=get_error_status_code(e))


def format_error_message(error_code: str, error_message: str, operation: str) -> str:
    """Format an error message for user display.

    Args:
        error_code: The error code
        error_message: The error message
        operation: The operation that was being performed

    Returns:
        A formatted error message
    """
    return f"Error in {operation}: {error_code} - {error_message}"


def create_error_response(message: str, details: Optional[Dict[str, Any]] = None, status_code: int = 500) -> Dict[str, Any]:
    """Create a standardized error response.

    Args:
        message: The error message
        details: Additional error details (optional)

    Returns:
        A standardized error response
    """
    response = {
        "status": "error",
        "message": message,
        "status_code": status_code,
        "timestamp": time.time(),
    }

    if details:
        response["details"] = details

    return response


def get_error_status_code(error: Union[ClientError, ValidationError, Exception]) -> int:
    """Get the appropriate HTTP status code for an error.

    Args:
        error: The error to get the status code for

    Returns:
        An HTTP status code
    """
    if isinstance(error, ClientError):
        error_code = error.response["Error"]["Code"]
        if error_code == "AccessDeniedException":
            return 403
        elif error_code == "CaseIdNotFound":
            return 404
        elif error_code == "ThrottlingException":
            return 429
        return 400
    elif isinstance(error, ValidationError):
        return 400
    return 500
