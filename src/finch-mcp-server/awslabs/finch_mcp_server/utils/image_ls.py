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

"""Image listing utilities for the Finch MCP server.

This module provides functions to list container images using Finch.
"""

from ..consts import STATUS_ERROR, STATUS_SUCCESS
from .common import execute_command, format_result
from loguru import logger
from typing import Any, Dict, List, Optional


def list_images(
    all_images: bool = False,
    filter_expr: Optional[List[str]] = None,
    no_trunc: bool = False,
    quiet: bool = False,
    digests: bool = False,
) -> Dict[str, Any]:
    """List container images using finch image ls with various options.

    Args:
        all_images: Show all images (default: False, hides intermediate images)
        filter_expr: Filter output based on conditions (e.g., ["dangling=true", "reference=alpine"])
        no_trunc: Don't truncate output
        quiet: Only display image IDs
        digests: Show digests

    Returns:
        Dict[str, Any]: A dictionary containing:
            - status (str): "success" if the operation succeeded, "error" otherwise
            - message (str): A descriptive message about the result
            - raw_output (str): Raw JSON output from the command (if successful)

    """
    try:
        logger.info('Listing container images')

        # Build command with options
        cmd = ['finch', 'image', 'ls', '--format', 'json']

        if all_images:
            cmd.append('-a')

        if filter_expr:
            for filter_item in filter_expr:
                cmd.extend(['-f', filter_item])

        if no_trunc:
            cmd.append('--no-trunc')

        if quiet:
            cmd.append('-q')

        if digests:
            cmd.append('--digests')

        # Execute command with options
        result = execute_command(cmd)

        if result.returncode != 0:
            error_msg = f'Failed to list images: {result.stderr}'
            logger.error(error_msg)
            return format_result(STATUS_ERROR, error_msg)

        return {
            'status': STATUS_SUCCESS,
            'message': 'Successfully listed images',
            'raw_output': result.stdout,
        }

    except Exception as e:
        error_msg = f'Error listing images: {str(e)}'
        logger.error(error_msg)
        return format_result(STATUS_ERROR, error_msg)
