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

"""Version utilities for the Finch MCP server.

This module provides functions to get Finch version information.
"""

from ..consts import STATUS_ERROR, STATUS_SUCCESS
from .common import execute_command, format_result
from loguru import logger
from typing import Any, Dict


def get_version() -> Dict[str, Any]:
    """Get Finch version information.

    Returns:
        Dict[str, Any]: A dictionary containing:
            - status (str): "success" if the operation succeeded, "error" otherwise
            - message (str): A descriptive message about the result
            - version (str): Version information if successful

    """
    try:
        logger.info('Getting Finch version')

        # Execute finch version
        result = execute_command(['finch', 'version'])

        if result.returncode != 0:
            error_msg = f'Failed to get version: {result.stderr}'
            logger.error(error_msg)
            return format_result(STATUS_ERROR, error_msg)

        version_info = result.stdout.strip()

        return {
            'status': STATUS_SUCCESS,
            'message': 'Successfully retrieved Finch version',
            'version': version_info,
        }

    except Exception as e:
        error_msg = f'Error getting version: {str(e)}'
        logger.error(error_msg)
        return format_result(STATUS_ERROR, error_msg)
