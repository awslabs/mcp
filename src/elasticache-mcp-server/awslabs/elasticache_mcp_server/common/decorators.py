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

"""Decorators for ElastiCache MCP Server."""

from ..context import Context
from functools import wraps
from typing import Any, Callable


def readonly_safe(func: Callable) -> Callable:
    """Mark a tool as safe to run in readonly mode.

    Tools without this decorator will be blocked when readonly mode is enabled.
    """
    setattr(func, '_readonly_safe', True)
    return func


def handle_exceptions(func: Callable) -> Callable:
    """Decorator to handle exceptions and enforce readonly mode for ElastiCache operations.

    Blocks tool execution in readonly mode unless the tool is marked with @readonly_safe.
    Wraps the function in a try-catch block and returns any exceptions
    in a standardized error format.

    Args:
        func: The function to wrap

    Returns:
        The wrapped function that enforces readonly mode and handles exceptions
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any):
        try:
            if Context.readonly_mode() and not getattr(func, '_readonly_safe', False):
                raise ValueError(
                    'You have configured this tool in readonly mode. To make this change you will have to update your configuration.'
                )
            return await func(*args, **kwargs)
        except Exception as e:
            return {'error': str(e)}

    return wrapper
