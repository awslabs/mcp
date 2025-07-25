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

"""Utility functions for inspecting containers using Finch.

This module provides functions for retrieving detailed information about containers.
It includes validation for container IDs to prevent security issues like command injection.
"""

import json
import logging
import re
from awslabs.finch_mcp_server.consts import SERVER_NAME
from awslabs.finch_mcp_server.utils.common import execute_command, format_result
from awslabs.finch_mcp_server.utils.container_ls import list_containers
from typing import Any, Dict, Optional, Tuple


logger = logging.getLogger(SERVER_NAME)


def validate_container_id(container_id: str) -> Tuple[bool, str]:
    """Validate a container ID to ensure it's safe to use.

    This function performs two levels of validation:
    1. Format validation using regex to prevent command injection
    2. Existence validation by checking if the container exists in the system

    Args:
        container_id (str): The container ID or name to validate

    Returns:
        Tuple[bool, str]: A tuple containing:
            - bool: True if the container ID is valid, False otherwise
            - str: An error message if validation fails, empty string otherwise

    """
    hex_pattern = r'^[0-9a-f]{2,64}$'
    name_pattern = r'^[a-zA-Z0-9][a-zA-Z0-9_\-\.]+$'

    if not (
        re.match(hex_pattern, container_id, re.IGNORECASE) or re.match(name_pattern, container_id)
    ):
        return False, f'Invalid container ID format: {container_id}'

    # Next, check if the container exists
    try:
        result = list_containers(all_containers=True, format_str='json')
        if result['status'] == 'error':
            logger.warning(f'Failed to list containers for validation: {result["message"]}')
            return True, ''

        if 'raw_output' not in result or not result['raw_output']:
            logger.warning('Empty container list returned')
            return False, 'No containers found in the system'

        containers = []
        for line in result['raw_output'].strip().split('\n'):
            if line:
                containers.append(json.loads(line))

        # Check if the container ID matches (or is a prefix of) any existing container
        for container in containers:
            logger.info(f'container: {container}')  # DEBUG: logging container being compared
            # Check ID match (including prefix match for short IDs)
            if 'ID' in container and container['ID'].startswith(container_id):
                return True, ''

            # Check name match
            if 'Names' in container and container_id in container['Names']:
                return True, ''

        return False, f'Container not found: {container_id}'

    except Exception as e:
        logger.error(f'Error validating container ID: {str(e)}')
        # If validation fails due to an error, we'll fail closed to prevent inspecting non-existent containers
        return False, f'Error validating container ID: {str(e)}'


def inspect_container(container_id: str, format_str: Optional[str] = None) -> Dict[str, Any]:
    """Inspect a container to get detailed information.

    This function validates the container ID before executing the inspect command
    to prevent security issues like command injection and operations on non-existent containers.

    Args:
        container_id (str): The ID or name of the container to inspect
        format_str (str, optional): Format the output using the given Go template
    Returns:
        Dict[str, Any]: A dictionary containing:
            - status (str): "success" if the operation succeeded, "error" otherwise
            - message (str): A descriptive message about the result of the operation
            - raw_output (str): Raw JSON output from the inspect command (if successful)

    """
    logger.info(f'Inspecting container: {container_id}')

    # Validate the container ID
    is_valid, error_message = validate_container_id(container_id)
    if not is_valid:
        logger.warning(f'Container ID validation failed: {error_message}')
        return format_result('error', f'Invalid container ID: {error_message}')

    # Build the command
    cmd = ['finch', 'container', 'inspect']

    if format_str:
        cmd.extend(['--format', format_str])
    else:
        # Default to JSON format for structured data
        cmd.extend(['--format', 'json'])

    cmd.append(container_id)

    try:
        result = execute_command(cmd)
        if result.returncode == 0:
            return {
                'status': 'success',
                'message': f'Successfully inspected container {container_id}',
                'raw_output': result.stdout,
            }
        else:
            return format_result('error', f'Failed to inspect container: {result.stderr}')
    except Exception as e:
        return format_result('error', f'Error inspecting container: {str(e)}')
