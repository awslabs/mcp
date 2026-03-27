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

"""Logging configuration for Amazon Translate MCP Server.

This module provides comprehensive logging setup with correlation IDs,
structured logging, and different log levels for various components.
"""

import logging
import logging.config
import os
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime
from typing import Optional


# Context variable for correlation ID tracking
correlation_id_context: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


class CorrelationIdFilter(logging.Filter):
    """Logging filter that adds correlation ID to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation ID to log record.

        Args:
            record: Log record to modify

        Returns:
            True to allow the record to be processed

        """
        # Get correlation ID from context or record
        correlation_id = getattr(record, 'correlation_id', None)
        if correlation_id is None:
            correlation_id = correlation_id_context.get()
        if correlation_id is None:
            correlation_id = 'no-correlation-id'

        record.correlation_id = correlation_id
        return True


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging."""

    def __init__(self, include_extra: bool = True):
        """Initialize structured formatter.

        Args:
            include_extra: Whether to include extra fields in log output

        """
        super().__init__()
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with structured information.

        Args:
            record: Log record to format

        Returns:
            Formatted log message

        """
        # Base log data
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'correlation_id': getattr(record, 'correlation_id', 'no-correlation-id'),
        }

        # Add exception information if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        # Add extra fields if enabled
        if self.include_extra:
            extra_fields = {}
            for key, value in record.__dict__.items():
                if key not in [
                    'name',
                    'msg',
                    'args',
                    'levelname',
                    'levelno',
                    'pathname',
                    'filename',
                    'module',
                    'lineno',
                    'funcName',
                    'created',
                    'msecs',
                    'relativeCreated',
                    'thread',
                    'threadName',
                    'processName',
                    'process',
                    'getMessage',
                    'exc_info',
                    'exc_text',
                    'stack_info',
                    'correlation_id',
                ]:
                    extra_fields[key] = value

            if extra_fields:
                log_data['extra'] = extra_fields

        # Format as key-value pairs for readability
        formatted_parts = []
        for key, value in log_data.items():
            if key == 'extra' and isinstance(value, dict):
                for extra_key, extra_value in value.items():
                    formatted_parts.append(f'{extra_key}={extra_value}')
            else:
                formatted_parts.append(f'{key}={value}')

        return ' | '.join(formatted_parts)


def setup_logging(
    log_level: Optional[str] = None,
    log_format: str = 'structured',
    enable_correlation_ids: bool = True,
    log_file: Optional[str] = None,
) -> None:
    """Set up logging configuration for the MCP server.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Log format type ('structured', 'simple', 'json')
        enable_correlation_ids: Whether to enable correlation ID tracking
        log_file: Optional file path for log output

    """
    # Get log level from environment or parameter
    if log_level is None:
        log_level = os.getenv('FASTMCP_LOG_LEVEL', 'INFO').upper()

    # Validate log level
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO
        log_level = 'INFO'

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler - use stderr for MCP compatibility
    # MCP servers must reserve stdout for JSON-RPC messages only
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(numeric_level)

    # Create file handler if specified
    file_handler = None
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(numeric_level)
        except (OSError, IOError) as e:
            print(f'Warning: Could not create log file {log_file}: {e}', file=sys.stderr)

    # Set up formatters
    if log_format == 'structured':
        formatter = StructuredFormatter(include_extra=True)
    elif log_format == 'simple':
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(correlation_id)s - %(message)s'
        )
    else:  # Default to structured
        formatter = StructuredFormatter(include_extra=True)

    # Apply formatter to handlers
    console_handler.setFormatter(formatter)
    if file_handler:
        file_handler.setFormatter(formatter)

    # Add correlation ID filter if enabled
    if enable_correlation_ids:
        correlation_filter = CorrelationIdFilter()
        console_handler.addFilter(correlation_filter)
        if file_handler:
            file_handler.addFilter(correlation_filter)

    # Add handlers to root logger
    root_logger.addHandler(console_handler)
    if file_handler:
        root_logger.addHandler(file_handler)

    # Configure specific loggers
    configure_component_loggers(numeric_level)

    # Log configuration
    logger = logging.getLogger(__name__)
    logger.info(
        f'Logging configured: level={log_level}, format={log_format}, correlation_ids={enable_correlation_ids}'
    )


def configure_component_loggers(base_level: int) -> None:
    """Configure logging levels for different components.

    Args:
        base_level: Base logging level for the application

    """
    # AWS SDK logging (reduce verbosity)
    logging.getLogger('boto3').setLevel(max(base_level, logging.WARNING))
    logging.getLogger('botocore').setLevel(max(base_level, logging.WARNING))
    logging.getLogger('urllib3').setLevel(max(base_level, logging.WARNING))

    # FastMCP logging
    logging.getLogger('fastmcp').setLevel(base_level)

    # Application component loggers
    component_loggers = [
        'awslabs.amazon_translate_mcp_server.translation_service',
        'awslabs.amazon_translate_mcp_server.batch_manager',
        'awslabs.amazon_translate_mcp_server.terminology_manager',
        'awslabs.amazon_translate_mcp_server.language_operations',
        'awslabs.amazon_translate_mcp_server.aws_client',
        'awslabs.amazon_translate_mcp_server.retry_handler',
    ]

    for logger_name in component_loggers:
        logging.getLogger(logger_name).setLevel(base_level)


def get_correlation_id() -> str:
    """Get current correlation ID from context or generate a new one.

    Returns:
        Correlation ID string

    """
    correlation_id = correlation_id_context.get()
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())
        correlation_id_context.set(correlation_id)
    return correlation_id


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID in context.

    Args:
        correlation_id: Correlation ID to set

    """
    correlation_id_context.set(correlation_id)


def clear_correlation_id() -> None:
    """Clear correlation ID from context."""
    correlation_id_context.set(None)


def with_correlation_id(correlation_id: Optional[str] = None):
    """Set correlation ID for function execution.

    Args:
        correlation_id: Optional correlation ID, generates new one if None

    Returns:
        Decorated function

    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate correlation ID if not provided
            if correlation_id is None:
                current_id = str(uuid.uuid4())
            else:
                current_id = correlation_id

            # Set correlation ID in context
            token = correlation_id_context.set(current_id)

            try:
                return func(*args, **kwargs)
            finally:
                # Reset correlation ID context
                correlation_id_context.reset(token)

        return wrapper

    return decorator


class LoggerMixin:
    """Mixin class to provide logger with correlation ID support."""

    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        if not hasattr(self, '_logger'):
            self._logger = logging.getLogger(
                f'{self.__class__.__module__}.{self.__class__.__name__}'
            )
        return self._logger

    def log_with_correlation(
        self, level: int, message: str, correlation_id: Optional[str] = None, **kwargs
    ) -> None:
        """Log message with correlation ID.

        Args:
            level: Logging level
            message: Log message
            correlation_id: Optional correlation ID
            **kwargs: Additional log data

        """
        extra = kwargs.copy()
        if correlation_id:
            extra['correlation_id'] = correlation_id

        self.logger.log(level, message, extra=extra)

    def debug(self, message: str, correlation_id: Optional[str] = None, **kwargs) -> None:
        """Log debug message."""
        self.log_with_correlation(logging.DEBUG, message, correlation_id, **kwargs)

    def info(self, message: str, correlation_id: Optional[str] = None, **kwargs) -> None:
        """Log info message."""
        self.log_with_correlation(logging.INFO, message, correlation_id, **kwargs)

    def warning(self, message: str, correlation_id: Optional[str] = None, **kwargs) -> None:
        """Log warning message."""
        self.log_with_correlation(logging.WARNING, message, correlation_id, **kwargs)

    def error(self, message: str, correlation_id: Optional[str] = None, **kwargs) -> None:
        """Log error message."""
        self.log_with_correlation(logging.ERROR, message, correlation_id, **kwargs)

    def critical(self, message: str, correlation_id: Optional[str] = None, **kwargs) -> None:
        """Log critical message."""
        self.log_with_correlation(logging.CRITICAL, message, correlation_id, **kwargs)


# Default logging configuration
DEFAULT_LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'structured': {
            '()': StructuredFormatter,
            'include_extra': True,
        },
        'simple': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(correlation_id)s - %(message)s',
        },
    },
    'filters': {
        'correlation_id': {
            '()': CorrelationIdFilter,
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'structured',
            'filters': ['correlation_id'],
            'stream': 'ext://sys.stdout',
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console'],
    },
    'loggers': {
        'boto3': {
            'level': 'WARNING',
        },
        'botocore': {
            'level': 'WARNING',
        },
        'urllib3': {
            'level': 'WARNING',
        },
    },
}
