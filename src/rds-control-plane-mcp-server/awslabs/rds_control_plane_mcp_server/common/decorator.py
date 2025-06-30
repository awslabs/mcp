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

"""Decorators used by the RDS Control Plane MCP Server."""

import json
from botocore.exceptions import ClientError
from functools import wraps
from inspect import iscoroutinefunction
from loguru import logger
from typing import Any, Callable
from ..common.constants import ERROR_AWS_API, ERROR_UNEXPECTED


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
            if isinstance(error, ClientError):
                error_code = error.response['Error']['Code']
                error_message = error.response['Error']['Message']
                logger.error(f'Failed with AWS error {error_code}: {error_message}')
                
                # JSON error response
                return json.dumps({
                    "error": ERROR_AWS_API.format(error_code),
                    "error_code": error_code,
                    "error_message": error_message,
                    "operation": func.__name__
                }, indent=2)
            else:
                logger.exception(f'Failed with unexpected error: {str(error)}')
                
                # general exceptions
                return json.dumps({
                    "error": ERROR_UNEXPECTED.format(str(error)),
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                    "operation": func.__name__
                }, indent=2)

    return wrapper
