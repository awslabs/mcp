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

"""Utility functions for listing containers using Finch.

This module provides functions for listing containers with various filtering options.
"""

import logging
from awslabs.finch_mcp_server.consts import SERVER_NAME
from awslabs.finch_mcp_server.utils.common import execute_command, format_result
from typing import Any, Dict, List, Optional


logger = logging.getLogger(SERVER_NAME)


def list_containers(
    all_containers: bool = True,
    filter_expr: Optional[List[str]] = None,
    format_str: Optional[str] = None,
    last: Optional[int] = None,
    latest: bool = False,
    no_trunc: bool = False,
    quiet: bool = False,
    size: bool = False,
) -> Dict[str, Any]:
    """List containers using Finch.

    Args:
        all_containers (bool, optional): Show all containers (default is True, showing all containers including stopped ones)
        filter_expr (List[str], optional): Filter output based on conditions provided
        format_str (str, optional): Format the output using the given Go template
        last (int, optional): Show n last created containers (includes all states)
        latest (bool, optional): Show the latest created container (includes all states)
        no_trunc (bool, optional): Don't truncate output
        quiet (bool, optional): Only display container IDs
        size (bool, optional): Display total file sizes
    Returns:
        Dict[str, Any]: A dictionary containing:
            - status (str): "success" if the operation succeeded, "error" otherwise
            - message (str): A descriptive message about the result of the operation
            - raw_output (str): Raw JSON output from the command (if successful)

    """
    logger.info('Listing containers')

    # Build the command
    cmd = ['finch', 'container', 'ls']

    if all_containers:
        cmd.append('--all')

    if filter_expr:
        for filter_item in filter_expr:
            cmd.extend(['--filter', filter_item])

    if format_str is None:
        # Default to JSON format for structured data
        format_str = 'json'

    if format_str:
        cmd.extend(['--format', format_str])

    if last is not None:
        cmd.extend(['--last', str(last)])

    if latest:
        cmd.append('--latest')

    if no_trunc:
        cmd.append('--no-trunc')

    if quiet:
        cmd.append('--quiet')

    if size:
        cmd.append('--size')

    try:
        result = execute_command(cmd)
        if result.returncode == 0:
            # Just return the raw output without trying to parse it
            return {
                'status': 'success',
                'message': 'Successfully listed containers',
                'raw_output': result.stdout,
            }
        else:
            return format_result('error', f'Failed to list containers: {result.stderr}')
    except Exception as e:
        return format_result('error', f'Error listing containers: {str(e)}')
