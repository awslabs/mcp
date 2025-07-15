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

"""Custom exceptions and exception handling for the RDS Control Plane MCP Server."""

import json
from ..constants import (
    ERROR_CLIENT,
    ERROR_READONLY_MODE,
    ERROR_UNEXPECTED,
)
from botocore.exceptions import ClientError
from functools import wraps
from inspect import iscoroutinefunction
from loguru import logger
from typing import Any, Callable


class RDSMCPException(Exception):
    """Base exception for RDS MCP Server."""

    pass


class ReadOnlyModeException(RDSMCPException):
    """Exception raised when a write operation is attempted in read-only mode."""

    def __init__(self, operation: str):
        """Initialize the ReadOnlyModeException.

        Args:
            operation: The name of the operation that was attempted in read-only mode
        """
        """Initialize the ReadOnlyModeException.

        Args:
            operation: The name of the operation that was attempted
        """
        self.operation = operation
        super().__init__(
            f"Operation '{operation}' requires write access. The server is currently in read-only mode."
        )


class ConfirmationRequiredException(RDSMCPException):
    """Exception raised when a destructive operation requires confirmation."""

    def __init__(
        self, operation: str, confirmation_token: str, warning_message: str, impact: dict
    ):
        """Initialize the ConfirmationRequiredException.

        Args:
            operation: The name of the operation that requires confirmation
            confirmation_token: A unique token to be used for confirming the operation
            warning_message: A message explaining the risks of the operation
            impact: A dictionary containing details about the potential impact of the operation
        """
        """Initialize the ConfirmationRequiredException.

        Args:
            operation: The name of the operation that requires confirmation
            confirmation_token: A unique token for confirming the operation
            warning_message: A message warning about the operation's impact
            impact: A dictionary containing details about the operation's impact
        """
        self.operation = operation
        self.confirmation_token = confirmation_token
        self.warning_message = warning_message
        self.impact = impact
        super().__init__(warning_message)


def handle_exceptions(func: Callable) -> Callable:
    """Decorator to handle exceptions in MCP operations.

    Wraps the function in a try-catch block and returns any exceptions
    in a standardized error format.

    Args:
        func: The function to wrap

    Returns:
        The wrapped function that handles exceptions
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any):
        try:
            if iscoroutinefunction(func):
                # If the decorated function is a coroutine, await it
                return await func(*args, **kwargs)
            return func(*args, **kwargs)
        except Exception as error:
            if isinstance(error, ReadOnlyModeException):
                logger.warning(f'Operation blocked in readonly mode: {error.operation}')
                return json.dumps(
                    {
                        'error': ERROR_READONLY_MODE,
                        'operation': error.operation,
                        'message': str(error),
                    },
                    indent=2,
                )
            elif isinstance(error, ConfirmationRequiredException):
                logger.info(f'Confirmation required for operation: {error.operation}')
                return json.dumps(
                    {
                        'requires_confirmation': True,
                        'warning': error.warning_message,
                        'impact': error.impact,
                        'confirmation_token': error.confirmation_token,
                        'message': f'{error.warning_message}\n\nTo confirm, please call this function again with the confirmation_token parameter set to this token.',
                    },
                    indent=2,
                )
            elif isinstance(error, ClientError):
                error_code = error.response['Error']['Code']
                error_message = error.response['Error']['Message']
                logger.error(f'Failed with client error {error_code}: {error_message}')

                # JSON error response
                return json.dumps(
                    {
                        'error': ERROR_CLIENT.format(error_code),
                        'error_code': error_code,
                        'error_message': error_message,
                        'operation': func.__name__,
                    },
                    indent=2,
                )
            else:
                logger.exception(f'Failed with unexpected error: {str(error)}')

                # general exceptions
                return json.dumps(
                    {
                        'error': ERROR_UNEXPECTED.format(str(error)),
                        'error_type': type(error).__name__,
                        'error_message': str(error),
                        'operation': func.__name__,
                    },
                    indent=2,
                )

    return wrapper
