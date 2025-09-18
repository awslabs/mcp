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

"""Decorators for AWS AppSync MCP Server."""

import functools
from typing import Callable


# Global state for write operations
_allow_write = False


def set_write_allowed(allowed: bool) -> None:
    """Set whether write operations are allowed.

    Args:
        allowed: Whether write operations should be allowed
    """
    global _allow_write
    _allow_write = allowed


def is_write_allowed() -> bool:
    """Check if write operations are allowed.

    Returns:
        True if write operations are allowed, False otherwise
    """
    return _allow_write


def write_operation(func: Callable) -> Callable:
    """Decorator to check if write operations are allowed.

    Args:
        func: The function to decorate

    Returns:
        The decorated function

    Raises:
        ValueError: If write operations are not allowed
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if not is_write_allowed():
            raise ValueError('Operation not permitted: Server is configured in read-only mode')
        return await func(*args, **kwargs)

    return wrapper
