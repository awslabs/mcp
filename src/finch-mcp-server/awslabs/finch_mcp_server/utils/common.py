# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
"""Common utility functions for the Finch MCP server.

This module provides shared utility functions used across the Finch MCP server,
including command execution and result formatting.

Note: These tools are intended for development and prototyping purposes only
and are not meant for production use cases.
"""

import os
import re
import subprocess
import sys
from loguru import logger
from pathlib import Path
from typing import Any, Dict, List


def get_dangerous_patterns() -> List[str]:
    """Get a list of dangerous patterns for command injection detection.

    Returns:
        List of dangerous patterns to check for

    """
    # Dangerous patterns that could indicate command injection attempts
    # Separated by platform for better organization and maintainability
    patterns = [
        '|',
        ';',
        '&',
        '&&',
        '||',  # Command chaining
        '>',
        '>>',
        '<',  # Redirection
        '`',
        '$(',  # Command substitution
        '--',  # Double dash options
        '/bin/',
        '/usr/bin/',  # Path references
        '../',
        './',  # Directory traversal
        # Unix/Linux specific dangerous patterns
        'sudo',  # Privilege escalation
        'chmod',
        'chown',  # File permission changes
        'su',  # Switch user
        'bash',
        'sh',
        'zsh',  # Shell execution
        'curl',
        'wget',  # Network access
        'ssh',
        'scp',  # Remote access
        'eval',  # Command evaluation
        'source',  # Script sourcing
        # Windows specific dangerous patterns
        'cmd',
        'powershell',
        'pwsh',  # Command shells
        'net',  # Network commands
        'reg',  # Registry access
        'runas',  # Privilege escalation
        'del',
        'rmdir',  # File deletion
        'taskkill',  # Process termination
        'sc',  # Service control
        'schtasks',  # Scheduled tasks
        'wmic',  # WMI commands
        '%SYSTEMROOT%',
        '%WINDIR%',  # System directories
        '.bat',
        '.cmd',
        '.ps1',  # Script files
    ]
    return patterns


def execute_command(command: list, env=None) -> subprocess.CompletedProcess:
    """Execute a command and return the result.

    This is a utility function that handles the execution of CLI commands.
    It sets up the proper environment variables (particularly HOME) and captures
    both stdout and stderr output from the command.

    Args:
        command: List of command parts to execute (e.g., ['finch', 'vm', 'status'])
               Note: Currently only 'finch' commands are allowed for security reasons.
        env: Optional environment variables dictionary. If None, uses a copy of the
             current environment with HOME set to the user's home directory.

    Returns:
        CompletedProcess object with command execution results, containing:
        - returncode: The exit code of the command (0 typically means success)
        - stdout: Standard output as text
        - stderr: Standard error as text

    Raises:
        ValueError: If the command is not a finch command (doesn't start with 'finch')
                   or if dangerous patterns are detected in the command

    """
    if env is None:
        env = os.environ.copy()
        path = Path('~')
        home_path = str(Path('~').expanduser())

        if sys.platform == 'win32':
            drive, path = os.path.splitdrive(home_path)
            env['HOMEDRIVE'] = drive
            env['HOMEPATH'] = path
        else:
            env['HOME'] = str(home_path)

    # Security check: Only allow finch commands
    if not command or command[0] != 'finch':
        error_msg = f'Security violation: Only finch commands are allowed. Received: {command}'
        logger.error(error_msg)
        raise ValueError(error_msg)

    dangerous_patterns = get_dangerous_patterns()
    logger.debug(f'Checking for {len(dangerous_patterns)} dangerous patterns')

    for pattern in dangerous_patterns:
        for part in command:
            escaped_pattern = re.escape(pattern)
            regex_pattern = r'^' + escaped_pattern + r'$'

            if re.search(regex_pattern, part):
                error_msg = f'Security violation: Potentially dangerous pattern "{pattern}" detected in command: {part}'
                logger.error(error_msg)
                raise ValueError(error_msg)

    result = subprocess.run(command, capture_output=True, text=True, env=env)
    cmd_str = ' '.join(command)
    logger.debug(f'Command executed: {cmd_str}')
    logger.debug(f'Return code: {result.returncode}')
    if result.stdout:
        logger.debug(f'STDOUT: {result.stdout}')
    if result.stderr:
        logger.debug(f'STDERR: {result.stderr}')

    return result


def format_result(status: str, message: str) -> Dict[str, Any]:
    """Format a result dictionary with status and message.

    This utility function creates a standardized response format used by
    all the MCP tools. It ensures consistent response structure.

    Args:
        status: Status code string. Common values include:
               - "success": Operation completed successfully
               - "error": Operation failed
               - "warn": Operation completed with warnings
               - "info": Informational status
               - "unknown": Status could not be determined
        message: Descriptive message providing details about the result

    Returns:
        Dict[str, Any]: A dictionary with 'status', 'message'

    """
    result = {'status': status, 'message': message}
    return result
