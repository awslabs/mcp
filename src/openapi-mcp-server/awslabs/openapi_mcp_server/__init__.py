"""
OpenAPI MCP Server - A server that dynamically creates MCP tools and resources from OpenAPI specifications.
"""

__version__ = '0.1.0'


import sys
import inspect
from loguru import logger

# Remove default loguru handler
logger.remove()

# Set up enhanced logging format to include function name, line number, and logger name
# Fixed the whitespace issue after log level by removing padding
logger.add(
    sys.stdout,
    format='<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>',
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
