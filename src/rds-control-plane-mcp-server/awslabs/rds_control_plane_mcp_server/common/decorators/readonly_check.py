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

"""Read-only mode handling for the RDS Control Plane MCP Server."""

from ..context import RDSContext
from functools import wraps
from inspect import iscoroutinefunction
from loguru import logger
from typing import Any, Callable


ERROR_READONLY_MODE = 'This operation is not allowed in read-only mode. Please run the server with --no-readonly to enable write operations.'


def readonly_check(func: Callable) -> Callable:
    """Decorator to check if operation is allowed in readonly mode.

    This decorator automatically checks if the server is in readonly mode
    and blocks write operations by returning a standardized JSON response.
    It determines the operation type from the function name.

    Args:
        func: The function to wrap

    Returns:
        The wrapped function that checks readonly mode
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any):
        if RDSContext.readonly_mode():
            operation = func.__name__
            error_message = f"Operation '{operation}' requires write access. The server is currently in read-only mode."
            logger.warning(f'Operation blocked in readonly mode: {operation}')
            return {
                'error': ERROR_READONLY_MODE,
                'operation': operation,
                'message': error_message,
            }

        if iscoroutinefunction(func):
            return await func(*args, **kwargs)
        return func(*args, **kwargs)

    return wrapper
