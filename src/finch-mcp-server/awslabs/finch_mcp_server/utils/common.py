import logging
import os
import subprocess
from typing import Any, Dict


logger = logging.getLogger(__name__)


def execute_command(command: list, env=None) -> subprocess.CompletedProcess:
    """Execute a command and return the result.

    This is a utility function that handles the execution of CLI commands.
    It sets up the proper environment variables (particularly HOME) and captures
    both stdout and stderr output from the command.

    Args:
        command: List of command parts to execute (e.g., ['finch', 'vm', 'status'])
        env: Optional environment variables dictionary. If None, uses a copy of the
             current environment with HOME set to the user's home directory.

    Returns:
        CompletedProcess object with command execution results, containing:
        - returncode: The exit code of the command (0 typically means success)
        - stdout: Standard output as text
        - stderr: Standard error as text

    """
    if env is None:
        env = os.environ.copy()
        env['HOME'] = os.path.expanduser('~')

    result = subprocess.run(command, capture_output=True, text=True, env=env)

    # Log stdout and stderr at debug level if LOG_LEVEL=debug
    if os.environ.get('LOG_LEVEL', '').lower() == 'debug':
        cmd_str = ' '.join(command)
        logger.debug(f'Command executed: {cmd_str}')
        logger.debug(f'Return code: {result.returncode}')
        if result.stdout:
            logger.debug(f'STDOUT: {result.stdout}')
        if result.stderr:
            logger.debug(f'STDERR: {result.stderr}')

    return result


def format_result(status: str, message: str, **kwargs) -> Dict[str, Any]:
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
        **kwargs: Additional key-value pairs to include in the result dictionary

    Returns:
        Dict[str, Any]: A dictionary with 'status', 'message', and any additional keys
                        (excluding stdout and stderr to prevent exposing sensitive information)

    """
    result = {'status': status, 'message': message}

    # Filter out stdout and stderr to prevent exposing sensitive information
    filtered_kwargs = {k: v for k, v in kwargs.items() if k not in ['stdout', 'stderr']}
    result.update(filtered_kwargs)

    return result
