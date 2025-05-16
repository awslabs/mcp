from typing import Any, Dict
import os
import subprocess
import logging

from ..consts import STATUS_SUCCESS, STATUS_ERROR

logger = logging.getLogger(__name__)

def execute_command(command: list, env=None) -> subprocess.CompletedProcess:
    """
    Execute a command and return the result.
    
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
    
    return subprocess.run(command, capture_output=True, text=True, env=env)

def format_result(status: str, message: str, **kwargs) -> Dict[str, Any]:
    """
    Format a result dictionary with status and message.
    
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
    """
    result = {"status": status, "message": message}
    result.update(kwargs)
    return result
