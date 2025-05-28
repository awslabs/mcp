"""Common utility functions for the Finch MCP server.

This module provides shared utility functions used across the Finch MCP server,
including command execution and result formatting.

Note: These tools are intended for development and prototyping purposes only
and are not meant for production use cases.
"""

import os
import subprocess
from loguru import logger
from typing import Any, Dict


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

    """
    if env is None:
        env = os.environ.copy()
        env['HOME'] = os.path.expanduser('~')

    # Security check: Only allow finch commands
    if not command or command[0] != 'finch':
        error_msg = f'Security violation: Only finch commands are allowed. Received: {command}'
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
