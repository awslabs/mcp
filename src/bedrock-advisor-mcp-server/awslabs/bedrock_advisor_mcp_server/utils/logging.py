"""
Logging utilities for the Bedrock Advisor MCP server.

This module provides a consistent logging interface for the application,
with structured logging support and configurable log levels.
"""

import logging
import sys
from typing import Any, Dict, Optional

import structlog

# Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Configure standard logging
logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=logging.INFO,
)


def get_logger(name: Optional[str] = None) -> structlog.BoundLogger:
    """
    Get a structured logger with the given name.

    Args:
        name: Logger name, typically the module name

    Returns:
        A structured logger instance
    """
    return structlog.get_logger(name)


def set_log_level(level: str) -> None:
    """
    Set the log level for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {level}")

    logging.getLogger().setLevel(numeric_level)


def log_with_context(
    logger: structlog.BoundLogger,
    level: str,
    message: str,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log a message with additional context.

    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        context: Additional context to include in the log
    """
    log_method = getattr(logger, level.lower(), None)
    if log_method is None:
        raise ValueError(f"Invalid log level: {level}")

    if context:
        log_method(message, **context)
    else:
        log_method(message)
