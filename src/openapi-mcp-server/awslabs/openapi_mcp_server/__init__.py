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
"""
OpenAPI MCP Server - A server that dynamically creates MCP tools and resources from OpenAPI specifications.
"""

__version__ = '0.1.0'


import inspect
import sys

from loguru import logger

# Remove default loguru handler
logger.remove()


def get_format():
    return '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>'


# Set up enhanced logging format to include function name, line number, and logger name
# Fixed the whitespace issue after log level by removing padding
logger.add(
    sys.stdout,
    format=get_format(),
    level='INFO',
)


def get_caller_info():
    """Get information about the caller of a function.

    Returns:
        str: A string containing information about the caller
    """
    # Get the current frame
    current_frame = inspect.currentframe()
    if not current_frame:
        return 'unknown'

    # Go up one frame
    parent_frame = current_frame.f_back
    if not parent_frame:
        return 'unknown'

    # Go up another frame to find the caller
    caller_frame = parent_frame.f_back
    if not caller_frame:
        return 'unknown'

    # Get filename, function name, and line number
    caller_info = inspect.getframeinfo(caller_frame)
    return f'{caller_info.filename}:{caller_info.function}:{caller_info.lineno}'


__all__ = ['__version__', 'logger', 'get_caller_info']
