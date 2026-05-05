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

"""Logging utilities for AWS Billing and Cost Management MCP Server.

This module provides centralized logging configuration using Loguru,
including formatted console output and optional file logging.
"""

import os
import sys
import time
from fastmcp import Context
from loguru import logger
from pathlib import Path
from typing import Any, Dict, Optional


# Default log level - can be overridden with environment variable
DEFAULT_LOG_LEVEL = 'INFO'

# Environment variable names
ENV_LOG_LEVEL = 'FASTMCP_LOG_LEVEL'
ENV_LOG_FILE = 'FASTMCP_LOG_FILE'
ENV_LOG_ROTATION = 'FASTMCP_LOG_ROTATION'
ENV_LOG_RETENTION = 'FASTMCP_LOG_RETENTION'

# Get log level from environment or use default
LOG_LEVEL = os.environ.get(ENV_LOG_LEVEL, DEFAULT_LOG_LEVEL).upper()

# Define log format
LOG_FORMAT = '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>'


def get_server_directory() -> Path:
    """Get the directory for storing server logs.

    Returns:
        Path: Directory for storing logs
    """
    base_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    log_dir = base_dir / 'logs'
    log_dir.mkdir(exist_ok=True)
    return log_dir


def configure_logging() -> None:
    """Configure Loguru logger with standard settings.

    Sets up console logging and optional file logging based on environment variables.
    """
    # Remove default handler
    logger.remove()

    # Add stderr handler with appropriate level
    logger.add(
        sys.stderr,
        format=LOG_FORMAT,
        level=LOG_LEVEL,
        colorize=True,
    )

    # Add file handler if environment variable is set or default to server logs
    log_file = os.environ.get(ENV_LOG_FILE)
    if not log_file:
        log_dir = get_server_directory()
        log_file = log_dir / 'billing-cost-management-mcp-server.log'

    # Configure rotation and retention
    rotation = os.environ.get(ENV_LOG_ROTATION, '10 MB')
    retention = os.environ.get(ENV_LOG_RETENTION, '7 days')

    # Add file sink with rotation
    logger.add(
        str(log_file),
        format=LOG_FORMAT,
        level=LOG_LEVEL,
        rotation=rotation,
        retention=retention,
        compression='zip',
    )


# Configure logging on module import
configure_logging()


def get_logger(name: str):
    """Get a logger instance with the specified name.

    Args:
        name: The name for the logger context, typically __name__

    Returns:
        Configured Loguru logger instance with name context
    """
    return logger.bind(name=name)


class LoggerContextAdapter:
    """Adapter for MCP Context to use Loguru for logging.

    This class enables seamless integration between MCP context-based logging
    and Loguru. It wraps the MCP context methods to also log through Loguru,
    ensuring consistent log formatting and aggregation.
    """

    def __init__(self, ctx: Context, module_name: str):
        """Initialize the adapter with an MCP context and module name.

        Args:
            ctx: The MCP context object
            module_name: The module name for logger context
        """
        self.ctx = ctx
        self.logger = get_logger(module_name)

    async def debug(self, message: str) -> None:
        """Log a debug message to both MCP context and Loguru.

        Args:
            message: The debug message to log
        """
        await self.ctx.debug(message)
        self.logger.debug(message)

    async def info(self, message: str) -> None:
        """Log an info message to both MCP context and Loguru.

        Args:
            message: The info message to log
        """
        await self.ctx.info(message)
        self.logger.info(message)

    async def warning(self, message: str) -> None:
        """Log a warning message to both MCP context and Loguru.

        Args:
            message: The warning message to log
        """
        await self.ctx.warning(message)
        self.logger.warning(message)

    async def error(self, message: str, exc_info: bool = False) -> None:
        """Log an error message to both MCP context and Loguru.

        Args:
            message: The error message to log
            exc_info: Whether to include exception info in the log
        """
        await self.ctx.error(message)
        if exc_info:
            self.logger.exception(message)
        else:
            self.logger.error(message)


def get_context_logger(ctx: Context, module_name: str) -> LoggerContextAdapter:
    """Get a logger adapter that logs to both MCP context and Loguru.

    Args:
        ctx: The MCP context object
        module_name: The module name for logger context

    Returns:
        LoggerContextAdapter instance
    """
    return LoggerContextAdapter(ctx, module_name)


class TimingLogger:
    """Utility class for tracking and logging operation timing.

    This class helps track the timing of operations and log them
    consistently with appropriate context.
    """

    def __init__(self, logger, operation_name: str, context: Optional[Dict[str, Any]] = None):
        """Initialize timing logger.

        Args:
            logger: Logger instance to use (can be regular logger or context adapter)
            operation_name: Name of the operation being timed
            context: Optional context information to include in logs
        """
        self.logger = logger
        self.operation_name = operation_name
        self.context = context or {}
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        """Start timing when entering context."""
        self.start_time = time.time()
        context_str = ' '.join(f'{k}={v}' for k, v in self.context.items())
        self.logger.debug(f'Starting {self.operation_name} {context_str}')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Log timing information when exiting context."""
        self.end_time = time.time()
        if self.start_time is not None:
            duration = round((self.end_time - self.start_time) * 1000, 2)
        else:
            duration = 0.0

        if exc_type:
            self.logger.error(f'{self.operation_name} failed after {duration}ms: {exc_val}')
        else:
            self.logger.debug(f'Completed {self.operation_name} in {duration}ms')

        return False  # Don't suppress exceptions
