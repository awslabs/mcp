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

"""Tool metadata decorators for AWS IoT SiteWise MCP Server."""

from typing import Any, Callable


def tool_metadata(readonly: bool = True):
    """Decorator to add metadata to tool functions.

    Args:
        readonly: Whether the tool is read-only (True) or requires write
        permissions (False)

    Example:
        @tool_metadata(readonly=True)
        def describe_asset(...):
            ...

        @tool_metadata(readonly=False)
        def create_asset(...):
            ...
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # Add type: ignore to suppress mypy error for dynamic attribute
        func._tool_readonly = readonly  # type: ignore[attr-defined]
        return func

    return decorator


def is_readonly_tool(func: Callable[..., Any]) -> bool:
    """Check if a tool function is marked as read-only.

    Args:
        func: The tool function to check

    Returns:
        True if the tool is read-only, False if it requires write permissions
        Defaults to True if no metadata is found (safe default)
    """
    return getattr(func, '_tool_readonly', True)
